"""
LakeTrace Logger - Enterprise-grade logging for Fabric & Databricks.

Vendored, zero-dependency implementation (stdlib only).
Designed for security, performance, and multi-platform compatibility.

Security Features:
- File permissions: Log files created with 0o600 (owner read/write only)
- Log injection prevention: Newlines and special chars escaped
- PII masking: Optional masking of sensitive fields
- No network I/O during logging (upload only at end-of-run)
- Bounded retries only on lakehouse upload
"""

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from laketrace.core_logger import (
    _CoreLogger,
    FileHandler,
    StreamHandler,
    JSONFormatter,
    TextFormatter,
    LogLevel,
    BoundLogger,
)
from laketrace.runtime import detect_runtime
from laketrace.config import LakeTraceConfig
from laketrace.security import sanitize_message, mask_pii


# Global lock to prevent duplicate handler registration
_logger_lock = threading.Lock()
_initialized_loggers: Dict[str, "Logger"] = {}


class Logger:
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
        log = logger("my_etl_job")
        log.info("Starting ETL process")
        
        # Bind context for structured logging
        stage_log = log.bind(stage="extract", source="sales_db")
        stage_log.info("Extracting data")
        ```
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ):
        """Initialize the logger with configuration."""
        print(f"[DEBUG] Logger.__init__ called for: {name}")
        self.name = name
        print(f"[DEBUG] Creating config...")
        self.config = LakeTraceConfig(config or {})
        print(f"[DEBUG] Config created, level={self.config.level}")
        self.run_id = run_id or os.getenv("LAKEHOUSE_CONTEXT_RUN_ID", "")
        
        # Get runtime metadata once
        print(f"[DEBUG] Detecting runtime...")
        self.runtime_metadata = detect_runtime()
        print(f"[DEBUG] Runtime detected: {self.runtime_metadata.platform.value}")
        
        # Track bound context
        self._bound_context: Dict[str, Any] = {}
        self._bound_context["platform"] = self.runtime_metadata.platform.value
        self._bound_context["runtime_type"] = self.runtime_metadata.runtime_type.value
        
        if self.run_id:
            self._bound_context["run_id"] = self.run_id
        
        # Track log file path
        self.log_file_path: Optional[Path] = None
        
        # Get core logger instance
        print(f"[DEBUG] Getting core logger...")
        self._logger = _CoreLogger.get_logger(name)
        print(f"[DEBUG] Setting level to {self.config.level}...")
        self._logger.set_level(self.config.level)
        
        # Reset handlers on notebook re-execution
        print(f"[DEBUG] Removing old handlers...")
        self._logger.remove_handlers()
        
        # Setup logging sinks
        print(f"[DEBUG] Setting up sinks...")
        self._setup_sinks()
        print(f"[DEBUG] Logger initialization complete!")
    
    def _setup_sinks(self) -> None:
        """Setup logging sinks for file and stdout output."""
        # Note: Already protected by _logger_lock in get_logger()
        # Setup file sink
        if self.config.log_dir:
            self._setup_file_sink()
        
        # Setup stdout sink
        if self.config.stdout:
            self._setup_stdout_sink()
    
    def _setup_file_sink(self) -> None:
        """Configure local file sink with rotation and secure permissions."""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct log file path
        log_file = log_dir / f"{self.name}.log"
        self.log_file_path = log_file
        
        # Determine formatter
        formatter = self._resolve_formatter(is_json=self.config.json)

        # Rotation configuration
        rotation = self.config.rotation
        if rotation is None and self.config.rotation_mb:
            rotation = int(self.config.rotation_mb * 1024 * 1024)

        # Retention configuration
        retention = self.config.retention
        if retention is None:
            retention = self.config.retention_files

        # Compression configuration
        compression = self.config.compression if self.config.compression != "none" else None

        file_handler = FileHandler(
            str(log_file),
            rotation=rotation,
            retention=retention,
            compression=compression,
            formatter=formatter,
            filter_func=self.config.filter,
            enqueue=self.config.enqueue,
            catch=self.config.catch,
            secure_permissions=self.config.secure_file_permissions,
        )

        self._logger.add_handler(file_handler)
    
    def _setup_stdout_sink(self) -> None:
        """Configure stdout sink for job output visibility."""
        formatter = self._resolve_formatter(is_json=self.config.json)

        stream_handler = StreamHandler(
            sys.stdout,
            formatter=formatter,
            filter_func=self.config.filter,
            enqueue=self.config.enqueue,
            catch=self.config.catch,
        )
        self._logger.add_handler(stream_handler)

    def _resolve_formatter(self, is_json: bool) -> Any:
        if callable(self.config.formatter):
            return self.config.formatter

        if not is_json and self.config.format:
            return TextFormatter(self.config.format).format

        if is_json:
            return lambda record: self._format_json(record)

        return lambda record: self._format_text(record)
    
    def _format_json(self, record) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "logger_name": self.name,
            "hostname": record.hostname,
            "pid": record.process_id,
        }

        # Add all context fields
        log_entry.update(record.extra)

        if self.config.serialize:
            log_entry.update(
                {
                    "thread_id": record.thread_id,
                    "process_id": record.process_id,
                }
            )

        if record.exception:
            import traceback
            log_entry["exception"] = {
                "type": record.exception.__class__.__name__,
                "value": str(record.exception),
                "traceback": "".join(traceback.format_exception(type(record.exception), record.exception, record.exception.__traceback__)),
            }

        return json.dumps(log_entry) + "\n"
    
    def _format_text(self, record) -> str:
        """Format log record as human-readable text."""
        timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level = record.level.name
        message = record.message
        
        # Build context string
        context_parts = []
        for key, value in self._bound_context.items():
            context_parts.append(f"{key}={value}")
        
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        return f"{timestamp} | {level:8} | {self.name}{context_str} | {message}\n"
    
    def bind(self, **kwargs: Any) -> "BoundLogger":
        """
        Create a new logger with bound context fields.
        
        Bound fields will be included in all subsequent log records from
        the returned logger.
        
        Args:
            **kwargs: Key-value pairs to bind to the logger
        
        Returns:
            Logger instance with bound context
        
        Example:
            ```python
            base_log = logger("etl")
            stage_log = base_log.bind(stage="extract", dataset="sales")
            stage_log.info("Processing")  # Will include stage and dataset fields
            ```
        """
        return BoundLogger(self._logger, {**self._bound_context, **kwargs})
    
    def trace(self, message: str, **kwargs: Any) -> None:
        """Log trace-level message."""
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.TRACE, message, extra=extra or None)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug-level message."""
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.DEBUG, message, extra=extra or None)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.INFO, message, extra=extra or None)
    
    def success(self, message: str, **kwargs: Any) -> None:
        """Log success-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.SUCCESS, message, extra=extra or None)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.WARNING, message, extra=extra or None)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error-level message."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.ERROR, message, extra=extra or None)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical-level message."""
        extra = {**self._bound_context, **kwargs}
        self._logger._log(LogLevel.CRITICAL, message, extra=extra or None)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        if self.config.sanitize_messages:
            message = sanitize_message(message)
        extra = {**self._bound_context, **kwargs}
        try:
            raise
        except Exception as e:
            self._logger._log(LogLevel.ERROR, message, exception=e, extra=extra or None)
    
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
        level_obj = LogLevel[level.upper()]
        combined_extra = {**self._bound_context}
        if data:
            combined_extra.update(data)
        
        self._logger._log(level_obj, message, extra=combined_extra or None)
    
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

    def close(self) -> None:
        """Close all handlers and release resources."""
        try:
            self._logger.remove_handlers()
        finally:
            with _logger_lock:
                if self.name in _initialized_loggers:
                    _initialized_loggers.pop(self.name, None)
    
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
        
        platform = self.runtime_metadata.platform.value
        
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



def get_logger(
    name: str,
    config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> Logger:
    """
    Get or create a logger instance.
    
    This is the primary factory function for creating loggers. It ensures that
    only one logger instance exists per name to prevent duplicate handlers.
    
    Args:
        name: Logger name (typically job or notebook name)
        config: Optional configuration dictionary
        run_id: Optional run identifier for correlation
    
    Returns:
        Logger instance
    
    Example:
        ```python
        from laketrace import get_logger
        
        # Basic usage
        log = get_logger("my_job")
        log.info("Processing started")
        
        # With custom configuration
        log = get_logger(
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
        logger_instance = Logger(name=name, config=config, run_id=run_id)
        _initialized_loggers[name] = logger_instance
        
        return logger_instance


# Alias for convenience (can be used with 'as' to avoid conflicts)
create_logger = get_logger
