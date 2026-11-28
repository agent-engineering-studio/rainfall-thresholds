"""The MCP server: the thresholds as tools an assistant can call.

    pip install "rainfall-thresholds[mcp]"
    rainfall-thresholds-mcp            # on standard input and output
    rainfall-thresholds-mcp --transport streamable-http --host 0.0.0.0 --port 8775

Over HTTP the MCP endpoint is ``/mcp`` and ``GET /health`` answers
``{"status": "ok"}`` for container healthchecks. Every option also reads an
environment variable (``RAINFALL_THRESHOLDS_MCP_TRANSPORT``, ``_HOST``,
``_PORT``, ``_ALLOWED_HOSTS``), so a compose file needs no command line.

The tools compute only from what the call gives them: no network, no live
rain. Bring the rain from a gauge, a radar or a model; the answer says how
far it is from the threshold, and that a threshold exceeded is not an alert.
The tools are the functions of :mod:`rainfall_thresholds.facts`, and
``check`` is :func:`rainfall_thresholds.check.check_text`.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any, cast

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from rainfall_thresholds.check import check_text
from rainfall_thresholds.facts import (
    RULE,
    assess_facts,
    fit_facts,
    margin_facts,
    published_facts,
    threshold_facts,
    trust_facts,
)

_ENV = "RAINFALL_THRESHOLDS_MCP_"

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
- The threshold is not calibrated equally well everywhere: `trust` says how
  it sits on the landslides of a region. Say it when the line is high or low
  there, or when the landslides are too few to tell.
- `margin` is the rain still needed if the rain goes on. It is not a
  forecast: compare it with one, and say what it supposes.
- {RULE} For danger to people, point to the bulletin, the regional civil
  protection and 112.
- Before answering in words, you can pass your text and the facts to `check`.
"""


def create_server() -> MCPServer[Any]:
    """The MCP server with its tools."""
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
    def trust(region: str) -> dict[str, Any]:
        """How well the threshold is calibrated in an Italian region.

        ``region``: a region name ("Valle d'Aosta") or its ISTAT code ("02").
        Answers how many landslides the threshold was fitted on there, how
        many are below it against the 5 % expected, the range the real share
        can be in, and the durations the line covers without extrapolating.
        """
        return _guard(lambda: trust_facts(region))

    @server.tool()
    def margin(
        series: list[tuple[str, float | None]],
        region: str,
        more_hours: list[int] | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """The rain still needed to reach the threshold if the rain goes on.

        ``series`` and ``source`` as in ``assess``. ``more_hours``: how many
        more hours to look at (default 1, 3 and 6). Answers the event still
        going, if any, and for each horizon the total the threshold asks for
        and how much is still missing (0 when already above). Not a forecast.
        """
        return _guard(
            lambda: margin_facts(
                [(datetime.fromisoformat(t.replace("Z", "+00:00")), mm) for t, mm in series],
                region,
                more_hours=more_hours or (1, 3, 6),
                source=source,
            )
        )

    @server.tool()
    def published(region: str) -> dict[str, Any]:
        """The thresholds the literature published for a region, with their sources.

        ``region``: a region name or its ISTAT code. Answers each published
        threshold for the whole region (alpha, beta, the rain it asks for in
        24 hours, citation, URL, licence) next to this package's.
        """
        return _guard(lambda: published_facts(region))

    @server.tool()
    def check(text: str, facts: dict[str, Any], question: str = "") -> dict[str, Any]:
        """Check a text against the facts of a tool: numbers invented, in the wrong unit, rounded.

        ``facts``: the answer of another tool of this server. Empty
        ``misquotes`` means every number is a fact of its unit; it does not
        prove the number is said of the right thing.
        """
        found = check_text(text, facts, question=question)
        return {"misquotes": [asdict(m) for m in found], "faithful": not found}

    async def health(_request: Request) -> Response:
        """``GET /health`` over HTTP, for container healthchecks."""
        return JSONResponse(
            {"status": "ok", "server": "rainfall-thresholds", "version": __version__}
        )

    # custom_route is untyped in the SDK: register the typed handler through a cast.
    route = cast(Callable[[Any], Any], server.custom_route("/health", methods=["GET"]))
    route(health)

    return server


def _guard(call: Any) -> dict[str, Any]:
    """What the library refuses, as an error the agent can read and act on."""
    try:
        found: dict[str, Any] = call()
        return found
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def options(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] = os.environ
) -> argparse.Namespace:
    """The command line of the server, each default from its environment variable."""
    top = argparse.ArgumentParser(
        prog="rainfall-thresholds-mcp", description="Rainfall thresholds as an MCP server."
    )
    top.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=environ.get(_ENV + "TRANSPORT", "stdio"),
        help="stdio (default) or streamable-http, served at /mcp",
    )
    top.add_argument(
        "--host",
        default=environ.get(_ENV + "HOST", "127.0.0.1"),
        help="HTTP address (default 127.0.0.1; 0.0.0.0 in a container)",
    )
    top.add_argument("--port", type=int, default=int(environ.get(_ENV + "PORT", "8775")))
    top.add_argument(
        "--allowed-host",
        action="append",
        default=[h for h in environ.get(_ENV + "ALLOWED_HOSTS", "").split(",") if h.strip()],
        metavar="HOST[:PORT]",
        help="accept only these Host headers (DNS rebinding protection); repeatable",
    )
    args = top.parse_args(argv)
    if args.transport not in ("stdio", "streamable-http"):
        top.error(f"unknown transport {args.transport!r}")
    return args


def http_options(args: argparse.Namespace) -> dict[str, Any]:
    """The keyword arguments of ``MCPServer.run`` for the HTTP transport."""
    found: dict[str, Any] = {"host": args.host, "port": args.port, "streamable_http_path": "/mcp"}
    if args.allowed_host:
        found["transport_security"] = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[h.strip() for h in args.allowed_host],
        )
    return found


def run(argv: Sequence[str] | None = None) -> None:
    """Entry point of ``rainfall-thresholds-mcp``: stdio, or HTTP when asked."""
    args = options(argv)
    if args.transport == "stdio":
        create_server().run("stdio")
    else:
        create_server().run("streamable-http", **http_options(args))


__all__ = ["INSTRUCTIONS", "create_server", "http_options", "options", "run"]
