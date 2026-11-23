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

## The gauge thresholds on radar rain, 2018-2025 (#8, limen#677)

`radar-2018-2025-landslides.csv` (one row per landslide) and
`radar-2018-2025-groups.csv` (one row per group of landslides), made by
`limen misura-soglia-radar` on 23/11/2026 (Limen commit `d6cda0e`) with
rainfall-thresholds 0.3.0, dpc-radar 0.4.0 and ispra-idrogeo 0.11.0. The
report, with every table, is
[`docs/misure/misura_soglia_radar_2018_2025.md`](https://github.com/agent-engineering-studio/limen/blob/main/docs/misure/misura_soglia_radar_2018_2025.md)
in Limen.

**What it is.** The radar history IT-DPC-SRI (radar alone, no gauges) from
2018 to 2025, read at the point of 4,200 landslides:

- 1,057 landslides of e-ITALICA v4 from 2018 to 2021. For 973 of them the
  catalogue gives the triggering rain at the nearest gauge (duration and
  cumulated rain).
- 3,143 landslides of IdroGEO dated to the day, from 2018 to 2025.

At each point, the rainfall events (6 dry hours, 2 mm) that touch the 48 hours
before the landslide. The score is the highest exceedance over the T5
threshold of the macroregion, in decades. `-99` means no rain event in the
window; an empty score means the window was not measured. The **ordinary
moments** are the same points every 30 days, at least 15 days away from a
landslide there, scored the same way: 388,063. They are not in the files:
the groups file has their counts, the cutoffs at a 2 % and a 5 % alert share,
and the AUC. "Radar corrected" is the radar rain times the bias factor of
dpc-radar at the point.

**What it says.**

- On the same 971 landslides, the rain is above T5 at the gauge for **928**
  (95.6 %) and on the radar for **641** (66.0 %). Without Liguria: 235 and 93
  of 250 (94.0 % and 37.2 %).
- Over the duration of the gauge event, the radar reads **0.68** times the
  gauge (median of 970 landslides); 0.51 without Liguria. With the bias
  factor: 0.46. The factor is built on 2026 against the «Merging», and here
  it lowers a rain that is already low.
- Against the ordinary moments the threshold still separates on radar rain.
  e-ITALICA: 643 of 1,053 landslides above T5 (61.1 %) against 9.7 % of the
  ordinary moments, AUC 0.85. IdroGEO: 1,074 of 3,055 (35.2 %) against 5.7 %,
  AUC 0.73.
- At the same alert share the bias factor changes nothing: 354 landslides
  caught at 2 % with the radar alone, 341 with the radar corrected (e-ITALICA);
  645 and 645 (IdroGEO). It moves the cutoff, not the order.
- It is not the same everywhere: in the centre 26 of 120 e-ITALICA landslides
  are above T5 on the radar, in the north 556 of 807.
- **A threshold fitted on radar rain does not hold.** The 5th percentile fit
  on the radar events of the landslides gives alpha 0.57 and beta 0.18 on
  e-ITALICA and alpha 0.42 and beta 0.19 on IdroGEO (T5 for Italy: 7.19 and
  0.57), and between 0.35 and 1.96 from one macroregion to another. No radar
  threshold goes into the library.

**What it does not say.** The radar is read at the landslide and the gauge is
the nearest one: not the same place. The durations of e-ITALICA come from
another reconstruction of the events. e-ITALICA from 2018 to 2021 is 74 %
Liguria and IdroGEO is 47 % Trentino-Alto Adige: read the numbers without
them too. 1,056 landslides have no rain event on the radar in the 48 hours,
and 92 are not measured. The ordinary moments are only at points where a
landslide happened.

**Licence.** Derived from the DPC radar (IT-DPC-SRI, Fondazione Bruno Kessler
on data © Dipartimento della Protezione Civile, CC BY-SA 4.0,
doi:10.5281/zenodo.18637608), from IdroGEO (ISPRA, CC BY-SA 4.0: "ISPRA –
Regioni e Province Autonome. Inventario dei Fenomeni Franosi in Italia -
IFFI. idrogeo.isprambiente.it") and from e-ITALICA v4 (CC BY 4.0,
doi:10.5281/zenodo.14204473): the two files are CC BY-SA 4.0.
