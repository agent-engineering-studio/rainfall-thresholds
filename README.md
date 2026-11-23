# rainfall-thresholds

**How much rain does it take to set off a landslide?**
A small, dependency-free Python library that answers that question with the
rainfall thresholds used in landslide science: turn an hourly rain-gauge
series into rainfall events, compare them with a threshold, and fit your own
threshold from past landslides. It ships ready-to-use thresholds for Italy,
fitted on 5,974 real landslides.

> **A threshold exceeded is not an alert.** It says the rain is like the rain
> that triggered landslides before. The official alert in Italy is the
> criticality bulletin of the
> [Dipartimento della Protezione Civile](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/).

**What it does not do.** It does not fetch rain: you bring the series, from a
gauge, a radar or a model. It does not say where a landslide will happen, and
it does not issue warnings. It does not know whether your radar can see:
mark the hours it could not measure as `None`.

[![ci](https://github.com/agent-engineering-studio/rainfall-thresholds/actions/workflows/ci.yml/badge.svg)](https://github.com/agent-engineering-studio/rainfall-thresholds/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rainfall-thresholds)](https://pypi.org/project/rainfall-thresholds/)
[![Python](https://img.shields.io/pypi/pyversions/rainfall-thresholds)](https://pypi.org/project/rainfall-thresholds/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/pyproject.toml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/LICENSE)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/id-plane-dark.png">
  <img alt="Log-log chart of rainfall duration against mean intensity. Thousands of grey dots, each a rainfall event that triggered a landslide in Italy, sit above a blue line, the T5 threshold. A red star marks an example storm of 82 mm in 10 hours, well above the line." src="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/id-plane-light.png">
</picture>

<sub>Every grey dot is a storm that triggered a landslide in Italy (e-ITALICA
catalogue). The blue line is the threshold this library fits: only 5 % of
those storms fall below it. The red star is the storm from the
[quick start](#quick-start).</sub>

---

## Contents

- [The idea in 30 seconds](#the-idea-in-30-seconds)
- [How it works](#how-it-works)
- [Install](#install)
- [Quick start](#quick-start)
- [Step by step](#step-by-step)
  - [1. From hourly rain to rainfall events](#1-from-hourly-rain-to-rainfall-events)
  - [2. Comparing an event with a threshold](#2-comparing-an-event-with-a-threshold)
  - [3. Fitting your own threshold](#3-fitting-your-own-threshold)
  - [4. Measuring what it costs](#4-measuring-what-it-costs)
- [Thresholds for Italy](#thresholds-for-italy)
- [Recipe: check a rain gauge](#recipe-check-a-rain-gauge)
- [API at a glance](#api-at-a-glance)
- [Benchmark](#benchmark)
- [Notebooks and Docker](#notebooks-and-docker)
- [A calibration bench for public bodies](#a-calibration-bench-for-public-bodies)
- [For assistants and agents](#for-assistants-and-agents)
- [Good to know](#good-to-know)
- [References](#references) · [Citing](#citing) · [Contributing](#contributing)

## The idea in 30 seconds

Shallow landslides start when the soil gets too wet. What makes it too wet
is a mix of **how hard** it rains and **for how long**:

- a short, violent downpour can do it: 30 mm in 2 hours;
- so can a long, gentle rain: 60 mm over three days.

In 1980 Nels Caine noticed that, on a log-log chart of *duration* against
*mean intensity*, the storms that triggered landslides sit above a straight
line. That line is the **rainfall threshold**:

```
I = α · D^(-β)

I  mean rainfall intensity (mm/h)
D  rainfall duration (hours)
α  how high the line sits     β  how fast it drops with duration
```

Above the line: rain like the rain that triggered landslides in the past.
Below it: rain that very rarely did. That is all a threshold says, and it is
why thresholds are at the heart of many landslide early-warning systems.

This library gives you the three pieces around that line, in plain Python
with no dependencies.

## How it works

```mermaid
flowchart LR
    A["🌧️ Hourly rain<br/>(timestamp, mm)"] -->|reconstruct_events| B["Rainfall events<br/>duration · total · intensity"]
    B -->|strongest_event| C["Event that matters"]
    C -->|"threshold.exceedance()"| D{"Above the<br/>threshold?"}
    D -->|"> 0"| E["⚠️ Conditions like<br/>past landslides"]
    D -->|"< 0"| F["✅ Below the line"]

    G["📚 Past landslides<br/>(duration, intensity)"] -->|fit_threshold| H["PowerLawThreshold<br/>α, β"]
    I["🇮🇹 ITALICA_T5<br/>ready-made for Italy"] --> H
    H --> D
```

| Step | What you have | What you call | What you get |
|---|---|---|---|
| 1 | an hourly rain series | `reconstruct_events`, `strongest_event` | rainfall events, each with duration, total and intensity |
| 2 | an event and a threshold | `PowerLawThreshold.intensity` / `.cumulated` / `.exceedance` | how much rain the threshold needs, and how far above or below it you are |
| 3 | a catalogue of landslide-triggering events | `fit_threshold` | your own threshold |

## Install

```bash
pip install rainfall-thresholds
```

Python 3.12 or newer. No dependencies: not even NumPy.

## Quick start

A storm over Calabria, southern Italy: 82 mm in about ten hours. Is it
landslide weather?

```python
from datetime import UTC, datetime, timedelta

from rainfall_thresholds import ITALICA_T5, macroregion_of, reconstruct_events, strongest_event

# Hourly rain from a gauge, in mm
start = datetime(2026, 10, 10, tzinfo=UTC)
hourly_mm = [0, 2, 8, 15, 22, 18, 9, 4, 0, 1, 3, 0, 0]
series = [(start + timedelta(hours=h), mm) for h, mm in enumerate(hourly_mm)]

# 1. Pick the threshold for the region
threshold = ITALICA_T5[macroregion_of("Calabria") or "italy"]  # "southern"

# 2. Cut the series into rainfall events and take the one that matters
events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)
event = strongest_event(events, threshold)
assert event is not None

# 3. Compare
print(f"{event.total_mm:.0f} mm in {event.duration_hours:.0f} h = {event.intensity_mm_h:.1f} mm/h")
print(f"T5 at that duration: {threshold.intensity(event.duration_hours):.1f} mm/h")
print(f"{threshold.exceedance(event.intensity_mm_h, event.duration_hours):+.2f} decades")
```

```
82 mm in 10 h = 8.2 mm/h
T5 at that duration: 2.0 mm/h
+0.62 decades
```

The storm is about four times as intense as the threshold (10^0.62 ≈ 4.2):
it is the red star in the chart at the top.

## Step by step

### 1. From hourly rain to rainfall events

A rain gauge gives you one number per hour. A threshold needs *events*: a
start, an end, a total. `reconstruct_events` cuts the series with two
simple rules:

- **`no_rain_break_hours`**: this many dry hours in a row end an event;
- **`min_event_mm`**: events with less rain than this are dropped as noise.

An event runs from its first to its last wet hour, so short dry spells
inside a storm stay in the same event.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/event-reconstruction-dark.png">
  <img alt="Bar chart of 36 hours of rain. Hours 1 to 9 form event 1, 30 mm in 9 hours, despite a 2-hour dry gap. Eight dry hours close it. A 1 mm drizzle at hours 18 and 19 is dropped. Hours 28 to 33 form event 2, 33 mm in 6 hours." src="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/event-reconstruction-light.png">
</picture>

```python
threshold = ITALICA_T5["southern"]
events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)
for e in events:
    print(e.start, e.end, e.duration_hours, e.total_mm, e.intensity_mm_h)

current = strongest_event(events, threshold)  # the event furthest above the threshold
```

**Which event?** A storm, six dry hours and then a little drizzle are two
events. `latest_event` gives the drizzle; `strongest_event` gives the storm.
For monitoring, pass the events of the window you watch (for example the last
48 hours) to `strongest_event`, so an old storm does not stay forever.

Each event is a frozen `RainfallEvent` with `start`, `end`,
`duration_hours`, `total_mm`, `unmeasured_hours`, `source` and the
`intensity_mm_h` and `fully_measured` properties.

> **Not measured is not dry.** The series should be hourly and without gaps:
> a dry hour is `0`, an hour that was not measured (a missing frame, a gauge
> that did not report, a place the radar cannot see) is `None`. A `None` hour
> adds no rain and does not count towards the dry break, so a gap never splits
> an event. The event counts it in `unmeasured_hours`, and its total is then a
> lower bound. If your gauge skips dry hours, fill them in with `0`.

Give the events a `source` (`reconstruct_events(..., source="DPC SRT1")`):
the Italian thresholds are fitted on rain gauges, and radar rain is not gauge
rain. The label is carried, never interpreted.

### 2. Comparing an event with a threshold

A `PowerLawThreshold` answers three questions for an event of a given
duration:

| Method | Question | Unit |
|---|---|---|
| `intensity(D)` | How intense must rain be, on average, to reach the line? | mm/h |
| `cumulated(D)` | How much rain in total must fall to reach the line? | mm |
| `exceedance(I, D)` | How far above (+) or below (−) the line is this event? | decades |

`cumulated` is usually the easiest to talk about. With the threshold for
northern Italy:

```python
from rainfall_thresholds import ITALICA_T5

t = ITALICA_T5["northern"]
for d in (1, 6, 24, 72):
    print(f"{d:>3} h  {t.cumulated(d):5.1f} mm  {t.intensity(d):5.2f} mm/h")
```

```
  1 h    6.4 mm   6.40 mm/h
  6 h   15.3 mm   2.55 mm/h
 24 h   30.0 mm   1.25 mm/h
 72 h   51.3 mm   0.71 mm/h
```

Longer rain needs more water in total, but less per hour.

**Reading `exceedance`.** It is `log10(I / I(D))`, so it is scale-free and
easy to put on a dashboard. Four 24-hour events against the national
threshold (28 mm in 24 h):

| Rain in 24 h | Mean intensity | `exceedance` | In words |
|---:|---:|---:|---|
| 12 mm | 0.5 mm/h | −0.37 | well below the line |
| 24 mm | 1.0 mm/h | −0.07 | just below |
| 58 mm | 2.4 mm/h | +0.31 | twice the threshold intensity |
| 288 mm | 12 mm/h | +1.01 | ten times: an extreme event |

A dry event (zero intensity) gives `-inf`.

### 3. Fitting your own threshold

Have a list of landslides and the rain that triggered them? Fit a threshold
for your own area:

```python
from rainfall_thresholds import fit_threshold

# (duration in hours, mean intensity in mm/h) of rain that triggered landslides
triggering_events = [
    (3, 9.0),
    (5, 4.0),
    (6, 6.5),
    (10, 5.5),
    (12, 3.1),
    (24, 2.4),
    (30, 1.4),
    (48, 1.1),
    (72, 1.0),
    (96, 0.6),
]

fit = fit_threshold(triggering_events, percentile=5)
t = fit.threshold
print(f"T5: I = {t.alpha:.2f} · D^-{t.beta:.3f}   ({fit.n_events} events)")
print(f"at 24 h: {t.intensity(24):.2f} mm/h, i.e. {t.cumulated(24):.0f} mm")
```

```
T5: I = 14.78 · D^-0.737   (10 events)
at 24 h: 1.42 mm/h, i.e. 34 mm
```

(Ten events are enough for an example, not for a real threshold: published
thresholds use hundreds.)

What `fit_threshold` does, in two steps:

1. **Best-fit line.** Least squares on `log I` against `log D` through all
   the events: the orange line below, returned as `fit.central`.
2. **Lower it.** Slide the line down, keeping its slope, until only
   `percentile` % of the events sit beneath it: the blue line, returned as
   `fit.threshold`. With `percentile=5` this is the **T5** threshold.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/fitting-dark.png">
  <img alt="Left: the e-ITALICA events on a log-log chart with an orange best-fit line and a parallel blue line lower down, the T5 threshold. Right: a histogram of the distance of each event from the best-fit line; the lowest 5 percent, left of -0.45, are highlighted in blue." src="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/fitting-light.png">
</picture>

This is the frequentist method of Brunetti et al. (2010) and Peruccacci et
al. (2012), with one difference: they take the percentile from a Gaussian
fitted to a kernel density of the residuals; this package takes it straight
from the residuals. The two agree when the residuals are close to normal,
and the empirical one makes no assumption about their shape.

### 4. Measuring what it costs

T5 catches 95 % of past landslides by construction. What it does not say is
how often it is exceeded when nothing happens. The `measure` functions answer
both on the same scale, for any score that grows with danger (an exceedance,
a 24-hour total, a probability):

```python
from rainfall_thresholds import auc, skill, skill_at_budget

# For each landslide, the highest score in the hours before it.
landslides = [0.62, 0.31, 0.05, -0.08, 0.44]
# For each unit you could alert on (cell-hours, municipality-days...).
ordinary = [-0.9, -0.4, -0.2, 0.1, -0.6, -0.3, 0.2, -1.1, -0.5, -0.7]

s = skill(landslides, ordinary, cutoff=0.0)  # above the threshold = alert
print(f"caught {s.caught} of {s.landslides}, {s.alert_share:.0%} of units on alert")
print(f"discrimination {s.discrimination:.1f}, {s.alerts_per_caught:.1f} alerts per landslide")

fair = skill_at_budget(landslides, ordinary, budget=0.10)  # 10 % of units on alert
print(f"at a 10 % budget: caught {fair.caught} of {fair.landslides}")
print(f"AUC {auc(landslides, ordinary):.2f}")
```

```
caught 4 of 5, 20% of units on alert
discrimination 4.0, 0.5 alerts per landslide
at a 10 % budget: caught 3 of 5
AUC 0.92
```

To compare two scores, compare them **at the same budget**: counting at a
fixed level rewards the score that alerts more. `None` is a score that was
not measured: it is left out and counted in `unmeasured`, never read as
zero. The definitions are those of Limen's backtests, and on the same inputs
the results are identical.

What this gives on real data was measured in Limen
([limen#243](https://github.com/agent-engineering-studio/limen/issues/243)),
with the national curve on model rain (ERA5): 40.7 % of the e-ITALICA
landslides above the threshold against 3.0 % of ordinary moments, and 0 of
286 landslides caught in the regions held out. A threshold fitted on rain
gauges and applied to other rain is not the same threshold.

## Thresholds for Italy

`ITALICA_T5` holds four T5 thresholds fitted with `fit_threshold(percentile=5)`
on the 5,974 events of [e-ITALICA](https://doi.org/10.5281/zenodo.14204473)
v4 with a positive duration and cumulated rainfall:

| Key | α (mm/h) | β | Events | Rain needed in 24 h | in 72 h |
|---|---:|---:|---:|---:|---:|
| `"italy"` | 7.193 | 0.5685 | 5,974 | 28.3 mm | 45.5 mm |
| `"northern"` | 6.400 | 0.5134 | 2,659 | 30.0 mm | 51.3 mm |
| `"central"` | 7.953 | 0.6085 | 1,890 | 27.6 mm | 42.4 mm |
| `"southern"` | 8.754 | 0.6449 | 1,425 | 27.1 mm | 40.0 mm |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/macroregions-dark.png">
  <img alt="Line chart of the rain needed to reach T5 against duration, up to 168 hours, for Italy and its three macroregions. The lines overlap up to about 12 hours; after that the northern threshold needs the most rain, about 78 mm in a week, and the southern the least, about 54 mm." src="https://raw.githubusercontent.com/agent-engineering-studio/rainfall-thresholds/main/docs/img/macroregions-light.png">
</picture>

For short bursts the regions behave alike; over days, the north needs
noticeably more rain than the south before landslides start.

Pick the threshold from the region name with `macroregion_of`:

```python
from rainfall_thresholds import ITALICA_T5, macroregion_of

macroregion_of("Liguria")  # "northern"
macroregion_of("Abruzzo")  # "central"
macroregion_of("Bavaria")  # None: not an Italian region

threshold = ITALICA_T5[macroregion_of("Sicilia") or "italy"]
```

> **Abruzzo and Molise are in the centre**, unlike the ISTAT "Sud". Use
> `macroregion_of` (or `MACROREGIONS`) rather than an ISTAT table, or the
> threshold will not be the one fitted on that region's landslides.

These numbers are **reproducible, not copied**: the catalogue ships with the
tests and `tests/test_italy.py` refits all four thresholds from it on every
run. They are not the thresholds published by the e-ITALICA authors, who use
their own method and partitions; they are what this package's method gives
on their data.

## Recipe: check a rain gauge

Read an hourly CSV, find the current rainfall event and see where it stands:

```python
import csv
from datetime import datetime

from rainfall_thresholds import ITALICA_T5, macroregion_of, reconstruct_events, strongest_event

with open("gauge.csv", encoding="utf-8") as f:  # columns: time, rain_mm (empty: not measured)
    series = [
        (datetime.fromisoformat(r["time"]), float(r["rain_mm"]) if r["rain_mm"] else None)
        for r in csv.DictReader(f)
    ]

threshold = ITALICA_T5[macroregion_of("Liguria") or "italy"]
events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0, source="rain gauge")
event = strongest_event(events, threshold)

if event is None:
    print("No rain event in the window")
else:
    e = threshold.exceedance(event.intensity_mm_h, event.duration_hours)
    needed = threshold.cumulated(event.duration_hours)
    print(
        f"{event.start:%d %b %H:%M} → {event.end:%H:%M}: {event.total_mm:.0f} mm "
        f"(T5 needs {needed:.0f} mm in {event.duration_hours:.0f} h) → {e:+.2f}"
    )
```

```
10 Oct 01:00 → 07:00: 78 mm (T5 needs 16 mm in 7 h) → +0.67
```

Run it every hour on the last two or three days of data and you have the
rainfall part of a simple monitoring loop: a number to watch, not an alert.

## API at a glance

| Name | Kind | What it is |
|---|---|---|
| `PowerLawThreshold(alpha, beta)` | frozen dataclass | `I = α·D^(-β)`, with `.intensity(D)`, `.cumulated(D)`, `.exceedance(I, D)` |
| `reconstruct_events(series, *, no_rain_break_hours, min_event_mm, source=None)` | function | hourly `(datetime, mm or None)` pairs → `list[RainfallEvent]`; `None` is not measured |
| `strongest_event(events, threshold)` | function | the event furthest above the threshold, or `None` |
| `latest_event(events)` | function | the event that ended last, or `None` |
| `RainfallEvent` | frozen dataclass | `start`, `end`, `duration_hours`, `total_mm`, `unmeasured_hours`, `source`, `.intensity_mm_h`, `.fully_measured` |
| `fit_threshold(events, *, percentile=5.0)` | function | `(D, I)` pairs → `ThresholdFit` |
| `ThresholdFit` | frozen dataclass | `threshold`, `central`, `percentile`, `n_events` |
| `percentile_of(values, percentile)` | function | linear-interpolation percentile, same as NumPy's default |
| `skill(landslides, ordinary, cutoff)` | function | landslides caught and units on alert at a cutoff → `Skill` |
| `skill_at_budget(landslides, ordinary, budget, *, floor=None)` | function | the same at the cutoff that puts `budget` of the units on alert |
| `cutoff_at_budget(ordinary, budget, *, floor=None)` | function | that cutoff |
| `Skill` | frozen dataclass | `caught`, `landslides`, `alerts`, `ordinary`, `unmeasured`; `.hit_rate`, `.alert_share`, `.discrimination`, `.alerts_per_caught` |
| `auc(landslides, ordinary)` | function | Mann-Whitney AUC, ties count half |
| `facts.threshold_facts`, `assess_facts`, `fit_facts` | functions | the same answers as JSON-ready dicts, with units and the alert rule |
| `check.check_text(text, facts, *, question="")` | function | numbers of a text that are invented, rounded or in the wrong unit → `list[Misquote]` |
| `mcp_server.create_server()`, `rainfall-thresholds-mcp` | MCP (extra `mcp`) | tools `threshold`, `assess`, `fit`, `check` |
| `ITALICA_T5` | read-only mapping | `"italy"`, `"northern"`, `"central"`, `"southern"` → `PowerLawThreshold` |
| `MACROREGIONS` | read-only mapping | macroregion → set of region names (e-ITALICA spelling) |
| `macroregion_of(region)` | function | region name → macroregion, or `None` |

Everything is fully typed (`py.typed`) and checked with `mypy --strict`.

## Benchmark

A fixed set of known cases runs in CI: the storm of Melito di Porto Salvo on
10 October 2026 on the DPC radar, six e-ITALICA landslides, and two cases
built to test one rule each. 0.1.0 passed **9 of 16** checks: it forgot a
storm when a little drizzle followed it, and could not take an hour that was
not measured. With `strongest_event` and `None` the library passes **13 of
16**. The three it misses are landslides under T5, as T5 allows by
construction. The details, and what is not there yet, are in
[`benchmarks/`](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/benchmarks).

```bash
uv run python -m benchmarks.run
```

## Notebooks and Docker

Four [example notebooks](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/notebooks):
the Italian thresholds over the e-ITALICA landslides, the storm of Melito on
the DPC radar, and fitting your own threshold, with no network; and the join
with the sister libraries, landslides dated by
[ispra-idrogeo](https://agentengineering.it/ispra-idrogeo/) against radar rain
from [dpc-radar](https://agentengineering.it/dpc-radar/). Open them with uv, or
with Docker alone:

```bash
uv run --group examples jupyter lab notebooks/
docker compose up              # http://localhost:8888
make docker-bench              # the benchmark, in a container
```

The compose file gives no fixed name to containers or images: Compose names
them after the project, so two copies run side by side.

## A calibration bench for public bodies

[`app/`](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/app)
is a page in Italian, with Bootstrap Italia, for a public body: it opens on
the e-ITALICA landslides of its region, fits a threshold on the ones that
matter, compares it with the national one, measures its cost in false alarms
on the body's own rain gauge, and exports it. It is not a warning system and
reads no live rain. `docker compose up taratura`, then http://localhost:3001.
[Riuso nella PA](https://agentengineering.it/rainfall-thresholds/riuso/)
says, in Italian, what it does and what stays with the body.

To explain what a threshold is, the docs site has
[Try it](https://agentengineering.it/rainfall-thresholds/explainer/): an
interactive intensity-duration plane that runs in the browser.

## For assistants and agents

A language model may word the numbers; it should never compute them. The
library gives them as data, and checks the words.

- **Facts.** `rainfall_thresholds.facts`: `threshold_facts`, `assess_facts`
  and `fit_facts` return plain dicts, with the unit in every key (`_mm`,
  `_mm_h`, `_h`, `_decades`), what the threshold was fitted on, and the rule
  that a threshold exceeded is not an alert.
- **MCP server.** `pip install "rainfall-thresholds[mcp]"`, then
  `rainfall-thresholds-mcp` on standard input and output. Four tools:
  `threshold`, `assess`, `fit`, `check`. They compute only from what the call
  gives them: no network, no live rain.
- **A check of the text.** `check_text(text, facts)` finds numbers invented,
  rounded the wrong way, or in the wrong unit: 30.9 mm written as 30.9 mm/h,
  the trap of every rainfall threshold. It knows that a number is a fact of
  its unit, not that it is said of the right thing.
- **A faithfulness set.** `benchmarks/faithful.py`: questions, facts, and
  answers written by hand, one faithful and one with known faults; in CI the
  check must find exactly those faults (8 of 8 today). Answers of a model are
  not in it yet.
- **For coding agents.** [`llms.txt`](https://agentengineering.it/rainfall-thresholds/llms.txt),
  [`llms-full.txt`](https://agentengineering.it/rainfall-thresholds/llms-full.txt)
  and an [agent skill](https://agentengineering.it/rainfall-thresholds/skills/rainfall-thresholds/SKILL.md)
  with the traps a model falls into when it writes this code from memory.

The base package still has no dependencies: the MCP SDK comes only with the
`mcp` extra.

## Good to know

- **A threshold is not a forecast.** Rain above T5 means "conditions like
  those that triggered landslides before", not "a landslide will happen
  here". Slope, soil, vegetation and antecedent wetness all matter. Use it
  as one input to a warning system, alongside expert judgement.
- **T5 is deliberately low.** By construction, 95 % of past triggering
  events sit above it: it favours catching events over avoiding false
  alarms.
- **Event reconstruction is simplified.** It follows Melillo et al. (2018),
  whose CTRL-T tool also varies the dry gap with the season. The e-ITALICA
  durations come from that fuller procedure, so applying the Italian
  thresholds to events from `reconstruct_events` mixes the two: fine for
  monitoring, worth knowing for a study.
- **Units are fixed:** hours, millimetres, millimetres per hour.
- **No sister library inside.** The package imports neither dpc-radar nor
  ispra-idrogeo, and a test keeps it so: [Limen](https://github.com/agent-engineering-studio/limen)
  pins all three, and a library that imported another would tie their
  releases together. The join lives in Limen, in notebook 04 and in `app/`.

## Where it's used

Extracted from [Limen](https://github.com/agent-engineering-studio/limen),
which uses it for the rainfall component of its landslide score. Using it
somewhere else? [Open an issue](https://github.com/agent-engineering-studio/rainfall-thresholds/issues)
and tell us: we'd love to list it here.

## References

- Caine N. (1980). The rainfall intensity-duration control of shallow
  landslides and debris flows. *Geografiska Annaler A* 62, 23-27.
- Brunetti M.T. et al. (2010). Rainfall thresholds for the possible
  occurrence of landslides in Italy. *NHESS* 10, 447-458.
- Peruccacci S. et al. (2012). Lithological and seasonal control on
  rainfall thresholds for the possible initiation of landslides in central
  Italy. *Geomorphology* 139-140, 79-90.
- Melillo M. et al. (2018). A tool for the automatic calculation of
  rainfall thresholds for landslide occurrence. *Environmental Modelling &
  Software* 105, 230-243.
- Peruccacci S. et al. (2023). ITALICA: an ITAlian rainfall-induced
  LandslIdes CAtalogue. *ESSD* 15, 2863-2877.
- Brunetti M.T. et al. (2024). e-ITALICA (enhanced ITAlian rainfall-induced
  LandslIdes CAtalogue), v4. Zenodo,
  [doi:10.5281/zenodo.14204473](https://doi.org/10.5281/zenodo.14204473).

## Citing

If this library helps your work, please cite the method and data papers
above, and link to this repository:

```
Zileni G. rainfall-thresholds: rainfall intensity-duration thresholds for
shallow landslides (Python). https://github.com/agent-engineering-studio/rainfall-thresholds
```

## Contributing

Issues and pull requests are welcome: new regional thresholds, better event
reconstruction, examples from other countries. See
[CONTRIBUTING.md](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/CONTRIBUTING.md). To set up and run the checks:

```bash
uv sync
make check     # ruff, mypy --strict, pytest with 100 % coverage
make figures   # redraw the README charts (docs/make_figures.py)
```

⭐ If you find it useful, a star helps others find it.

## Data licence

The test fixture `tests/fixtures/italica_v4_dur_rain.csv` is e-ITALICA v4
(Brunetti et al. 2024), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
reduced to four columns (id, region, duration, cumulated rainfall). The
charts in `docs/img/` are drawn from it.

## License

Code: [Apache-2.0](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/LICENSE).
