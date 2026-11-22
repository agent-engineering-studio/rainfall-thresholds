from __future__ import annotations

import ast
from pathlib import Path

import rainfall_thresholds

SRC = Path(rainfall_thresholds.__file__).parent

#: Sister libraries and Limen. Limen pins all of them: if one imported another,
#: Limen would get a circular dependency and pins in conflict.
FORBIDDEN = {"dpc_radar", "ispra_idrogeo", "limen"}


def test_version_is_exposed() -> None:
    assert rainfall_thresholds.__version__


def test_the_package_imports_no_sister_library() -> None:
    found = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            found += [f"{path.name}: {n}" for n in names if n.split(".")[0] in FORBIDDEN]
    assert found == []
