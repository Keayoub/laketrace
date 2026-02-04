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

Recommended Import Patterns:
    ```python
    # Safe: No name conflicts
    from laketrace import get_logger
    log = get_logger("my_job")
    
    # Alternative: Direct class usage
    from laketrace import Logger
    log = Logger("my_job")
    
    # With alias to avoid conflicts
    from laketrace import get_logger as trace_logger
    log = trace_logger("my_job")
    ```
"""

from laketrace.logger import Logger, get_logger, create_logger
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
    "Logger",
    "get_logger",
    "create_logger",
    # Runtime utilities
    "detect_runtime",
    "stop_spark_if_active",
    # Security utilities
    "sanitize_message",
    "mask_pii",
    "escape_newlines",
    "escape_format_strings",
]

