"""Draw the README figures from the package and the e-ITALICA fixture.

    uv run --with matplotlib python docs/make_figures.py

Each figure is written twice, ``<name>-light.png`` and ``<name>-dark.png``,
so the README can pick one with ``<picture>`` and GitHub's colour scheme.
"""

from __future__ import annotations

import csv
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rainfall_thresholds import (
    ITALICA_T5,
    MACROREGIONS,
    RainfallEvent,
    fit_threshold,
    latest_event,
    reconstruct_events,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"
FIXTURE = ROOT / "tests" / "fixtures" / "italica_v4_dur_rain.csv"

THEMES = {
    "light": {
        "surface": "#ffffff",
        "text": "#0b0b0b",
        "muted": "#52514e",
        "grid": "#e4e3df",
        "points": "#9a9993",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
        "accent": "#e34948",
    },
    "dark": {
        "surface": "#0d1117",
        "text": "#f0efec",
        "muted": "#c3c2b7",
        "grid": "#30363d",
        "points": "#6e6d68",
        "series": ["#3987e5", "#d95926", "#199e70"],
        "accent": "#e66767",
    },
}

EXAMPLE_HOURS = [0, 2, 8, 15, 22, 18, 9, 4, 0, 1, 3, 0, 0]


def load_catalogue() -> list[tuple[str, float, float]]:
    with FIXTURE.open(encoding="utf-8") as f:
        return [
            (
                row["region"],
                float(row["duration_h"]),
                float(row["cumulated_rainfall_mm"]) / float(row["duration_h"]),
            )
            for row in csv.DictReader(f)
        ]


def style(ax: plt.Axes, t: dict[str, object]) -> None:
    ax.set_facecolor(t["surface"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["muted"])
    ax.tick_params(colors=t["muted"], which="both")
    ax.xaxis.label.set_color(t["text"])
    ax.yaxis.label.set_color(t["text"])
    ax.title.set_color(t["text"])
    ax.grid(True, which="major", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def legend(ax: plt.Axes, t: dict[str, object], **kw: object) -> None:
    leg = ax.legend(frameon=False, **kw)
    for text in leg.get_texts():
        text.set_color(t["text"])


def save(fig: plt.Figure, name: str, theme: str) -> None:
    fig.savefig(
        OUT / f"{name}-{theme}.png", dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight"
    )
    plt.close(fig)


def example_event() -> RainfallEvent:
    start = datetime(2026, 10, 10, tzinfo=UTC)
    series = [(start + timedelta(hours=h), mm) for h, mm in enumerate(EXAMPLE_HOURS)]
    event = latest_event(reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0))
    assert event is not None
    return event


def id_plane(catalogue: list[tuple[str, float, float]], theme: str) -> None:
    """The hero figure: every e-ITALICA event, the national T5, an example event."""
    t = THEMES[theme]
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=t["surface"])
    style(ax, t)
    ds = [d for _, d, _ in catalogue]
    is_ = [i for _, _, i in catalogue]
    ax.scatter(
        ds,
        is_,
        s=6,
        color=t["points"],
        alpha=0.45,
        linewidths=0,
        label=f"Rainfall that triggered a landslide ({len(catalogue):,} events)",
    )
    t5 = ITALICA_T5["italy"]
    xs = [10 ** (k / 20) for k in range(0, 81)]
    ax.plot(
        xs,
        [t5.intensity(x) for x in xs],
        color=t["series"][0],
        linewidth=2.2,
        label=f"T5 threshold for Italy: I = {t5.alpha:.2f} · D$^{{-{t5.beta:.3f}}}$",
    )
    ax.fill_between(xs, [t5.intensity(x) for x in xs], 1e-2, color=t["series"][0], alpha=0.07)
    event = example_event()
    ax.scatter(
        [event.duration_hours],
        [event.intensity_mm_h],
        s=140,
        marker="*",
        color=t["accent"],
        edgecolors=t["surface"],
        linewidths=1.5,
        zorder=5,
        label="Example storm: 82 mm in 10 h",
    )
    ax.text(
        14,
        0.25,
        "below the line:\nonly 5 % of past landslides",
        color=t["series"][0],
        fontsize=9,
        ha="left",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, 1e4)
    ax.set_ylim(1e-2, 2e2)
    ax.set_xlabel("Rainfall duration D (hours)")
    ax.set_ylabel("Mean rainfall intensity I (mm/h)")
    legend(ax, t, loc="upper right", fontsize=9)
    save(fig, "id-plane", theme)


def macroregions(theme: str) -> None:
    """The four T5 lines as cumulated rainfall, the number people act on."""
    t = THEMES[theme]
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=t["surface"])
    style(ax, t)
    xs = [1 + k for k in range(0, 168)]
    t5 = ITALICA_T5["italy"]
    ax.plot(
        xs,
        [t5.cumulated(x) for x in xs],
        color=t["muted"],
        linewidth=2,
        linestyle="--",
        label="Italy",
    )
    ax.text(169, t5.cumulated(168), " Italy", color=t["text"], va="center", fontsize=9)
    for color, name in zip(t["series"], ("northern", "central", "southern"), strict=True):
        th = ITALICA_T5[name]
        ax.plot(
            xs, [th.cumulated(x) for x in xs], color=color, linewidth=2, label=name.capitalize()
        )
        ax.text(
            169,
            th.cumulated(168),
            f" {name.capitalize()}",
            color=t["text"],
            va="center",
            fontsize=9,
        )
    ax.set_xlim(0, 195)
    ax.set_ylim(0, 90)
    ax.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
    ax.set_xlabel("Rainfall duration D (hours)")
    ax.set_ylabel("Rain needed to reach T5 (mm)")
    legend(ax, t, loc="upper left", fontsize=9)
    save(fig, "macroregions", theme)


