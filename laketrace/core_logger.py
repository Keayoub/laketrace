"""
LakeTrace Core Logger - Production-grade logging

This is standalone logging implementation built for enterprise use.
Designed specifically for Microsoft Fabric and Databricks environments.

Key features:
- File rotation (size and time-based)
- Multiple sinks (file, stdout, custom)
- Structured JSON output
- Context binding
- Thread-safe
- Exception formatting
- No external dependencies
"""

import atexit
import glob
import os
import queue
import sys
import json
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List, Union
from enum import Enum

from laketrace.rotation import make_rotation_function
from laketrace.retention import make_retention_function
from laketrace.compression import make_compression_function


class LogLevel(Enum):
    """Log level enumeration."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogRecord:
    """Represents a single log record."""
    
    def __init__(
        self,
        level: LogLevel,
        message: str,
        logger_name: str,
        timestamp: datetime,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
    ):
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.timestamp = timestamp
        self.extra = extra or {}
        self.exception = exception
        self.thread_id = threading.get_ident()
        self.process_id = os.getpid()
        self.hostname = os.getenv("HOSTNAME", "unknown")


class Handler:
    """Base handler for log records."""

    def __init__(
        self,
        formatter: Optional[Callable[[LogRecord], str]] = None,
        filter_func: Optional[Callable[[LogRecord], bool]] = None,
        enqueue: bool = False,
        catch: bool = True,
    ):
        self.formatter = formatter
        self.filter_func = filter_func
        self.enqueue = enqueue
        self.catch = catch
        self._lock = threading.Lock()
        self._queue: Optional[queue.Queue] = None
        self._thread: Optional[threading.Thread] = None

        if self.enqueue:
            self._queue = queue.Queue()
            self._thread = threading.Thread(target=self._queued_writer, daemon=True)
            self._thread.start()

    def _should_log(self, record: LogRecord) -> bool:
        if self.filter_func is None:
            return True
        try:
            return bool(self.filter_func(record))
        except Exception:
            return False

    def emit(self, record: LogRecord) -> None:
        """Emit a log record."""
        if not self._should_log(record):
            return

        if self.enqueue and self._queue is not None:
            self._queue.put(record)
            return

        self._emit(record)

    def _emit(self, record: LogRecord) -> None:
        """Emit a log record directly (no queue)."""
        raise NotImplementedError

    def _queued_writer(self) -> None:
        if self._queue is None:
            return
        while True:
            record = self._queue.get()
            if record is None:
                break
            try:
                self._emit(record)
            except Exception as e:
                if self.catch:
                    print(f"Error in handler: {e}", file=sys.stderr)
                else:
                    raise

    def close(self) -> None:
        """Close the handler and release resources."""
        if self._queue is not None:
            self._queue.put(None)
            if self._thread:
                self._thread.join(timeout=2)


class FileHandler(Handler):
    """Handler that writes logs to a file with rotation, retention, and compression."""

    def __init__(
        self,
        filename: str,
        rotation: Optional[Any] = None,
        retention: Optional[Any] = None,
        compression: Optional[Any] = None,
        encoding: str = "utf-8",
        formatter: Optional[Callable[[LogRecord], str]] = None,
        filter_func: Optional[Callable[[LogRecord], bool]] = None,
        enqueue: bool = False,
        catch: bool = True,
        secure_permissions: bool = True,
    ):
        self.filename = Path(filename)
        self.encoding = encoding
        self.secure_permissions = secure_permissions
        self.file = None
        self._rotation_function = make_rotation_function(rotation)
        self._retention_function = make_retention_function(retention)
        self._compression_function = make_compression_function(compression)

        super().__init__(
            formatter=formatter or self._default_format,
            filter_func=filter_func,
            enqueue=enqueue,
            catch=catch,
        )

        self._ensure_dir()
        self._open_file()

    def _ensure_dir(self) -> None:
        """Ensure parent directory exists."""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def _open_file(self) -> None:
        """Open log file with secure permissions."""
        try:
            if self.secure_permissions:
                fd = os.open(
                    str(self.filename),
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o600,
                )
                self.file = os.fdopen(fd, "a", encoding=self.encoding)
            else:
                self.file = open(str(self.filename), "a", encoding=self.encoding)
        except Exception as e:
            print(f"Error opening log file: {e}", file=sys.stderr)

    def _collect_logs(self) -> List[str]:
        pattern = f"{self.filename}*"
        return [p for p in glob.glob(pattern) if os.path.isfile(p)]

    def _rotate_if_needed(self, formatted: str) -> None:
        if not self._rotation_function or not self.file:
            return

        try:
            if self._rotation_function(formatted, self.file):
                self._do_rotation()
        except Exception as e:
            if self.catch:
                print(f"Error checking rotation: {e}", file=sys.stderr)
            else:
                raise

    def _do_rotation(self) -> None:
        try:
            if self.file:
                self.file.close()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.filename}.{timestamp}"
            if self.filename.exists():
                self.filename.rename(backup_name)

            if self._compression_function is not None:
                self._compression_function(str(backup_name))

            if self._retention_function is not None:
                self._retention_function(self._collect_logs())

            self._open_file()
        except Exception as e:
            if self.catch:
                print(f"Error rotating log file: {e}", file=sys.stderr)
            else:
                raise

    def _default_format(self, record: LogRecord) -> str:
        """Default text format."""
        timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"{timestamp} | {record.level.name:8} | {record.logger_name} | {record.message}\n"

    def _emit(self, record: LogRecord) -> None:
        with self._lock:
            try:
                formatted = self.formatter(record) if self.formatter else self._default_format(record)
                self._rotate_if_needed(formatted)
                if self.file:
                    self.file.write(formatted)
                    self.file.flush()
            except Exception as e:
                if self.catch:
                    print(f"Error writing log: {e}", file=sys.stderr)
                else:
                    raise

    def close(self) -> None:
        super().close()
        with self._lock:
            if self.file:
                try:
                    self.file.close()
                except Exception:
                    pass
        if self._compression_function is not None and self.filename.exists():
            try:
                self._compression_function(str(self.filename))
            except Exception:
                pass


class StreamHandler(Handler):
    """Handler that writes logs to a stream (e.g., stdout)."""

    def __init__(
        self,
        stream: Any = sys.stdout,
        formatter: Optional[Callable[[LogRecord], str]] = None,
        filter_func: Optional[Callable[[LogRecord], bool]] = None,
        enqueue: bool = False,
        catch: bool = True,
    ):
        self.stream = stream
        super().__init__(
            formatter=formatter or self._default_format,
            filter_func=filter_func,
            enqueue=enqueue,
            catch=catch,
        )

    def _default_format(self, record: LogRecord) -> str:
        """Default text format."""
        timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"{timestamp} | {record.level.name:8} | {record.logger_name} | {record.message}\n"

    def _emit(self, record: LogRecord) -> None:
        with self._lock:
            try:
                formatted = self.formatter(record) if self.formatter else self._default_format(record)
                self.stream.write(formatted)
                self.stream.flush()
            except Exception as e:
                if self.catch:
                    print(f"Error writing to stream: {e}", file=sys.stderr)
                else:
                    raise


class JSONFormatter:
    """Format log records as JSON."""
    
    def __init__(self, include_extra: bool = True, include_exception: bool = True):
        self.include_extra = include_extra
        self.include_exception = include_exception
    
    def format(self, record: LogRecord) -> str:
        """Format record as JSON."""
        entry = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "logger_name": record.logger_name,
            "thread_id": record.thread_id,
            "process_id": record.process_id,
            "hostname": record.hostname,
        }
        
        if self.include_extra and record.extra:
            entry.update(record.extra)
        
        if self.include_exception and record.exception:
            entry["exception"] = {
                "type": record.exception.__class__.__name__,
                "value": str(record.exception),
                "traceback": traceback.format_exc(),
            }
        
        return json.dumps(entry) + "\n"


class TextFormatter:
    """Format log records as plain text."""
    
    def __init__(self, format_string: str = "{timestamp} | {level:8} | {logger_name} | {message}"):
        self.format_string = format_string
    
    def format(self, record: LogRecord) -> str:
        """Format record as text."""
        timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        context_parts = []
        for key, value in record.extra.items():
            context_parts.append(f"{key}={value}")
        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""
        
        formatted = self.format_string.format(
            timestamp=timestamp,
            level=record.level.name,
            logger_name=record.logger_name,
            message=record.message + context_str,
        )
        
        if record.exception:
            formatted += "\n" + traceback.format_exc()
        
        return formatted + "\n"


class _CoreLogger:
    """
    Production-grade logger engine without external dependencies.
    
    Internal implementation - use via Logger public API.
    """
    
    _instances: Dict[str, "_CoreLogger"] = {}
    _instances_lock = threading.Lock()
    _atexit_registered = False
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: Dict[int, Handler] = {}
        self._handler_id = 0
        self._context: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._min_level = LogLevel.INFO
    
    @classmethod
    def get_logger(cls, name: str) -> "_CoreLogger":
        """Get or create logger instance."""
        with cls._instances_lock:
            if name not in cls._instances:
                cls._instances[name] = cls(name)
                if not cls._atexit_registered:
                    atexit.register(cls.shutdown_all)
                    cls._atexit_registered = True
            return cls._instances[name]
    
    def add_handler(self, handler: Handler) -> int:
        """Add a handler to the logger."""
        with self._lock:
            handler_id = self._handler_id
            self._handler_id += 1
            self.handlers[handler_id] = handler
            return handler_id

    def remove_handler(self, handler_id: int) -> None:
        """Remove a handler by id."""
        with self._lock:
            handler = self.handlers.pop(handler_id, None)
            if handler and hasattr(handler, "close"):
                handler.close()
    
    def remove_handlers(self) -> None:
        """Remove all handlers."""
        with self._lock:
            for handler in self.handlers.values():
                if hasattr(handler, "close"):
                    handler.close()
            self.handlers.clear()
    
    def set_level(self, level: Union[str, LogLevel]) -> None:
        """Set minimum log level."""
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        self._min_level = level
    
    def bind(self, **context: Any) -> "BoundLogger":
        """Create a bound logger with context."""
        return BoundLogger(self, context)
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        exception: Optional[BaseException] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal logging method."""
        if level.value < self._min_level.value:
            return
        
        record = LogRecord(
            level=level,
            message=message,
            logger_name=self.name,
            timestamp=datetime.now(timezone.utc),
            extra={**self._context, **(extra or {})},
            exception=exception,
        )
        
        with self._lock:
            for handler in self.handlers.values():
                handler.emit(record)

    @classmethod
    def shutdown_all(cls) -> None:
        """Shutdown all logger instances and close handlers."""
        with cls._instances_lock:
            for logger in cls._instances.values():
                try:
                    logger.remove_handlers()
                except Exception:
                    pass
            cls._instances.clear()
    
    def trace(self, message: str, **extra: Any) -> None:
        """Log at TRACE level."""
        self._log(LogLevel.TRACE, message, extra=extra or None)
    
    def debug(self, message: str, **extra: Any) -> None:
        """Log at DEBUG level."""
        self._log(LogLevel.DEBUG, message, extra=extra or None)
    
    def info(self, message: str, **extra: Any) -> None:
        """Log at INFO level."""
        self._log(LogLevel.INFO, message, extra=extra or None)
    
    def success(self, message: str, **extra: Any) -> None:
        """Log at SUCCESS level."""
        self._log(LogLevel.SUCCESS, message, extra=extra or None)
    
    def warning(self, message: str, **extra: Any) -> None:
        """Log at WARNING level."""
        self._log(LogLevel.WARNING, message, extra=extra or None)
    
    def error(self, message: str, **extra: Any) -> None:
        """Log at ERROR level."""
        self._log(LogLevel.ERROR, message, extra=extra or None)
    
    def critical(self, message: str, **extra: Any) -> None:
        """Log at CRITICAL level."""
        self._log(LogLevel.CRITICAL, message, extra=extra or None)
    
    def exception(self, message: str, **extra: Any) -> None:
        """Log exception with traceback."""
        try:
            raise
        except Exception as e:
            self._log(LogLevel.ERROR, message, exception=e, extra=extra or None)


