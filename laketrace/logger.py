"""
Core logging implementation using Loguru.

Provides the LakeTraceLogger class with safe local file rotation,
structured JSON output, and optional lakehouse storage integration.

Security Features:
- File permissions: Log files created with 0o600 (owner read/write only)
- Log injection prevention: Newlines and special chars escaped by default
- PII masking: Optional masking of sensitive fields
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
import threading

from loguru import logger as loguru_logger

from laketrace.config import LakeTraceConfig
from laketrace.runtime import RuntimeDetector, get_run_id_from_environment
from laketrace.security import (
    get_secure_file_opener,
    sanitize_message,
    mask_pii,
    SecurityConfig,
)


# Global lock to prevent duplicate handler registration
_logger_lock = threading.Lock()
_initialized_loggers: Dict[str, "LakeTraceLogger"] = {}


class LakeTraceLogger:
    """
    Production-grade logger for Spark data platforms.
    
    This logger is designed to work safely in Fabric and Databricks environments,
    providing local file rotation, structured logging, and optional lakehouse upload.
    
    Key Design Principles:
    - Driver-only logging (not for use in Spark executors)
    - No remote file appends during logging
    - Thread-safe and notebook re-execution safe
    - Bounded retries (no infinite loops)
    - Graceful degradation on failures
    
    Args:
        name: Logger name (typically job or notebook name)
        config: Optional configuration dictionary
        run_id: Optional run identifier for correlation
    
    Example:
        ```python
        logger = LakeTraceLogger("my_etl_job")
        logger.info("Starting ETL process")
        
        # Bind context for structured logging
        stage_logger = logger.bind(stage="extract", source="sales_db")
        stage_logger.info("Extracting data")
        ```
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ):
        """Initialize the logger with configuration."""
        self.name = name
        self.config = LakeTraceConfig(config)
        self.run_id = run_id or get_run_id_from_environment()
        
        # Get runtime metadata once
        self.runtime_metadata = RuntimeDetector.get_runtime_metadata()
        
        # Track bound context
        self._bound_context: Dict[str, Any] = {}

        # Track log file path
        self.log_file_path: Optional[Path] = None
        
        # Initialize loguru logger
        self._logger = loguru_logger.bind(logger_name=name)
        
        # Setup logging sinks
        self._setup_sinks()
    
    def _setup_sinks(self) -> None:
        """
        Setup loguru sinks for file and stdout output.
        
        This method is idempotent - calling it multiple times (e.g., in notebook
        re-executions) will not create duplicate handlers.
        """
        with _logger_lock:
            # Remove existing handlers to prevent duplicates
            self._logger.remove()
            
            # Setup file sink
            self._setup_file_sink()
            
            # Setup stdout sink
            if self.config.stdout:
                self._setup_stdout_sink()
    
    def _setup_file_sink(self) -> None:
        """Configure local file sink with rotation and secure permissions."""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine compression extension
        compression_ext = ""
        if self.config.compression == "zip":
            compression_ext = ".zip"
        elif self.config.compression == "gz":
            compression_ext = ".gz"
        
        # Construct log file path
        log_file = log_dir / f"{self.name}.log"
        self.log_file_path = log_file
        
        # Rotation size in bytes
        rotation_bytes = f"{self.config.rotation_mb} MB"
        
        # Get secure file opener if enabled
        opener = get_secure_file_opener() if self.config.secure_file_permissions else None
        
        # Configure file handler
        self._logger.add(
            str(log_file),
            format=self._format_json if self.config.json else self._format_text,
            level=self.config.level,
            rotation=rotation_bytes,
            retention=self.config.retention_files,
            compression=self.config.compression if self.config.compression != "none" else None,
            enqueue=self.config.enqueue,
            catch=True,  # Don't let logging errors crash the application
            opener=opener,  # Use secure permissions (0o600) if enabled
        )
    
    def _setup_stdout_sink(self) -> None:
        """Configure stdout sink for job output visibility."""
        self._logger.add(
            sys.stdout,
            format=self._format_json if self.config.json else self._format_text,
            level=self.config.level,
            enqueue=self.config.enqueue,
            catch=True,
            colorize=not self.config.json,  # Only colorize for text format
        )
    
    def _format_json(self, record: Dict[str, Any]) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Loguru record dictionary
        
        Returns:
            JSON string with newline
        """
        # Build structured log entry
        log_entry = {
            "timestamp": record["time"].astimezone(timezone.utc).isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "logger_name": self.name,
        }
        
        # Add runtime context if enabled
        if self.config.add_runtime_context:
            log_entry["hostname"] = self.runtime_metadata.get("hostname", "unknown")
            log_entry["pid"] = self.runtime_metadata.get("pid", 0)
            log_entry["platform"] = self.runtime_metadata.get("platform", "unknown")
            log_entry["runtime_type"] = self.runtime_metadata.get("platform", "unknown")
        
        # Add run_id if available
        if self.run_id:
            log_entry["run_id"] = self.run_id
        
        # Add bound context
        if self._bound_context:
            log_entry.update(self._bound_context)
        
        # Add extra fields from record
        if record.get("extra"):
            for key, value in record["extra"].items():
                if key not in log_entry and key != "logger_name":
                    log_entry[key] = value
        
        # Add exception info if present
        if record.get("exception"):
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
            }
        
        return json.dumps(log_entry) + "\n"
    
    def _format_text(self, record: Dict[str, Any]) -> str:
        """
        Format log record as human-readable text.
        
        Args:
            record: Loguru record dictionary
        
        Returns:
            Formatted text string with newline
        """
        timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S")
        level = record["level"].name
        message = record["message"]
        
        # Build context string
        context_parts = []
        if self.run_id:
            context_parts.append(f"run_id={self.run_id}")
        
        for key, value in self._bound_context.items():
            context_parts.append(f"{key}={value}")
        
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        return f"{timestamp} | {level:8} | {self.name}{context_str} | {message}\n"
    
    def bind(self, **kwargs: Any) -> "LakeTraceLogger":
        """
        Create a new logger with bound context fields.
        
        Bound fields will be included in all subsequent log records from
        the returned logger.
        
        Args:
            **kwargs: Key-value pairs to bind to the logger
        
        Returns:
            New LakeTraceLogger instance with bound context
        
        Example:
            ```python
            base_logger = get_laketrace_logger("etl")
            stage_logger = base_logger.bind(stage="extract", dataset="sales")
            stage_logger.info("Processing")  # Will include stage and dataset fields
            ```
        """
        bound_logger = object.__new__(LakeTraceLogger)
        bound_logger.name = self.name
        bound_logger.config = self.config
        bound_logger.run_id = self.run_id
        bound_logger.runtime_metadata = self.runtime_metadata
        bound_logger.log_file_path = self.log_file_path
        bound_logger._bound_context = {**self._bound_context, **kwargs}
        bound_logger._logger = self._logger.bind(**kwargs)

        return bound_logger
    
    def trace(self, message: str, **kwargs: Any) -> None:
        """Log trace-level message."""
        self._logger.trace(message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug-level message."""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        self._logger.info(message, **kwargs)
    
    def success(self, message: str, **kwargs: Any) -> None:
        """Log success-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        self._logger.success(message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical-level message."""
        self._logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        self._logger.exception(message, **kwargs)
    
    def log_structured(
        self,
        message: str,
        level: str = "INFO",
        data: Optional[Dict[str, Any]] = None,
        mask_sensitive: bool = True,
    ) -> None:
        """
        Log a message with structured data, with optional PII masking.

        This is useful when logging dictionaries or structured data that may
        contain sensitive information.

        Args:
            message: Primary log message
            level: Log level (default: INFO)
            data: Dictionary of structured data to include
            mask_sensitive: Whether to mask PII in the data (default: True)

        Example:
            ```python
            logger.log_structured(
                "User login",
                level="INFO",
                data={"user": "john@example.com", "ip": "192.168.1.1"},
                mask_sensitive=True
            )
            ```
        """
        if self.config.sanitize_messages:
            message = sanitize_message(message)

        # Mask PII if enabled
        if data and (self.config.mask_pii or mask_sensitive):
            data = mask_pii(data)

        # Log with data as extra fields
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        if data:
            log_method(message, extra=data)
        else:
            log_method(message)
    
    def tail(self, n: int = 50) -> None:
        """
        Print the last N lines from the log file.
        
        Useful for debugging in notebook environments.
        
        Args:
            n: Number of lines to display (default: 50)
        """
        if not self.log_file_path or not self.log_file_path.exists():
            print(f"Log file not found: {self.log_file_path}")
            return
        
        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                tail_lines = lines[-n:] if len(lines) > n else lines
                
                print(f"=== Last {len(tail_lines)} lines from {self.log_file_path.name} ===")
                for line in tail_lines:
                    print(line.rstrip())
                print("=" * 70)
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    def upload_log_to_lakehouse(
        self,
        target_path: str,
        max_retries: int = 2,
    ) -> bool:
        """
        Upload log file to lakehouse storage at end of run.
        
        This method performs a single-shot upload using platform-specific utilities.
        It will NOT perform remote appends or chunk-based uploads.
        
        Args:
            target_path: Target path in lakehouse (e.g., "Files/logs/my_job.log")
            max_retries: Maximum number of retry attempts (default: 2)
        
        Returns:
            True if upload succeeded, False otherwise
        
        Behavior:
            - Fabric: Uses notebookutils.fs.put with overwrite=True
            - Databricks: Uses dbutils.fs.put with overwrite=True
            - Other: Logs warning and skips upload
            
        Note:
            Failures are logged but do NOT raise exceptions to prevent
            job failures due to logging issues.
        
        Example:
            ```python
            logger = get_laketrace_logger("my_job")
            # ... do work ...
            logger.upload_log_to_lakehouse("Files/logs/job_2024_01_15.log")
            ```
        """
        if not self.log_file_path or not self.log_file_path.exists():
            self.warning(f"Cannot upload: log file not found at {self.log_file_path}")
            return False
        
        platform = self.runtime_metadata.get("platform", "unknown")
        
        try:
            # Read log file content once
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                log_content = f.read()
            
            if not log_content:
                self.warning("Log file is empty, skipping upload")
                return False
            
            # Attempt upload based on platform
            if platform == "fabric":
                return self._upload_fabric(target_path, log_content, max_retries)
            elif platform == "databricks":
                return self._upload_databricks(target_path, log_content, max_retries)
            else:
                self.warning(
                    f"Lakehouse upload not supported for platform '{platform}'. "
                    f"Log file remains at: {self.log_file_path}"
                )
                return False
        
        except Exception as e:
            self.error(f"Unexpected error during log upload: {e}")
            return False
    
    def _upload_fabric(
        self,
        target_path: str,
        content: str,
        max_retries: int,
    ) -> bool:
        """Upload log to Fabric lakehouse using notebookutils."""
        try:
            import notebookutils  # type: ignore
        except ImportError:
            self.warning("notebookutils not available in Fabric environment")
            return False
        
        for attempt in range(max_retries + 1):
            try:
                # Use fs.put with overwrite - single operation
                notebookutils.fs.put(target_path, content, overwrite=True)
                self.info(f"Successfully uploaded log to Fabric: {target_path}")
                return True
            
            except Exception as e:
                if attempt < max_retries:
                    self.warning(
                        f"Fabric upload attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                    )
                else:
                    self.error(f"Failed to upload log to Fabric after {max_retries + 1} attempts: {e}")
                    return False
        
        return False
    
    def _upload_databricks(
        self,
        target_path: str,
        content: str,
        max_retries: int,
    ) -> bool:
        """Upload log to Databricks DBFS using dbutils."""
        try:
            # Import dbutils in Databricks context
            from pyspark.dbutils import DBUtils  # type: ignore
            from pyspark.sql import SparkSession
            
            spark = SparkSession.getActiveSession()
            if not spark:
                self.warning("No active Spark session for Databricks upload")
                return False
            
            dbutils = DBUtils(spark)
        
        except ImportError:
            self.warning("dbutils not available in Databricks environment")
            return False
        
        for attempt in range(max_retries + 1):
            try:
                # Ensure target path has dbfs:/ prefix if not present
                dbfs_path = target_path if target_path.startswith("dbfs:/") else f"dbfs:/{target_path}"
                
                # Use dbutils.fs.put with overwrite - single operation
                dbutils.fs.put(dbfs_path, content, overwrite=True)
                self.info(f"Successfully uploaded log to Databricks: {dbfs_path}")
                return True
            
            except Exception as e:
                if attempt < max_retries:
                    self.warning(
                        f"Databricks upload attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                    )
                else:
                    self.error(
                        f"Failed to upload log to Databricks after {max_retries + 1} attempts: {e}"
                    )
                    return False
        
        return False


def get_laketrace_logger(
    name: str,
    config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> LakeTraceLogger:
    """
    Get or create a LakeTrace logger instance.
    
    This is the primary factory function for creating loggers. It ensures that
    only one logger instance exists per name to prevent duplicate handlers.
    
    Args:
        name: Logger name (typically job or notebook name)
        config: Optional configuration dictionary
        run_id: Optional run identifier for correlation
    
    Returns:
        LakeTraceLogger instance
    
    Example:
        ```python
        from laketrace import get_laketrace_logger
        
        # Basic usage
        logger = get_laketrace_logger("my_job")
        logger.info("Processing started")
        
        # With custom configuration
        logger = get_laketrace_logger(
            "my_job",
            config={
                "log_dir": "/custom/log/path",
                "rotation_mb": 20,
                "level": "DEBUG",
            }
        )
        ```
    """
    with _logger_lock:
        # Return existing logger if already initialized
        if name in _initialized_loggers:
            return _initialized_loggers[name]
        
        # Create new logger
        logger_instance = LakeTraceLogger(name=name, config=config, run_id=run_id)
        _initialized_loggers[name] = logger_instance
        
        return logger_instance
