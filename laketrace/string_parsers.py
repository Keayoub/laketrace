"""
Simple parsers for rotation/retention configuration.
"""

import re
from datetime import timedelta, time
from typing import Optional, Tuple


_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)\s*$", re.IGNORECASE)
_DURATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(second|minute|hour|day|week|month|year)s?\s*$", re.IGNORECASE)
_TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")


def parse_size(value: str) -> Optional[int]:
    """Parse a human-readable size string into bytes."""
    match = _SIZE_RE.match(value)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()

    multipliers = {
        "b": 1,
        "kb": 1024,
        "mb": 1024 ** 2,
        "gb": 1024 ** 3,
    }

    return int(number * multipliers[unit])


def parse_duration(value: str) -> Optional[timedelta]:
    """Parse a human-readable duration into timedelta."""
    match = _DURATION_RE.match(value)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()

    seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
        "month": 2592000,  # 30 days
        "year": 31536000,  # 365 days
    }[unit]

    return timedelta(seconds=number * seconds)


def parse_frequency(value: str) -> Optional[timedelta]:
    """Parse frequency keywords into timedelta."""
    normalized = value.strip().lower()
    if normalized == "daily":
        return timedelta(days=1)
    if normalized == "weekly":
        return timedelta(weeks=1)
    if normalized == "monthly":
        return timedelta(days=30)
    if normalized == "yearly":
        return timedelta(days=365)
    return None


def parse_daytime(value: str) -> Optional[time]:
    """Parse a HH:MM[:SS] string into time."""
    match = _TIME_RE.match(value)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    second = int(match.group(3) or 0)

    if hour > 23 or minute > 59 or second > 59:
        return None

    return time(hour=hour, minute=minute, second=second)


def parse_daytime_with_weekday(value: str) -> Optional[Tuple[int, time]]:
    """Parse strings like 'monday 12:00' into (weekday, time)."""
    parts = value.strip().lower().split()
    if len(parts) != 2:
        return None

    day, time_str = parts
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    if day not in weekdays:
        return None

    parsed_time = parse_daytime(time_str)
    if parsed_time is None:
        return None

    return weekdays[day], parsed_time