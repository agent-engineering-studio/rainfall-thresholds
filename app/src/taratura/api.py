"""Il banco di taratura: una piccola API sopra rainfall-thresholds, e la sua pagina.

Non è un sistema di allerta e non legge pioggia dal vivo. Serve a tarare una
soglia sulle frane del passato e a misurarne il costo in falsi allarmi sui
dati che l'ente porta. Una soglia superata non è un'allerta: l'allerta
ufficiale è il bollettino di criticità del Dipartimento della Protezione
Civile.

    uvicorn taratura.api:app        # http://127.0.0.1:8000

Configurazione, con variabili d'ambiente:

* ``TARATURA_ENTE``: il nome dell'ente nella testata (default: nessuno);
* ``TARATURA_REGIONE``: la regione proposta all'apertura, come la scrive
  e-ITALICA (``Puglia``, ``Emilia-Romagna``). Un nome sconosciuto è ignorato.
"""

from __future__ import annotations

import csv
import io
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import BaseRoute, Mount, Route
from starlette.staticfiles import StaticFiles

from rainfall_thresholds import (
    ITALICA_T5,
    MACROREGIONS,
    PowerLawThreshold,
    __version__,
    fit_threshold,
    macroregion_of,
    reconstruct_events,
    skill,
)
from rainfall_thresholds.facts import ALERT_URL, RULE

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("TARATURA_DATI", HERE.parent.parent / "data" / "italica_v4_eventi.csv"))
STATIC = Path(os.environ.get("TARATURA_STATIC", HERE.parent.parent / "static"))

REGOLA = (
    "Una soglia superata non è un'allerta: dice che la pioggia somiglia a quella che in "
    "passato ha innescato frane. L'allerta ufficiale è il bollettino di criticità del "
    "Dipartimento della Protezione Civile."
)
NON_MISURATO = "non misurato"
TIPI = {
    "SL": "scivolamento",
    "RF": "crollo",
    "DF": "colata detritica",
    "EF": "colata di terra",
    "MF": "colata di fango",
}
DURATE = (1, 3, 6, 12, 24, 48, 72)
FINESTRA_ORE = 72  # una frana è colta se un evento sopra soglia finisce nelle 72 h prima


@dataclass(frozen=True, slots=True)
class Frana:
    id: str
    regione: str
    anno: int
    mese: int
    tipo: str
    durata_h: float
    pioggia_mm: float


@cache
def catalogo() -> tuple[Frana, ...]:
    with DATA.open(encoding="utf-8") as f:
        righe = csv.DictReader(line for line in f if not line.startswith("#"))
        return tuple(
            Frana(
                r["id"],
                r["region"],
                int(r["year"]),
                int(r["month"]),
                r["type"],
                float(r["duration_h"]),
                float(r["cumulated_mm"]),
            )
            for r in righe
        )


def _regioni() -> list[str]:
    return sorted({f.regione for f in catalogo()})


def _filtra(q: dict[str, Any]) -> list[Frana]:
    regioni = set(q.get("regioni") or [])
    mesi = {int(m) for m in q.get("mesi") or []}
    tipi = set(q.get("tipi") or [])
    return [
        f
        for f in catalogo()
        if (not regioni or f.regione in regioni)
        and (not mesi or f.mese in mesi)
        and (not tipi or f.tipo in tipi)
    ]


def _soglia(t: PowerLawThreshold) -> dict[str, Any]:
    return {
        "alpha": round(t.alpha, 3),
        "beta": round(t.beta, 4),
        "pioggia": [
            {
                "durata_h": d,
                "pioggia_mm": round(t.cumulated(d), 1),
                "intensita_mm_h": round(t.intensity(d), 2),
            }
            for d in DURATE
        ],
    }


def _riferimento(regioni: list[str]) -> str:
    """La soglia nazionale di confronto: quella della macroregione, se è una sola."""
    macro = {macroregion_of(r) for r in regioni}
    if len(macro) == 1:
        (unica,) = macro
        return unica or "italy"
    return "italy"


