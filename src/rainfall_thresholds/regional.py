"""Published regional rainfall thresholds for Italy, with their sources.

``regional_thresholds.toml`` collects thresholds published by the literature
for a region, a physiographic area or an alert zone, each with its citation
and licence. They are data to compare with, not what this package fits
(:data:`~rainfall_thresholds.italy.ITALICA_T5`), and nothing here applies
them: a threshold for a zone needs the zone's geometry, which the caller has.

Moved from Limen (``core/scoring/soglie_regionali.py`` and its YAML), with
Limen's area ids replaced by region names; a parity test compares the file
with Limen's, entry by entry.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from types import MappingProxyType
from typing import Literal

from rainfall_thresholds.threshold import PowerLawThreshold

_FILE = "regional_thresholds.toml"


@dataclass(frozen=True, slots=True)
class Source:
    """Where a threshold was published, and under which licence."""

    citation: str
    url: str
    license: str


@dataclass(frozen=True, slots=True)
class RegionalThreshold:
    """One published threshold.

    ``form`` is ``"E-D"`` (``E = alpha * D^gamma``, mm and hours) or ``"I-D"``
    (``I = alpha * D^(-beta)``, mm/h and hours). ``regions`` are the Italian
    regions it covers whole, as e-ITALICA spells them; a threshold for an
    alert zone or a physiographic area has ``zone`` instead. ``source`` is a
    key of :attr:`RegionalCatalogue.sources`.
    """

    id: str
    form: Literal["E-D", "I-D"]
    alpha: float
    source: str
    gamma: float | None = None
    beta: float | None = None
    regions: tuple[str, ...] = ()
    zone: str | None = None
    duration_hours: tuple[float, float] | None = None
    level: str | None = None
    no_rain_gap_hours: float | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.alpha <= 0:
            raise ValueError(f"{self.id}: alpha must be > 0, got {self.alpha}")
        if (self.form == "E-D") != (self.gamma is not None) or (
            (self.form == "I-D") != (self.beta is not None)
        ):
            raise ValueError(f"{self.id}: E-D wants gamma, I-D wants beta")
        if not self.regions and self.zone is None:
            raise ValueError(f"{self.id}: regions or zone is needed")

    def as_intensity(self) -> PowerLawThreshold:
        """The threshold as ``I = alpha * D^(-beta)``, mm/h."""
        if self.gamma is not None:
            return PowerLawThreshold(alpha=self.alpha, beta=1.0 - self.gamma)
        assert self.beta is not None  # by __post_init__
        return PowerLawThreshold(alpha=self.alpha, beta=self.beta)


@dataclass(frozen=True, slots=True)
class RegionalCatalogue:
    """The thresholds and their sources. A region has one threshold at most."""

    sources: MappingProxyType[str, Source]
    thresholds: tuple[RegionalThreshold, ...]

    def __post_init__(self) -> None:
        unknown = {t.source for t in self.thresholds} - set(self.sources)
        if unknown:
            raise ValueError(f"sources not declared: {sorted(unknown)}")
        regions = [r for t in self.thresholds for r in t.regions]
        if len(regions) != len(set(regions)):
            raise ValueError("a region has two regional thresholds")

    def by_region(self) -> dict[str, RegionalThreshold]:
        """The threshold of each region that has one of its own."""
        return {r: t for t in self.thresholds for r in t.regions}


@cache
def load_regional_catalogue() -> RegionalCatalogue:
    """The catalogue shipped with the package (read once, immutable)."""
    data = tomllib.loads(files("rainfall_thresholds").joinpath(_FILE).read_text(encoding="utf-8"))
    return RegionalCatalogue(
        sources=MappingProxyType({key: Source(**s) for key, s in data["sources"].items()}),
        thresholds=tuple(
            RegionalThreshold(
                **{
                    **t,
                    "regions": tuple(t.get("regions", ())),
                    "duration_hours": tuple(t["duration_hours"]) if "duration_hours" in t else None,
                }
            )
            for t in data["thresholds"]
        ),
    )
