"""The logic moved from Limen gives Limen's numbers, on fixed inputs.

``limen_reference`` is Limen's code as it was; every test here runs it next
to the package's function on the same input.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import limen_reference as limen
import pytest

from rainfall_thresholds import (
    ITALICA_T5,
    PowerLawThreshold,
    RainfallEvent,
    api_factor,
    api_kohler_linsley,
    caine_excess,
    cumulate,
    event_against_threshold,
    load_regional_catalogue,
    threshold_for,
)

T0 = datetime(2026, 10, 1, tzinfo=UTC)
CATALOGUE = Path(__file__).parent / "fixtures" / "limen_soglie_frane_regionali.json"

#: Limen's AOI ids for the three regional thresholds, as region names.
AOI_REGION = {
    "it-calabria": "Calabria",
    "it-abruzzo": "Abruzzo",
    "it-marche": "Marche",
    "it-umbria": "Umbria",
    "it-sicilia": "Sicilia",
}

#: Limen's `caine.macroregions`: the same thresholds under Limen's key.
MACROREGIONS = {
    "italy_default": ITALICA_T5["italy"],
    "southern": ITALICA_T5["southern"],
    "northern": ITALICA_T5["northern"],
}


def _series(seed: int, hours: int, *, gaps: float) -> dict[datetime, float | None]:
    """Showers, dry spells and unmeasured hours, the same for a given seed."""
    rng = random.Random(seed)
    strongest = (0.6, 3.0, 14.0)[seed % 3]  # drizzle, rain, storm: below and above the line
    out: dict[datetime, float | None] = {}
    wet = False
    for k in range(hours):
        if rng.random() < 0.15:
            wet = not wet
        if rng.random() < gaps:
            out[T0 + timedelta(hours=k)] = None
        else:
            out[T0 + timedelta(hours=k)] = round(rng.uniform(0.2, strongest), 1) if wet else 0.0
    return out


SERIES = [
    _series(seed, hours, gaps=gaps) for seed in range(12) for hours, gaps in ((30, 0.0), (96, 0.08))
]


# --- Antecedent Precipitation Index -----------------------------------------


@pytest.mark.parametrize("decay_k", [0.5, 0.85, 0.95])
@pytest.mark.parametrize("initial", [0.0, 37.5])
def test_api_kohler_linsley_is_limens(decay_k: float, initial: float) -> None:
    rng = random.Random(7)
    daily = [rng.choice([0.0, 0.0, rng.uniform(0, 60)]) for _ in range(30)]
    assert api_kohler_linsley(daily, decay_k=decay_k, initial=initial) == limen.api_kohler_linsley(
        daily, decay_k=decay_k, initial=initial
    )


@pytest.mark.parametrize("api_mm", [None, 0.0, 12.0, 80.0, 143.7, 900.0])
@pytest.mark.parametrize(
    ("baseline_mm", "sigma_mm"), [(None, None), (55.0, None), (None, 4.0), (120.0, 45.0)]
)
def test_api_factor_is_limens(
    api_mm: float | None, baseline_mm: float | None, sigma_mm: float | None
) -> None:
    ours = api_factor(
        api_mm,
        fallback_baseline_mm=80.0,
        fallback_sigma_mm=60.0,
        sigma_min_mm=20.0,
        baseline_mm=baseline_mm,
        sigma_mm=sigma_mm,
    )
    theirs = limen.api_factor(
        api_mm,
        fallback_mm=80.0,
        sigmoid_sigma_mm=60.0,
        sigma_min_mm=20.0,
        baseline_mm=baseline_mm,
        sigma_mm=sigma_mm,
    )
    assert ours == theirs


# --- Gap-aware windows -------------------------------------------------------


@pytest.mark.parametrize("ore", SERIES)
def test_cumulate_is_limens(ore: dict[datetime, float | None]) -> None:
    end = max(ore)
    ours = cumulate(ore, end, windows_hours=limen.CUMULATE)
    as_limen = {
        f"{w.hours}h": {
            "mm": None if w.total_mm is None else round(w.total_mm, 1),
            "ore_non_misurate": w.unmeasured_hours,
        }
        for w in ours.values()
    }
    assert as_limen == limen.cumulate(ore, end)


def test_cumulate_of_an_empty_series_is_limens() -> None:
    ours = cumulate({}, T0, windows_hours=limen.CUMULATE)
    theirs = limen.cumulate({}, T0)
    assert {f"{h}h" for h in ours} == set(theirs)
    assert all(w.total_mm is None and w.unmeasured_hours == w.hours for w in ours.values())


# --- An event against the threshold ------------------------------------------


def _as_limen(a: Any) -> dict[str, Any]:
    e = a.event
    return {
        "inizio": e.start,
        "fine": e.end,
        "durata_h": e.duration_hours,
        "cumulata_mm": round(e.total_mm, 1),
        "intensita_mm_h": round(e.intensity_mm_h, 2),
        "soglia_mm_h": round(a.threshold_mm_h, 2),
        "soglia_mm": round(a.threshold_mm, 1),
        "rapporto_soglia": round(a.ratio, 2),
        "ore_non_misurate": e.unmeasured_hours,
        "confina_con_ore_non_misurate": a.borders_unmeasured,
        "almeno": a.at_least,
    }


@pytest.mark.parametrize("ore", SERIES)
@pytest.mark.parametrize(("choice", "scelta"), [("latest", "ultimo"), ("strongest", "piu_forte")])
@pytest.mark.parametrize("macroregion", ["southern", "nowhere"])
def test_event_against_threshold_is_limens(
    ore: dict[datetime, float | None], choice: str, scelta: str, macroregion: str
) -> None:
    ours = event_against_threshold(
        ore,
        threshold_for(macroregion, MACROREGIONS, default="italy_default"),
        no_rain_break_hours=6,
        min_event_mm=1.0,
        choice=choice,  # type: ignore[arg-type]
        source="pluviometro",
    )
    theirs = limen.evento_contro_soglia(
        ore,
        macroregions=MACROREGIONS,
        macroregione=macroregion,
        no_rain_break_hours=6,
        min_event_mm=1.0,
        scelta_evento=scelta,
    )
    assert (None if ours is None else _as_limen(ours)) == theirs
    assert ours is None or ours.event.source == "pluviometro"


def test_the_series_have_events_and_gaps() -> None:
    """The parity above is not an agreement on nothing."""
    found = [
        event_against_threshold(
            ore, ITALICA_T5["italy"], no_rain_break_hours=6, min_event_mm=1.0, choice="strongest"
        )
        for ore in SERIES
    ]
    assert sum(a is not None for a in found) >= 20
    assert any(a is not None and a.event.unmeasured_hours > 0 for a in found)
    assert any(a is not None and a.borders_unmeasured for a in found)
    assert any(a is not None and not a.at_least for a in found)
    assert any(a is not None and a.ratio > 1 for a in found)
    assert any(a is not None and a.ratio < 1 for a in found)


# --- Caine excess and the macroregion resolution ---------------------------------


EVENTS = [
    None,
    RainfallEvent(T0, T0, 1.0, 0.4),
    RainfallEvent(T0, T0 + timedelta(hours=5), 6.0, 31.0),
    RainfallEvent(T0, T0 + timedelta(hours=23), 24.0, 120.0),
    RainfallEvent(T0, T0 + timedelta(hours=71), 72.0, 44.0),
    RainfallEvent(T0, T0 + timedelta(hours=2), 3.0, 0.0),
]


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize("macroregion", ["italy_default", "southern", "nowhere"])
@pytest.mark.parametrize("alpha_factor", [1.0, 0.7])
def test_caine_excess_is_limens(
    event: RainfallEvent | None, macroregion: str, alpha_factor: float
) -> None:
    threshold = threshold_for(macroregion, MACROREGIONS, default="italy_default")
    assert caine_excess(event, threshold.scaled(alpha_factor)) == limen.caine_excess(
        event, macroregions=MACROREGIONS, macroregion=macroregion, alpha_factor=alpha_factor
    )


@pytest.mark.parametrize("macroregion", ["italy_default", "southern", "northern", "nowhere"])
def test_threshold_for_is_limens_resolution(macroregion: str) -> None:
    assert threshold_for(
        macroregion, MACROREGIONS, default="italy_default"
    ) is limen.resolve_region(MACROREGIONS, macroregion)


# --- The catalogue of regional thresholds ----------------------------------------


@pytest.fixture(scope="module")
def limen_catalogue() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return data


def test_the_catalogue_has_limens_sources(limen_catalogue: dict[str, Any]) -> None:
    ours = load_regional_catalogue()
    assert {
        key: {"citazione": s.citation, "url": s.url, "licenza": s.license}
        for key, s in ours.sources.items()
    } == limen_catalogue["fonti"]


def test_the_catalogue_has_limens_thresholds(limen_catalogue: dict[str, Any]) -> None:
    ours = load_regional_catalogue()
    as_limen = [
        {
            "id": t.id,
            "forma": t.form,
            "alpha": t.alpha,
            "gamma": t.gamma,
            "beta": t.beta,
            "regions": list(t.regions),
            "zona": t.zone,
            "durata_h": None if t.duration_hours is None else list(t.duration_hours),
            "livello": t.level,
            "nrg_h": t.no_rain_gap_hours,
            "fonte": t.source,
            "nota": t.note,
        }
        for t in ours.thresholds
    ]
    theirs = [
        {
            "id": s["id"],
            "forma": s["forma"],
            "alpha": s["alpha"],
            "gamma": s.get("gamma"),
            "beta": s.get("beta"),
            "regions": [AOI_REGION[a] for a in s.get("aoi", [])],
            "zona": s.get("zona"),
            "durata_h": s.get("durata_h"),
            "livello": s.get("livello"),
            "nrg_h": s.get("nrg_h"),
            "fonte": s["fonte"],
            "nota": s.get("nota"),
        }
        for s in limen_catalogue["soglie"]
    ]
    assert as_limen == theirs


def test_as_intensity_is_limens_in_intensita(limen_catalogue: dict[str, Any]) -> None:
    ours = {t.id: t.as_intensity() for t in load_regional_catalogue().thresholds}
    for s in limen_catalogue["soglie"]:
        alpha, beta = limen.in_intensita(s)
        assert ours[s["id"]] == PowerLawThreshold(alpha=alpha, beta=beta)
