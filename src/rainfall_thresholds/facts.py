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
from datetime import datetime, timedelta
from typing import Any

from rainfall_thresholds.assess import rain_to_threshold
from rainfall_thresholds.events import latest_event, reconstruct_events, strongest_event
from rainfall_thresholds.fit import fit_threshold
from rainfall_thresholds.italy import ITALICA_T5, macroregion_of
from rainfall_thresholds.regional import load_regional_catalogue
from rainfall_thresholds.threshold import PowerLawThreshold
from rainfall_thresholds.trust import EXPECTED_BELOW, calibration_of

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


_NOT_GAUGE = (
    "The threshold is fitted on rain gauges. Rain from a radar or a model is not "
    "gauge rain: the comparison is not validated."
)

_READING = {
    "high": (
        "More of this region's landslides are below the line than the 5 % it was fitted "
        "for: the line is high here, and misses more landslides than elsewhere."
    ),
    "low": (
        "Fewer of this region's landslides are below the line than the 5 % it was fitted "
        "for: the line is low here, and rain crosses it more easily than elsewhere."
    ),
}


def trust_facts(region: str) -> dict[str, Any]:
    """How well the threshold is calibrated in an Italian region.

    ``region`` is a region name (e-ITALICA spelling) or its ISTAT code. The
    facts are those of :func:`rainfall_thresholds.trust.calibration_of`: the
    landslides the threshold was fitted on in the region, how many are below
    it, and the range the real share can be in.
    """
    c = calibration_of(region)
    if c is None:
        raise ValueError(
            f"unknown region {region!r}: use an Italian region as e-ITALICA spells it "
            "(for example 'Calabria', 'Emilia-Romagna') or its ISTAT region code"
        )
    low, high = c.interval()
    reading = _READING.get(
        c.position,
        f"With {c.events} landslides the 5 % is within what chance gives: nothing says "
        "the line sits differently here"
        + (", but so few landslides would not show it." if c.events < 100 else "."),
    )
    return {
        "region": c.region,
        "threshold": _threshold(c.macroregion, ITALICA_T5[c.macroregion]),
        "landslides": c.events,
        "below_threshold": c.below,
        "below_share_pct": round(100 * c.below_share, 1),
        "expected_pct": 100 * EXPECTED_BELOW,
        "interval_pct": [round(100 * low, 1), round(100 * high, 1)],
        "interval": "Wilson score interval, 95 %",
        "fitted_from_h": c.duration_hours[0],
        "fitted_to_h": c.duration_hours[1],
        "position": c.position,
        "reading": reading,
        "notes": [
            "This is how the line sits on the landslides of the past, at rain gauges. How "
            "often it is crossed with no landslide is not here: measure it on your own rain.",
            "Outside the durations it was fitted on, the line is extrapolated.",
        ],
        "rule": RULE,
    }


def margin_facts(
    series: Iterable[tuple[datetime, float | None]],
    region: str,
    *,
    more_hours: Iterable[int] = (1, 3, 6),
    source: str | None = None,
    no_rain_break_hours: int = 6,
    min_event_mm: float = 2.0,
) -> dict[str, Any]:
    """The rain still needed to reach the threshold if the rain goes on.

    The event still going at the end of the series (its last wet hour is less
    than ``no_rain_break_hours`` before the last hour), or none: then the
    count starts from nothing. For each of ``more_hours``, what the threshold
    asks of the longer event and how much of it is still missing. Compare it
    with a forecast; it is not one.
    """
    key = resolve(region)
    t = ITALICA_T5[key]
    samples = sorted(series, key=lambda sample: sample[0])
    last = latest_event(
        reconstruct_events(
            samples,
            no_rain_break_hours=no_rain_break_hours,
            min_event_mm=min_event_mm,
            source=source,
        )
    )
    going_on = (
        last is not None
        and bool(samples)
        and samples[-1][0] - last.end < timedelta(hours=no_rain_break_hours)
    )
    event = last if going_on else None
    duration = 0.0 if event is None else event.duration_hours
    needed = rain_to_threshold(event, t, more_hours=more_hours)
    notes = [
        f"It supposes the rain does not stop: after {no_rain_break_hours} dry hours the "
        "event is over and the count starts again."
    ]
    if event is not None and event.unmeasured_hours:
        notes.append(
            f"{event.unmeasured_hours} hours of the event were not measured: its total is a "
            "lower bound, and the rain still needed may be less."
        )
    if source is None or "gauge" not in source.lower():
        notes.append(_NOT_GAUGE)
    return {
        "region": region,
        "threshold": _threshold(key, t),
        "source": source,
        "event": None if event is None else _event(event, t),
        "going_on": going_on,
        "needed": [
            {
                "more_h": h,
                "duration_h": duration + h,
                "threshold_mm": round(t.cumulated(duration + h), 1),
                "needed_mm": round(mm, 1),
            }
            for h, mm in needed.items()
        ],
        "notes": notes,
        "rule": RULE,
    }


def _at_24_h(t: PowerLawThreshold) -> dict[str, Any]:
    return {"cumulated_mm": round(t.cumulated(24), 1), "intensity_mm_h": round(t.intensity(24), 2)}


def published_facts(region: str) -> dict[str, Any]:
    """The thresholds the literature published for a region, next to this package's.

    From :func:`rainfall_thresholds.regional.load_regional_catalogue`: only
    thresholds for the whole region, each with its citation and licence, and
    the rain each asks for in 24 hours.
    """
    c = calibration_of(region)
    if c is None:
        raise ValueError(
            f"unknown region {region!r}: use an Italian region as e-ITALICA spells it "
            "or its ISTAT region code"
        )
    catalogue = load_regional_catalogue()
    published = []
    for entry in catalogue.thresholds:
        if c.region not in entry.regions:
            continue
        line = entry.as_intensity()
        origin = catalogue.sources[entry.source]
        published.append(
            {
                "id": entry.id,
                "level": entry.level,
                "alpha": line.alpha,
                "beta": round(line.beta, 4),
                "at_24_h": _at_24_h(line),
                "citation": origin.citation,
                "url": origin.url,
                "license": origin.license,
            }
        )
    ours = ITALICA_T5[c.macroregion]
    return {
        "region": c.region,
        "published": published,
        "this_package": {**_threshold(c.macroregion, ours), "at_24_h": _at_24_h(ours)},
        "notes": [
            "Different landslides, years and methods: two thresholds for the same region "
            "are not expected to be the same."
            if published
            else f"The catalogue has no published threshold for the whole of {c.region}: "
            "either none is published in numbers, or its licence is not declared."
        ],
        "rule": RULE,
    }