class BoundLogger:
    """Logger with bound context."""
    
    def __init__(self, logger: _CoreLogger, context: Dict[str, Any]):
        self._logger = logger
        self._context = context
    
    def bind(self, **context: Any) -> "BoundLogger":
        """Create new bound logger with additional context."""
        return BoundLogger(self._logger, {**self._context, **context})
    
    def trace(self, message: str, **extra: Any) -> None:
        """Log at TRACE level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.TRACE, message, extra=combined or None)
    
    def debug(self, message: str, **extra: Any) -> None:
        """Log at DEBUG level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.DEBUG, message, extra=combined or None)
    
    def info(self, message: str, **extra: Any) -> None:
        """Log at INFO level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.INFO, message, extra=combined or None)
    
    def success(self, message: str, **extra: Any) -> None:
        """Log at SUCCESS level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.SUCCESS, message, extra=combined or None)
    
    def warning(self, message: str, **extra: Any) -> None:
        """Log at WARNING level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.WARNING, message, extra=combined or None)
    
    def error(self, message: str, **extra: Any) -> None:
        """Log at ERROR level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.ERROR, message, extra=combined or None)
    
    def critical(self, message: str, **extra: Any) -> None:
        """Log at CRITICAL level."""
        combined = {**self._context, **extra}
        self._logger._log(LogLevel.CRITICAL, message, extra=combined or None)
    
    def exception(self, message: str, **extra: Any) -> None:
        """Log exception with traceback."""
        try:
            raise
        except Exception as e:
            combined = {**self._context, **extra}
            self._logger._log(LogLevel.ERROR, message, exception=e, extra=combined or None)
