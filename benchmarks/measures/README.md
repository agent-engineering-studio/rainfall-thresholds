# Measures on real data

Results of measures that need more than this library, run elsewhere and kept
here as small files with their source. The tests recompute every number
quoted in the docs from these files (`tests/test_measures_data.py`).

## Pilot 2026: the «Merging» against the radar alone (#8)

`pilot-2026-merging-vs-radar.csv`, made by [`tools/pilot_2026.py`](https://github.com/agent-engineering-studio/rainfall-thresholds/blob/main/tools/pilot_2026.py)
on 23/11/2026 with ispra-idrogeo 0.10.0, dpc-radar 0.3.0 and
rainfall-thresholds 0.3.0, on the local archive of Limen (DPC frames from
9 June to 16 November 2026).

**What it is.** The IdroGEO landslides dated to the day inside those months,
with the point within 1 km: 40. Of these, the 9 slides and flows (falls,
sinkholes and n.d. left out). At each point, two hourly rain series over the
whole period: the «Merging» (CUM3, rain gauges and radar, split into hours by
the radar as dpc-radar does; missing when CUM3 is missing) and the radar alone
(SRT1). For each series, the rainfall events of the period (6 dry hours, 2 mm),
compared with the T5 threshold of the macroregion:

- a landslide is **caught** when an event above T5 ends in the 72 hours
  before the end of its day (the date has no hour);
- every event above T5 at that point in the period is an **alert**.

**What it says.**

- «Merging»: **7 of 9** landslides caught; **66 of 338** events above T5
  (19.5 %); **9.4 alerts per landslide caught**.
- Radar alone: **8 of 9** caught; **98 of 382** events above T5 (25.7 %);
  **12.25 alerts per landslide caught**.
- One landslide (Lazio, 11/08) had no rain event in the window with either
  rain, although the rain was measured.
- At the same points the radar alone gives more events and more of them above
  the threshold: one landslide more, 32 alerts more. At a single point an
  event above T5 comes every two or three weeks, in summer and autumn.

**What it does not say.** Nine landslides, all but one in the north, in five
months of summer and autumn: a pilot, not a validation. "Alerts" count every
event above T5, including the ones that came with the landslides and with
landslides nobody recorded. The «Merging» is gauges and radar, not gauges
alone, and some gauges in it were faulty in 2026 (dpc-radar#44). The measure
from 2018, on the radar history and all the dated landslides, region by region,
is [limen#677](https://github.com/agent-engineering-studio/limen/issues/677);
the cost in false alarms of the trigger terms of Limen is
[limen#676](https://github.com/agent-engineering-studio/limen/issues/676).

**Licence.** Derived from IdroGEO (ISPRA, CC BY-SA 4.0: "ISPRA – Regione <X>.
Inventario dei Fenomeni Franosi in Italia - IFFI. idrogeo.isprambiente.it")
and from the DPC radar (© Dipartimento della Protezione Civile, CC BY-SA
4.0): the file is CC BY-SA 4.0.
