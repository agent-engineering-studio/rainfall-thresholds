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
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

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

    def as_record(self, *, where: Mapping[str, Any] | None, licence: str) -> dict[str, Any]:
        """The assessment as a fact of ``opendata-record/v2``, a plain dict.

        The record format the libraries of the family exchange. ``where`` is
        a GeoJSON geometry (or ``None``) and ``licence`` the licence of the
        rain: an assessment knows neither. The source of the record is the
        event's ``source`` label, which must be there. An hour is labelled by
        its end, so the record's time begins an hour before the event's
        first. No name in it says more than a measure against a line.
        """
        event = self.event
        if not event.source:
            raise ValueError("a record needs the source of the rain: give `source` to the event")
        from rainfall_thresholds import __version__

        return {
            "schema": "opendata-record/v2",
            "kind": "fact",
            "question": "How does this rainfall event compare with the threshold at its duration?",
            "headline": "ratio",
            "source": {"name": event.source, "licence": licence},
            "made_by": {"name": "rainfall-thresholds", "version": __version__},
            "time": {
                "first": _utc(event.start - timedelta(hours=1)),
                "last": _utc(event.end),
                "exact": True,
            },
            "where": None if where is None else dict(where),
            "reliability": {
                "reliable": not self.at_least,
                "method": "every hour of the event and of the dry break around it was measured",
                "reasons": [
                    *(["hours_not_measured"] if event.unmeasured_hours else []),
                    *(["borders_not_measured"] if self.borders_unmeasured else []),
                ],
            },
            "values": {
                "duration": {"value": event.duration_hours, "unit": "h"},
                "total": {"value": event.total_mm, "unit": "mm"},
                "intensity": {"value": event.intensity_mm_h, "unit": "mm/h"},
                "threshold_intensity": {"value": self.threshold_mm_h, "unit": "mm/h"},
                "threshold_total": {"value": self.threshold_mm, "unit": "mm"},
                "threshold_alpha": {"value": self.threshold.alpha, "unit": "mm/h"},
                "threshold_beta": {"value": self.threshold.beta, "unit": "1"},
                "ratio": {
                    "value": self.ratio,
                    "unit": "1",
                    "meaning": "event intensity over threshold intensity; "
                    "above 1 is above the line",
                },
                "excess_decades": {
                    "value": self.excess_decades,
                    "unit": "1",
                    "meaning": "log10 of ratio",
                },
                "unmeasured_hours": {"value": event.unmeasured_hours, "unit": "h"},
                "borders_unmeasured": {"value": self.borders_unmeasured},
                "at_least": {
                    "value": self.at_least,
                    "meaning": "true: the measured rain is a lower bound of the real one",
                },
                "rain_source": {"value": event.source, "scheme": "label given by the caller"},
            },
            "notes": [
                "A threshold exceeded is not an alert. The official alert is the criticality "
                "bulletin of the Dipartimento della Protezione Civile."
            ],
        }


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


def rain_to_threshold(
    event: RainfallEvent | None,
    threshold: PowerLawThreshold,
    *,
    more_hours: Iterable[float],
    radar_gauge_factor: float = 1.0,
) -> dict[float, float]:
    """The rain still needed to reach the threshold if the event goes on, in mm.

    For each ``h`` of ``more_hours``: what the threshold asks of an event
    ``h`` hours longer, less what has already fallen; zero when the event is
    already there. It supposes the event does not stop: a dry break closes it
    and the count starts again. With no event (``None``) it is the rain a new
    event of ``h`` hours needs. Compare it with a forecast, or read it as the
    margin left.

    The line asks more of a longer event, so an event above it now can be
    below it later if it goes on with little rain.
    """
    applied = _for_radar(threshold, radar_gauge_factor)
    duration = 0.0 if event is None else event.duration_hours
    fallen = 0.0 if event is None else event.total_mm
    out: dict[float, float] = {}
    for h in more_hours:
        if h < 0 or duration + h <= 0:
            raise ValueError(f"more_hours must be >= 0, and > 0 with no event, got {h}")
        out[h] = max(0.0, applied.cumulated(duration + h) - fallen)
    return out


def relative_total(
    hours: Mapping[datetime, float | None],
    end: datetime,
    *,
    window_hours: int,
    reference_mm: float,
    saturation: float,
    reduction: float = 0.0,
    longer_references_mm: Mapping[int, float] | None = None,
) -> float | None:
    """The rain of the last hours against the place's own climate, from 0 to 1.

    A threshold in millimetres is not the same everywhere: 60 mm in a day are
    ordinary in Liguria and rare in Sardegna. Here the total of the
    ``window_hours`` up to ``end`` is divided by ``reference_mm``, a high
    quantile of that same total **at that place** (the caller's climatology),
    and is 1 at ``saturation`` times the reference. ``reduction`` (0 to 1,
    excluded) lowers the bar, for ground that needs less rain.
    ``longer_references_mm`` adds longer windows, each with its reference: the
    answer is the highest of all.

    The window is ``(end - window_hours, end]``. Only measured hours are
    summed, so with hours missing the answer is a lower bound; with no
    measured hour in the first window it is ``None``: rain not read is not no
    rain. Moved from Limen's engine (limen#243), with a parity test.
    """
    if reference_mm <= 0 or saturation <= 0:
        raise ValueError(
            f"reference_mm and saturation must be > 0, got {reference_mm} and {saturation}"
        )
    if not 0.0 <= reduction < 1.0:
        raise ValueError(f"reduction must be in [0, 1), got {reduction}")

    def window(n: int) -> list[float]:
        start = end - timedelta(hours=n)
        return [mm for when, mm in hours.items() if mm is not None and start < when <= end]

    first = window(window_hours)
    if not first:
        return None
    bar = saturation * (1.0 - reduction)
    found = _clamp01(sum(first) / (bar * reference_mm))
    for n, reference in (longer_references_mm or {}).items():
        found = max(found, _clamp01(sum(window(n)) / (bar * reference)))
    return found


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _for_radar(threshold: PowerLawThreshold, radar_gauge_factor: float) -> PowerLawThreshold:
    if not (math.isfinite(radar_gauge_factor) and radar_gauge_factor > 0):
        raise ValueError(f"radar_gauge_factor must be a number > 0, got {radar_gauge_factor}")
    return threshold if radar_gauge_factor == 1.0 else threshold.scaled(radar_gauge_factor)
