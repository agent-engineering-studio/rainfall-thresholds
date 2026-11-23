"""The numbers quoted for the measures are recomputed from their files."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from rainfall_thresholds import skill

PILOT = Path(__file__).parent.parent / "benchmarks" / "measures" / "pilot-2026-merging-vs-radar.csv"


@pytest.fixture(scope="module")
def pilot() -> list[dict[str, str]]:
    with PILOT.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _score(row: dict[str, str], source: str) -> float:
    value = row[f"{source}_exceedance"]
    return float(value) if value else float("-inf")


@pytest.mark.parametrize(
    ("source", "caught", "alerts", "events", "per_caught"),
    [("merging", 7, 66, 338, 66 / 7), ("radar", 8, 98, 382, 98 / 8)],
)
def test_pilot_2026(
    pilot: list[dict[str, str]],
    source: str,
    caught: int,
    alerts: int,
    events: int,
    per_caught: float,
) -> None:
    assert len(pilot) == 9
    total_events = sum(int(r[f"{source}_events"]) for r in pilot)
    total_alerts = sum(int(r[f"{source}_alerts"]) for r in pilot)
    landslides = [_score(r, source) for r in pilot]
    # The alerts as `skill` counts them: events above zero, out of all events.
    ordinary = [1.0] * total_alerts + [-1.0] * (total_events - total_alerts)
    s = skill(landslides, ordinary, cutoff=0.0)
    assert (s.caught, s.landslides, s.alerts, s.ordinary) == (caught, 9, alerts, events)
    assert s.alerts_per_caught is not None
    assert s.alerts_per_caught == pytest.approx(per_caught)


def test_one_landslide_had_no_rain_event(pilot: list[dict[str, str]]) -> None:
    none = [r["id"] for r in pilot if not r["merging_exceedance"] and not r["radar_exceedance"]]
    assert none == ["EIT202600078"]


# --- The gauge thresholds on radar rain, 2018-2025 (limen#677) ---

MEASURES = PILOT.parent
NO_EVENT = -99.0


@pytest.fixture(scope="module")
def radar() -> list[dict[str, str]]:
    with (MEASURES / "radar-2018-2025-landslides.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def groups() -> list[dict[str, str]]:
    with (MEASURES / "radar-2018-2025-groups.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(value: str) -> float | None:
    return float(value) if value else None


def test_radar_sets(radar: list[dict[str, str]]) -> None:
    assert sum(r["set"] == "e-italica" for r in radar) == 1057
    assert sum(r["set"] == "idrogeo" for r in radar) == 3143
    assert sum(r["set"] == "e-italica" and r["region"] == "Liguria" for r in radar) == 785
    assert sum(r["region"] == "Trentino-Alto Adige" for r in radar if r["set"] == "idrogeo") == 1485
    assert sum(r["radar_exceedance"] == str(NO_EVENT) for r in radar) == 1056
    assert sum(r["radar_exceedance"] == "" for r in radar) == 92


@pytest.mark.parametrize(
    ("liguria", "landslides", "gauge", "radar_above"),
    [(True, 971, 928, 641), (False, 250, 235, 93)],
)
def test_same_landslides_at_the_gauge_and_on_the_radar(
    radar: list[dict[str, str]], liguria: bool, landslides: int, gauge: int, radar_above: int
) -> None:
    rows = [
        r
        for r in radar
        if r["gauge_exceedance"] and r["radar_exceedance"] and (liguria or r["region"] != "Liguria")
    ]
    assert len(rows) == landslides
    assert sum(float(r["gauge_exceedance"]) > 0 for r in rows) == gauge
    assert sum(float(r["radar_exceedance"]) > 0 for r in rows) == radar_above


def test_the_radar_reads_less_than_the_gauge(radar: list[dict[str, str]]) -> None:
    from statistics import median

    rows = [r for r in radar if r["gauge_mm"] and r["radar_mm_same_duration"]]
    assert len(rows) == 970
    ratio = [float(r["radar_mm_same_duration"]) / float(r["gauge_mm"]) for r in rows]
    assert median(ratio) == pytest.approx(0.68, abs=0.005)
    assert median(
        x for r, x in zip(rows, ratio, strict=True) if r["region"] != "Liguria"
    ) == pytest.approx(0.51, abs=0.005)
    corrected = [x * float(r["bias_factor"]) for r, x in zip(rows, ratio, strict=True)]
    assert median(corrected) == pytest.approx(0.46, abs=0.005)


def _in_group(row: dict[str, str], group: str) -> bool:
    if group == "all":
        return True
    if group.startswith("without "):
        return row["region"] != group.removeprefix("without ")
    return row["macroregion"] == group


def test_groups_recomputed_from_the_landslides(
    radar: list[dict[str, str]], groups: list[dict[str, str]]
) -> None:
    checked = 0
    for g in groups:
        if "reliability" in g["group"]:
            continue
        column = "radar_exceedance" if g["rain"] == "radar" else "radar_corrected_exceedance"
        scores = [
            _num(r[column]) for r in radar if r["set"] == g["set"] and _in_group(r, g["group"])
        ]
        above, ordinary = int(g["ordinary_above"]), int(g["ordinary"])
        # The ordinary moments are not in the file: only how many were above T5.
        s = skill(scores, [1.0] * above + [-1.0] * (ordinary - above), cutoff=1e-9)
        assert s.landslides == int(g["landslides"])
        measured = [x for x in scores if x is not None]
        # Scores and cutoffs are rounded to four decimals: a tie may move one landslide.
        assert abs(s.caught - int(g["landslides_above"])) <= 1
        for share in ("2", "5"):
            caught = sum(x >= float(g[f"cutoff_{share}"]) for x in measured)
            assert abs(caught - int(g[f"caught_{share}"])) <= 1
        checked += 1
    assert checked == 20


@pytest.mark.parametrize(
    ("which", "landslides", "above", "ordinary_share", "caught_2", "auc_"),
    [
        ("e-italica", 1053, 643, 0.097, 354, 0.85),
        ("idrogeo", 3055, 1074, 0.057, 645, 0.73),
    ],
)
def test_radar_against_ordinary_moments(
    groups: list[dict[str, str]],
    which: str,
    landslides: int,
    above: int,
    ordinary_share: float,
    caught_2: int,
    auc_: float,
) -> None:
    (g,) = [x for x in groups if (x["set"], x["group"], x["rain"]) == (which, "all", "radar")]
    assert (int(g["landslides"]), int(g["landslides_above"])) == (landslides, above)
    assert int(g["ordinary_above"]) / int(g["ordinary"]) == pytest.approx(ordinary_share, abs=5e-4)
    assert int(g["caught_2"]) == caught_2
    assert float(g["auc"]) == pytest.approx(auc_, abs=0.005)
    (c,) = [
        x for x in groups if (x["set"], x["group"], x["rain"]) == (which, "all", "radar corrected")
    ]
    # The bias factor moves the cutoff, not the order.
    assert abs(float(c["auc"]) - float(g["auc"])) < 0.005
    assert abs(int(c["caught_2"]) - caught_2) <= 13


@pytest.mark.parametrize(
    ("which", "alpha", "beta"), [("e-italica", 0.57, 0.18), ("idrogeo", 0.42, 0.19)]
)
def test_a_threshold_fitted_on_radar_rain_is_not_t5(
    radar: list[dict[str, str]], which: str, alpha: float, beta: float
) -> None:
    from rainfall_thresholds import ITALICA_T5, fit_threshold

    events = [
        (float(r["radar_duration_h"]), float(r["radar_mm"]) / float(r["radar_duration_h"]))
        for r in radar
        if r["set"] == which and r["radar_duration_h"]
    ]
    fitted = fit_threshold(events).threshold
    assert fitted.alpha == pytest.approx(alpha, abs=0.005)
    assert fitted.beta == pytest.approx(beta, abs=0.005)
    assert fitted.alpha < ITALICA_T5["italy"].alpha / 10
