"""Smoke tests for assemble._load_raw.

Run with: pytest skills/build-attribution-dashboard/tests/

The transforms downstream (blended_kpis, platform_tiles, daily_nc_roas)
all read fields like ``ad_account_spend`` at the top level of the dict
returned by ``_load_raw``. This test pins that contract for the three
shapes Claude might write to disk:

  1. Native MCP shape — ``{"store_currency": ..., "overview": {...}}``
  2. JSON-RPC envelope — ``{"result": {<native MCP shape>}}``
  3. Already-unwrapped payload — just the inner dict

A regression here is what caused PR #N: the assembler unwrapped only the
JSON-RPC envelope, leaving the native MCP wrapper intact, and every KPI
that read ``overview["ad_account_spend"]`` silently returned 0.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ASSEMBLE_PATH = (
    Path(__file__).resolve().parent.parent
    / "resources"
    / "dashboards"
    / "attribution"
    / "orchestrators"
    / "assemble.py"
)


def _load_assemble():
    spec = importlib.util.spec_from_file_location("assemble", ASSEMBLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INNER_OVERVIEW = {
    "total_revenue": 127_741_774,
    "total_orders": 36_999,
    "ad_account_spend": 50_313_489,
    "platform_statistics": [
        {"platform": "meta", "spend": 30_000_000},
        {"platform": "google", "spend": 20_313_489},
    ],
}


@pytest.fixture()
def assemble():
    return _load_assemble()


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_unwraps_native_mcp_overview_wrapper(tmp_path, assemble):
    inputs_dir = _write(
        tmp_path,
        "overview.json",
        {"store_currency": "GBP", "currency": "GBP", "overview": INNER_OVERVIEW},
    )

    out = assemble._load_raw(inputs_dir, "overview.json")

    assert out["ad_account_spend"] == INNER_OVERVIEW["ad_account_spend"]
    assert out["total_revenue"] == INNER_OVERVIEW["total_revenue"]
    assert out["total_orders"] == INNER_OVERVIEW["total_orders"]
    assert out["platform_statistics"] == INNER_OVERVIEW["platform_statistics"]
    # Currency context from the outer envelope must be carried down so
    # transforms / insights that want a symbol can still find it.
    assert out["store_currency"] == "GBP"
    assert out["currency"] == "GBP"


def test_unwraps_jsonrpc_envelope_around_native_mcp_overview(tmp_path, assemble):
    inputs_dir = _write(
        tmp_path,
        "overview.json",
        {
            "result": {
                "store_currency": "EUR",
                "currency": "EUR",
                "overview": INNER_OVERVIEW,
            }
        },
    )

    out = assemble._load_raw(inputs_dir, "overview.json")

    assert out["ad_account_spend"] == INNER_OVERVIEW["ad_account_spend"]
    assert out["store_currency"] == "EUR"


def test_passes_through_already_unwrapped_payload(tmp_path, assemble):
    inputs_dir = _write(tmp_path, "overview.json", INNER_OVERVIEW)

    out = assemble._load_raw(inputs_dir, "overview.json")

    assert out["ad_account_spend"] == INNER_OVERVIEW["ad_account_spend"]
    assert out["platform_statistics"] == INNER_OVERVIEW["platform_statistics"]


def test_missing_file_returns_empty_dict(tmp_path, assemble):
    assert assemble._load_raw(tmp_path, "does_not_exist.json") == {}


def test_does_not_unwrap_overview_field_on_non_overview_files(tmp_path, assemble):
    """The "overview" unwrap is gated on filename so unrelated payloads
    that happen to carry an "overview" field (e.g. a future tool that
    nests a section under that key) are left alone."""
    payload = {"overview": {"foo": "bar"}, "rows": [1, 2, 3]}
    inputs_dir = _write(tmp_path, "daily.json", payload)

    out = assemble._load_raw(inputs_dir, "daily.json")

    assert out == payload
