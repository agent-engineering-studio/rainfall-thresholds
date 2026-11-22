from __future__ import annotations

import pytest

from rainfall_thresholds.check import Misquote, check_text, facts_of, parse_number

FACTS = {
    "strongest": {
        "duration_h": 35.0,
        "total_mm": 165.7,
        "intensity_mm_h": 4.73,
        "needed_mm": 30.9,
        "exceedance_decades": 0.73,
        "unmeasured_h": 0,
        "start": "2026-10-09T12:00:00+00:00",
    },
    "threshold": {"alpha": 8.754, "beta": 0.6449, "percentile": 5, "landslides": 1425},
    "above_threshold": True,
    "events": [{"total_mm": 2.5, "exceedance_decades": -0.65}],
}


def faults(text: str, question: str = "") -> list[tuple[str, str]]:
    return [(m.text, m.fault) for m in check_text(text, FACTS, question=question)]


def test_a_faithful_text_passes() -> None:
    text = (
        "On 10 October 2026 at 03:00 Melito got 165.7 mm in 35 h, 4.73 mm/h on average: "
        "+0.73 decades above T5, which asks 30.9 mm. The drizzle after it, 2.5 mm, "
        "was -0.65. T5 is fitted on 1,425 landslides; 5 % sit below it."
    )
    assert faults(text) == []


def test_fewer_decimals_and_round_numbers_are_fine() -> None:
    assert faults("about 166 mm in 35 hours, against 31 mm; 1,400 landslides") == []


def test_a_total_written_as_an_intensity_is_a_unit_fault() -> None:
    got = check_text("the threshold asks 30.9 mm/h", FACTS)
    assert got == [Misquote("30.9 mm/h", "mm/h", "unit", "strongest.needed_mm = 30.9 mm")]


def test_invented_and_badly_rounded_numbers() -> None:
    assert faults("about 0.8 decades above, 172 mm in total") == [
        ("0.8 decades", "rounded"),
        ("172 mm", "invented"),
    ]
    assert faults("only 20 mm") == [("20 mm", "invented")]
    # A unit with no fact near it is invented, even if a unitless fact is close.
    assert faults("9 hours missing") == [("9 hours", "invented")]  # alpha 8.754 is unitless


def test_numbers_of_the_question_are_not_checked() -> None:
    assert faults("over 48 hours it is fine", question="what about 48 hours?") == []


def test_parse_number() -> None:
    assert parse_number("1,603") == (1603.0, 0)
    assert parse_number("2,5") == (2.5, 1)
    assert parse_number("1.603,5") == (1603.5, 1)
    assert parse_number("1.234.567") == (1234567.0, 0)
    assert parse_number("0.506") == (0.506, 3)
    assert parse_number("1.603") == (1.603, 3)
    assert parse_number("\u22120.65") == (-0.65, 2)


def test_facts_of_reads_units_from_keys() -> None:
    units = {p: u for p, _, u in facts_of(FACTS)}
    assert units["strongest.total_mm"] == "mm"
    assert units["strongest.intensity_mm_h"] == "mm/h"
    assert units["strongest.duration_h"] == "h"
    assert units["strongest.exceedance_decades"] == "decades"
    assert units["threshold.alpha"] is None
    assert "above_threshold" not in units
    assert {p for p, _, _ in facts_of({"a_pct": 3, "b": float("inf"), "c": None})} == {"a_pct"}


@pytest.mark.parametrize("unit", ["mm", "millimetres", "MM"])
def test_unit_spellings(unit: str) -> None:
    assert faults(f"165.7 {unit}") == []
