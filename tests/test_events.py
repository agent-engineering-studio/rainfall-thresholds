from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rainfall_thresholds import RainfallEvent, latest_event, reconstruct_events

T0 = datetime(2026, 6, 1, tzinfo=UTC)


def hourly(values: list[float]) -> list[tuple[datetime, float]]:
    return [(T0 + timedelta(hours=i), v) for i, v in enumerate(values)]


def events(values: list[float]) -> list[RainfallEvent]:
    return reconstruct_events(hourly(values), no_rain_break_hours=6, min_event_mm=2.0)


def test_a_long_dry_gap_splits_the_series() -> None:
    got = events([2, 3, 2, *[0] * 11, 4, 3, 2])
    assert [e.total_mm for e in got] == [7.0, 9.0]
    assert got[0].start == T0 and got[0].end == T0 + timedelta(hours=2)
    assert got[0].duration_hours == 3.0
    assert got[1].start == T0 + timedelta(hours=14)


def test_a_short_dry_gap_does_not() -> None:
    (only,) = events([2, 0, 0, 0, 0, 0, 3])
    assert only.total_mm == 5.0
    assert only.duration_hours == 7.0  # first to last wet hour, both included
    assert only.intensity_mm_h == pytest.approx(5.0 / 7.0)


def test_a_gap_exactly_at_the_break_splits() -> None:
    assert len(events([2, 0, 0, 0, 0, 0, 0, 3])) == 2


def test_events_below_the_minimum_are_dropped() -> None:
    assert events([0.5, 0.5, *[0] * 6]) == []
    assert [e.total_mm for e in events([0.5, *[0] * 6, 3])] == [3.0]


def test_one_wet_hour_is_a_one_hour_event() -> None:
    (only,) = events([0, 0, 4, 0])
    assert only.duration_hours == 1.0 and only.intensity_mm_h == 4.0


def test_an_event_still_raining_at_the_end_is_kept() -> None:
    (only,) = events([0, 0, 3, 3])
    assert only.end == T0 + timedelta(hours=3)


def test_order_of_the_input_does_not_matter() -> None:
    series = hourly([2, 3, 2, *[0] * 11, 4, 3, 2])
    shuffled = series[::2] + series[1::2]
    assert reconstruct_events(shuffled, no_rain_break_hours=6, min_event_mm=2.0) == events(
        [2, 3, 2, *[0] * 11, 4, 3, 2]
    )


def test_empty_and_dry_series_have_no_events() -> None:
    assert events([]) == []
    assert events([0, 0, 0]) == []


def test_negative_rainfall_is_refused() -> None:
    with pytest.raises(ValueError, match="negative rainfall"):
        events([1, -1])


def test_the_break_must_be_at_least_an_hour() -> None:
    with pytest.raises(ValueError, match="no_rain_break_hours"):
        reconstruct_events(hourly([1]), no_rain_break_hours=0, min_event_mm=0.0)


def test_latest_event_is_the_one_that_ended_last() -> None:
    got = events([2, 3, 2, *[0] * 11, 4, 3, 2])
    assert latest_event(got) is got[1]
    assert latest_event(reversed(got)) is got[1]
    assert latest_event([]) is None
