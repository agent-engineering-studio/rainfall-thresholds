"""Rain still needed, the total against the place's own climate, and the record."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jsonschema
import limen_reference as limen
import pytest

import rainfall_thresholds
from rainfall_thresholds import (
    ITALICA_T5,
    RainfallEvent,
    event_against_threshold,
    rain_to_threshold,
    relative_total,
)

T0 = datetime(2026, 10, 1, tzinfo=UTC)
SCHEMA = json.loads(
    (Path(__file__).parent / "fixtures" / "opendata-record-v2.json").read_text(encoding="utf-8")
)


# --- Rain still needed ------------------------------------------------------------


def test_rain_to_threshold_is_what_the_line_asks_at_the_longer_duration() -> None:
    line = ITALICA_T5["southern"]
    event = RainfallEvent(T0, T0 + timedelta(hours=5), 6.0, 10.0)
    needed = rain_to_threshold(event, line, more_hours=(0, 3, 6))
    assert needed == {
        0: pytest.approx(line.cumulated(6.0) - 10.0),
        3: pytest.approx(line.cumulated(9.0) - 10.0),
        6: pytest.approx(line.cumulated(12.0) - 10.0),
    }
    assert needed[0] < needed[3] < needed[6]  # the line asks more of a longer event


def test_an_event_above_the_line_needs_nothing_until_the_line_catches_up() -> None:
    line = ITALICA_T5["southern"]
    event = RainfallEvent(T0, T0 + timedelta(hours=5), 6.0, 40.0)
    assert line.cumulated(6.0) < 40.0 < line.cumulated(200.0)
    needed = rain_to_threshold(event, line, more_hours=(0, 3, 200 - 6))
    assert (needed[0], needed[3]) == (0.0, 0.0)
    assert needed[194] == pytest.approx(line.cumulated(200.0) - 40.0)


def test_rain_to_threshold_with_no_event_starts_from_nothing() -> None:
    line = ITALICA_T5["italy"]
    assert rain_to_threshold(None, line, more_hours=(1, 6)) == {
        1: pytest.approx(line.cumulated(1.0)),
        6: pytest.approx(line.cumulated(6.0)),
    }
    with pytest.raises(ValueError, match="more_hours"):
        rain_to_threshold(None, line, more_hours=(0,))  # no event and no hours: no duration


def test_rain_to_threshold_on_radar_rain_and_bad_hours() -> None:
    line = ITALICA_T5["italy"]
    event = RainfallEvent(T0, T0, 1.0, 1.0)
    gauge = rain_to_threshold(event, line, more_hours=(3,))[3]
    radar = rain_to_threshold(event, line, more_hours=(3,), radar_gauge_factor=0.68)[3]
    assert radar == pytest.approx(0.68 * line.cumulated(4.0) - 1.0) and radar < gauge
    with pytest.raises(ValueError, match="more_hours"):
        rain_to_threshold(event, line, more_hours=(-1,))


# --- The total against the place's own climate (limen#243) -----------------------


def _samples(seed: int, hours: int) -> list[tuple[datetime, float]]:
    rng = random.Random(seed)
    return [
        (T0 + timedelta(hours=k), round(rng.choice([0.0, 0.0, rng.uniform(0, 9)]), 1))
        for k in range(1, hours + 1)
    ]


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("riduzione", [0.0, 0.3])
@pytest.mark.parametrize(
    ("durate", "lunghe"),
    [((), {}), ((72, 168), {72: 95.0, 168: 140.0}), ((72, 168), {168: 60.0})],
)
def test_relative_total_is_limens(
    seed: int, riduzione: float, durate: tuple[int, ...], lunghe: dict[int, float]
) -> None:
    samples = _samples(seed, 200)
    end = T0 + timedelta(hours=190)
    theirs = limen.cumulata_norm(
        samples,
        end,
        window_hours=24,
        saturazione=1.2,
        durate_lunghe=durate,
        riferimento=48.0,
        riferimento_lunghe=lunghe,
        riduzione=riduzione,
    )
    ours = relative_total(
        dict(samples),
        end,
        window_hours=24,
        reference_mm=48.0,
        saturation=1.2,
        reduction=riduzione,
        longer_references_mm={d: lunghe[d] for d in durate if d in lunghe},
    )
    assert ours == theirs
    assert ours is not None and 0.0 <= ours <= 1.0


def test_relative_total_of_no_hour_is_not_known() -> None:
    """No hour read in the window is rain not read, not no rain: Limen's rule."""
    kwargs: dict[str, Any] = {"window_hours": 24, "reference_mm": 48.0, "saturation": 1.0}
    assert relative_total({}, T0, **kwargs) is None
    assert relative_total({T0: None}, T0, **kwargs) is None
    assert limen.cumulata_norm(
        [], T0, window_hours=24, saturazione=1.0, durate_lunghe=(), riferimento=48.0,
        riferimento_lunghe={}, riduzione=0.0,
    ) is None  # fmt: skip


