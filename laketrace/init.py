"""Compatibility module for LakeTrace package.

This module mirrors the public API in __init__.py to satisfy environments
that expect laketrace.init as an import path.
"""

from laketrace.logger import LakeTraceLogger, get_laketrace_logger
from laketrace.runtime import RuntimeDetector, stop_spark_if_active

__all__ = [
    "LakeTraceLogger",
    "get_laketrace_logger",
    "RuntimeDetector",
    "stop_spark_if_active",
]
