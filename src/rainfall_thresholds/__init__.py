"""Rainfall intensity-duration thresholds for shallow landslides."""

from importlib.metadata import version

from rainfall_thresholds.antecedent import api_factor, api_kohler_linsley
from rainfall_thresholds.assess import (
    EventAssessment,
    WindowTotal,
    caine_excess,
    cumulate,
    event_against_threshold,
    rain_to_threshold,
    relative_total,
)
from rainfall_thresholds.events import (
    RainfallEvent,
    latest_event,
    reconstruct_events,
    strongest_event,
)
from rainfall_thresholds.fit import ThresholdFit, fit_threshold, percentile_of
from rainfall_thresholds.italy import (
    ISTAT_REGIONS,
    ITALICA_T5,
    MACROREGIONS,
    macroregion_of,
    threshold_for,
)
from rainfall_thresholds.measure import Skill, auc, cutoff_at_budget, skill, skill_at_budget
from rainfall_thresholds.regional import (
    RegionalCatalogue,
    RegionalThreshold,
    Source,
    load_regional_catalogue,
)
from rainfall_thresholds.sources import RainSource, point_series
from rainfall_thresholds.threshold import PowerLawThreshold
from rainfall_thresholds.trust import CALIBRATION, EXPECTED_BELOW, Calibration, calibration_of

__version__ = version("rainfall-thresholds")

__all__ = [
    "CALIBRATION",
    "EXPECTED_BELOW",
    "ISTAT_REGIONS",
    "ITALICA_T5",
    "MACROREGIONS",
    "Calibration",
    "EventAssessment",
    "PowerLawThreshold",
    "RainSource",
    "RainfallEvent",
    "RegionalCatalogue",
    "RegionalThreshold",
    "Skill",
    "Source",
    "ThresholdFit",
    "WindowTotal",
    "__version__",
    "api_factor",
    "api_kohler_linsley",
    "auc",
    "caine_excess",
    "calibration_of",
    "cumulate",
    "cutoff_at_budget",
    "event_against_threshold",
    "fit_threshold",
    "latest_event",
    "load_regional_catalogue",
    "macroregion_of",
    "percentile_of",
    "point_series",
    "rain_to_threshold",
    "reconstruct_events",
    "relative_total",
    "skill",
    "skill_at_budget",
    "strongest_event",
    "threshold_for",
]
