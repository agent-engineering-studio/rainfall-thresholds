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


def macroregion_of(region: str) -> str | None:
    """The macroregion of an Italian region (e-ITALICA spelling), or ``None``."""
    return next((name for name, regions in MACROREGIONS.items() if region in regions), None)
