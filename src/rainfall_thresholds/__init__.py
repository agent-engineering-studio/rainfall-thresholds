"""Rainfall intensity-duration thresholds for shallow landslides."""

from importlib.metadata import version

from rainfall_thresholds.antecedent import api_factor, api_kohler_linsley
from rainfall_thresholds.assess import (
    EventAssessment,
    WindowTotal,
    caine_excess,
    cumulate,
    event_against_threshold,
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

__version__ = version("rainfall-thresholds")

__all__ = [
    "ISTAT_REGIONS",
    "ITALICA_T5",
    "MACROREGIONS",
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
    "cumulate",
    "cutoff_at_budget",
    "event_against_threshold",
    "fit_threshold",
    "latest_event",
    "load_regional_catalogue",
    "macroregion_of",
    "percentile_of",
    "point_series",
    "reconstruct_events",
    "skill",
    "skill_at_budget",
    "strongest_event",
    "threshold_for",
]
