"""Rainfall events from an hourly series, after Melillo et al. (2018).

The series is split wherever ``no_rain_break_hours`` or more consecutive
dry hours occur; an event whose cumulated rainfall is below ``min_event_mm``
is dropped. An event runs from its first to its last wet hour, both
included, so a single wet hour is a one-hour event.

An hour can be **not measured** (``None``): a missing frame, a gauge that did
not report, a place the radar cannot see. Not measured is not dry. Such an
hour adds no rain and does not count towards the dry break, so a gap never
splits an event on its own; the event counts it in ``unmeasured_hours``, and
its total is then a lower bound.

This is a simplified reconstruction: Melillo et al. also vary the dry gap
with the season and separate sub-events within a rainfall period. Use their
CTRL-T tool when the reconstruction itself is what you are studying.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rainfall_thresholds.threshold import PowerLawThreshold


@dataclass(frozen=True, slots=True)
class RainfallEvent:
    """One rainfall event: first and last wet hour, duration and total.

    ``unmeasured_hours`` counts the hours inside the event that were not
    measured: when it is above zero, ``total_mm`` is what was measured, a
    lower bound. ``source`` is the label given to :func:`reconstruct_events`
    (for example ``"rain gauge"`` or ``"DPC SRT1"``), carried as it is.
    """

    start: datetime
    end: datetime
    duration_hours: float
    total_mm: float
    unmeasured_hours: int = 0
    source: str | None = None

    @property
    def intensity_mm_h(self) -> float:
        """Mean intensity over the event."""
        return self.total_mm / self.duration_hours

    @property
    def fully_measured(self) -> bool:
        """``True`` when every hour of the event was measured."""
        return self.unmeasured_hours == 0


def reconstruct_events(
    series: Iterable[tuple[datetime, float | None]],
    *,
    no_rain_break_hours: int,
    min_event_mm: float,
    source: str | None = None,
) -> list[RainfallEvent]:
    """Split an hourly ``(timestamp, mm)`` series into rainfall events.

    The series is sorted by timestamp first. It is expected to be hourly and
    without gaps: a dry hour must be in the series as ``0``, an hour not
    measured as ``None``. ``source`` labels the events (the Italian
    thresholds are fitted on rain gauges, so it matters where the rain comes
    from); it is carried, never interpreted.
    """
    if no_rain_break_hours < 1:
        raise ValueError(f"no_rain_break_hours must be >= 1, got {no_rain_break_hours}")
    samples = sorted(series, key=lambda s: s[0])
    events: list[RainfallEvent] = []
    first: datetime | None = None
    last: datetime | None = None
    total = 0.0
    dry = 0
    unmeasured = 0  # inside the event, up to its last wet hour
    pending = 0  # since the last wet hour: inside the event only if it rains again

    def close() -> None:
        if first is not None and last is not None and total >= min_event_mm:
            hours = max(1.0, (last - first).total_seconds() / 3600.0 + 1.0)
            events.append(RainfallEvent(first, last, hours, total, unmeasured, source))

    for when, mm in samples:
        if mm is None:
            if first is not None:
                pending += 1
            continue
        if mm < 0:
            raise ValueError(f"negative rainfall at {when.isoformat()}: {mm}")
        if mm > 0:
            if first is None:
                first = when
            total += mm
            last = when
            dry = 0
            unmeasured += pending
            pending = 0
        else:
            dry += 1
            if dry >= no_rain_break_hours and first is not None:
                close()
                first, last, total, unmeasured, pending = None, None, 0.0, 0, 0
    close()
    return events


def latest_event(events: Iterable[RainfallEvent]) -> RainfallEvent | None:
    """The event that ended last, or ``None``.

    For monitoring, prefer :func:`strongest_event`: the last event can be a
    little drizzle after a storm.
    """
    return max(events, key=lambda e: e.end, default=None)


def strongest_event(
    events: Iterable[RainfallEvent], threshold: PowerLawThreshold
) -> RainfallEvent | None:
    """The event furthest above (or least below) ``threshold``, or ``None``.

    A storm followed by six dry hours and a little drizzle is two events: the
    last one is the drizzle, the strongest is the storm. Which events count is
    the caller's choice: pass the events of the window you monitor (for
    example the last 48 hours), so an old storm does not stay forever.
    Ties go to the event that ended last.
    """
    return max(
        events,
        key=lambda e: (threshold.exceedance(e.intensity_mm_h, e.duration_hours), e.end),
        default=None,
    )
