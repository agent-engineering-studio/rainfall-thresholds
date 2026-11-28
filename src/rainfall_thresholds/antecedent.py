"""The Antecedent Precipitation Index (Kohler & Linsley 1951) and a wetness factor.

    API_t = k * API_(t-1) + P_t        P in mm per day, 0 < k < 1

How wet the ground already is when the rain comes: every day keeps a share
``k`` of the day before and adds its own rain. :func:`api_factor` reads an
API against a baseline as a number between 0 and 1.

There are no defaults for ``k``, the baseline or the sigma: they depend on
the place and on what the factor is used for, and are the caller's
configuration. Moved from Limen (``core/scoring/api.py``); a parity test
keeps the numbers the same.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def api_kohler_linsley(
    daily_precip_mm: Iterable[float],
    *,
    decay_k: float,
    initial: float = 0.0,
) -> float:
    """The API at the end of a series of daily totals, in mm.

    Args:
        daily_precip_mm: Daily totals in chronological order.
        decay_k: Daily decay coefficient, ``0 < k < 1``.
        initial: API at the start of the series.
    """
    if not 0.0 < decay_k < 1.0:
        raise ValueError(f"decay_k must be in (0, 1), got {decay_k}")
    api = float(initial)
    for p in daily_precip_mm:
        if p < 0.0:
            raise ValueError(f"daily_precip_mm must be >= 0, got {p}")
        api = decay_k * api + float(p)
    return api


def api_factor(
    api_mm: float | None,
    *,
    fallback_baseline_mm: float,
    fallback_sigma_mm: float,
    sigma_min_mm: float,
    baseline_mm: float | None = None,
    sigma_mm: float | None = None,
) -> float:
    """An API as a wetness factor between 0 and 1.

    The logistic of the standardised anomaly, ``(API - baseline) / sigma``:
    0.5 at the baseline, towards 1 when wetter. ``baseline_mm`` and
    ``sigma_mm`` are the place's own climatology for the month; a place
    without one is read against ``fallback_baseline_mm`` and
    ``fallback_sigma_mm``. A place's own sigma is never taken below
    ``sigma_min_mm``: where the rain of a month varies by a few millimetres,
    an ordinary storm would read as an anomaly of ten sigma.

    ``None`` (no API known) gives 0.5, neutral: not knowing moves the factor
    neither up nor down.
    """
    if api_mm is None:
        return 0.5
    baseline = baseline_mm if baseline_mm is not None else fallback_baseline_mm
    sigma = max(sigma_mm, sigma_min_mm) if sigma_mm is not None else fallback_sigma_mm
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    return _sigmoid((api_mm - baseline) / sigma)


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)
