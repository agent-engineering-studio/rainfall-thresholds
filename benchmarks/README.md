# Benchmark: known cases

A small, fixed set of cases where we already know the answer. Every change to
how an event is read, or compared with a threshold, runs here first. Without
it, every improvement is an opinion. Tracked in
[#5](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/5).

```bash
uv run python -m benchmarks.run            # the table
uv run python -m benchmarks.run --check    # CI: fails if an outcome changed
uv run python -m benchmarks.run --write    # accept the new outcomes (results.json)
```

> **A threshold exceeded is not an alert.** The official alert is the
> criticality bulletin of the Dipartimento della Protezione Civile. A case
> here says whether the rain was like the rain of past landslides, nothing
> more.

## The cases

| Case | What happened | What a method must do |
|---|---|---|
| **Melito di Porto Salvo, 10 October 2026** | landslides in the Reggio Calabria area; the radar alone read 166 mm in 48 h at Melito | read the storm, above T5 |
| **Bagaladi, same storm** | 104 mm in 48 h, 13 km north | above T5 |
| **Melito, the day after** | nothing | no event |
| **The storm, then drizzle** *(constructed)* | Melito's storm hours, six dry hours, 2.5 mm | keep the storm: do not forget it because it drizzled after |
| **The storm with a gap** *(constructed)* | Melito's storm hours, three of them not measured | do not read the gap as dry; what was measured is still above T5 |
| **Six e-ITALICA landslides** | in each macroregion, the landslide at the median of T5's exceedance and the one at the 2nd percentile | above T5 |

The expected answer is **what happened**, not what a threshold can do. The
three e-ITALICA landslides at the 2nd percentile sit under T5: T5 leaves 5 %
of past landslides below it by construction. They fail for every method that
uses T5, and they are there to say so.

The radar series are the DPC product SRT1 (rain over the last hour, radar
only), read at the point as the median of the valid 3×3 pixels, the hour
labelled by its end. They were cut from Limen's archive of the DPC radar: the
DPC deletes its frames after about five months, so once here, a case keeps
working. The two constructed cases are made from those hours, and their files
say how.

## Today's score

`v0.1` is what 0.1.0 does, and what Limen does with it: `reconstruct_events`
with a 6-hour dry break and 2 mm minimum, then `latest_event`. `v0.2` (#6)
takes hours not measured (`None`) and the strongest event of the window,
`strongest_event`.

| Check | v0.1 | v0.2 |
|---|---|---|
| Melito and Bagaladi above T5 (4 checks) | ✓ ✓ ✓ ✓ | ✓ ✓ ✓ ✓ |
| Melito's event includes the peak hour | ✓ | ✓ |
| The day after: no event | ✓ | ✓ |
| Storm then drizzle: above T5 | ✗ (−0.65: it reads the drizzle) | ✓ (+0.78) |
| Storm then drizzle: event includes the storm | ✗ | ✓ |
| Storm with a gap (2 checks) | ! (cannot take hours not measured) | ✓ ✓ (59.6 mm measured, +0.51) |
| e-ITALICA, median landslides (3) | ✓ ✓ ✓ | ✓ ✓ ✓ |
| e-ITALICA, 2nd-percentile landslides (3) | ✗ ✗ ✗ | ✗ ✗ ✗ (under T5, by construction) |
| **Total** | **9 of 16** | **13 of 16** |

On the real Melito series both do well: the rain from the afternoon of the
9th to the night of the 10th is one event (166 mm in 35 h, +0.73 decades), so
the drizzle fault does not show there. It shows as soon as six dry hours
separate the storm from a little more rain.

## What is not there

- **Heavy rain with no landslide.** The cases that measure false alarms. A day
  of heavy rain with no landslide on record is not a day with no landslide:
  the candidates come from the rare-rain catalogue of the DPC radar, and only
  Limen checks them in the news. Until then, none.
- **The «Merging».** The series are radar only. The «Merging» (CUM3) is
  closer to the rain gauges the thresholds are fitted on, but comes every
  three hours, too coarse for an hourly series. It is quoted in the sources as
  a check.
- **Lipari, 10 October 2026.** A cloudburst the radar did not see. Its series
  would read zero, not "not measured": telling the two apart needs a
  reliability map, which is not this library's job. The caller passes `None`.
- **More events.** Melito is one storm. The landslides of the radar era
  (IdroGEO, from 2018) are for
  [#8](https://github.com/agent-engineering-studio/rainfall-thresholds/issues/8).

## Data licence

Radar series © Dipartimento della Protezione Civile,
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). e-ITALICA v4
(Brunetti et al. 2024, doi:10.5281/zenodo.14204473),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
