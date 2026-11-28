"""What lets the other libraries feed this one with plain types, no imports."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

import pytest

from rainfall_thresholds import (
    ISTAT_REGIONS,
    ITALICA_T5,
    MACROREGIONS,
    PowerLawThreshold,
    RainfallEvent,
    RainSource,
    RegionalCatalogue,
    RegionalThreshold,
    Source,
    api_factor,
    api_kohler_linsley,
    caine_excess,
    cumulate,
    event_against_threshold,
    load_regional_catalogue,
    macroregion_of,
    point_series,
    threshold_for,
)

T0 = datetime(2026, 10, 1, tzinfo=UTC)


def _hours(values: Sequence[float | None]) -> dict[datetime, float | None]:
    return {T0 + timedelta(hours=k): v for k, v in enumerate(values)}


# --- ISTAT region codes ----------------------------------------------------------


def test_istat_regions_are_the_twenty_of_the_macroregions() -> None:
    assert sorted(ISTAT_REGIONS) == list(range(1, 21))
    assert set(ISTAT_REGIONS.values()) == set().union(*MACROREGIONS.values())


@pytest.mark.parametrize(
    ("code", "macroregion"),
    [(3, "northern"), ("03", "northern"), ("3", "northern"), (13, "central"), ("18", "southern")],
)
def test_macroregion_of_an_istat_code(code: str | int, macroregion: str) -> None:
    assert macroregion_of(code) == macroregion


@pytest.mark.parametrize("code", [0, 21, "00", "99", "3a", True])
def test_macroregion_of_an_unknown_code_is_none(code: str | int) -> None:
    assert macroregion_of(code) is None


# --- Threshold resolution and the radar/gauge factor --------------------------


def test_threshold_for_defaults_to_the_italian_ones() -> None:
    assert threshold_for("southern") is ITALICA_T5["southern"]
    assert threshold_for(None) is ITALICA_T5["italy"]
    assert threshold_for("atlantis") is ITALICA_T5["italy"]


def test_scaled_multiplies_alpha_only() -> None:
    t = PowerLawThreshold(alpha=8.0, beta=0.6).scaled(0.5)
    assert t == PowerLawThreshold(alpha=4.0, beta=0.6)
    with pytest.raises(ValueError, match="factor"):
        PowerLawThreshold(alpha=8.0, beta=0.6).scaled(0.0)


def test_the_radar_gauge_factor_lowers_the_threshold_for_radar_rain() -> None:
    """A radar that reads 0.68 of the gauge meets the threshold with 0.68 of the rain."""
    threshold = ITALICA_T5["italy"]
    on_the_line = threshold.cumulated(6.0)
    radar_event = RainfallEvent(T0, T0 + timedelta(hours=5), 6.0, 0.68 * on_the_line)
    assert caine_excess(radar_event, threshold) == 0.0
    assert caine_excess(radar_event, threshold, radar_gauge_factor=0.5) == pytest.approx(
        math.log10(0.68 / 0.5)
    )
    assert caine_excess(radar_event, threshold, radar_gauge_factor=0.68) == pytest.approx(
        0.0, abs=1e-12
    )


def test_event_against_threshold_with_the_radar_gauge_factor() -> None:
    ore = _hours([0.0] * 6 + [5.0, 5.0, 5.0] + [0.0] * 6)
    threshold = ITALICA_T5["italy"]
    gauge = event_against_threshold(ore, threshold, no_rain_break_hours=6, min_event_mm=1.0)
    radar = event_against_threshold(
        ore, threshold, no_rain_break_hours=6, min_event_mm=1.0, radar_gauge_factor=0.68
    )
    assert gauge is not None and radar is not None
    assert radar.threshold == threshold.scaled(0.68)
    assert radar.threshold_mm_h == pytest.approx(0.68 * gauge.threshold_mm_h)
    assert radar.ratio == pytest.approx(gauge.ratio / 0.68)
    assert radar.excess_decades == pytest.approx(math.log10(radar.ratio))


@pytest.mark.parametrize("factor", [0.0, -1.0, math.nan, math.inf])
def test_a_radar_gauge_factor_that_is_not_a_positive_number_is_refused(factor: float) -> None:
    event = RainfallEvent(T0, T0, 1.0, 10.0)
    with pytest.raises(ValueError, match="radar_gauge_factor"):
        caine_excess(event, ITALICA_T5["italy"], radar_gauge_factor=factor)


# --- An event against the threshold: the edges ----------------------------------


def test_an_event_closed_by_measured_dry_hours_is_not_a_lower_bound() -> None:
    ore = _hours([0.0] * 3 + [4.0, 6.0] + [0.0] * 3)
    a = event_against_threshold(ore, ITALICA_T5["italy"], no_rain_break_hours=3, min_event_mm=1.0)
    assert a is not None
    assert (a.event.total_mm, a.event.duration_hours) == (10.0, 2.0)
    assert not a.borders_unmeasured and not a.at_least
    assert a.threshold_mm == pytest.approx(ITALICA_T5["italy"].cumulated(2.0))


def test_an_event_at_the_end_of_the_series_is_a_lower_bound() -> None:
    """The archive stops before the dry break closes the event: it may go on."""
    ore = _hours([0.0] * 3 + [4.0, 6.0])
    a = event_against_threshold(ore, ITALICA_T5["italy"], no_rain_break_hours=3, min_event_mm=1.0)
    assert a is not None and a.borders_unmeasured and a.at_least


def test_an_event_with_an_unmeasured_hour_inside_is_a_lower_bound() -> None:
    ore = _hours([0.0] * 3 + [4.0, None, 6.0] + [0.0] * 3)
    a = event_against_threshold(ore, ITALICA_T5["italy"], no_rain_break_hours=3, min_event_mm=1.0)
    assert a is not None
    assert a.event.unmeasured_hours == 1 and not a.borders_unmeasured and a.at_least


def test_no_event_is_none_and_an_unknown_choice_is_refused() -> None:
    assert (
        event_against_threshold(
            _hours([0.0] * 8), ITALICA_T5["italy"], no_rain_break_hours=3, min_event_mm=1.0
        )
        is None
    )
    with pytest.raises(ValueError, match="choice"):
        event_against_threshold(
            _hours([1.0]),
            ITALICA_T5["italy"],
            no_rain_break_hours=3,
            min_event_mm=1.0,
            choice="biggest",  # type: ignore[arg-type]
        )


# --- Windows ---------------------------------------------------------------------


def test_cumulate_says_none_when_an_hour_is_not_measured() -> None:
    ore = _hours([1.0, 2.0, None, 4.0])
    out = cumulate(ore, T0 + timedelta(hours=3), windows_hours=(1, 2, 4, 6))
    assert sorted(out) == [1, 2, 4]  # six hours do not fit in a four-hour series
    assert (out[1].total_mm, out[1].unmeasured_hours) == (4.0, 0)
    assert (out[2].total_mm, out[2].unmeasured_hours) == (None, 1)
    assert (out[4].total_mm, out[4].unmeasured_hours) == (None, 1)
    with pytest.raises(ValueError, match="windows_hours"):
        cumulate(ore, T0, windows_hours=(0,))


# --- API --------------------------------------------------------------------------


def test_api_refuses_what_limen_refuses() -> None:
    with pytest.raises(ValueError, match="decay_k"):
        api_kohler_linsley([1.0], decay_k=1.0)
    with pytest.raises(ValueError, match="daily_precip_mm"):
        api_kohler_linsley([-1.0], decay_k=0.9)
    with pytest.raises(ValueError, match="sigma"):
        api_factor(10.0, fallback_baseline_mm=80.0, fallback_sigma_mm=0.0, sigma_min_mm=20.0)


def test_api_factor_is_neutral_at_the_baseline_and_without_data() -> None:
    kwargs = {"fallback_baseline_mm": 80.0, "fallback_sigma_mm": 60.0, "sigma_min_mm": 20.0}
    assert api_factor(None, **kwargs) == 0.5
    assert api_factor(80.0, **kwargs) == 0.5
    assert api_factor(200.0, **kwargs) > 0.85 > 0.15 > api_factor(-40.0, **kwargs)


# --- The regional catalogue ---------------------------------------------------------


def test_the_catalogue_by_region() -> None:
    by_region = load_regional_catalogue().by_region()
    assert sorted(by_region) == ["Abruzzo", "Calabria", "Marche", "Sicilia", "Umbria"]
    calabria = by_region["Calabria"]
    assert calabria.as_intensity() == PowerLawThreshold(alpha=8.6, beta=1.0 - 0.41)
    assert load_regional_catalogue().sources[calabria.source].license == "CC BY 3.0"
    assert set(by_region) <= set().union(*MACROREGIONS.values())


def test_a_catalogue_wants_declared_sources_and_one_threshold_per_region() -> None:
    source = MappingProxyType({"s": Source(citation="c", url="u", license="l")})
    one = RegionalThreshold(id="a", form="I-D", alpha=1.0, beta=0.5, regions=("Lazio",), source="s")
    two = RegionalThreshold(id="b", form="I-D", alpha=2.0, beta=0.5, regions=("Lazio",), source="s")
    with pytest.raises(ValueError, match="sources not declared"):
        RegionalCatalogue(sources=MappingProxyType({}), thresholds=(one,))
    with pytest.raises(ValueError, match="two regional thresholds"):
        RegionalCatalogue(sources=source, thresholds=(one, two))


def test_a_threshold_wants_the_exponent_of_its_form_and_a_place() -> None:
    with pytest.raises(ValueError, match="gamma"):
        RegionalThreshold(id="x", form="E-D", alpha=1.0, beta=0.5, zone="Z", source="s")
    with pytest.raises(ValueError, match="gamma"):
        RegionalThreshold(id="x", form="I-D", alpha=1.0, gamma=0.5, zone="Z", source="s")
    with pytest.raises(ValueError, match="regions or zone"):
        RegionalThreshold(id="x", form="I-D", alpha=1.0, beta=0.5, source="s")
    with pytest.raises(ValueError, match="alpha"):
        RegionalThreshold(id="x", form="I-D", alpha=0.0, beta=0.5, zone="Z", source="s")


# --- A rain source ------------------------------------------------------------------


class _Archive:
    """The shape of dpc-radar's ``MergingArchive.hourly`` and ``SriHistory.hourly``."""

    def hourly(
        self, points: list[tuple[float, float]], start: datetime, end: datetime
    ) -> dict[datetime, list[float | None]]:
        hours = int((end - start).total_seconds() // 3600)
        return {
            start + timedelta(hours=k): [float(k), None][: len(points)] for k in range(1, hours + 1)
        }


def _read(source: RainSource) -> dict[datetime, list[float | None]]:
    return source.hourly([(16.0, 38.0), (9.0, 45.0)], T0, T0 + timedelta(hours=3))


def test_an_object_with_hourly_is_a_rain_source() -> None:
    assert isinstance(_Archive(), RainSource)
    assert not isinstance(object(), RainSource)
    rain = _read(_Archive())
    assert point_series(rain, 0) == {T0 + timedelta(hours=k): float(k) for k in (1, 2, 3)}
    assert set(point_series(rain, 1).values()) == {None}
