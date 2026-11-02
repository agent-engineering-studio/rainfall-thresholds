from __future__ import annotations

import math

import pytest

from rainfall_thresholds import PowerLawThreshold

T = PowerLawThreshold(alpha=7.19, beta=0.568)


def test_intensity_is_the_power_law() -> None:
    assert T.intensity(1.0) == pytest.approx(7.19)
    assert T.intensity(24.0) == pytest.approx(7.19 * 24.0**-0.568)
    assert T.intensity(1.0) / T.intensity(24.0) == pytest.approx(24.0**0.568)


def test_cumulated_is_intensity_times_duration() -> None:
    assert T.cumulated(48.0) == pytest.approx(T.intensity(48.0) * 48.0)


def test_exceedance_counts_decades() -> None:
    on_the_line = T.intensity(6.0)
    assert T.exceedance(on_the_line, 6.0) == pytest.approx(0.0)
    assert T.exceedance(on_the_line * 10, 6.0) == pytest.approx(1.0)
    assert T.exceedance(on_the_line / 10, 6.0) == pytest.approx(-1.0)


def test_a_dry_event_is_infinitely_below() -> None:
    assert T.exceedance(0.0, 6.0) == -math.inf


@pytest.mark.parametrize("duration", [0.0, -1.0])
def test_duration_must_be_positive(duration: float) -> None:
    with pytest.raises(ValueError, match="duration_hours"):
        T.intensity(duration)
    with pytest.raises(ValueError, match="duration_hours"):
        T.cumulated(duration)


def test_negative_intensity_is_refused() -> None:
    with pytest.raises(ValueError, match="intensity_mm_h"):
        T.exceedance(-1.0, 6.0)


def test_alpha_must_be_positive() -> None:
    with pytest.raises(ValueError, match="alpha"):
        PowerLawThreshold(alpha=0.0, beta=0.5)
