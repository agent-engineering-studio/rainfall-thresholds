# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-11-22

### Added

- `facts`: `threshold_facts`, `assess_facts`, `fit_facts`, the answers as
  JSON-ready dicts with units in the keys and the alert rule (#9).
- `check.check_text`: numbers of a text that are invented, rounded the wrong
  way or in the wrong unit (mm for mm/h) (#9).
- An MCP server, `rainfall-thresholds-mcp`, with the optional extra `mcp`:
  tools `threshold`, `assess`, `fit`, `check`; no network (#9).
- `benchmarks/faithful.py`: a faithfulness set of hand-written answers, run
  in CI with `--check` (#9).
- `llms.txt`, `llms-full.txt` and an agent skill, built with the site (#9).
- `measure`: `skill`, `skill_at_budget`, `cutoff_at_budget`, `Skill` and
  `auc`, to measure a threshold on landslides and ordinary moments: hit rate,
  alert share, discrimination, alerts per landslide caught (#7). Same
  definitions as Limen's backtests: on 2,000 random inputs the results equal
  Limen's `_soglia_a_carico` and both of its `auc` functions.
- `notebooks/`: three example notebooks, run without network and in CI
  (#14).
- `Dockerfile` and `compose.yaml`: the notebooks and the benchmark with
  Docker alone, with no fixed container or image name; `make docker-up`,
  `docker-bench`, `docker-down` (#14).

## [0.2.0] - 2026-11-22

### Added

- `benchmarks/`: known cases with the answer we expect, run in CI with
  `--check` (#5). Melito di Porto Salvo and Bagaladi on 10 October 2026 (DPC
  radar, SRT1), six e-ITALICA landslides, and two constructed cases. 0.1.0
  passes 9 of 16 checks.
- `strongest_event(events, threshold)`: the event furthest above the
  threshold. `latest_event` can pick a little drizzle after a storm and
  forget the storm (#6).
- Hours not measured: `reconstruct_events` takes `None` for an hour that was
  not measured. It adds no rain and does not count towards the dry break, so
  a gap never splits an event; `RainfallEvent.unmeasured_hours` and
  `.fully_measured` say so (#6).
- `source=` on `reconstruct_events`, carried as `RainfallEvent.source` (#6).
- A test that fails if the package imports dpc_radar, ispra_idrogeo or limen.
- README: a threshold exceeded is not an alert; what the library does not do.

With these the benchmark goes from 9 to 13 of 16.

## [0.1.0] - 2026-11-02

### Added

- `PowerLawThreshold`: the Caine intensity-duration threshold, with the
  threshold intensity, cumulated rainfall and the exceedance in decades.
- `reconstruct_events` / `latest_event`: rainfall events from an hourly
  series (dry-gap split and minimum total, after Melillo et al. 2018).
- `fit_threshold`: the frequentist fit (least squares in log-log, lowered
  by a percentile of the residuals).
- `ITALICA_T5` and `MACROREGIONS`: T5 thresholds for Italy refitted on
  e-ITALICA v4, with the catalogue as a test fixture to refit them.
- Extracted from Limen (`src/limen/core/scoring/caine.py` at 3eadcda) and
  relicensed under Apache-2.0 by its sole author; the API is new and has no
  dependency on Limen's configuration types.
