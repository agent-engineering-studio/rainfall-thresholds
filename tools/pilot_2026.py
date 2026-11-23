"""Pilot of rainfall-thresholds#8 on the 2026 archive of Limen: Merging vs radar alone.

For the IdroGEO landslides dated to the day, point within 1 km, slides and flows,
inside the archived months: the hourly rain at the point from the «Merging»
(CUM3 split into hours by the radar, as dpc-radar does) and from the radar
alone (SRT1). For each rain: the rainfall events of the whole period at that
point, which are above T5 (alerts), and whether the landslide had an event
above T5 ending in the 72 hours before the end of its day (caught).

    uv run --group examples python tools/pilot_2026.py \\
        <Limen's data/radar_merging> <out.csv> <summary.json>

It reads the sister libraries, so it lives here in tools/, outside the
package, and runs with the `examples` dependency group (decision B2, #21).
It needs the network for IdroGEO and Limen's local archive of DPC frames.
The result is benchmarks/measures/pilot-2026-merging-vs-radar.csv.
"""

from __future__ import annotations

import asyncio
import csv
import json
import math
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from dpc_radar import reliability
from dpc_radar.archive import MergingArchive, split_block
from ispra_idrogeo import IdroGEO
from ispra_idrogeo.dated import dated_landslides

from rainfall_thresholds import ITALICA_T5, macroregion_of, reconstruct_events, skill

ARCHIVE, OUT_CSV, OUT_JSON = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
REGION = {
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
RAINFALL_MOVEMENTS = {2, 4, 5, 7, 11}
WINDOW_H = 72


def archive_span() -> tuple[datetime, datetime]:
    days = sorted(
        datetime(int(y.name), int(m.name), int(d.name), tzinfo=UTC)
        for y in (ARCHIVE / "CUM3").iterdir()
        if y.is_dir()
        for m in y.iterdir()
        if m.is_dir()
        for d in m.iterdir()
        if d.is_dir()
    )
    return days[0], days[-1] + timedelta(days=1)


def hourly(arch: MergingArchive, points, start, end):
    """Two hourly series per point: Merging (None if CUM3 is missing) and radar alone."""
    merging = {k: [] for k in range(len(points))}
    radar = {k: [] for k in range(len(points))}
    t = start
    while t < end:
        block_end = t + timedelta(hours=3)
        hours = [block_end - timedelta(hours=k) for k in (2, 1, 0)]
        m = arch._sample("CUM3", block_end, points)
        r = [arch._sample("SRT1", h, points) for h in hours]
        for j, h in enumerate(hours):
            for k in range(len(points)):
                rk = r[j][k]
                radar[k].append((h, None if rk is None or not math.isfinite(rk) else max(rk, 0.0)))
                mk = m[k]
                if mk is None or not math.isfinite(mk):
                    merging[k].append((h, None))
                else:
                    v = split_block(mk, [x[k] for x in r], j)
                    merging[k].append((h, None if v is None else max(v, 0.0)))
        t = block_end
    return merging, radar


def score(events, threshold, day):
    end = datetime.combine(day, time(23), tzinfo=UTC)
    before = [
        threshold.exceedance(e.intensity_mm_h, e.duration_hours)
        for e in events
        if timedelta(0) <= end - e.end <= timedelta(hours=WINDOW_H + 24)
    ]
    return max(before, default=-math.inf)


async def landslides(start: date, end: date):
    async with IdroGEO() as g:
        found = await dated_landslides(
            g, sources=["eventi"], since=start, until=end, max_interval_days=1, max_position_m=1000
        )
    return found


def main() -> None:
    start, end = archive_span()
    found = asyncio.run(
        landslides((start + timedelta(days=4)).date(), (end - timedelta(days=1)).date())
    )
    kept = [f for f in found if f.movement in RAINFALL_MOVEMENTS and f.lon is not None]
    print(f"archive {start:%Y-%m-%d} -> {end:%Y-%m-%d}")
    print(f"{len(found)} dated landslides, {len(kept)} slides and flows")
    points = [(f.lon, f.lat) for f in kept]
    arch = MergingArchive(ARCHIVE, cache_frames=16)
    merging, radar = hourly(arch, points, start, end)

    rows, summary = [], {}
    per_source = {"merging": merging, "radar": radar}
    pos = {s: [] for s in per_source}
    neg = {s: [] for s in per_source}
    for k, f in enumerate(kept):
        name = REGION[f.region]
        t = ITALICA_T5[macroregion_of(name) or "italy"]
        row = {
            "id": f.id,
            "day": f.start.isoformat(),
            "region": name,
            "lon": round(f.lon, 5),
            "lat": round(f.lat, 5),
            "movement": f.movement,
            "position_m": f.position_m,
            "reliability": round(reliability(f.lon, f.lat).score, 2),
        }
        for s, series in per_source.items():
            events = reconstruct_events(series[k], no_rain_break_hours=6, min_event_mm=2.0)
            x = score(events, t, f.start)
            ex = [t.exceedance(e.intensity_mm_h, e.duration_hours) for e in events]
            missing = sum(mm is None for _, mm in series[k])
            pos[s].append(None if x == -math.inf and missing == len(series[k]) else x)
            neg[s].extend(ex)
            before = [
                e
                for e in events
                if timedelta(0)
                <= datetime.combine(f.start, time(23), tzinfo=UTC) - e.end
                <= timedelta(hours=WINDOW_H + 24)
            ]
            best = max(
                before, key=lambda e: t.exceedance(e.intensity_mm_h, e.duration_hours), default=None
            )
            row |= {
                f"{s}_events": len(events),
                f"{s}_alerts": sum(v > 0 for v in ex),
                f"{s}_total_mm": None if best is None else round(best.total_mm, 1),
                f"{s}_duration_h": None if best is None else best.duration_hours,
                f"{s}_exceedance": None if x == -math.inf else round(x, 2),
                f"{s}_hours_not_measured": missing,
            }
        rows.append(row)
    for s in per_source:
        sk = skill(pos[s], neg[s], cutoff=0.0)
        summary[s] = {
            "landslides": sk.landslides,
            "caught": sk.caught,
            "events": sk.ordinary,
            "alerts": sk.alerts,
            "alert_share": sk.alert_share,
            "alerts_per_caught": sk.alerts_per_caught,
            "unmeasured": sk.unmeasured,
        }
    summary["period"] = [start.isoformat(), end.isoformat()]
    summary["dated_landslides"] = len(found)
    summary["slides_and_flows"] = len(kept)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    OUT_JSON.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for r in rows:
        print(
            r["id"],
            r["day"],
            r["region"],
            "rel",
            r["reliability"],
            "| merging",
            r["merging_total_mm"],
            r["merging_duration_h"],
            r["merging_exceedance"],
            "alerts",
            r["merging_alerts"],
            "| radar",
            r["radar_total_mm"],
            r["radar_duration_h"],
            r["radar_exceedance"],
            "alerts",
            r["radar_alerts"],
        )


main()
