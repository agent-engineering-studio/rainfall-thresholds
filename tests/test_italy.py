"""The Italian thresholds are refitted from e-ITALICA, not trusted as constants.

``fixtures/italica_v4_dur_rain.csv`` is e-ITALICA v4 (Brunetti et al. 2024,
doi:10.5281/zenodo.14204473, CC BY 4.0) reduced to the id, region, duration
and cumulated rainfall of the 5,974 events where both values are positive.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from rainfall_thresholds import ITALICA_T5, MACROREGIONS, fit_threshold, macroregion_of

FIXTURE = Path(__file__).parent / "fixtures" / "italica_v4_dur_rain.csv"


@pytest.fixture(scope="module")
def catalogue() -> list[tuple[str, float, float]]:
    with FIXTURE.open(encoding="utf-8") as f:
        return [
            (
                row["region"],
                float(row["duration_h"]),
                float(row["cumulated_rainfall_mm"]) / float(row["duration_h"]),
            )
            for row in csv.DictReader(f)
        ]


def test_the_fixture_is_the_whole_usable_catalogue(
    catalogue: list[tuple[str, float, float]],
) -> None:
    assert len(catalogue) == 5974
    assert {r for r, _, _ in catalogue} == set().union(*MACROREGIONS.values())


@pytest.mark.parametrize("name", ["italy", "northern", "central", "southern"])
def test_each_threshold_is_the_fit_of_its_regions(
    name: str, catalogue: list[tuple[str, float, float]]
) -> None:
    regions = MACROREGIONS.get(name)
    pairs = [(d, i) for r, d, i in catalogue if regions is None or r in regions]
    fit = fit_threshold(pairs, percentile=5)
    assert fit.threshold.alpha == pytest.approx(ITALICA_T5[name].alpha, abs=5e-4)
    assert fit.threshold.beta == pytest.approx(ITALICA_T5[name].beta, abs=5e-5)


def test_five_percent_of_the_events_sit_below_the_national_line(
    catalogue: list[tuple[str, float, float]],
) -> None:
    t5 = ITALICA_T5["italy"]
    below = sum(i < t5.intensity(d) for _, d, i in catalogue)
    assert below / len(catalogue) == pytest.approx(0.05, abs=0.001)


def test_macroregion_of() -> None:
    assert macroregion_of("Abruzzo") == "central"
    assert macroregion_of("Basilicata") == "southern"
    assert macroregion_of("Liguria") == "northern"
    assert macroregion_of("Corsica") is None
