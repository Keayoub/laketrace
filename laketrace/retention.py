"""
Retention helpers for LakeTrace.

Adapted from Loguru (MIT License): https://github.com/Delgan/loguru
Original author: Julien Danjou
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Union

from laketrace.string_parsers import parse_duration


RetentionFunction = Callable[[List[str]], None]


def _retention_count(logs: List[str], count: int) -> None:
    logs_sorted = sorted(logs, key=lambda p: os.path.getmtime(p))
    while len(logs_sorted) > count:
        old_file = logs_sorted.pop(0)
        try:
            os.remove(old_file)
        except Exception:
            pass


def _retention_time(logs: List[str], delta: timedelta) -> None:
    limit = datetime.now(timezone.utc) - delta
    for log_file in logs:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(log_file), tz=timezone.utc)
            if mtime < limit:
                os.remove(log_file)
        except Exception:
            pass


def make_retention_function(retention: Optional[Union[str, int, timedelta, RetentionFunction]]):
    """Create a retention cleanup function from configuration."""
    if retention is None:
        return None

    if isinstance(retention, int):
        return lambda logs: _retention_count(logs, retention)

    if isinstance(retention, timedelta):
        return lambda logs: _retention_time(logs, retention)

    if isinstance(retention, str):
        # Try to parse as "N files" first
        if "file" in retention.lower():
            try:
                count = int(retention.split()[0])
                return lambda logs: _retention_count(logs, count)
            except (ValueError, IndexError):
                pass
        
        # Try to parse as duration (e.g., "7 days")
        duration = parse_duration(retention)
        if duration is not None:
            return lambda logs: _retention_time(logs, duration)
        
        raise ValueError(f"Cannot parse retention from: '{retention}'")

    if callable(retention):
        return retention

    raise TypeError(f"Cannot infer retention for objects of type: '{type(retention).__name__}'")