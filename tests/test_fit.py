from __future__ import annotations

import math
import random

import pytest

from rainfall_thresholds import fit_threshold, percentile_of


def test_points_on_a_line_give_that_line() -> None:
    pairs = [(d, 10.0 * d**-0.5) for d in (1, 2, 4, 8, 16, 32)]
    fit = fit_threshold(pairs, percentile=5)
    assert fit.threshold.alpha == pytest.approx(10.0)
    assert fit.threshold.beta == pytest.approx(0.5)
    assert fit.central == fit.threshold
    assert fit.n_events == 6


def test_the_percentile_lowers_the_line_and_keeps_the_slope() -> None:
    rng = random.Random(42)
    pairs = []
    for _ in range(2000):
        d = 10 ** rng.uniform(0, 2)
        pairs.append((d, 8.0 * d**-0.6 * 10 ** rng.gauss(0, 0.2)))
    t5 = fit_threshold(pairs, percentile=5)
    t50 = fit_threshold(pairs, percentile=50)
    assert t5.threshold.beta == pytest.approx(t50.threshold.beta)
    assert t5.threshold.beta == pytest.approx(0.6, abs=0.02)
    # A Gaussian 5th percentile is 1.645 sigma below the mean.
    assert math.log10(t50.threshold.alpha / t5.threshold.alpha) == pytest.approx(
        1.645 * 0.2, abs=0.02
    )
    below = sum(i < t5.threshold.intensity(d) for d, i in pairs)
    assert below / len(pairs) == pytest.approx(0.05, abs=0.001)


def test_pairs_without_a_logarithm_are_skipped() -> None:
    pairs = [(1.0, 10.0), (4.0, 5.0), (16.0, 2.5), (0.0, 3.0), (5.0, 0.0)]
    assert fit_threshold(pairs).n_events == 3


def test_too_few_events_is_an_error() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        fit_threshold([(1.0, 10.0), (4.0, 5.0)])


def test_a_single_duration_has_no_slope() -> None:
    with pytest.raises(ValueError, match="same duration"):
        fit_threshold([(6.0, 1.0), (6.0, 2.0), (6.0, 3.0)])


@pytest.mark.parametrize("p", [0.0, 100.0, -5.0])
def test_percentile_must_be_inside_the_range(p: float) -> None:
    with pytest.raises(ValueError, match="percentile"):
        fit_threshold([(1.0, 10.0), (4.0, 5.0), (16.0, 2.5)], percentile=p)


def test_percentile_of_interpolates_like_numpy() -> None:
    values = [3.0, 1.0, 4.0, 1.5, 5.0]
    assert percentile_of(values, 0) == 1.0
    assert percentile_of(values, 100) == 5.0
    assert percentile_of(values, 50) == 3.0
    assert percentile_of(values, 10) == pytest.approx(1.2)  # numpy.percentile(values, 10)
