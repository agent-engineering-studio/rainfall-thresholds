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
        assert sorted(tools) == ["assess", "check", "fit", "threshold"]
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
    monkeypatch.setattr(MCPServer, "run", lambda self, transport: served.append(transport))
    m.run()
    assert served == ["stdio"]


def test_the_package_does_not_import_mcp() -> None:
    import subprocess
    import sys

    code = "import sys, rainfall_thresholds; print('mcp' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
