"""The power-law rainfall intensity-duration threshold (Caine 1980).

    I(D) = alpha * D^(-beta)        I in mm/h, D in hours

A rainfall event of mean intensity ``I`` lasting ``D`` hours is above the
threshold when ``I > I(D)``. Equivalently, in cumulated rainfall,
``E(D) = alpha * D^(1 - beta)`` mm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PowerLawThreshold:
    """``I(D) = alpha * D^(-beta)``, with ``alpha`` in mm/h and ``D`` in hours."""

    alpha: float
    beta: float

    def __post_init__(self) -> None:
        if self.alpha <= 0:
            raise ValueError(f"alpha must be > 0, got {self.alpha}")

    def intensity(self, duration_hours: float) -> float:
        """The threshold mean intensity for an event of this duration, in mm/h."""
        _check_duration(duration_hours)
        return float(self.alpha * duration_hours ** (-self.beta))

    def cumulated(self, duration_hours: float) -> float:
        """The threshold cumulated rainfall for an event of this duration, in mm."""
        _check_duration(duration_hours)
        return float(self.alpha * duration_hours ** (1.0 - self.beta))

    def exceedance(self, intensity_mm_h: float, duration_hours: float) -> float:
        """``log10(I / I(D))``: decades above (positive) or below (negative) the line.

        Negative infinity for a dry event (zero intensity).
        """
        if intensity_mm_h < 0:
            raise ValueError(f"intensity_mm_h must be >= 0, got {intensity_mm_h}")
        if intensity_mm_h == 0:
            return -math.inf
        return math.log10(intensity_mm_h) - math.log10(self.intensity(duration_hours))


def _check_duration(duration_hours: float) -> None:
    if duration_hours <= 0:
        raise ValueError(f"duration_hours must be > 0, got {duration_hours}")
