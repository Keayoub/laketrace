"""
LakeTrace Logger - Production-grade logging for Spark data platforms.

A cross-platform Python logging module designed for Microsoft Fabric and Databricks
that provides safe local logging with optional lakehouse storage integration.

Key Features:
- Works identically in Fabric Notebooks, Fabric Spark Jobs, and Databricks
- Uses Loguru for powerful logging capabilities
- Safe local file rotation (no remote append during logging)
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
from laketrace.runtime import RuntimeDetector, stop_spark_if_active
from laketrace.security import (
    SecurityConfig,
    sanitize_message,
    mask_pii,
    escape_newlines,
    escape_format_strings,
    get_secure_file_opener,
)
from laketrace.spark_integration import (
    setup_logging_with_spark,
    stop_spark_and_upload_logs,
    SparkLogHandler,
)

__version__ = "1.0.0"
__all__ = [
    # Core API
    "LakeTraceLogger",
    "get_laketrace_logger",
    # Runtime utilities
    "RuntimeDetector",
    "stop_spark_if_active",
    # Security utilities
    "SecurityConfig",
    "sanitize_message",
    "mask_pii",
    "escape_newlines",
    "escape_format_strings",
    "get_secure_file_opener",
    # Spark integration
    "setup_logging_with_spark",
    "stop_spark_and_upload_logs",
    "SparkLogHandler",
]
