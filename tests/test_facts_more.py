"""The facts of 0.5: how much to trust, rain still needed, published thresholds."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from rainfall_thresholds import ITALICA_T5
from rainfall_thresholds.check import check_text
from rainfall_thresholds.facts import RULE, margin_facts, published_facts, trust_facts

T0 = datetime(2026, 10, 10, tzinfo=UTC)


def _series(values: Sequence[float | None]) -> list[tuple[datetime, float | None]]:
    return [(T0 + timedelta(hours=k), v) for k, v in enumerate(values)]


def test_trust_facts_of_a_region_where_the_line_is_high() -> None:
    f = trust_facts("Valle d'Aosta")
    assert f["threshold"]["macroregion"] == "northern"
    assert (f["landslides"], f["below_threshold"]) == (68, 11)
    assert (f["below_share_pct"], f["expected_pct"]) == (16.2, 5.0)
    assert f["interval_pct"] == [9.3, 26.7]
    assert (f["fitted_from_h"], f["fitted_to_h"]) == (3.0, 254.0)
    assert f["position"] == "high" and "misses more" in f["reading"]
    assert f["rule"] == RULE


def test_trust_facts_say_when_the_landslides_are_too_few_to_tell() -> None:
    f = trust_facts("14")  # Molise, by ISTAT code
    assert f["region"] == "Molise" and f["landslides"] == 17 and f["position"] == "as fitted"
    assert "17 landslides" in f["reading"]
    assert trust_facts("Calabria")["position"] == "low"
    with pytest.raises(ValueError, match="unknown region"):
        trust_facts("southern")  # a macroregion is not a place


def test_a_faithful_text_about_trust_passes_the_check() -> None:
    f = trust_facts("Valle d'Aosta")
    assert not check_text("11 of 68 landslides are below the line: 16.2 %, not 5 %.", f)
    assert [m.fault for m in check_text("As many as 38 % are below the line.", f)] == ["invented"]


def test_margin_facts_of_an_event_still_going() -> None:
    f = margin_facts(_series([0.0, 0.0, 3.0, 4.0, 3.0]), "Calabria", source="rain gauge")
    line = ITALICA_T5["southern"]
    assert f["event"]["total_mm"] == 10.0 and f["event"]["duration_h"] == 3.0
    assert f["going_on"] is True
    assert [n["more_h"] for n in f["needed"]] == [1, 3, 6]
    assert f["needed"][1] == {
        "more_h": 3,
        "duration_h": 6.0,
        "threshold_mm": round(line.cumulated(6.0), 1),
        "needed_mm": round(line.cumulated(6.0) - 10.0, 1),
    }
    assert f["rule"] == RULE and f["notes"] == [
        "It supposes the rain does not stop: after 6 dry hours the event is over "
        "and the count starts again."
    ]


def test_margin_facts_after_the_event_is_over_start_from_nothing() -> None:
    f = margin_facts(
        _series([5.0, 5.0] + [0.0] * 6), "Calabria", source="rain gauge", more_hours=(6,)
    )
    assert f["event"] is None and f["going_on"] is False
    assert f["needed"][0]["needed_mm"] == round(ITALICA_T5["southern"].cumulated(6.0), 1)


def test_margin_facts_flag_rain_that_is_not_gauge_rain_and_hours_not_measured() -> None:
    f = margin_facts(_series([3.0, None, 4.0]), "Calabria", source="DPC SRT1")
    assert f["event"]["unmeasured_h"] == 1
    assert any("lower bound" in n for n in f["notes"])
    assert any("not validated" in n for n in f["notes"])


def test_published_facts_of_a_region_with_a_threshold_of_its_own() -> None:
    f = published_facts("Calabria")
    assert [t["id"] for t in f["published"]] == ["calabria-t5"]
    t = f["published"][0]
    assert (t["alpha"], t["beta"]) == (8.6, 0.59) and t["license"] == "CC BY 3.0"
    assert "Vennari" in t["citation"] and t["url"].startswith("https://nhess")
    assert t["at_24_h"]["cumulated_mm"] == round(8.6 * 24**0.41, 1)
    assert f["this_package"]["at_24_h"]["cumulated_mm"] == round(
        ITALICA_T5["southern"].cumulated(24), 1
    )
    assert f["rule"] == RULE


def test_published_facts_of_a_region_with_none_say_so() -> None:
    f = published_facts("Lombardia")
    assert f["published"] == [] and "no published threshold" in f["notes"][0]
    with pytest.raises(ValueError, match="unknown region"):
        published_facts("Corsica")
