# rainfall-thresholds

Rainfall intensity-duration thresholds for shallow landslides: the Caine
power law, the reconstruction of rainfall events from an hourly series, and
the frequentist fit of a threshold to the events that triggered landslides.
Pure Python, no dependencies.

[![ci](https://github.com/agent-engineering-studio/rainfall-thresholds/actions/workflows/ci.yml/badge.svg)](https://github.com/agent-engineering-studio/rainfall-thresholds/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rainfall-thresholds)](https://pypi.org/project/rainfall-thresholds/)

## What it does

A shallow landslide is triggered when rain is intense enough for long
enough. The usual empirical model (Caine 1980) is a line in log-log space:

```
I(D) = alpha * D^(-beta)      I: mean intensity (mm/h), D: duration (h)
```

An event above the line is in the conditions that triggered landslides
before. The package covers the three steps around that line:

| Step | Function |
|---|---|
| Hourly rain → events | `reconstruct_events`, `latest_event` |
| Event → threshold → how far above | `PowerLawThreshold.intensity` / `.cumulated` / `.exceedance` |
| Catalogue of triggering events → threshold | `fit_threshold` |

It also ships T5 thresholds for Italy refitted on the e-ITALICA catalogue,
with a test that refits them from the data.

## Install

```bash
pip install rainfall-thresholds
```

## Use

```python
from datetime import UTC, datetime, timedelta

from rainfall_thresholds import ITALICA_T5, latest_event, reconstruct_events

start = datetime(2026, 10, 10, tzinfo=UTC)
hourly_mm = [0, 2, 8, 15, 22, 18, 9, 4, 0, 1, 3, 0, 0]
series = [(start + timedelta(hours=h), mm) for h, mm in enumerate(hourly_mm)]

event = latest_event(reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0))
assert event is not None
threshold = ITALICA_T5["southern"]

print(f"{event.total_mm:.0f} mm in {event.duration_hours:.0f} h = {event.intensity_mm_h:.1f} mm/h")
print(f"T5 at that duration: {threshold.intensity(event.duration_hours):.1f} mm/h")
print(f"{threshold.exceedance(event.intensity_mm_h, event.duration_hours):+.2f} decades")
```

```
82 mm in 10 h = 8.2 mm/h
T5 at that duration: 2.0 mm/h
+0.62 decades
```

`exceedance` is `log10(I / I(D))`: 0 on the line, +1 at ten times the
threshold intensity, negative below.

### Fitting your own threshold

```python
from rainfall_thresholds import fit_threshold

# (duration_h, intensity_mm_h) of rainfall events that triggered landslides
fit = fit_threshold(triggering_events, percentile=5)
fit.threshold  # PowerLawThreshold: 5 % of the events sit below it
fit.central  # the least-squares line before it is lowered
```

The method is the frequentist one of Brunetti et al. (2010) and
Peruccacci et al. (2012): least squares on `log I` against `log D`, then
the line is lowered by the chosen percentile of the residuals. One
difference: they take the percentile from a Gaussian fitted to a kernel
density of the residuals; this package takes it from the residuals
themselves. The two agree when the residuals are close to normal.

## Thresholds for Italy

Fitted with `fit_threshold(percentile=5)` on the 5,974 events of e-ITALICA
v4 with a positive duration and cumulated rainfall:

| Macroregion | alpha (mm/h) | beta | Events | E at 24 h | E at 72 h |
|---|---|---|---|---|---|
| `italy` | 7.193 | 0.5685 | 5,974 | 28.3 mm | 45.5 mm |
| `northern` | 6.400 | 0.5134 | 2,659 | 30.0 mm | 51.3 mm |
| `central` | 7.953 | 0.6085 | 1,890 | 27.6 mm | 42.4 mm |
| `southern` | 8.754 | 0.6449 | 1,425 | 27.1 mm | 40.0 mm |

`MACROREGIONS` lists the regions in each group. **Abruzzo and Molise are in
the centre**, unlike the ISTAT "Sud": use `macroregion_of(region)` rather
than an ISTAT table, or the threshold will not be the one fitted on that
region's events.

These are not the thresholds published by the e-ITALICA authors, who use
their own method and partitions: they are what this package's method gives
on their data, and `tests/test_italy.py` checks that they still do.

### Event reconstruction

An event runs from its first to its last wet hour; `no_rain_break_hours`
dry hours in a row end it, and an event below `min_event_mm` is dropped.
This is a simplified form of Melillo et al. (2018), whose CTRL-T tool also
varies the dry gap with the season. The e-ITALICA durations come from that
fuller procedure, so a threshold fitted on them and applied to events from
`reconstruct_events` mixes the two: fine for monitoring, worth knowing for
a study.

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

## Data licence

The test fixture `tests/fixtures/italica_v4_dur_rain.csv` is e-ITALICA v4
(Brunetti et al. 2024), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
reduced to four columns (id, region, duration, cumulated rainfall).

Extracted from [Limen](https://github.com/agent-engineering-studio/limen),
which uses it for the rainfall component of its landslide score.

## Development

```bash
uv sync
make check
```

## License

Code: [Apache-2.0](./LICENSE).
