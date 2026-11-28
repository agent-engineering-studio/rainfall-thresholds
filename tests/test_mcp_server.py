from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("mcp")

from mcp import Client
from mcp.server.mcpserver import MCPServer

from rainfall_thresholds import mcp_server as m
from rainfall_thresholds.facts import RULE


async def call(client: Client, tool: str, **args: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    assert not result.is_error, result.content
    found: dict[str, Any] = result.structured_content
    return found


async def test_the_tools_and_the_rules() -> None:
    async with Client(m.create_server()) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert sorted(tools) == [
            "assess",
            "check",
            "fit",
            "margin",
            "published",
            "threshold",
            "trust",
        ]
        assert all(t.description for t in tools.values())
        assert client.instructions == m.INSTRUCTIONS
        assert "not an alert" in m.INSTRUCTIONS and "null, never 0" in m.INSTRUCTIONS


async def test_every_tool_answers_with_facts_and_the_rule() -> None:
    async with Client(m.create_server()) as client:
        t = await call(client, "threshold", region="Abruzzo", duration_h=24)
        assert t["threshold"]["macroregion"] == "central" and t["rule"] == RULE
        series = [
            ["2026-10-10T00:00Z", 20.0],
            ["2026-10-10T01:00Z", None],
            ["2026-10-10T02:00Z", 30.0],
        ]
        a = await call(client, "assess", series=series, region="Calabria", source="DPC SRT1")
        assert a["strongest"]["total_mm"] == 50.0 and a["strongest"]["unmeasured_h"] == 1
        f = await call(client, "fit", events=[[1, 10], [10, 30], [100, 90]])
        assert f["landslides"] == 3
        wrong_unit = f"it asks {t['cumulated_mm']} mm/h"  # a total, written as an intensity
        c = await call(client, "check", text=wrong_unit, facts=t)
        assert c["faithful"] is False and c["misquotes"][0]["fault"] == "unit"


async def test_what_the_library_refuses_is_an_error_the_agent_can_read() -> None:
    async with Client(m.create_server()) as client:
        result = await client.call_tool("threshold", {"region": "Bavaria", "duration_h": 24})
        assert result.is_error
        assert "unknown region" in str(result.content)


def test_run_serves_on_standard_input_and_output(monkeypatch: pytest.MonkeyPatch) -> None:
    served: list[str] = []
    monkeypatch.setattr(MCPServer, "run", lambda self, transport, **kw: served.append(transport))
    m.run([])
    assert served == ["stdio"]


def test_the_package_does_not_import_mcp() -> None:
    import subprocess
    import sys

    code = "import sys, rainfall_thresholds; print('mcp' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


async def test_the_new_tools_answer_with_facts() -> None:
    async with Client(m.create_server()) as client:
        t = await call(client, "trust", region="Valle d'Aosta")
        assert t["position"] == "high" and t["landslides"] == 68
        series = [["2026-10-10T00:00Z", 3.0], ["2026-10-10T01:00Z", 4.0]]
        g = await call(client, "margin", series=series, region="Calabria", source="rain gauge")
        assert g["going_on"] is True and [n["more_h"] for n in g["needed"]] == [1, 3, 6]
        p = await call(client, "published", region="Sicilia")
        assert p["published"][0]["id"] == "sicilia-t5"


def test_the_options_come_from_flags_then_the_environment() -> None:
    env = {
        "RAINFALL_THRESHOLDS_MCP_TRANSPORT": "streamable-http",
        "RAINFALL_THRESHOLDS_MCP_HOST": "0.0.0.0",
        "RAINFALL_THRESHOLDS_MCP_PORT": "9000",
        "RAINFALL_THRESHOLDS_MCP_ALLOWED_HOSTS": "rainfall-thresholds-mcp:*, ",
    }
    from_env = m.options([], environ=env)
    assert (from_env.transport, from_env.host, from_env.port) == (
        "streamable-http",
        "0.0.0.0",
        9000,
    )
    assert m.http_options(from_env)["transport_security"].allowed_hosts == [
        "rainfall-thresholds-mcp:*"
    ]
    flags = m.options(["--port", "8000", "--transport", "stdio"], environ=env)
    assert (flags.port, flags.transport) == (8000, "stdio")
    assert m.http_options(m.options([], environ={})) == {
        "host": "127.0.0.1",
        "port": 8775,
        "streamable_http_path": "/mcp",
    }
    with pytest.raises(SystemExit):
        m.options([], environ={"RAINFALL_THRESHOLDS_MCP_TRANSPORT": "sse"})


def test_run_serves_over_http_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    served: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        MCPServer, "run", lambda self, transport, **kw: served.append((transport, kw))
    )
    m.run(["--transport", "streamable-http", "--port", "8775"])
    assert served == [
        ("streamable-http", {"host": "127.0.0.1", "port": 8775, "streamable_http_path": "/mcp"})
    ]


def test_health_and_mcp_over_http() -> None:
    from starlette.testclient import TestClient

    app = m.create_server().streamable_http_app()
    with TestClient(app) as http:
        health = http.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok" and health.json()["server"] == "rainfall-thresholds"
        assert 400 <= http.get("/mcp").status_code < 500  # no session: refused, but alive
