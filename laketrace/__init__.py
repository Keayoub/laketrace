"""
LakeTrace Logger - Production-grade logging for Spark data platforms.

A cross-platform Python logging module designed for Microsoft Fabric and Databricks
that provides safe local logging with optional lakehouse storage integration.

Zero external dependencies - uses only Python stdlib.

Key Features:
- Works identically in Fabric Notebooks, Fabric Spark Jobs, and Databricks
- Vendored logging engine (no Loguru dependency)
- Safe local file rotation with size-based limits
- Structured JSON output with runtime context
- Stdout emission for job output visibility
- Optional end-of-run lakehouse upload
- Spark-safe (driver-only pattern)
- Thread-safe and notebook re-execution safe

Example Usage:
    ```python
    from laketrace import get_laketrace_logger
    
    logger = get_laketrace_logger("my_job")
    logger.info("Starting data processing")
    
    # Bind context
    bound = logger.bind(stage="extract", dataset="sales")
    bound.info("Processing sales data")
    
    # At end of job, optionally upload to lakehouse
    logger.upload_log_to_lakehouse("Files/logs/my_job.log")
    ```
"""

from laketrace.logger import LakeTraceLogger, get_laketrace_logger
from laketrace.runtime import detect_runtime, stop_spark_if_active
from laketrace.security import (
    sanitize_message,
    mask_pii,
    escape_newlines,
    escape_format_strings,
)

__version__ = "1.0.0"
__all__ = [
    # Core API
    "LakeTraceLogger",
    "get_laketrace_logger",
    # Runtime utilities
    "detect_runtime",
    "stop_spark_if_active",
    # Security utilities
    "sanitize_message",
    "mask_pii",
    "escape_newlines",
    "escape_format_strings",
]

