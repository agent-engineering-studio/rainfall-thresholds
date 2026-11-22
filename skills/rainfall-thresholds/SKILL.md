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
(`threshold_facts`, `assess_facts`, `fit_facts`), and before you send the
text, `rainfall_thresholds.check.check_text(text, facts)`.

## The traps

- **mm is not mm/h.** `cumulated(D)` is a total in mm, `intensity(D)` a mean
  intensity in mm/h. Over 35 hours T5 asks 30.9 mm, not 30.9 mm/h.
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
