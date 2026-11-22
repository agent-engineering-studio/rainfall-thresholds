"""The MCP server: the thresholds as tools an assistant can call.

    pip install "rainfall-thresholds[mcp]"
    rainfall-thresholds-mcp            # on standard input and output

The tools compute only from what the call gives them: no network, no live
rain. Bring the rain from a gauge, a radar or a model; the answer says how
far it is from the threshold, and that a threshold exceeded is not an alert.
The tools are the functions of :mod:`rainfall_thresholds.facts`, and
``check`` is :func:`rainfall_thresholds.check.check_text`.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from rainfall_thresholds.check import check_text
from rainfall_thresholds.facts import RULE, assess_facts, fit_facts, threshold_facts

INSTRUCTIONS = f"""\
Rainfall thresholds for shallow landslides in Italy (Caine power law, T5
fitted on the e-ITALICA landslides, measured at rain gauges).

Rules for every answer:
- Quote numbers only from the tools, with their units. mm is a total, mm/h an
  intensity: a threshold asks for both, and they differ by the duration.
- Exceedance is in decades: +0.3 is twice the threshold intensity, +1 ten
  times, negative is below.
- The thresholds are fitted on rain gauges. On radar or model rain the
  comparison is not validated: say so.
- An hour not measured is null, never 0. A total with hours not measured is
  a lower bound.
- Abruzzo and Molise use the threshold of central Italy.
- {RULE} For danger to people, point to the bulletin, the regional civil
  protection and 112.
- Before answering in words, you can pass your text and the facts to `check`.
"""


def create_server() -> MCPServer[Any]:
    """The MCP server with its four tools."""
    from rainfall_thresholds import __version__

    server: MCPServer[Any] = MCPServer(
        name="rainfall-thresholds",
        title="Rainfall thresholds for landslides (Italy)",
        instructions=INSTRUCTIONS,
        website_url="https://agentengineering.it/rainfall-thresholds/",
        version=__version__,
    )

    @server.tool()
    def threshold(region: str, duration_h: float) -> dict[str, Any]:
        """The rain the Italian T5 threshold asks for over a duration.

        ``region``: an Italian region as e-ITALICA spells it ("Calabria",
        "Emilia-Romagna"), or "italy", "northern", "central", "southern".
        ``duration_h``: hours, > 0. Answers the intensity (mm/h) and the total
        (mm) of the threshold, and what it was fitted on.
        """
        return _guard(lambda: threshold_facts(region, duration_h))

    @server.tool()
    def assess(
        series: list[tuple[str, float | None]], region: str, source: str | None = None
    ) -> dict[str, Any]:
        """The rainfall events of an hourly series and where the strongest stands.

        ``series``: ``[[time, mm], ...]``, one per hour, time in ISO 8601;
        mm ``null`` for an hour not measured (never 0). ``source``: where the
        rain comes from ("rain gauge", "DPC SRT1", "ERA5"...). Answers each
        event (start, end, duration, total, intensity, the total the threshold
        asks for, exceedance in decades, hours not measured) and the strongest.
        """
        return _guard(
            lambda: assess_facts(
                [(datetime.fromisoformat(t.replace("Z", "+00:00")), mm) for t, mm in series],
                region,
                source=source,
            )
        )

    @server.tool()
    def fit(events: list[tuple[float, float]], percentile: float = 5.0) -> dict[str, Any]:
        """A threshold fitted on your own landslides.

        ``events``: ``[[duration_h, total_mm], ...]`` of the rain that
        triggered each landslide, at least three. Answers alpha, beta and the
        rain the threshold asks for in 24 and 72 hours.
        """
        return _guard(lambda: fit_facts(events, percentile=percentile))

    @server.tool()
    def check(text: str, facts: dict[str, Any], question: str = "") -> dict[str, Any]:
        """Check a text against the facts of a tool: numbers invented, in the wrong unit, rounded.

        ``facts``: the answer of ``threshold``, ``assess`` or ``fit``. Empty
        ``misquotes`` means every number is a fact of its unit; it does not
        prove the number is said of the right thing.
        """
        found = check_text(text, facts, question=question)
        return {"misquotes": [asdict(m) for m in found], "faithful": not found}

    return server


def _guard(call: Any) -> dict[str, Any]:
    """What the library refuses, as an error the agent can read and act on."""
    try:
        found: dict[str, Any] = call()
        return found
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def run() -> None:
    """Serve on standard input and output, until the client hangs up."""
    create_server().run("stdio")


__all__ = ["INSTRUCTIONS", "create_server", "run"]
