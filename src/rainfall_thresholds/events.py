"""Rainfall events from an hourly series, after Melillo et al. (2018).

The series is split wherever ``no_rain_break_hours`` or more consecutive
dry hours occur; an event whose cumulated rainfall is below ``min_event_mm``
is dropped. An event runs from its first to its last wet hour, both
included, so a single wet hour is a one-hour event.

This is a simplified reconstruction: Melillo et al. also vary the dry gap
with the season and separate sub-events within a rainfall period. Use their
CTRL-T tool when the reconstruction itself is what you are studying.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RainfallEvent:
    """One rainfall event: first and last wet hour, duration and total."""

    start: datetime
    end: datetime
    duration_hours: float
    total_mm: float

    @property
    def intensity_mm_h(self) -> float:
        """Mean intensity over the event."""
        return self.total_mm / self.duration_hours


def reconstruct_events(
    series: Iterable[tuple[datetime, float]],
    *,
    no_rain_break_hours: int,
    min_event_mm: float,
) -> list[RainfallEvent]:
    """Split an hourly ``(timestamp, mm)`` series into rainfall events.

    The series is sorted by timestamp first. Dry hours are counted as
    samples, so the series is expected to be hourly and without gaps.
    """
    if no_rain_break_hours < 1:
        raise ValueError(f"no_rain_break_hours must be >= 1, got {no_rain_break_hours}")
    samples = sorted(series, key=lambda s: s[0])
    events: list[RainfallEvent] = []
    first: datetime | None = None
    last: datetime | None = None
    total = 0.0
    dry = 0

    def close() -> None:
        if first is not None and last is not None and total >= min_event_mm:
            hours = max(1.0, (last - first).total_seconds() / 3600.0 + 1.0)
            events.append(RainfallEvent(first, last, hours, total))

    for when, mm in samples:
        if mm < 0:
            raise ValueError(f"negative rainfall at {when.isoformat()}: {mm}")
        if mm > 0:
            if first is None:
                first = when
            total += mm
            last = when
            dry = 0
        else:
            dry += 1
            if dry >= no_rain_break_hours and first is not None:
                close()
                first, last, total = None, None, 0.0
    close()
    return events


def latest_event(events: Iterable[RainfallEvent]) -> RainfallEvent | None:
    """The event that ended last, or ``None``."""
    return max(events, key=lambda e: e.end, default=None)
