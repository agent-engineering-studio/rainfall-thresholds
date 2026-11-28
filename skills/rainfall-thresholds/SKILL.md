---
name: rainfall-thresholds
description: Compare rainfall with the landslide rainfall thresholds of Italy (Caine intensity-duration, T5 fitted on the e-ITALICA landslides) in Python with the rainfall-thresholds library - rainfall events from an hourly series, how far an event is above the threshold, fitting your own threshold, measuring a threshold's cost in false alarms, checking that a text quotes the numbers right. Use when code or an answer asks whether rain is enough to trigger landslides, or mentions rainfall thresholds, Caine, ITALICA, e-ITALICA, T5 or rainfall-thresholds.
---

# rainfall-thresholds

`rainfall-thresholds` answers one question: **is this rain like the rain
that triggered landslides before?** It has no dependencies. It does not fetch
rain: the caller brings an hourly series from a gauge, a radar or a model.

Full documentation: https://agentengineering.it/rainfall-thresholds/ ·
everything as plain text: https://agentengineering.it/rainfall-thresholds/llms-full.txt

## The rule that goes with every answer

**A threshold exceeded is not an alert.** The official alert in Italy is the
criticality bulletin of the Dipartimento della Protezione Civile
(https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/). For
danger to people, point to the bulletin, the regional civil protection and
112. Never write "alert", "warning" or "risk of landslide here" from a
threshold alone.

## Setup

```bash
pip install rainfall-thresholds            # the library, no dependencies
pip install "rainfall-thresholds[mcp]"     # + the MCP server: rainfall-thresholds-mcp
```

## Recipe

```python
from datetime import datetime

from rainfall_thresholds import ITALICA_T5, macroregion_of, reconstruct_events, strongest_event

series: list[tuple[datetime, float | None]] = ...  # hourly; 0 = dry, None = not measured
threshold = ITALICA_T5[macroregion_of("Calabria") or "italy"]
events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0, source="rain gauge")
event = strongest_event(events, threshold)  # not latest_event: see the traps
if event is not None:
    print(event.total_mm, event.duration_hours, threshold.cumulated(event.duration_hours))
    print(threshold.exceedance(event.intensity_mm_h, event.duration_hours))  # decades
```

The same as data, for an answer in words: `rainfall_thresholds.facts`
(`threshold_facts`, `assess_facts`, `fit_facts`, `trust_facts`,
`margin_facts`, `published_facts`), and before you send the text,
`rainfall_thresholds.check.check_text(text, facts)`.

From a mapping `{hour: mm or None}`, `event_against_threshold(hours,
threshold, no_rain_break_hours=6, min_event_mm=2.0, choice="strongest")`
gives the event with `.ratio`, `.excess_decades` and `.at_least` (the rain is
a lower bound: hours not measured inside the event or at its edges).
`rain_to_threshold(event, threshold, more_hours=(1, 3, 6))` is the rain still
needed if the event goes on: arithmetic on the line, not a forecast.
`calibration_of("Valle d'Aosta")` says how the line sits on the landslides of
a region (`.position`: `"high"`, `"low"`, `"as fitted"`); `macroregion_of`
and `calibration_of` take the ISTAT region code too.

## The traps

- **mm is not mm/h.** `cumulated(D)` is a total in mm, `intensity(D)` a mean
  intensity in mm/h. Over 35 hours T5 asks 30.9 mm, not 30.9 mm/h.
- **The line is not equally good everywhere.** 16.2 % of Valle d'Aosta's
  landslides are below it, 1.3 % of Calabria's, where 5 % is expected. Say it
  (`trust_facts`), and say when the landslides are too few to tell.
- **A landslide with a day and no hour** takes the end of its day: the next
  local midnight in Europe/Rome, as UTC. Not noon, not 00:00, not +24 h.
- **Exceedance is in decades**, `log10(I / I(D))`: +0.3 is twice the threshold
  intensity, +1 ten times; below zero is below. A dry event is `-inf`.
- **The last event is not the one that matters.** A storm, six dry hours and
  2.5 mm of drizzle are two events; `latest_event` gives the drizzle. Use
  `strongest_event` over the window you watch.
- **Not measured is not dry.** A missing hour is `None`, never `0`: a zero can
  split an event and hide a storm. With `unmeasured_hours > 0` the total is a
  lower bound.
- **Gauge, not radar.** The Italian thresholds are fitted on rain gauges. On
  radar or model rain the comparison is not validated: say so. In 2026 the DPC
  radar alone read about 20 % more than the gauge-corrected «Merging», and
  differently from place to place.
- **Abruzzo and Molise are central**, not southern: use `macroregion_of`, not
  the ISTAT macroareas. Region names as e-ITALICA spells them
  ("Emilia-Romagna", "Trentino-Alto Adige").
- **T5 misses 5 % of past landslides by construction**, and says nothing of
  false alarms. To measure them: `rainfall_thresholds.measure`
  (`skill_at_budget`, `auc`), comparing two scores at the same alert budget.
- **These are not the published e-ITALICA thresholds**: they are this
  library's fit on the e-ITALICA data.
- **Units are fixed:** hours, mm, mm/h. The series must be hourly.

Data: e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473), CC BY 4.0.
