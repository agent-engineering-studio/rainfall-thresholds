# Example notebooks

Three notebooks, run with no network: what they read is in the repository.

| Notebook | What it shows |
|---|---|
| [`01_italian_thresholds`](01_italian_thresholds.ipynb) | the four T5 thresholds, in millimetres; which region gets which; the 5,974 e-ITALICA landslides under the lines, and the 5 % below them |
| [`02_melito_storm`](02_melito_storm.ipynb) | the storm of Melito di Porto Salvo, 10 October 2026, on the DPC radar; the strongest event and the last one; hours not measured |
| [`03_fit_your_threshold`](03_fit_your_threshold.ipynb) | a threshold fitted on the landslides of one region, and how the percentile moves it |

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
docker compose up        # then open http://localhost:8888
docker compose down
```

The page listens on `127.0.0.1` only, without a token: it is for your
machine. `RAINFALL_THRESHOLDS_PORT` changes the port.

## Data

e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473), CC BY 4.0.
The Melito series: DPC SRT1, © Dipartimento della Protezione Civile,
CC BY-SA 4.0.
