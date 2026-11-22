"""The same answers as data: what a tool, a report or a model can quote.

Every function returns a plain ``dict`` (JSON-ready) with the numbers, their
units in the key names (``_mm``, ``_mm_h``, ``_h``, ``_decades``), where the
threshold comes from, and the rule that goes with every answer:

    A threshold exceeded is not an alert.

A language model may word these facts; it never computes them. The numbers
come from here, and :func:`rainfall_thresholds.check.check_text` checks a text
against them.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from rainfall_thresholds.events import reconstruct_events, strongest_event
from rainfall_thresholds.fit import fit_threshold
from rainfall_thresholds.italy import ITALICA_T5, macroregion_of
from rainfall_thresholds.threshold import PowerLawThreshold

#: Where the official alert is. Every answer carries it.
ALERT_URL = "https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/"

RULE = (
    "A threshold exceeded is not an alert: it says the rain is like the rain that "
    "triggered landslides before. The official alert in Italy is the criticality "
    f"bulletin of the Dipartimento della Protezione Civile ({ALERT_URL})."
)

#: How many e-ITALICA landslides each Italian threshold was fitted on.
ITALICA_EVENTS = {"italy": 5974, "northern": 2659, "central": 1890, "southern": 1425}

_GAUGE = "e-ITALICA v4 rain gauges (Brunetti et al. 2024, doi:10.5281/zenodo.14204473)"


def resolve(region: str) -> str:
    """``"italy"``, a macroregion, or an Italian region name -> the key of ITALICA_T5."""
    if region in ITALICA_T5:
        return region
    found = macroregion_of(region)
    if found is None:
        raise ValueError(
            f"unknown region {region!r}: use an Italian region as e-ITALICA spells it "
            f"(for example 'Calabria', 'Emilia-Romagna'), or one of {sorted(ITALICA_T5)}"
        )
    return found


def _threshold(key: str, t: PowerLawThreshold) -> dict[str, Any]:
    return {
        "name": f"ITALICA_T5[{key!r}]",
        "macroregion": key,
        "alpha": t.alpha,
        "beta": t.beta,
        "percentile": 5,
        "fitted_on": _GAUGE,
        "landslides": ITALICA_EVENTS[key],
    }


def threshold_facts(region: str, duration_h: float) -> dict[str, Any]:
    """The rain the Italian T5 threshold asks for over ``duration_h`` hours."""
    key = resolve(region)
    t = ITALICA_T5[key]
    return {
        "region": region,
        "threshold": _threshold(key, t),
        "duration_h": duration_h,
        "intensity_mm_h": round(t.intensity(duration_h), 2),
        "cumulated_mm": round(t.cumulated(duration_h), 1),
        "rule": RULE,
    }


def _event(e: Any, t: PowerLawThreshold) -> dict[str, Any]:
    return {
        "start": e.start.isoformat(),
        "end": e.end.isoformat(),
        "duration_h": e.duration_hours,
        "total_mm": round(e.total_mm, 1),
        "intensity_mm_h": round(e.intensity_mm_h, 2),
        "needed_mm": round(t.cumulated(e.duration_hours), 1),
        "exceedance_decades": round(t.exceedance(e.intensity_mm_h, e.duration_hours), 2),
        "unmeasured_h": e.unmeasured_hours,
    }


def assess_facts(
    series: Iterable[tuple[datetime, float | None]],
    region: str,
    *,
    source: str | None = None,
    no_rain_break_hours: int = 6,
    min_event_mm: float = 2.0,
) -> dict[str, Any]:
    """The rainfall events of an hourly series, and where the strongest stands.

    ``None`` in the series is an hour not measured. ``source`` says where the
    rain comes from; the thresholds are fitted on rain gauges, so rain from a
    radar or a model is flagged.
    """
    key = resolve(region)
    t = ITALICA_T5[key]
    events = reconstruct_events(
        series, no_rain_break_hours=no_rain_break_hours, min_event_mm=min_event_mm, source=source
    )
    strongest = strongest_event(events, t)
    found: dict[str, Any] = {
        "region": region,
        "threshold": _threshold(key, t),
        "source": source,
        "events": [_event(e, t) for e in events],
        "strongest": None if strongest is None else _event(strongest, t),
        "above_threshold": None
        if strongest is None
        else t.exceedance(strongest.intensity_mm_h, strongest.duration_hours) > 0,
        "rule": RULE,
    }
    notes = []
    if source is None or "gauge" not in source.lower():
        notes.append(
            "The threshold is fitted on rain gauges. Rain from a radar or a model is not "
            "gauge rain: the comparison is not validated."
        )
    if strongest is not None and strongest.unmeasured_hours:
        notes.append(
            f"{strongest.unmeasured_hours} hours of the event were not measured: its total "
            "is a lower bound."
        )
    found["notes"] = notes
    return found


def fit_facts(events: Iterable[tuple[float, float]], *, percentile: float = 5.0) -> dict[str, Any]:
    """A threshold fitted on ``(duration_h, total_mm)`` of landslide-triggering rain."""
    pairs = [(d, mm / d) for d, mm in events if d > 0]
    fit = fit_threshold(pairs, percentile=percentile)
    t = fit.threshold
    return {
        "alpha": round(t.alpha, 3),
        "beta": round(t.beta, 4),
        "percentile": percentile,
        "landslides": fit.n_events,
        "needed": [{"duration_h": d, "cumulated_mm": round(t.cumulated(d), 1)} for d in (24, 72)],
        "rule": RULE,
    }
