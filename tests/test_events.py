from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rainfall_thresholds import (
    ITALICA_T5,
    RainfallEvent,
    latest_event,
    reconstruct_events,
    strongest_event,
)

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


# --- Hours not measured -----------------------------------------------------------


def gappy(values: list[float | None]) -> list[RainfallEvent]:
    series = [(T0 + timedelta(hours=i), v) for i, v in enumerate(values)]
    return reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)


def test_an_hour_not_measured_is_not_dry() -> None:
    (only,) = gappy([5, None, None, None, None, None, None, 5])
    assert only.total_mm == 10.0
    assert only.duration_hours == 8.0
    assert only.unmeasured_hours == 6
    assert not only.fully_measured


def test_measured_dry_hours_still_break_around_a_gap() -> None:
    # 3 dry + 1 not measured + 3 dry: six measured dry hours close the event.
    assert len(gappy([5, 0, 0, 0, None, 0, 0, 0, 5])) == 2


def test_gaps_outside_the_event_are_not_counted() -> None:
    (only,) = gappy([None, None, 4, 0, None, *[0] * 6])
    assert only.unmeasured_hours == 0
    assert only.fully_measured


def test_a_series_never_measured_has_no_events() -> None:
    assert gappy([None, None, None]) == []


def test_the_source_is_carried() -> None:
    (only,) = reconstruct_events(
        hourly([0, 4, 3]), no_rain_break_hours=6, min_event_mm=2.0, source="DPC SRT1"
    )
    assert only.source == "DPC SRT1"
    assert events([4])[0].source is None


# --- Which event --------------------------------------------------------------------


def test_the_strongest_event_is_the_storm_not_the_drizzle_after_it() -> None:
    storm_then_drizzle = events([20, 30, 40, 20, *[0] * 6, 1.0, 1.5])
    assert len(storm_then_drizzle) == 2
    threshold = ITALICA_T5["southern"]
    assert latest_event(storm_then_drizzle) is storm_then_drizzle[1]
    assert strongest_event(storm_then_drizzle, threshold) is storm_then_drizzle[0]
    assert strongest_event([], threshold) is None


def test_ties_go_to_the_event_that_ended_last() -> None:
    same = events([4, *[0] * 6, 4])
    assert strongest_event(same, ITALICA_T5["italy"]) is same[1]
