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
