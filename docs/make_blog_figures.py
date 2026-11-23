"""Draw the figures of the blog article, in Italian and English, from the repository's data.

    uv run --with matplotlib python docs/make_blog_figures.py

Writes ``docs/img/blog/<name>-<lang>.png``: the Melito storm against the
threshold, the drizzle trap, a tile map of the regions, and how the three
libraries meet. Every number comes from the package, the benchmark series,
the e-ITALICA fixture or ``docs/data/region_counts.json``.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from rainfall_thresholds import (
    ITALICA_T5,
    latest_event,
    macroregion_of,
    reconstruct_events,
    strongest_event,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img" / "blog"
SERIES = ROOT / "benchmarks" / "series"

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
BLUE, ORANGE, GREEN, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#9a9993"
MACRO_COLOURS = {"northern": "#2a78d6", "central": "#1baf7a", "southern": "#eb6834"}

TEXT = {
    "it": {
        "hours_since": "ore dall'inizio dell'evento",
        "mm": "millimetri",
        "hourly": "pioggia di ogni ora (radar DPC, SRT1)",
        "cumulated": "pioggia accumulata",
        "t5": "quanta pioggia chiede la soglia T5 del Sud",
        "melito_title": "Melito di Porto Salvo, 9-10 ottobre 2026",
        "melito_note": "{mm:.0f} mm in {h:.0f} ore: la soglia ne chiedeva {need:.0f}. Circa {k:.0f} volte.",
        "trap_title": "La trappola della pioggerella",
        "hour": "ora",
        "storm": "il nubifragio\n{mm} mm in {h} ore\n{x} decadi",
        "drizzle": "pioggerella\n{mm} mm\n{x} decadi",
        "dry": "6 ore asciutte",
        "latest": "l'ultimo evento",
        "strongest": "l'evento più forte",
        "map_left": "Frane con la loro pioggia\ne-ITALICA, 1996-2021",
        "map_right": "Frane datate al giorno, punto entro 1 km\nIdroGEO, dal 2018",
        "map_legend": "Soglia T5: Nord {n:.0f} mm, Centro {c:.0f} mm, Sud {s:.0f} mm in 24 ore",
        "schema_title": "Tre librerie, ognuna per conto suo. Le unisce chi le usa.",
        "dpc": "dpc-radar\nquanto è piovuto, qui\n(radar della Protezione Civile)",
        "ispra": "ispra-idrogeo\ndove e quando è franato\n(inventario ISPRA)",
        "rt": "rainfall-thresholds\nbasta per far franare?\n(soglie e-ITALICA)",
        "join": "Limen, un notebook, una pagina",
        "series": "serie oraria\n(None = non misurato)",
        "dated": "frane datate",
        "answer": "un numero, con la sua unità:\nnon un'allerta",
        "bulletin": "l'allerta è il bollettino\ndella Protezione Civile",
    },
    "en": {
        "hours_since": "hours from the start of the event",
        "mm": "millimetres",
        "hourly": "rain of each hour (DPC radar, SRT1)",
        "cumulated": "rain so far",
        "t5": "rain the T5 threshold of the south asks for",
        "melito_title": "Melito di Porto Salvo, 9-10 October 2026",
        "melito_note": "{mm:.0f} mm in {h:.0f} hours: the threshold asked {need:.0f}. About {k:.0f} times.",
        "trap_title": "The drizzle trap",
        "hour": "hour",
        "storm": "the storm\n{mm} mm in {h} hours\n{x} decades",
        "drizzle": "drizzle\n{mm} mm\n{x} decades",
        "dry": "6 dry hours",
        "latest": "the last event",
        "strongest": "the strongest event",
        "map_left": "Landslides with their rain\ne-ITALICA, 1996-2021",
        "map_right": "Landslides dated to the day, point within 1 km\nIdroGEO, since 2018",
        "map_legend": "T5 threshold: north {n:.0f} mm, centre {c:.0f} mm, south {s:.0f} mm in 24 hours",
        "schema_title": "Three libraries, each on its own. Whoever uses them joins them.",
        "dpc": "dpc-radar\nhow much it rained, here\n(Civil Protection radar)",
        "ispra": "ispra-idrogeo\nwhere and when it slid\n(ISPRA inventory)",
        "rt": "rainfall-thresholds\nis it enough to trigger landslides?\n(e-ITALICA thresholds)",
        "join": "Limen, a notebook, a page",
        "series": "hourly series\n(None = not measured)",
        "dated": "dated landslides",
        "answer": "a number, with its unit:\nnot an alert",
        "bulletin": "the alert is the bulletin\nof the Civil Protection",
    },
}

#: A tile map: one square per region, roughly where it is.
TILES = {
    "Valle d'Aosta": (0, 0, "VdA"),
    "Lombardia": (1, 0, "Lom"),
    "Trentino-Alto Adige": (2, 0, "TAA"),
    "Veneto": (3, 0, "Ven"),
    "Friuli-Venezia Giulia": (4, 0, "FVG"),
    "Piemonte": (0, 1, "Pie"),
    "Emilia-Romagna": (1.5, 1, "EmR"),
    "Liguria": (0, 2, "Lig"),
    "Toscana": (1, 2, "Tos"),
    "Umbria": (2, 2, "Umb"),
    "Marche": (3, 2, "Mar"),
    "Lazio": (2, 3, "Laz"),
    "Abruzzo": (3, 3, "Abr"),
    "Molise": (4, 3, "Mol"),
    "Sardegna": (0, 4.2, "Sar"),
    "Campania": (3, 4, "Cam"),
    "Puglia": (4.5, 4, "Pug"),
    "Basilicata": (4, 5, "Bas"),
    "Calabria": (4, 6, "Cal"),
    "Sicilia": (3, 7, "Sic"),
}


def num(x: float, lang: str, fmt: str) -> str:
    """A number as the language writes it: 2,5 in Italian, 2.5 in English."""
    text = format(x, fmt)
    return text.replace(".", ",") if lang == "it" else text


def read_series(name: str) -> list[tuple[datetime, float | None]]:
    with (SERIES / name).open(encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return [
            (
                datetime.fromisoformat(r["time"].replace("Z", "+00:00")),
                float(r["mm"]) if r["mm"] else None,
            )
            for r in rows
        ]


def axes_style(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig: plt.Figure, name: str, lang: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}-{lang}.png", dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def melito(lang: str) -> None:
    t = TEXT[lang]
    threshold = ITALICA_T5["southern"]
    series = read_series("melito-srt1.csv")
    event = strongest_event(
        reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0), threshold
    )
    assert event is not None
    hours = [(ts, mm or 0.0) for ts, mm in series if event.start <= ts <= event.end]
    x = list(range(1, len(hours) + 1))
    cum, total = [], 0.0
    for _, mm in hours:
        total += mm
        cum.append(total)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    axes_style(ax)
    ax.bar(x, [mm for _, mm in hours], color=GREY, width=0.8, label=t["hourly"])
    ax.plot(x, cum, color=RED, linewidth=3, label=t["cumulated"])
    ax.plot(x, [threshold.cumulated(h) for h in x], color=BLUE, linewidth=3, label=t["t5"])
    need = threshold.cumulated(event.duration_hours)
    ax.annotate(
        t["melito_note"].format(
            mm=event.total_mm,
            h=event.duration_hours,
            need=need,
            k=10 ** threshold.exceedance(event.intensity_mm_h, event.duration_hours),
        ),
        xy=(x[-1], cum[-1]),
        xytext=(x[0] + 0.5, cum[-1] * 0.93),
        color=INK,
        fontsize=11,
    )
    ax.set_xlabel(t["hours_since"], color=INK)
    ax.set_ylabel(t["mm"], color=INK)
    ax.set_title(t["melito_title"], color=INK, loc="left", fontsize=13, fontweight="bold")
    ax.legend(frameon=False, loc="center right", labelcolor=INK)
    save(fig, "melito-storm", lang)


def trap(lang: str) -> None:
    t = TEXT[lang]
    threshold = ITALICA_T5["southern"]
    series = read_series("melito-then-drizzle.csv")
    events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)
    last, strong = latest_event(events), strongest_event(events, threshold)
    assert last is not None and strong is not None
    x = list(range(len(series)))
    fig, ax = plt.subplots(figsize=(9, 4.4))
    axes_style(ax)
    colours = [
        RED
        if strong.start <= ts <= strong.end
        else ORANGE
        if last.start <= ts <= last.end
        else GREY
        for ts, _ in series
    ]
    ax.bar(x, [mm or 0.0 for _, mm in series], color=colours, width=0.8)

    def ex(e: object) -> float:
        return threshold.exceedance(e.intensity_mm_h, e.duration_hours)  # type: ignore[attr-defined]

    storm = t["storm"].format(
        mm=num(strong.total_mm, lang, ".0f"),
        h=num(strong.duration_hours, lang, ".0f"),
        x=num(ex(strong), lang, "+.2f"),
    )
    drizzle = t["drizzle"].format(mm=num(last.total_mm, lang, ".1f"), x=num(ex(last), lang, "+.2f"))
    ax.text(1.5, 33, storm, color=RED, fontsize=11, va="bottom")
    ax.text(13.6, 6, drizzle, color=ORANGE, fontsize=11, va="bottom")
    ax.annotate("", xy=(8, 2), xytext=(13, 2), arrowprops={"arrowstyle": "<->", "color": MUTED})
    ax.text(10.5, 3, t["dry"], color=MUTED, ha="center", fontsize=10)
    ax.text(
        15,
        22,
        "latest_event  →  " + t["latest"],
        color=ORANGE,
        ha="right",
        fontsize=10,
        family="monospace",
    )
    ax.text(
        15,
        26,
        "strongest_event  →  " + t["strongest"],
        color=RED,
        ha="right",
        fontsize=10,
        family="monospace",
    )
    ax.set_ylim(0, 48)
    ax.set_xticks(x, [ts.strftime("%H") for ts, _ in series])
    ax.set_xlabel(t["hour"], color=INK)
    ax.set_ylabel(t["mm"], color=INK)
    ax.set_title(t["trap_title"], color=INK, loc="left", fontsize=13, fontweight="bold")
    save(fig, "drizzle-trap", lang)


def tile_map(lang: str) -> None:
    t = TEXT[lang]
    counts = json.loads((ROOT / "docs" / "data" / "region_counts.json").read_text(encoding="utf-8"))
    panels = (("e_italica", t["map_left"]), ("idrogeo_events_day_1km_since_2018", t["map_right"]))
    fig, axes = plt.subplots(1, 2, figsize=(10, 7.2))
    for ax, (key, title) in zip(axes, panels, strict=True):
        values = counts[key]
        top = max(values.values())
        for region, (cx, cy, short) in TILES.items():
            n = values.get(region, 0)
            macro = macroregion_of(region) or "northern"
            ax.add_patch(
                Rectangle(
                    (cx, -cy),
                    0.94,
                    0.94,
                    facecolor=MACRO_COLOURS[macro],
                    alpha=0.12 + 0.78 * (n / top) ** 0.5,
                    edgecolor=SURFACE,
                )
            )
            ax.text(
                cx + 0.47,
                -cy + 0.6,
                short,
                ha="center",
                va="center",
                fontsize=10,
                color=INK,
                fontweight="bold",
            )
            ax.text(
                cx + 0.47,
                -cy + 0.3,
                f"{n:,}".replace(",", "." if lang == "it" else ","),
                ha="center",
                va="center",
                fontsize=10,
                color=INK,
            )
        ax.set_xlim(-0.2, 5.7)
        ax.set_ylim(-7.15, 1.1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, color=INK, fontsize=11.5)
    s = {k: ITALICA_T5[k].cumulated(24) for k in ("northern", "central", "southern")}
    fig.text(
        0.5,
        0.06,
        t["map_legend"].format(n=s["northern"], c=s["central"], s=s["southern"]),
        ha="center",
        color=MUTED,
        fontsize=10.5,
    )
    save(fig, "regions-map", lang)


def schema(lang: str) -> None:
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    def box(
        x: float, y: float, w: float, h: float, text: str, colour: str, *, bold: bool = True
    ) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.04,rounding_size=0.12",
                facecolor=colour,
                alpha=0.14,
                edgecolor=colour,
                linewidth=2,
            )
        )
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=10.5,
            color=INK,
            fontweight="bold" if bold else "normal",
            linespacing=1.4,
        )

    def arrow(a: tuple[float, float], b: tuple[float, float], *, dashed: bool = False) -> None:
        ax.add_patch(
            FancyArrowPatch(
                a,
                b,
                arrowstyle="-|>",
                mutation_scale=16,
                color=MUTED,
                linewidth=1.6,
                linestyle="--" if dashed else "-",
            )
        )

    ax.add_patch(
        FancyBboxPatch(
            (0.15, 0.2),
            8.25,
            4.9,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            facecolor="none",
            edgecolor=GREY,
            linestyle="--",
            linewidth=1.2,
        )
    )
    ax.text(0.4, 4.75, t["join"], fontsize=10.5, color=MUTED, style="italic")
    box(0.5, 3.0, 3.6, 1.4, t["dpc"], BLUE)
    box(0.5, 0.6, 3.6, 1.4, t["ispra"], GREEN)
    box(5.2, 1.8, 3.0, 1.4, t["rt"], ORANGE)
    box(9.0, 2.75, 2.8, 1.2, t["answer"], RED, bold=False)
    box(9.0, 0.75, 2.8, 1.2, t["bulletin"], GREY, bold=False)
    arrow((4.1, 3.5), (5.2, 2.85))
    arrow((4.1, 1.3), (5.2, 2.15))
    arrow((8.2, 2.7), (9.0, 3.25))
    arrow((10.4, 2.75), (10.4, 1.95), dashed=True)
    ax.text(4.25, 3.6, t["series"], fontsize=9, color=MUTED, va="bottom")
    ax.text(4.25, 1.2, t["dated"], fontsize=9, color=MUTED, va="top")
    ax.set_title(t["schema_title"], color=INK, loc="left", fontsize=13, fontweight="bold")
    save(fig, "three-libraries", lang)


def main() -> None:
    for lang in TEXT:
        melito(lang)
        trap(lang)
        tile_map(lang)
        schema(lang)
    for p in sorted(OUT.glob("*.png")):
        print(p.relative_to(ROOT), f"{p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
