# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-11-28

How much to trust the line in each region, the rain still missing, and the
standard of the family for Docker, the MCP server and the records. Nothing
that was public changes, except the default ports and names of the containers.

### Added

- `trust`: `CALIBRATION` and `calibration_of(region)`, how the threshold sits
  on the landslides of each region. A T5 line has 5 % of the landslides of its
  macroregion below it; region by region the share goes from 1.3 % (Calabria,
  4 of 298) to 16.2 % (Valle d'Aosta, 11 of 68). `Calibration.interval()` is
  the range the real share can be in (Wilson score), `position` reads it:
  `high` in six regions, `low` in three, `as fitted` in eleven, where the
  landslides do not tell (Molise has 17). `tests/test_trust.py` counts them
  again from e-ITALICA.
- `rain_to_threshold(event, threshold, *, more_hours)`: the rain still needed
  to reach the threshold if the event goes on. Arithmetic on the line, not a
  forecast.
- `relative_total`: the rain of the last hours against a climatological
  reference of the same place, from 0 to 1, with longer windows; `None` when
  no hour was read. From Limen's engine (limen#243), with a parity test.
- `EventAssessment.as_record(where=, licence=)`: the assessment as a fact of
  `opendata-record/v2`, the plain format the libraries of the family
  exchange. The schema is copied in the tests and validated there with
  jsonschema, a test dependency only.
- `facts`: `trust_facts`, `margin_facts`, `published_facts`; MCP tools
  `trust`, `margin`, `published`. The faithfulness set has a fifth question,
  on trust (10 of 10 hand answers scored as written).
- The MCP server over HTTP: `rainfall-thresholds-mcp --transport
  streamable-http` (default port 8775), `/mcp` and `GET /health`; every option
  also from `RAINFALL_THRESHOLDS_MCP_*`. Standard input and output stays the
  default.
- `notebooks/05_trust_and_margin`: the calibration region by region, the rain
  still missing during the storm of Melito, the published thresholds, the
  record. No network; run in CI.
- `make help`, `make demo`, `make docker`, `make down`, `make mcp`.

### Changed

- Docker: the containers are named after the library
  (`rainfall-thresholds-ui`, `-mcp`, `-notebooks`), with the prefix in
  `RAINFALL_THRESHOLDS_NAME` for a second copy. The notebooks move from port
  8888 to **8881**, which no sister library uses; the calibration bench stays
  on 3001; the MCP server is a new service on 8775.
- Notebook 04 and the `examples` group use dpc-radar 0.6 and ispra-idrogeo
  0.14. The notebook reads the ISTAT code with `macroregion_of`, uses
  `event_against_threshold`, and gives a landslide dated to the day the
  instant of the family's convention: the end of its day, the next local
  midnight in Europe/Rome. It is saved without outputs: IdroGEO did not
  answer on 28/11/2026, so the new code has not run against the live
  services yet.
- `benchmarks/measures/README.md` says which rule each measure used for a
  landslide with no hour. They were made before the convention and are not
  recomputed.


## [0.4.0] - 2026-11-28

The rainfall logic of one domain that lived in Limen moves here, so that
Limen can be a thin application. Nothing that was public changes.

### Added

- `assess`: `event_against_threshold`, the event of an hourly series against
  the threshold at its duration, as an `EventAssessment` (`threshold_mm_h`,
  `threshold_mm`, `ratio`, `excess_decades`, `borders_unmeasured`,
  `at_least`: an event with hours not measured inside or at its edges is a
  lower bound); `cumulate`, the totals of the last N hours as `WindowTotal`,
  with no total when an hour is not measured; `caine_excess`, decades above
  the line, zero below. From Limen's `core/pioggia_frane.py` and
  `core/scoring/caine.py`.
- `radar_gauge_factor` on `event_against_threshold` and `caine_excess`: a
  threshold fitted on gauges, applied to radar rain, is lowered by the
  radar/gauge ratio. A plain number of the caller's; the default is 1, no
  correction. `PowerLawThreshold.scaled(factor)` is the same line with
  `alpha` multiplied.
- `antecedent`: `api_kohler_linsley`, the Antecedent Precipitation Index
  (Kohler & Linsley 1951), and `api_factor`, an API as a wetness factor
  between 0 and 1. The decay, the baseline and the sigmas are parameters
  with no default. From Limen's `core/scoring/api.py`.
- `regional`: `load_regional_catalogue`, 44 published thresholds for Italian
  regions, physiographic areas and alert zones (Vennari 2014, Peruccacci
  2017, Segoni 2015, Nocentini 2024), each with citation, URL and licence, as
  `RegionalThreshold` with `.as_intensity()`. Data to compare with: nothing
  applies them. In `regional_thresholds.toml`, read with the standard
  library. From Limen's `soglie_frane_regionali.yaml`, with Limen's area ids
  replaced by region names.
- `macroregion_of` also takes an ISTAT region code (`8`, `"08"`);
  `ISTAT_REGIONS`, code to region name.
- `threshold_for(macroregion, thresholds=ITALICA_T5, *, default="italy")`:
  the threshold of a macroregion, or the default one.
- `sources.RainSource`, a `typing.Protocol` for what gives hourly rain at
  points (`hourly(points, start, end) -> dict[datetime, list[float | None]]`,
  `None` is not measured), and `point_series`, the series of one point. The
  archives of dpc-radar have this shape; the package still imports no sister
  library.
- `tests/limen_reference.py` and `tests/test_limen_parity.py`: Limen's code
  as it was at 3b0e1ee, run next to the package's on fixed inputs.


- `benchmarks/measures/`: the measure of #8 from 2018 to 2025, made in Limen
  (limen#677) on the radar history and 4,200 dated landslides. On the same
  971 landslides the rain is above T5 at the gauge for 95.6 % and on the
  radar for 66.0 %; the radar reads 0.68 times the gauge on the triggering
  events; the threshold still separates on radar rain (AUC 0.85 and 0.73); a
  threshold fitted on radar rain does not hold, so none goes in.
  `tests/test_measures_data.py` recomputes the numbers.

- `benchmarks/measures/`: the pilot of #8 on 2026, the «Merging» against the
  radar alone at 9 IdroGEO landslides, made by `tools/pilot_2026.py` on
  Limen's archive: 7 of 9 caught with 9.4 alerts per landslide caught, 8 of
  9 with 12.25. `tests/test_measures_data.py` recomputes the numbers.

- Docs site: Examples, Benchmark and Roadmap pages; README: the docs badge,
  the article of the Open Data series, a roadmap section, where it is used.
- `docs/make_blog_figures.py` and `docs/img/blog/`: the figures of the
  article, in Italian and English, from the repository's data.

- `notebooks/04_radar_on_dated_landslides`: the join with the sister
  libraries, run once on 23/11/2026: 9 dated slides and flows since June
  2026 (IdroGEO), 48 hours of DPC radar rain at each, 7 of 8 with a rain
  event above T5. Needs the network; not run in CI. dpc-radar and
  ispra-idrogeo are in the `examples` group only, never in the package.

- `app/`: a calibration bench for public bodies, in Italian, with Bootstrap
  Italia and no CDN. It fits a threshold on e-ITALICA filtered by region,
  month and landslide type, or on the body's own landslides; compares it with
  the national one; measures its cost in false alarms on the body's rain
  gauge ("non misurato" until then); exports it as YAML. `docker compose up
  taratura`. Not a warning system, no live rain (#10).
- `docs/riuso.md`: for a public body, in Italian (#10).
- "Try it", an interactive intensity-duration plane on the docs site: a
  region, a duration and a rain total against the Italian threshold and the
  e-ITALICA landslides, in the browser, no backend. Its data are written by
  `docs/make_explainer_data.py` from the library, and a test fails when they
  are stale (#10).
- `publiccode.yml`, for the software catalogue of Developers Italia, checked
  in CI (#10).

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
