"""A measured hourly series against a threshold: windows, the event, the excess.

The series is a mapping from the hour to its rain in mm, with ``None`` for an
hour **not measured**. Not measured is never read as zero:

* a window with an unmeasured hour has no total, and says how many are missing;
* an event with unmeasured hours inside, or bordered by them (the archive
  stops before the dry break closes it, or starts after it began), is a lower
  bound: :attr:`EventAssessment.at_least`.

The Italian thresholds are fitted on rain gauges. Rain from a radar is not the
same quantity: where the two were measured together, pass their ratio as
``radar_gauge_factor`` and the threshold is lowered by it. The factor is a
plain number of the caller's, with no default other than 1 (no correction):
it depends on the radar product, the place and the years
(``benchmarks/measures`` has one measure of it, 0.68 on triggering events,
2018-2025).

Moved from Limen (``core/pioggia_frane.py``, ``core/scoring/caine.py``);
parity tests keep the numbers the same.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from rainfall_thresholds.events import (
    RainfallEvent,
    latest_event,
    reconstruct_events,
    strongest_event,
)
from rainfall_thresholds.threshold import PowerLawThreshold


@dataclass(frozen=True, slots=True)
class WindowTotal:
    """The rain of the last ``hours`` hours: ``None`` if any was not measured."""

    hours: int
    total_mm: float | None
    unmeasured_hours: int


def cumulate(
    hours: Mapping[datetime, float | None],
    end: datetime,
    *,
    windows_hours: Iterable[int],
) -> dict[int, WindowTotal]:
    """The totals of the windows that end at ``end``, by window length.

    A window is the ``n`` hours up to ``end`` included. One that starts
    before the first hour of the series is left out; an hour missing from the
    series counts as not measured, like one that is ``None``. Totals are not
    rounded.
    """
    first = min(hours, default=end)
    out: dict[int, WindowTotal] = {}
    for n in windows_hours:
        if n < 1:
            raise ValueError(f"windows_hours must be >= 1, got {n}")
        if end - timedelta(hours=n - 1) < first:
            continue
        window = [hours.get(end - timedelta(hours=k)) for k in range(n)]
        measured = [v for v in window if v is not None]
        missing = n - len(measured)
        out[n] = WindowTotal(n, None if missing else sum(measured), missing)
    return out


def caine_excess(
    event: RainfallEvent | None,
    threshold: PowerLawThreshold,
    *,
    radar_gauge_factor: float = 1.0,
) -> float:
    """``max(0, log10(I_event / I_threshold(D_event)))``: decades above the line.

    Zero with no event and for an event on or below the threshold. To lower
    or raise the threshold for another reason (after an earthquake, say),
    pass ``threshold.scaled(factor)``.
    """
    if event is None:
        return 0.0
    excess = _for_radar(threshold, radar_gauge_factor).exceedance(
        event.intensity_mm_h, event.duration_hours
    )
    # -inf (a dry event) goes to zero; +inf from a corrupt series stays.
    return excess if excess > 0.0 else 0.0


@dataclass(frozen=True, slots=True)
class EventAssessment:
    """A rainfall event and the threshold at its duration.

    ``threshold`` is the one applied, already lowered by the radar/gauge
    factor if one was given. ``borders_unmeasured`` says that an hour within
    the dry break before or after the event was not measured (or is not in
    the series): the event may have begun earlier or not be over.
    """

    event: RainfallEvent
    threshold: PowerLawThreshold
    borders_unmeasured: bool

    @property
    def threshold_mm_h(self) -> float:
        """The threshold mean intensity at the event's duration."""
        return self.threshold.intensity(self.event.duration_hours)

    @property
    def threshold_mm(self) -> float:
        """The threshold cumulated rainfall at the event's duration."""
        return self.threshold_mm_h * self.event.duration_hours

    @property
    def ratio(self) -> float:
        """Event intensity over threshold intensity: above 1 is above the line."""
        return self.event.intensity_mm_h / self.threshold_mm_h

    @property
    def excess_decades(self) -> float:
        """``log10`` of :attr:`ratio`, negative below the line."""
        return self.threshold.exceedance(self.event.intensity_mm_h, self.event.duration_hours)

    @property
    def at_least(self) -> bool:
        """``True`` when the measured rain is a lower bound of the real one."""
        return self.event.unmeasured_hours > 0 or self.borders_unmeasured


def event_against_threshold(
    hours: Mapping[datetime, float | None],
    threshold: PowerLawThreshold,
    *,
    no_rain_break_hours: int,
    min_event_mm: float,
    choice: Literal["latest", "strongest"] = "latest",
    source: str | None = None,
    radar_gauge_factor: float = 1.0,
) -> EventAssessment | None:
    """The rainfall event of an hourly series, against the threshold at its duration.

    The events are those of :func:`~rainfall_thresholds.events.reconstruct_events`
    with the same ``no_rain_break_hours``, ``min_event_mm`` and ``source``;
    ``choice`` takes the one that ended last or the one furthest above the
    threshold (:func:`~rainfall_thresholds.events.strongest_event`). ``None``
    when the series has no event.
    """
    if choice not in ("latest", "strongest"):
        raise ValueError(f"choice must be 'latest' or 'strongest', got {choice!r}")
    applied = _for_radar(threshold, radar_gauge_factor)
    events = reconstruct_events(
        hours.items(),
        no_rain_break_hours=no_rain_break_hours,
        min_event_mm=min_event_mm,
        source=source,
    )
    event = strongest_event(events, applied) if choice == "strongest" else latest_event(events)
    if event is None:
        return None
    borders = [event.start - timedelta(hours=k) for k in range(1, no_rain_break_hours + 1)] + [
        event.end + timedelta(hours=k) for k in range(1, no_rain_break_hours + 1)
    ]
    return EventAssessment(event, applied, any(hours.get(t) is None for t in borders))


def _for_radar(threshold: PowerLawThreshold, radar_gauge_factor: float) -> PowerLawThreshold:
    if not (math.isfinite(radar_gauge_factor) and radar_gauge_factor > 0):
        raise ValueError(f"radar_gauge_factor must be a number > 0, got {radar_gauge_factor}")
    return threshold if radar_gauge_factor == 1.0 else threshold.scaled(radar_gauge_factor)