def _evento_ente(riga: list[Any]) -> tuple[float, float]:
    durata, pioggia = float(riga[0]), float(riga[1])
    if durata <= 0 or pioggia < 0:
        raise ValueError(f"evento non valido: durata {durata} h, pioggia {pioggia} mm")
    return durata, pioggia


async def config(_: Request) -> JSONResponse:
    regione = os.environ.get("TARATURA_REGIONE", "").strip()
    return JSONResponse(
        {
            "ente": os.environ.get("TARATURA_ENTE", "").strip() or None,
            "regione": regione if regione in _regioni() else None,
            "regioni": _regioni(),
            "macroregioni": {k: sorted(v) for k, v in MACROREGIONS.items()},
            "tipi": TIPI,
            "regola": REGOLA,
            "rule": RULE,
            "bollettino": ALERT_URL,
            "versione": __version__,
            "fonte": "e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473), CC BY 4.0",
        }
    )


async def taratura(request: Request) -> JSONResponse:
    """Una soglia sulle frane scelte (e-ITALICA filtrato, o gli eventi dell'ente)."""
    q = await request.json()
    try:
        percentile = float(q.get("percentile", 5))
        if q.get("eventi_ente"):
            eventi = [_evento_ente(r) for r in q["eventi_ente"]]
            origine = "eventi dell'ente"
            regioni: list[str] = list(q.get("regioni") or [])
        else:
            frane = _filtra(q)
            eventi = [(f.durata_h, f.pioggia_mm) for f in frane]
            origine = "e-ITALICA"
            regioni = sorted({f.regione for f in frane})
        fit = fit_threshold([(d, e / d) for d, e in eventi], percentile=percentile)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    t = fit.threshold
    sotto = sum(t.exceedance(e / d, d) < 0 for d, e in eventi)
    rif = _riferimento(regioni)
    return JSONResponse(
        {
            "origine": origine,
            "frane": fit.n_events,
            "percentile": percentile,
            "soglia": _soglia(t),
            "centrale": _soglia(fit.central),
            "sotto_soglia": {"frane": sotto, "quota": round(sotto / len(eventi), 4)},
            "riferimento": {"nome": f"ITALICA_T5['{rif}']", **_soglia(ITALICA_T5[rif])},
            "punti": [[d, e] for d, e in eventi],
            "costo": {
                "stato": NON_MISURATO,
                "perche": "Il costo in falsi allarmi si misura sulla pioggia dei giorni senza "
                "frane, che il catalogo non contiene. Caricate la serie oraria di un "
                "pluviometro e le date delle frane per misurarlo.",
            },
            "avvertenze": _avvertenze(fit.n_events),
            "regola": REGOLA,
        }
    )


def _avvertenze(n: int) -> list[str]:
    note = [
        "La soglia è tarata su pioggia misurata dai pluviometri: su pioggia radar o di modello "
        "il confronto non è validato.",
        "Il metodo è quello di rainfall-thresholds (percentile dei residui), non quello degli "
        "autori di e-ITALICA.",
    ]
    if n < 100:
        note.insert(
            0,
            f"Solo {n} frane: una soglia su meno di un centinaio di eventi cambia "
            "molto con il campione.",
        )
    return note


def _serie(testo: str) -> list[tuple[datetime, float | None]]:
    """CSV ``ora,mm``; mm vuoto = non misurato."""
    righe = csv.reader(io.StringIO(testo))
    serie: list[tuple[datetime, float | None]] = []
    for i, r in enumerate(righe):
        if not r or r[0].startswith("#") or (i == 0 and not r[0][:1].isdigit()):
            continue
        valore = r[1].strip() if len(r) > 1 else ""
        serie.append((datetime.fromisoformat(r[0].strip()), float(valore) if valore else None))
    if not serie:
        raise ValueError("la serie è vuota")
    return serie


