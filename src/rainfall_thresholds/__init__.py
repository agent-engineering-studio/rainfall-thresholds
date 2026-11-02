"""Rainfall intensity-duration thresholds for shallow landslides."""

from importlib.metadata import version

from rainfall_thresholds.events import RainfallEvent, latest_event, reconstruct_events
from rainfall_thresholds.fit import ThresholdFit, fit_threshold, percentile_of
from rainfall_thresholds.italy import ITALICA_T5, MACROREGIONS, macroregion_of
from rainfall_thresholds.threshold import PowerLawThreshold

__version__ = version("rainfall-thresholds")

__all__ = [
    "ITALICA_T5",
    "MACROREGIONS",
    "PowerLawThreshold",
    "RainfallEvent",
    "ThresholdFit",
    "__version__",
    "fit_threshold",
    "latest_event",
    "macroregion_of",
    "percentile_of",
    "reconstruct_events",
]
