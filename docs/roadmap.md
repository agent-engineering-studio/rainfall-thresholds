# Roadmap

Where rainfall-thresholds goes, and what each step measured. The plan is
tracked in [#4](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/4);
every phase has its issue.

!!! warning "Ground rule"
    A threshold exceeded is not an alert. The official alert in Italy is the
    [criticality bulletin](https://rischi.protezionecivile.gov.it/it/meteo-idro/allertamento/)
    of the Dipartimento della Protezione Civile. Where nothing was measured,
    the answer is "not measured", never zero.

## Where it started

The library came out of [Limen](https://github.com/agent-engineering-studio/limen),
an open early-warning system for landslides, floods and wildfires in Italy,
which uses it for the rainfall trigger of its landslide score. Limen's
backtests ([limen#243](https://github.com/agent-engineering-studio/limen/issues/243))
said what the threshold does there, with model rain (ERA5): 40.7 % of the
e-ITALICA landslides above the threshold against 3.0 % of ordinary moments,
and 0 of 286 landslides caught by the engine in the regions held out. The
24-hour total ranked better than the engine's score (AUC 0.75 against 0.60).
That is where this plan starts.

## Rules that hold for every phase

- **The package depends on no sister library.** It imports neither
  [dpc-radar](https://agentengineering.it/dpc-radar/) nor
  [ispra-idrogeo](https://agentengineering.it/ispra-idrogeo/) nor Limen, and
  a test keeps it so. Limen pins all three: a library that imported another
  would tie their releases together. The join lives in Limen, in notebook 04
  and in `app/` ([#21](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/21)).
- **Data come in as data.** A measure that needs other libraries runs in
  Limen; its result comes here as a small file with its source, and the
  tests recompute from it.
- **Data first, then conclusions.**

## Phase 0 · Benchmark of known cases · [#5](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/5) · ✅

Sixteen checks in [`benchmarks/`](benchmark.md): the Melito di Porto Salvo
storm of 10 October 2026 on the DPC radar, the day after, six e-ITALICA
landslides picked by a rule, and two cases built from Melito's hours.

**Check:** 0.1.0 passed 9 of 16.

## Phase 1 · The right event, and rain that was not measured · [#6](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/6) · ✅

`strongest_event` instead of the last event, `None` for an hour not
measured, a `source` label, and the README rule that a threshold is not an
alert.

**Check:** 13 of 16. The storm followed by drizzle went from −0.65 to +0.78;
the storm with three hours missing reads +0.51 on the 59.6 mm measured. The
three still missed are landslides under T5, as T5 allows by construction.

**For Limen:** `caine.event_reconstruction.scelta_evento` in `landslide.yaml`
([limen#660](https://github.com/agent-engineering-studio/limen/pull/660)),
**off** (`ultimo`) until the backtest of the twelve windows of limen#122
measures `piu_forte`.

## Phase 2 · The cost in false alarms · [#7](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/7) · functions ✅, measure open

`skill`, `skill_at_budget`, `cutoff_at_budget`, `auc`: landslides caught,
alert share, discrimination, alerts per landslide caught.

**Check:** on 2,000 random inputs, the same results as Limen's own cutoff
and both of its AUC functions, with no difference.

**What is not there:** the numbers of limen#243 recomputed with these
functions. The ordinary moments are in Limen's archive: it runs on Limen's
server.

## Phase 3 · Rain that does not come from a rain gauge · [#8](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/8) · pilot ✅, measure from 2018 ✅

The Italian thresholds are fitted on rain gauges; the DPC radar alone read
about 20 % more than the gauge-corrected «Merging» in 2026, and not the same
everywhere. Is a gauge threshold valid on radar rain?

The data are ready: IdroGEO has 1,710 landslides dated to the day since 2018,
1,608 with the point within 1 km (counted on 23/11/2026, `dated_landslides`
of ispra-idrogeo). They are uneven: Emilia-Romagna 305, Apulia 2. The measure
runs in Limen, region by region; a result does not stand for Italy.

**Pilot on 2026** ([the data and how they were made](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/benchmarks/measures)):
the 9 IdroGEO slides and flows dated to the day between June and November
2026, point within 1 km, on Limen's archive of DPC frames. With the
«Merging» (gauges and radar), 7 of 9 caught and 66 of 338 rainfall events
above T5 at those points: 9.4 alerts per landslide caught. With the radar
alone, 8 of 9 caught and 98 of 382 events above T5: 12.25 alerts per
landslide caught. One landslide more, 32 alerts more.

**Measure from 2018 to 2025** ([the data and how they were made](https://github.com/agent-engineering-studio/rainfall-thresholds/tree/main/benchmarks/measures),
[limen#677](https://github.com/agent-engineering-studio/limen/issues/677)):
the radar history at 4,200 dated landslides, 1,057 of e-ITALICA (with the
rain at the gauge) and 3,143 of IdroGEO.

- On the same 971 landslides the rain is above T5 at the gauge for 95.6 %
  and on the radar for 66.0 % (37.2 % without Liguria). On the triggering
  events the radar reads 0.68 times the gauge.
- Against 388,063 ordinary moments at the same points, the gauge threshold
  still separates on radar rain: AUC 0.85 on e-ITALICA, 0.73 on IdroGEO.
- The bias factor of dpc-radar lowers the rain and does not change the
  order: the same landslides caught at the same alert share.
- A threshold fitted on radar rain does not hold: alpha between 0.35 and
  1.96 from one set and one macroregion to another. **No radar threshold
  goes into the library.**

**What is not there:** a comparison at the same place (the radar is read at
the landslide, the gauge is the nearest one), and samples that are not
mostly one region: e-ITALICA from 2018 is 74 % Liguria, IdroGEO 47 %
Trentino-Alto Adige.

## Phase 4 · AI layer · [#9](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/9) · ✅

Facts as JSON-ready dicts with the unit in every key, `check_text` (numbers
invented, rounded the wrong way, or in the wrong unit), an MCP server as the
optional extra `mcp`, `llms.txt` and an agent skill.

**Check:** the faithfulness set, four questions with a faithful and a faulty
hand answer each: 8 of 8 scored as expected. Writing it found a wrong number
in a hand answer and two faults of the check, all fixed.

**What is not there:** answers of a model in the set; calls to a paid model
only after an explicit yes.

## Phase 5 · A tool for public bodies · [#10](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/10) · ✅

A calibration bench in `app/`, in Italian, with Bootstrap Italia and no CDN;
[Try it](explainer.md); `publiccode.yml` checked in CI;
[Riuso nella PA](riuso.md). It does not compete with Limen: no real time, no
score, no alerts.

**What is not there:** the cost in false alarms on real data, which needs a
body's own gauge series; English texts in the bench.

## Also done

Four [notebooks](examples.md) and Docker with no fixed container names
([#14](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/14)).
The story, in Italian: [Basta questa pioggia per far franare?](https://agentengineering.it/blog/soglie-pioggia-frane-rainfall-thresholds/)
([English](https://agentengineering.it/en/blog/soglie-pioggia-frane-rainfall-thresholds/)).
