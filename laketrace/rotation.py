"""
Rotation helpers for LakeTrace.

Adapted from Loguru (MIT License): https://github.com/Delgan/loguru
Original author: Julien Danjou
"""

import datetime
import os
from functools import partial
from typing import Callable, Optional, Union

from laketrace.string_parsers import parse_size, parse_duration, parse_frequency, parse_daytime, parse_daytime_with_weekday


RotationFunction = Callable[[str, object], bool]


class Rotation:
    """Rotation helpers."""

    @staticmethod
    def forward_day(t: datetime.datetime) -> datetime.datetime:
        return t + datetime.timedelta(days=1)

    @staticmethod
    def forward_weekday(t: datetime.datetime, weekday: int) -> datetime.datetime:
        while True:
            t += datetime.timedelta(days=1)
            if t.weekday() == weekday:
                return t

    @staticmethod
    def forward_interval(t: datetime.datetime, interval: datetime.timedelta) -> datetime.datetime:
        return t + interval

    @staticmethod
    def rotation_size(message: str, file, size_limit: int) -> bool:
        file.seek(0, os.SEEK_END)
        return file.tell() + len(message) > size_limit

    class RotationTime:
        def __init__(self, step_forward: Callable[[datetime.datetime], datetime.datetime], time_init: Optional[datetime.time] = None):
            self._step_forward = step_forward
            self._time_init = time_init
            self._limit: Optional[datetime.datetime] = None

        def __call__(self, message: str, file) -> bool:
            record_time = datetime.datetime.now(datetime.timezone.utc)

            if self._limit is None:
                try:
                    creation_time = datetime.datetime.fromtimestamp(os.path.getmtime(file.name), tz=datetime.timezone.utc)
                except Exception:
                    creation_time = record_time

                time_init = self._time_init

                if time_init is None:
                    limit = creation_time.replace(tzinfo=None)
                    limit = self._step_forward(limit)
                else:
                    limit = creation_time.replace(
                        hour=time_init.hour,
                        minute=time_init.minute,
                        second=time_init.second,
                        microsecond=time_init.microsecond,
                        tzinfo=None,
                    )

                    if limit <= creation_time.replace(tzinfo=None):
                        limit = self._step_forward(limit)

                self._limit = limit

            record_time_naive = record_time.replace(tzinfo=None)

            if record_time_naive >= self._limit:
                while self._limit <= record_time_naive:
                    self._limit = self._step_forward(self._limit)
                return True
            return False

    class RotationGroup:
        def __init__(self, rotations):
            self._rotations = rotations

        def __call__(self, message: str, file) -> bool:
            return any(rotation(message, file) for rotation in self._rotations)


def make_rotation_function(rotation: Optional[Union[str, int, float, datetime.time, datetime.timedelta, RotationFunction, list]]):
    """Create a rotation function from configuration."""
    if rotation is None:
        return None

    if isinstance(rotation, (list, tuple, set)):
        if len(rotation) == 0:
            raise ValueError("Must provide at least one rotation condition")
        return Rotation.RotationGroup([make_rotation_function(rot) for rot in rotation])

    if isinstance(rotation, str):
        size = parse_size(rotation)
        if size is not None:
            return make_rotation_function(size)

        interval = parse_duration(rotation)
        if interval is not None:
            return make_rotation_function(interval)

        frequency = parse_frequency(rotation)
        if frequency is not None:
            return Rotation.RotationTime(partial(Rotation.forward_interval, interval=frequency))

        daytime = parse_daytime(rotation)
        if daytime is not None:
            return Rotation.RotationTime(Rotation.forward_day, daytime)

        weekday = parse_daytime_with_weekday(rotation)
        if weekday is not None:
            day, time_init = weekday
            return Rotation.RotationTime(partial(Rotation.forward_weekday, weekday=day), time_init)

        raise ValueError(f"Cannot parse rotation from: '{rotation}'")

    if isinstance(rotation, (int, float)):
        return partial(Rotation.rotation_size, size_limit=int(rotation))

    if isinstance(rotation, datetime.time):
        return Rotation.RotationTime(Rotation.forward_day, rotation)

    if isinstance(rotation, datetime.timedelta):
        return Rotation.RotationTime(partial(Rotation.forward_interval, interval=rotation))

    if callable(rotation):
        return rotation

    raise TypeError(f"Cannot infer rotation for objects of type: '{type(rotation).__name__}'")