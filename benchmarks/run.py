"""Run the known cases against each method and print the score.

    uv run python -m benchmarks.run            # the table
    uv run python -m benchmarks.run --check    # CI: fail if an outcome changed
    uv run python -m benchmarks.run --write    # save the outcomes in results.json

A method reads a case and gives the rainfall event it would compare with the
threshold. ``--check`` fails when an outcome differs from ``results.json``,
so a change to the code or to a case is seen, and saved on purpose.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from rainfall_thresholds import (
    ITALICA_T5,
    PowerLawThreshold,
    RainfallEvent,
    latest_event,
    reconstruct_events,
    strongest_event,
)

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"

Outcome = Literal["pass", "fail", "error"]
Series = list[tuple[datetime, float | None]]
#: A method: an hourly series (``None`` = not measured) and the threshold of the
#: place -> the event it compares with the threshold, or None.
Method = Callable[[Series, PowerLawThreshold], RainfallEvent | None]


def v0_1(series: Series, _threshold: PowerLawThreshold) -> RainfallEvent | None:
    """What 0.1.0 does, and Limen with it: the last event, gaps not allowed."""
    if any(mm is None for _, mm in series):
        raise ValueError("a series with hours not measured")
    dense = [(t, mm) for t, mm in series if mm is not None]
    return latest_event(reconstruct_events(dense, no_rain_break_hours=6, min_event_mm=2.0))


def v0_2(series: Series, threshold: PowerLawThreshold) -> RainfallEvent | None:
    """Hours not measured allowed, and the strongest event of the window (#6)."""
    events = reconstruct_events(series, no_rain_break_hours=6, min_event_mm=2.0)
    return strongest_event(events, threshold)


METHODS: dict[str, Method] = {"v0.1": v0_1, "v0.2": v0_2}


@dataclass(frozen=True, slots=True)
class Result:
    case: str
    check: str
    outcome: Outcome
    got: str


def load_series(name: str) -> Series:
    path = HERE / "series" / name
    with path.open(encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return [
            (
                datetime.fromisoformat(r["time"].replace("Z", "+00:00")),
                float(r["mm"]) if r["mm"] else None,
            )
            for r in rows
        ]


def label(check: dict[str, Any]) -> str:
    kind = check["kind"]
    at = f" as of {check['as_of']:%d/%m %H:%M}" if "as_of" in check else ""
    if kind == "event":
        return f"event includes {check['hour']:%d/%m %H:%M}{at}"
    return f"{kind}{at}"


def judge(case: dict[str, Any], check: dict[str, Any], method: Method) -> Result:
    name = label(check)
    threshold = ITALICA_T5[case["macroregion"]]
    try:
        if "series" in case:
            series = load_series(case["series"])
            start = case.get("start")
            end = check.get("as_of")
            series = [
                s
                for s in series
                if (start is None or s[0] >= start) and (end is None or s[0] <= end)
            ]
            event = method(series, threshold)
        else:
            d = float(case["duration_h"])
            event = RainfallEvent(datetime.min, datetime.min, d, float(case["total_mm"]))
    except ValueError as exc:
        return Result(case["id"], name, "error", str(exc))

    kind = check["kind"]
    if kind == "dry":
        ok = event is None
        got = "no event" if event is None else f"{event.total_mm:.1f} mm"
    elif event is None:
        ok, got = False, "no event"
    elif kind == "above":
        e = threshold.exceedance(event.intensity_mm_h, event.duration_hours)
        ok = (e > 0) == check["expect"]
        got = f"{event.total_mm:.1f} mm in {event.duration_hours:.0f} h, {e:+.2f}"
    elif kind == "event":
        ok = event.start <= check["hour"] <= event.end
        got = f"{event.start:%d/%m %H:%M}-{event.end:%d/%m %H:%M}"
    else:
        raise ValueError(f"unknown check kind {kind!r}")
    return Result(case["id"], name, "pass" if ok else "fail", got)


def run() -> dict[str, list[Result]]:
    cases = tomllib.loads((HERE / "cases.toml").read_text(encoding="utf-8"))["case"]
    return {
        name: [judge(case, check, method) for case in cases for check in case["check"]]
        for name, method in METHODS.items()
    }


MARK = {"pass": "✓", "fail": "✗", "error": "!"}


def report(results: dict[str, list[Result]]) -> str:
    lines = []
    for name, rows in results.items():
        passed = sum(r.outcome == "pass" for r in rows)
        lines.append(f"{name}: {passed} of {len(rows)}")
        for r in rows:
            lines.append(f"  {MARK[r.outcome]} {r.case:<22} {r.check:<44} {r.got}")
    return "\n".join(lines)


def outcomes(results: dict[str, list[Result]]) -> dict[str, dict[str, str]]:
    return {
        name: {f"{r.case} · {r.check}": r.outcome for r in rows} for name, rows in results.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if outcomes differ")
    parser.add_argument("--write", action="store_true", help="save outcomes to results.json")
    args = parser.parse_args(argv)
    results = run()
    print(report(results))
    now = outcomes(results)
    if args.write:
        RESULTS.write_text(json.dumps(now, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.check:
        saved = json.loads(RESULTS.read_text(encoding="utf-8"))
        if saved != now:
            changed = sorted(
                f"{m} · {k}: {saved.get(m, {}).get(k)} -> {v}"
                for m, rows in now.items()
                for k, v in rows.items()
                if saved.get(m, {}).get(k) != v
            ) or ["a check was removed"]
            print("\noutcomes changed (run with --write to accept):", *changed, sep="\n  ")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
