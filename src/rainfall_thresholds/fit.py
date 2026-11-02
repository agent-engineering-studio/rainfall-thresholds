"""Fitting a threshold to the rainfall conditions that triggered landslides.

The frequentist approach of Brunetti et al. (2010) and Peruccacci et al.
(2012): fit ``log10 I = log10 alpha - beta log10 D`` by least squares over
the (D, I) pairs of known landslide-triggering events, then lower the line
until a chosen share of the events sits below it. The threshold at the 5th
percentile, ``T5``, leaves 5 % of the triggering events beneath.

Where Peruccacci et al. take the percentile from a Gaussian fitted to a
kernel density of the residuals, this module takes it from the residuals
themselves (linear interpolation between order statistics). The two agree
when the residuals are close to normal; the empirical one needs no
assumption about their shape.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass

from rainfall_thresholds.threshold import PowerLawThreshold


@dataclass(frozen=True, slots=True)
class ThresholdFit:
    """A fitted threshold and what it was fitted on."""

    threshold: PowerLawThreshold
    percentile: float
    n_events: int
    #: The least-squares line before it is lowered (the 50 % threshold is
    #: close to it, but not equal when the residuals are skewed).
    central: PowerLawThreshold


def fit_threshold(
    events: Iterable[tuple[float, float]],
    *,
    percentile: float = 5.0,
) -> ThresholdFit:
    """Fit ``I = alpha * D^(-beta)`` at ``percentile`` to ``(duration_h, intensity_mm_h)`` pairs.

    Pairs with a non-positive duration or intensity are skipped: they have
    no logarithm. At least three usable pairs are needed.
    """
    if not 0 < percentile < 100:
        raise ValueError(f"percentile must be in (0, 100), got {percentile}")
    pairs = [(d, i) for d, i in events if d > 0 and i > 0]
    if len(pairs) < 3:
        raise ValueError(f"need at least 3 events with D > 0 and I > 0, got {len(pairs)}")
    x = [math.log10(d) for d, _ in pairs]
    y = [math.log10(i) for _, i in pairs]
    if len(set(x)) < 2:
        raise ValueError("all events have the same duration: the slope is undefined")
    slope, intercept = statistics.linear_regression(x, y)
    residuals = [yi - (intercept + slope * xi) for xi, yi in zip(x, y, strict=True)]
    shift = percentile_of(residuals, percentile)
    return ThresholdFit(
        threshold=PowerLawThreshold(alpha=10 ** (intercept + shift), beta=-slope),
        percentile=percentile,
        n_events=len(pairs),
        central=PowerLawThreshold(alpha=10**intercept, beta=-slope),
    )


def percentile_of(values: list[float], percentile: float) -> float:
    """The ``percentile``-th percentile, interpolating linearly between order statistics.

    The same definition as NumPy's default (``method="linear"``).
    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100.0
    below = math.floor(position)
    above = min(below + 1, len(ordered) - 1)
    return ordered[below] + (ordered[above] - ordered[below]) * (position - below)
