"""T5 thresholds for Italy, fitted on the e-ITALICA catalogue.

e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473,
CC BY 4.0) lists rainfall-induced landslides with the duration and
cumulated rainfall of the triggering event, measured at a rain gauge.
The 5,974 events with both values positive were fitted with
:func:`~rainfall_thresholds.fit.fit_threshold` at the 5th percentile,
nationally and for three macroregions. ``tests/test_italy.py`` refits them
from the catalogue, so these numbers are reproducible, not transcribed.

They are not the thresholds published by the e-ITALICA authors, who use a
kernel-density estimate of the residuals and their own regional
partitions: they are what this package's method gives on their data.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from rainfall_thresholds.threshold import PowerLawThreshold

#: The regions in each macroregion, as named in e-ITALICA. Abruzzo and Molise
#: are in the centre (unlike the ISTAT "Sud").
MACROREGIONS: MappingProxyType[str, frozenset[str]] = MappingProxyType(
    {
        "northern": frozenset(
            {
                "Piemonte",
                "Valle d'Aosta",
                "Liguria",
                "Lombardia",
                "Trentino-Alto Adige",
                "Veneto",
                "Friuli-Venezia Giulia",
                "Emilia-Romagna",
            }
        ),
        "central": frozenset({"Toscana", "Umbria", "Marche", "Lazio", "Abruzzo", "Molise"}),
        "southern": frozenset(
            {"Campania", "Puglia", "Basilicata", "Calabria", "Sicilia", "Sardegna"}
        ),
    }
)

#: T5 thresholds, ``I = alpha * D^(-beta)`` (mm/h, hours). ``"italy"`` is the
#: national fit; the others use the regions in :data:`MACROREGIONS`.
ITALICA_T5: MappingProxyType[str, PowerLawThreshold] = MappingProxyType(
    {
        "italy": PowerLawThreshold(alpha=7.193, beta=0.5685),  # 5,974 events
        "northern": PowerLawThreshold(alpha=6.400, beta=0.5134),  # 2,659 events
        "central": PowerLawThreshold(alpha=7.953, beta=0.6085),  # 1,890 events
        "southern": PowerLawThreshold(alpha=8.754, beta=0.6449),  # 1,425 events
    }
)


#: The ISTAT code of each region, with the e-ITALICA spelling of its name.
#: Trentino-Alto Adige is one region (code 4), as in ISTAT: the two autonomous
#: provinces have province codes, not region codes.
ISTAT_REGIONS: MappingProxyType[int, str] = MappingProxyType(
    {
        1: "Piemonte",
        2: "Valle d'Aosta",
        3: "Lombardia",
        4: "Trentino-Alto Adige",
        5: "Veneto",
        6: "Friuli-Venezia Giulia",
        7: "Liguria",
        8: "Emilia-Romagna",
        9: "Toscana",
        10: "Umbria",
        11: "Marche",
        12: "Lazio",
        13: "Abruzzo",
        14: "Molise",
        15: "Campania",
        16: "Puglia",
        17: "Basilicata",
        18: "Calabria",
        19: "Sicilia",
        20: "Sardegna",
    }
)


def macroregion_of(region: str | int) -> str | None:
    """The macroregion of an Italian region, or ``None``.

    ``region`` is the name as e-ITALICA spells it (``"Emilia-Romagna"``) or
    the ISTAT region code, as a number or as text (``8``, ``"08"``).
    """
    name = _region_name(region)
    return next((key for key, regions in MACROREGIONS.items() if name in regions), None)


def _region_name(region: str | int) -> str | None:
    if isinstance(region, bool):
        return None
    if isinstance(region, int):
        return ISTAT_REGIONS.get(region)
    if region.isascii() and region.isdigit():
        return ISTAT_REGIONS.get(int(region))
    return region


def threshold_for(
    macroregion: str | None,
    thresholds: Mapping[str, PowerLawThreshold] = ITALICA_T5,
    *,
    default: str = "italy",
) -> PowerLawThreshold:
    """The threshold of a macroregion, or the ``default`` one when it has none.

    ``thresholds`` are the caller's own if given (a calibration, a
    configuration file); it must have the ``default`` key.
    """
    found = thresholds.get(macroregion) if macroregion is not None else None
    return thresholds[default] if found is None else found
