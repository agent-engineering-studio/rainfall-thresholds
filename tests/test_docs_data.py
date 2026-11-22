"""The data of the interactive page of the docs are the library's, not a copy."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_explainer_data_are_up_to_date() -> None:
    spec = importlib.util.spec_from_file_location("make", ROOT / "docs" / "make_explainer_data.py")
    assert spec is not None and spec.loader is not None
    make = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make)
    saved = json.loads((ROOT / "docs" / "data" / "explainer.json").read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(make.build())), "run: python docs/make_explainer_data.py"
    assert len(saved["landslides"]) == 5974
