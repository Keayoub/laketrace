"""Compatibility module for LakeTrace package.

This module mirrors the public API in __init__.py to satisfy environments
that expect laketrace.init as an import path.
"""

from laketrace.logger import Logger, get_logger
from laketrace.runtime import detect_runtime, stop_spark_if_active

__all__ = [
    "Logger",
    "get_logger",
    "detect_runtime",
    "stop_spark_if_active",
]