async def costo(request: Request) -> JSONResponse:
    """Il costo in falsi allarmi di una soglia sulla pioggia e sulle frane dell'ente.

    Unità: l'evento di pioggia. Un evento sopra soglia è un'allerta; una frana
    è colta se un evento sopra soglia finisce nelle 72 ore prima.
    """
    q = await request.json()
    try:
        soglia = PowerLawThreshold(float(q["alpha"]), float(q["beta"]))
        serie = _serie(q["serie"])
        frane = [date.fromisoformat(d.strip()) for d in q.get("frane") or [] if d.strip()]
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc
    eventi = reconstruct_events(serie, no_rain_break_hours=6, min_event_mm=2.0)
    misura = [soglia.exceedance(e.intensity_mm_h, e.duration_hours) for e in eventi]
    inizio, fine = serie[0][0], serie[-1][0]

    def punteggio(giorno: date) -> float | None:
        """Il più alto degli eventi finiti nelle 72 h prima della fine del giorno.

        Nessun evento: ``-inf`` (mancata) se in quelle ore la pioggia è stata
        misurata, ``None`` (non misurata) se non c'è nessuna ora misurata.
        """
        quando = datetime.combine(giorno, datetime.max.time(), tzinfo=inizio.tzinfo)
        finestra = timedelta(hours=FINESTRA_ORE + 24)
        prima = [
            x
            for e, x in zip(eventi, misura, strict=True)
            if timedelta(0) <= quando - e.end <= finestra
        ]
        if prima:
            return max(prima)
        misurate = any(mm is not None for t, mm in serie if timedelta(0) <= quando - t <= finestra)
        return -math.inf if misurate else None

    dentro = [g for g in frane if inizio.date() <= g <= fine.date()]
    s = skill([punteggio(g) for g in dentro], misura, cutoff=0.0)
    return JSONResponse(
        {
            "eventi_di_pioggia": len(eventi),
            "allerte": s.alerts,
            "frane": len(dentro),
            "frane_fuori_periodo": len(frane) - len(dentro),
            "frane_senza_pioggia_misurata": s.unmeasured,
            "frane_mancate": s.landslides - s.caught,
            "frane_colte": s.caught,
            "allerte_per_frana_colta": _o_non_misurato(s.alerts_per_caught),
            "quota_eventi_in_allerta": _o_non_misurato(s.alert_share),
            "ore_non_misurate": sum(mm is None for _, mm in serie),
            "periodo": [inizio.isoformat(), fine.isoformat()],
            "regola": REGOLA,
        }
    )


def _o_non_misurato(x: float | None) -> float | str:
    return NON_MISURATO if x is None else round(x, 3)


async def esporta(request: Request) -> PlainTextResponse:
    """La soglia come blocco YAML, nel formato delle macroregioni di Limen."""
    p = request.query_params
    try:
        alpha, beta = float(p["alpha"]), float(p["beta"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, "servono alpha e beta") from exc
    nome = (
        "".join(c for c in p.get("nome", "soglia_ente") if c.isalnum() or c == "_") or "soglia_ente"
    )
    testo = (
        f"# Soglia tarata con rainfall-thresholds {__version__} il {date.today().isoformat()}.\n"
        f"# Frane: {p.get('origine', 'e-ITALICA')}, {p.get('frane', '?')} eventi, "
        f"percentile {p.get('percentile', '5')}.\n"
        "# Una soglia superata non è un'allerta.\n"
        f"{nome}:\n  alpha: {alpha:.3f}\n  beta:  {beta:.4f}\n"
    )
    return PlainTextResponse(testo, media_type="text/yaml; charset=utf-8")


async def salute(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "frane": len(catalogo())})


routes: list[BaseRoute] = [
    Route("/api/salute", salute),
    Route("/api/config", config),
    Route("/api/taratura", taratura, methods=["POST"]),
    Route("/api/costo", costo, methods=["POST"]),
    Route("/api/esporta", esporta),
]
if STATIC.is_dir():
    routes.append(Mount("/", StaticFiles(directory=STATIC, html=True), name="pagina"))

app = Starlette(routes=routes)
