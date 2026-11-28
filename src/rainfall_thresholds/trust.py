"""How well the Italian threshold is calibrated, region by region.

A T5 threshold is fitted so that 5 % of the landslides of its macroregion
sit below it. A macroregion is not one place: inside it, a region can have
many more of its landslides below the line (the line is high for it, and
misses more of them there) or many fewer (the line is low for it, and rain
crosses it more easily there). And a region with seventeen landslides cannot
tell either way.

:data:`CALIBRATION` counts, for each region, the e-ITALICA landslides the
thresholds were fitted on, how many are below the threshold of their
macroregion, and the durations they cover. ``tests/test_trust.py`` counts
them again from the catalogue. :meth:`Calibration.interval` is the range the
real share can be in, given how many landslides there are (a Wilson score
interval), and :attr:`Calibration.position` reads it against the 5 %.

This says how the line sits on the landslides of the past, at rain gauges.
It does not say how often it is crossed without a landslide: that is
:mod:`rainfall_thresholds.measure`, on the caller's own rain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from rainfall_thresholds.italy import ISTAT_REGIONS

#: The share of landslides below a T5 threshold where it was fitted.
EXPECTED_BELOW = 0.05


@dataclass(frozen=True, slots=True)
class Calibration:
    """The landslides of a region against the threshold of its macroregion.

    ``events`` landslides of e-ITALICA v4, ``below`` of them under the line.
    ``duration_hours`` are the 5th and 95th percentile of the durations of
    their rain: outside that range the line is extrapolated.
    """

    region: str
    macroregion: str
    events: int
    below: int
    duration_hours: tuple[float, float]

    @property
    def below_share(self) -> float:
        """The share of the region's landslides below the line."""
        return self.below / self.events

    def interval(self, z: float = 1.96) -> tuple[float, float]:
        """The range of the real share, as a Wilson score interval.

        ``z`` is the normal quantile of the confidence wanted: 1.96, the
        default, is the usual 95 %.
        """
        if not z > 0:
            raise ValueError(f"z must be > 0, got {z}")
        n, p = self.events, self.below_share
        centre = (p + z * z / (2 * n)) / (1 + z * z / n)
        half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        return max(0.0, centre - half), min(1.0, centre + half)

    @property
    def position(self) -> Literal["as fitted", "high", "low"]:
        """Where the line sits for this region, at 95 %.

        ``"high"``: more than 5 % of its landslides are below, beyond what
        chance gives. ``"low"``: fewer. ``"as fitted"``: the 5 % is within the
        interval, which with few landslides is wide and says little.
        """
        low, high = self.interval()
        if low > EXPECTED_BELOW:
            return "high"
        if high < EXPECTED_BELOW:
            return "low"
        return "as fitted"


_TABLE: tuple[tuple[str, str, int, int, tuple[float, float]], ...] = (
    ("Piemonte", "northern", 253, 8, (4.0, 303.0)),
    ("Valle d'Aosta", "northern", 68, 11, (3.0, 254.0)),
    ("Lombardia", "northern", 288, 13, (3.0, 294.9)),
    ("Trentino-Alto Adige", "northern", 123, 16, (2.0, 242.1)),
    ("Veneto", "northern", 144, 9, (2.0, 333.5)),
    ("Friuli-Venezia Giulia", "northern", 99, 3, (3.9, 128.2)),
    ("Liguria", "northern", 1603, 62, (6.0, 366.0)),
    ("Emilia-Romagna", "northern", 81, 11, (4.0, 164.0)),
    ("Toscana", "central", 250, 4, (3.0, 314.6)),
    ("Umbria", "central", 203, 19, (3.0, 562.5)),
    ("Marche", "central", 1131, 55, (3.0, 524.0)),
    ("Lazio", "central", 148, 6, (4.0, 217.2)),
    ("Abruzzo", "central", 141, 10, (2.0, 167.0)),
    ("Molise", "central", 17, 1, (5.0, 201.6)),
    ("Campania", "southern", 316, 10, (2.0, 189.8)),
    ("Puglia", "southern", 140, 8, (3.0, 133.4)),
    ("Basilicata", "southern", 55, 6, (3.7, 151.0)),
    ("Calabria", "southern", 298, 4, (2.0, 282.0)),
    ("Sicilia", "southern", 400, 20, (3.0, 176.2)),
    ("Sardegna", "southern", 216, 24, (3.0, 336.0)),
)

#: Region (e-ITALICA spelling) -> its calibration, in the order of the ISTAT codes.
CALIBRATION: MappingProxyType[str, Calibration] = MappingProxyType(
    {row[0]: Calibration(*row) for row in _TABLE}
)


def calibration_of(region: str | int) -> Calibration | None:
    """The calibration of a region, by name or ISTAT region code, or ``None``."""
    if isinstance(region, bool):
        return None
    if isinstance(region, int) or (region.isascii() and region.isdigit()):
        region = ISTAT_REGIONS.get(int(region), "")
    return CALIBRATION.get(region)
