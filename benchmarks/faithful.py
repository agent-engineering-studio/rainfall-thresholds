"""How faithfully a text quotes the facts: numbers invented, in the wrong unit, rounded.

    uv run python -m benchmarks.faithful            # the table
    uv run python -m benchmarks.faithful --check    # CI: the hand answers score as written

**The set** (``faithful.json``): questions, the tool that answers each, and
answers written by hand, one faithful and one with known faults. The facts are
computed by the library when the set runs, so a change in a number shows here.
``--check`` fails when :func:`rainfall_thresholds.check.check_text` does not
find exactly the faults written in ``expect``: it tests the checker, not a
model.

**A model's answers** are not here yet. Asking a model costs money and needs
an API key: it is done only after an explicit yes, and its answers are then
added to the set with ``by`` naming the model.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from rainfall_thresholds.check import check_text
from rainfall_thresholds.facts import assess_facts, fit_facts, threshold_facts

HERE = Path(__file__).parent
FIXTURE = HERE.parent / "tests" / "fixtures" / "italica_v4_dur_rain.csv"


def _series(name: str) -> list[tuple[datetime, float | None]]:
    with (HERE / "series" / name).open(encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return [
            (
                datetime.fromisoformat(r["time"].replace("Z", "+00:00")),
                float(r["mm"]) if r["mm"] else None,
            )
            for r in rows
        ]


def facts(case: dict[str, Any]) -> dict[str, Any]:
    args = case["args"]
    if case["tool"] == "threshold":
        return threshold_facts(args["region"], args["duration_h"])
    if case["tool"] == "assess":
        return assess_facts(_series(args["series"]), args["region"], source=args.get("source"))
    if case["tool"] == "fit":
        with FIXTURE.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["region"] == args["region"]]
        return fit_facts(
            [(float(r["duration_h"]), float(r["cumulated_rainfall_mm"])) for r in rows]
        )
    raise ValueError(f"unknown tool {case['tool']!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a hand answer scores wrong")
    args = parser.parse_args(argv)
    cases = json.loads((HERE / "faithful.json").read_text(encoding="utf-8"))["cases"]
    wrong = 0
    total = 0
    for case in cases:
        found_facts = facts(case)
        print(f"{case['id']}: {case['question']}")
        for answer in case["answers"]:
            total += 1
            got = [[m.text, m.fault] for m in check_text(answer["text"], found_facts)]
            ok = got == answer["expect"]
            wrong += not ok
            faults = ", ".join(f"{t} ({f})" for t, f in got) or "no fault"
            print(f"  {'✓' if ok else '✗'} {answer['by']:<16} {faults}")
            if not ok:
                print(f"      expected: {answer['expect']}")
    print(f"\n{total - wrong} of {total} answers scored as expected")
    return 1 if args.check and wrong else 0


if __name__ == "__main__":
    sys.exit(main())
