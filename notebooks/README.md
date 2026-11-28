# Example notebooks

Five notebooks. Four run with no network: what they read is in the
repository. The fourth reads IdroGEO and the DPC radar.

| Notebook | What it shows |
|---|---|
| [`01_italian_thresholds`](01_italian_thresholds.ipynb) | the four T5 thresholds, in millimetres; which region gets which; the 5,974 e-ITALICA landslides under the lines, and the 5 % below them |
| [`02_melito_storm`](02_melito_storm.ipynb) | the storm of Melito di Porto Salvo, 10 October 2026, on the DPC radar; the strongest event and the last one; hours not measured |
| [`03_fit_your_threshold`](03_fit_your_threshold.ipynb) | a threshold fitted on the landslides of one region, and how the percentile moves it |
| [`04_radar_on_dated_landslides`](04_radar_on_dated_landslides.ipynb) | the join with the sister libraries: landslides dated by IdroGEO ([ispra-idrogeo](https://agentengineering.it/ispra-idrogeo/)), hourly radar rain at their place ([dpc-radar](https://agentengineering.it/dpc-radar/)), and the threshold. A landslide dated to the day takes the end of its day in Europe/Rome. Needs the network; not run in CI. Last run on 28/11/2026 with dpc-radar 0.6 and ispra-idrogeo 0.15 |
| [`05_trust_and_margin`](05_trust_and_margin.ipynb) | how the line sits on the landslides of each region, and where they are too few to tell; the rain still missing during the storm of Melito; the thresholds the literature published; the assessment as a record |

The package imports neither sister library: notebook 04 joins them, as
[Limen](https://github.com/agent-engineering-studio/limen) does. They are in the
`examples` dependency group only.

> **A threshold exceeded is not an alert.** The official alert in Italy is
> the criticality bulletin of the Dipartimento della Protezione Civile.

## Run them

With [uv](https://docs.astral.sh/uv/):

```bash
uv run --group examples jupyter lab notebooks/
make notebooks     # run them all again and save the results
```

With Docker alone, from the root of the repository:

```bash
docker compose up notebooks   # then open http://localhost:8881
make down
```

The page listens on `127.0.0.1` only, without a token: it is for your
machine. `RAINFALL_THRESHOLDS_PORT` changes the port.

## Data

e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473), CC BY 4.0.
The Melito series and the radar of notebook 04: DPC SRT1, © Dipartimento della
Protezione Civile, CC BY-SA 4.0. The dated landslides of notebook 04: IdroGEO,
ISPRA, CC BY-SA 4.0.