def test_relative_total_reads_measured_hours_only_and_saturates() -> None:
    hours = {T0 - timedelta(hours=1): 12.0, T0: None, T0 - timedelta(hours=30): 500.0}
    assert relative_total(hours, T0, window_hours=24, reference_mm=48.0, saturation=1.0) == 0.25
    assert relative_total(hours, T0, window_hours=24, reference_mm=6.0, saturation=1.0) == 1.0
    with pytest.raises(ValueError, match="reference_mm"):
        relative_total(hours, T0, window_hours=24, reference_mm=0.0, saturation=1.0)
    with pytest.raises(ValueError, match="reduction"):
        relative_total(hours, T0, window_hours=24, reference_mm=6.0, saturation=1.0, reduction=1.0)


# --- The assessment as a record of opendata-record/v2 --------------------------------

WHERE = {"type": "Point", "coordinates": [14.1205, 40.8225]}


def _assessment() -> Any:
    """The fixed series of egms-client's contract (tests/contracts.py, ASSESSMENT)."""
    mm = [2.0, 5.5, 9.0, None, 12.5, 7.0, 3.0, 1.5]
    hours = {
        datetime(2026, 11, 20, 7, tzinfo=UTC) + timedelta(hours=k): v for k, v in enumerate(mm)
    }
    return event_against_threshold(
        hours, ITALICA_T5["southern"], no_rain_break_hours=48, min_event_mm=1.0, source="rain gauge"
    )


def test_the_record_is_valid_and_carries_the_contract_numbers() -> None:
    record = _assessment().as_record(where=WHERE, licence="CC0-1.0")
    jsonschema.Draft202012Validator(SCHEMA).validate(record)
    assert record["schema"] == "opendata-record/v2" and record["kind"] == "fact"
    assert record["made_by"] == {
        "name": "rainfall-thresholds",
        "version": rainfall_thresholds.__version__,
    }
    assert record["source"] == {"name": "rain gauge", "licence": "CC0-1.0"}
    # The hours are labelled by their end: the event begins an hour before its first.
    assert record["time"] == {
        "first": "2026-11-20T06:00:00Z",
        "last": "2026-11-20T14:00:00Z",
        "exact": True,
    }
    assert record["where"] == WHERE
    values = {k: v["value"] for k, v in record["values"].items()}
    assert values == {
        "duration": 8.0,
        "total": 40.5,
        "intensity": 5.0625,
        "threshold_intensity": pytest.approx(2.2898329986183925),
        "threshold_total": pytest.approx(18.31866398894714),
        "threshold_alpha": 8.754,
        "threshold_beta": 0.6449,
        "ratio": pytest.approx(2.210859919939376),
        "excess_decades": pytest.approx(0.34456122655673416),
        "unmeasured_hours": 1,
        "borders_unmeasured": True,
        "at_least": True,
        "rain_source": "rain gauge",
    }
    assert record["reliability"]["reliable"] is False
    assert record["reliability"]["reasons"] == ["hours_not_measured", "borders_not_measured"]
    assert "not an alert" in record["notes"][0]


def test_a_fully_measured_event_is_a_reliable_record_with_no_place() -> None:
    hours = {T0 + timedelta(hours=k): v for k, v in enumerate([0.0, 0.0, 4.0, 6.0, 0.0, 0.0])}
    a = event_against_threshold(
        hours, ITALICA_T5["italy"], no_rain_break_hours=2, min_event_mm=1.0, source="DPC SRT1"
    )
    assert a is not None
    record = a.as_record(where=None, licence="CC BY 4.0")
    jsonschema.Draft202012Validator(SCHEMA).validate(record)
    assert record["reliability"]["reliable"] is True and record["reliability"]["reasons"] == []
    assert record["where"] is None


def test_no_name_of_the_record_reads_as_a_verdict() -> None:
    """The schema's rule: no key says alert, alarm, warning or risk."""
    record = _assessment().as_record(where=WHERE, licence="CC0-1.0")

    def keys(node: Any) -> list[str]:
        if isinstance(node, dict):
            return [*node, *(k for v in node.values() for k in keys(v))]
        return []

    assert not [
        k for k in keys(record) if any(w in k for w in ("alert", "alarm", "warning", "risk"))
    ]


def test_a_record_wants_to_know_where_the_rain_comes_from() -> None:
    hours = {T0: 5.0}
    a = event_against_threshold(hours, ITALICA_T5["italy"], no_rain_break_hours=2, min_event_mm=1.0)
    assert a is not None and a.event.source is None
    with pytest.raises(ValueError, match="source"):
        a.as_record(where=None, licence="CC0-1.0")
