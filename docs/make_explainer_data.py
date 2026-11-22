"""Write docs/data/explainer.json: what the interactive page of the docs draws.

The thresholds come from the library and the landslides from the e-ITALICA
fixture, so the page never holds a hand-copied number.
``tests/test_docs_data.py`` fails when the file is stale:

    uv run python docs/make_explainer_data.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from rainfall_thresholds import ITALICA_T5, MACROREGIONS, macroregion_of
from rainfall_thresholds.facts import ALERT_URL, ITALICA_EVENTS

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "italica_v4_dur_rain.csv"
OUT = ROOT / "docs" / "data" / "explainer.json"


def _macroregion(region: str) -> str:
    found = macroregion_of(region)
    if found is None:
        raise ValueError(f"{region!r} is in no macroregion")
    return found


def build() -> dict[str, Any]:
    with FIXTURE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    macro = ["northern", "central", "southern"]
    return {
        "source": "e-ITALICA v4 (Brunetti et al. 2024, doi:10.5281/zenodo.14204473), CC BY 4.0",
        "alert_url": ALERT_URL,
        "thresholds": {
            k: {"alpha": t.alpha, "beta": t.beta, "landslides": ITALICA_EVENTS[k]}
            for k, t in ITALICA_T5.items()
        },
        "regions": {r: k for k, rs in MACROREGIONS.items() for r in sorted(rs)},
        "macroregions": macro,
        # [macroregion index, duration h, cumulated mm] per landslide
        "landslides": [
            [
                macro.index(_macroregion(r["region"])),
                float(r["duration_h"]),
                float(r["cumulated_rainfall_mm"]),
            ]
            for r in rows
        ],
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
