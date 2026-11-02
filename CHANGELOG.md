# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
