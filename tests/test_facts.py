from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rainfall_thresholds import ITALICA_T5
from rainfall_thresholds.facts import (
    ALERT_URL,
    ITALICA_EVENTS,
    RULE,
    assess_facts,
    fit_facts,
    resolve,
    threshold_facts,
)

T0 = datetime(2026, 10, 10, tzinfo=UTC)


def series(values: list[float | None]) -> list[tuple[datetime, float | None]]:
    return [(T0 + timedelta(hours=i), v) for i, v in enumerate(values)]


def test_every_answer_carries_the_rule() -> None:
    assert ALERT_URL in RULE and "not an alert" in RULE
    assert threshold_facts("italy", 24)["rule"] == RULE
    assert assess_facts(series([0]), "italy")["rule"] == RULE
    assert fit_facts([(1, 10), (10, 30), (100, 90)])["rule"] == RULE


def test_regions_resolve_like_e_italica() -> None:
    assert resolve("Abruzzo") == "central"
    assert resolve("southern") == "southern"
    with pytest.raises(ValueError, match="unknown region"):
        resolve("Bavaria")


def test_threshold_facts() -> None:
    f = threshold_facts("Liguria", 24)
    assert f["threshold"]["macroregion"] == "northern"
    assert f["threshold"]["landslides"] == ITALICA_EVENTS["northern"] == 2659
    assert f["cumulated_mm"] == 30.0
    assert f["intensity_mm_h"] == 1.25


def test_assess_reads_the_storm_and_flags_what_it_cannot_vouch_for() -> None:
    f = assess_facts(series([20, 30, None, 20, *[0] * 6, 1.0, 1.5]), "Calabria", source="radar")
    assert len(f["events"]) == 2
    storm = f["strongest"]
    assert storm["total_mm"] == 70.0 and storm["unmeasured_h"] == 1
    t = ITALICA_T5["southern"]
    assert storm["exceedance_decades"] == round(t.exceedance(70 / 4, 4), 2)
    assert f["above_threshold"] is True
    assert any("not gauge rain" in n for n in f["notes"])
    assert any("lower bound" in n for n in f["notes"])


def test_assess_with_gauge_rain_and_no_event() -> None:
    f = assess_facts(series([0, 0, 0]), "italy", source="rain gauge")
    assert f["strongest"] is None and f["above_threshold"] is None
    assert f["notes"] == []


def test_fit_facts_skips_zero_durations() -> None:
    f = fit_facts([(0, 5), (1, 10), (10, 30), (100, 90)], percentile=5)
    assert f["landslides"] == 3
