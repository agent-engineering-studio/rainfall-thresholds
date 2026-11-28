"""Limen's single-domain rainfall logic, frozen for the parity tests.

Copied from limen at commit 3b0e1ee:

* ``src/limen/core/scoring/api.py``: ``api_kohler_linsley``, ``api_factor``;
* ``src/limen/core/pioggia_frane.py``: ``cumulate``, ``evento_contro_soglia``;
* ``src/limen/core/scoring/caine.py``: ``_resolve_region``, ``caine_excess``;
* ``src/limen/core/scoring/soglie_regionali.py``: ``Soglia.in_intensita``
  (the catalogue itself is ``fixtures/limen_soglie_frane_regionali.json``,
  Limen's ``config/soglie_frane_regionali.yaml`` converted to JSON as it is).

Limen's pydantic configuration blocks (``ApiBlock``, ``CaineBlock``,
``RegionalThresholds``) are replaced by their plain values; nothing else is
changed. ``evento_contro_soglia`` calls ``reconstruct_events`` and
``latest_event`` of this package, as it does in Limen. The package never
imports Limen (tests/test_package.py); this copy is test data.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

from rainfall_thresholds import PowerLawThreshold, RainfallEvent, latest_event, reconstruct_events

CUMULATE = (1, 3, 6, 24, 72)


def api_kohler_linsley(
    daily_precip_mm: Iterable[float],
    *,
    decay_k: float,
    initial: float = 0.0,
) -> float:
    if not 0.0 < decay_k < 1.0:
        raise ValueError(f"decay_k must be in (0, 1), got {decay_k}")
    api = float(initial)
    for p in daily_precip_mm:
        if p < 0.0:
            raise ValueError(f"daily_precip_mm must be >= 0, got {p}")
        api = decay_k * api + float(p)
    return api


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def api_factor(
    api_30_mm: float | None,
    *,
    fallback_mm: float,  # api.baseline.fallback_mm
    sigma_min_mm: float,  # api.baseline.sigma_min_mm
    sigmoid_sigma_mm: float,  # api.sigmoid_sigma_mm
    baseline_mm: float | None = None,
    sigma_mm: float | None = None,
) -> float:
    if api_30_mm is None:
        return 0.5
    baseline = baseline_mm if baseline_mm is not None else fallback_mm
    sigma = max(sigma_mm, sigma_min_mm) if sigma_mm is not None else sigmoid_sigma_mm
    if sigma <= 0:
        raise ValueError(f"sigmoid_sigma_mm must be > 0, got {sigma}")
    z = (api_30_mm - baseline) / sigma
    return _sigmoid(z)


def cumulate(ore: dict[datetime, float | None], fine: datetime) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for h in CUMULATE:
        if fine - timedelta(hours=h - 1) < min(ore, default=fine):
            continue
        finestra = [ore.get(fine - timedelta(hours=k)) for k in range(h)]
        mancanti = sum(v is None for v in finestra)
        out[f"{h}h"] = {
            "mm": None if mancanti else round(sum(v for v in finestra if v is not None), 1),
            "ore_non_misurate": mancanti,
        }
    return out


def resolve_region(
    macroregions: Mapping[str, PowerLawThreshold], macroregion: str
) -> PowerLawThreshold:
    region = macroregions.get(macroregion)
    if region is None:
        return macroregions["italy_default"]
    return region


def evento_contro_soglia(
    ore: dict[datetime, float | None],
    *,
    macroregions: Mapping[str, PowerLawThreshold],  # soglie.caine.macroregions
    macroregione: str,
    no_rain_break_hours: int,  # caine.event_reconstruction.*
    min_event_mm: float,
    scelta_evento: str,
) -> dict[str, Any] | None:
    def threshold_intensity_mm_h(duration_hours: float) -> float:
        return resolve_region(macroregions, macroregione).intensity(duration_hours)

    pausa = no_rain_break_hours
    eventi = reconstruct_events(
        sorted(ore.items()),
        no_rain_break_hours=pausa,
        min_event_mm=min_event_mm,
        source="pluviometro",
    )

    def rapporto(e: RainfallEvent) -> float:
        soglia = threshold_intensity_mm_h(e.duration_hours)
        return e.intensity_mm_h / soglia

    if scelta_evento == "piu_forte":
        evento = max(eventi, key=rapporto, default=None)
    else:
        evento = latest_event(eventi)
    if evento is None:
        return None
    bordi = [evento.start - timedelta(hours=k) for k in range(1, pausa + 1)] + [
        evento.end + timedelta(hours=k) for k in range(1, pausa + 1)
    ]
    aperto = any(ore.get(t) is None for t in bordi)
    soglia_mm_h = threshold_intensity_mm_h(evento.duration_hours)
    return {
        "inizio": evento.start,
        "fine": evento.end,
        "durata_h": evento.duration_hours,
        "cumulata_mm": round(evento.total_mm, 1),
        "intensita_mm_h": round(evento.intensity_mm_h, 2),
        "soglia_mm_h": round(soglia_mm_h, 2),
        "soglia_mm": round(soglia_mm_h * evento.duration_hours, 1),
        "rapporto_soglia": round(evento.intensity_mm_h / soglia_mm_h, 2),
        "ore_non_misurate": evento.unmeasured_hours,
        "confina_con_ore_non_misurate": aperto,
        "almeno": evento.unmeasured_hours > 0 or aperto,
    }


def caine_excess(
    event: RainfallEvent | None,
    *,
    macroregions: Mapping[str, PowerLawThreshold],  # caine.macroregions
    macroregion: str = "italy_default",
    alpha_factor: float = 1.0,
) -> float:
    if event is None:
        return 0.0
    region = resolve_region(macroregions, macroregion)
    excess = PowerLawThreshold(alpha=region.alpha * alpha_factor, beta=region.beta).exceedance(
        event.intensity_mm_h, event.duration_hours
    )
    return excess if excess > 0.0 else 0.0


def in_intensita(soglia: Mapping[str, Any]) -> tuple[float, float]:
    """``Soglia.in_intensita``: (alpha, beta) of ``I = alpha * D^(-beta)``."""
    if soglia.get("gamma") is not None:
        return soglia["alpha"], 1.0 - soglia["gamma"]
    assert soglia.get("beta") is not None
    return soglia["alpha"], soglia["beta"]