def reconstruction(theme: str) -> None:
    """Hourly bars, coloured by the event they end up in."""
    t = THEMES[theme]
    hourly = [
        0,
        1,
        4,
        9,
        6,
        2,
        0,
        0,
        3,
        5,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0.5,
        0.5,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        2,
        7,
        12,
        8,
        3,
        1,
        0,
        0,
    ]
    start = datetime(2026, 10, 10, tzinfo=UTC)
    series = [(start + timedelta(hours=h), mm) for h, mm in enumerate(hourly)]
    events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)
    fig, ax = plt.subplots(figsize=(9, 3.4), facecolor=t["surface"])
    style(ax, t)
    ax.grid(False, axis="x")
    colors = [t["points"]] * len(hourly)
    for k, e in enumerate(events):
        first = int((e.start - start).total_seconds() // 3600)
        last = int((e.end - start).total_seconds() // 3600)
        for h in range(first, last + 1):
            colors[h] = t["series"][k]
        ax.axvspan(first - 0.5, last + 0.5, color=t["series"][k], alpha=0.08)
        ax.text(
            (first + last) / 2,
            13.2,
            f"Event {k + 1}\n{e.total_mm:.0f} mm in {e.duration_hours:.0f} h",
            ha="center",
            color=t["text"],
            fontsize=9,
        )
    ax.bar(range(len(hourly)), hourly, color=colors, width=0.8)
    ax.annotate(
        "", xy=(17.5, 6), xytext=(9.5, 6), arrowprops={"arrowstyle": "<->", "color": t["muted"]}
    )
    ax.text(
        13.5, 6.6, "8 dry hours ≥ 6\n→ event 1 closes", ha="center", color=t["muted"], fontsize=8.5
    )
    ax.text(18.5, 1.2, "1 mm < 2 mm\n→ dropped", ha="center", color=t["muted"], fontsize=8.5)
    ax.text(6.5, 5.2, "2 dry h < 6\n→ same event", ha="center", color=t["muted"], fontsize=8)
    ax.set_ylim(0, 17)
    ax.set_xlim(-1, len(hourly))
    ax.set_xlabel("Hour")
    ax.set_ylabel("Rain (mm)")
    save(fig, "event-reconstruction", theme)


def fitting(catalogue: list[tuple[str, float, float]], theme: str) -> None:
    """Step 1: least squares. Step 2: lower it to the 5th percentile of residuals."""
    t = THEMES[theme]
    pairs = [(d, i) for _, d, i in catalogue]
    fit = fit_threshold(pairs, percentile=5)
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(10, 4.2), facecolor=t["surface"], gridspec_kw={"width_ratios": [1.4, 1]}
    )
    style(left, t)
    style(right, t)
    left.scatter(
        [d for d, _ in pairs],
        [i for _, i in pairs],
        s=5,
        color=t["points"],
        alpha=0.4,
        linewidths=0,
    )
    xs = [10 ** (k / 20) for k in range(0, 81)]
    left.plot(
        xs,
        [fit.central.intensity(x) for x in xs],
        color=t["series"][1],
        linewidth=2,
        label="① best-fit line (least squares)",
    )
    left.plot(
        xs,
        [fit.threshold.intensity(x) for x in xs],
        color=t["series"][0],
        linewidth=2.2,
        label="② lowered to the 5th percentile = T5",
    )
    left.annotate(
        "",
        xy=(300, fit.threshold.intensity(300)),
        xytext=(300, fit.central.intensity(300)),
        arrowprops={"arrowstyle": "->", "color": t["text"]},
    )
    left.set_xscale("log")
    left.set_yscale("log")
    left.set_xlim(1, 1e4)
    left.set_ylim(1e-2, 2e2)
    left.set_xlabel("Duration D (hours)")
    left.set_ylabel("Intensity I (mm/h)")
    legend(left, t, loc="upper right", fontsize=8.5)

    residuals = [math.log10(i) - math.log10(fit.central.intensity(d)) for d, i in pairs]
    shift = math.log10(fit.threshold.alpha / fit.central.alpha)
    bins = [-1.6 + k * 0.05 for k in range(0, 65)]
    below = [r for r in residuals if r < shift]
    above = [r for r in residuals if r >= shift]
    right.hist(above, bins=bins, color=t["points"], rwidth=0.85)
    right.hist(below, bins=bins, color=t["series"][0], rwidth=0.85)
    right.axvline(shift, color=t["series"][0], linewidth=1.5, linestyle="--")
    right.axvline(0, color=t["series"][1], linewidth=1.5)
    right.text(
        shift - 0.05,
        right.get_ylim()[1] * 0.85,
        f"5 %\n({shift:+.2f})",
        ha="right",
        color=t["text"],
        fontsize=9,
    )
    right.text(0.05, right.get_ylim()[1] * 0.85, "best fit", ha="left", color=t["text"], fontsize=9)
    right.set_xlabel("Distance from the best-fit line (log10 I)")
    right.set_ylabel("Events")
    save(fig, "fitting", theme)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    catalogue = load_catalogue()
    assert {r for r, _, _ in catalogue} == set().union(*MACROREGIONS.values())
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    for theme in THEMES:
        id_plane(catalogue, theme)
        macroregions(theme)
        reconstruction(theme)
        fitting(catalogue, theme)


if __name__ == "__main__":
    main()
