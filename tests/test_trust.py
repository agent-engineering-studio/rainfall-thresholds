"""How well the threshold is calibrated in each region, recomputed from e-ITALICA."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from rainfall_thresholds import (
    CALIBRATION,
    EXPECTED_BELOW,
    ITALICA_T5,
    MACROREGIONS,
    Calibration,
    calibration_of,
    macroregion_of,
    percentile_of,
)

FIXTURE = Path(__file__).parent / "fixtures" / "italica_v4_dur_rain.csv"


def _recomputed() -> dict[str, Calibration]:
    by_region: dict[str, list[tuple[float, float]]] = {}
    with FIXTURE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = float(row["duration_h"])
            by_region.setdefault(row["region"], []).append(
                (d, float(row["cumulated_rainfall_mm"]) / d)
            )
    out = {}
    for region, events in by_region.items():
        macroregion = macroregion_of(region)
        assert macroregion is not None
        line = ITALICA_T5[macroregion]
        durations = [d for d, _ in events]
        out[region] = Calibration(
            region=region,
            macroregion=macroregion,
            events=len(events),
            below=sum(i < line.intensity(d) for d, i in events),
            duration_hours=(
                round(percentile_of(durations, 5), 1),
                round(percentile_of(durations, 95), 1),
            ),
        )
    return out


def test_the_table_is_what_the_catalogue_gives() -> None:
    assert dict(CALIBRATION) == _recomputed()
    assert set(CALIBRATION) == set().union(*MACROREGIONS.values())
    assert sum(c.events for c in CALIBRATION.values()) == 5974


def test_the_expected_share_is_the_percentile_of_the_fit() -> None:
    assert EXPECTED_BELOW == 0.05
    below = sum(c.below for c in CALIBRATION.values())
    assert below / 5974 == pytest.approx(0.05, abs=0.002)  # three fits, each at 5 %


def test_valle_d_aosta_sits_under_a_line_that_is_high_for_it() -> None:
    c = calibration_of("Valle d'Aosta")
    assert c is not None
    assert (c.events, c.below) == (68, 11)
    assert c.below_share == pytest.approx(0.162, abs=0.001)
    low, high = c.interval()
    assert low > EXPECTED_BELOW
    assert low == pytest.approx(0.093, abs=0.001)
    assert high == pytest.approx(0.267, abs=0.001)
    assert c.position == "high"


def test_calabria_sits_over_a_line_that_is_low_for_it() -> None:
    c = calibration_of(18)
    assert c is not None and c.region == "Calabria"
    assert (c.events, c.below) == (298, 4)
    assert c.interval()[1] < EXPECTED_BELOW
    assert c.position == "low"


def test_seventeen_landslides_cannot_tell() -> None:
    """Molise: one landslide in 17 under the line, and an interval from 1 % to 27 %."""
    c = calibration_of("Molise")
    assert c is not None and (c.events, c.below) == (17, 1)
    low, high = c.interval()
    assert low < 0.02 and high > 0.25
    assert c.position == "as fitted"


def test_an_unknown_region_has_no_calibration() -> None:
    assert calibration_of("Corsica") is None
    assert calibration_of(21) is None
    assert calibration_of(True) is None


def test_the_interval_takes_its_z() -> None:
    c = Calibration("X", "northern", events=100, below=5, duration_hours=(1.0, 2.0))
    narrow, wide = c.interval(z=1.0), c.interval(z=2.576)
    assert wide[0] < narrow[0] < 0.05 < narrow[1] < wide[1]
    with pytest.raises(ValueError, match="z"):
        c.interval(z=0.0)
