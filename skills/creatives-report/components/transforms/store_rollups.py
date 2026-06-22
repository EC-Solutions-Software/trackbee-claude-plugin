"""Creatives Report — per-store roll-ups.

Aggregates the unified ad records (from ``ad_processing.py``) into the
header-tile KPIs (ad count, total spend / revenue / purchases, blended
ROAS, average Meta frequency).

Inputs: the store dict produced by the orchestrator (``ads`` list).
Output: ``{n_ads, total_spend, total_rev, ...}``."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_H = _load("format_helpers", _CHROME / "format_helpers.py")
safe_float = _H.safe_float
median = _H.median


def rollups(store: dict) -> dict:
    """Return the per-store KPI roll-up dictionary."""
    ads = store.get("ads") or []
    sym = store.get("sym") or ""

    spending = [a for a in ads if a["spend"] > 0]

    total_spend = sum(a["spend"]     for a in spending)
    total_rev   = sum(a["revenue"]   for a in spending)
    total_purch = sum(a["purchases"] for a in spending)
    blended_roas = (total_rev / total_spend) if total_spend > 0 else 0

    # `is not None`: a genuine frequency of 0.0 belongs in the median;
    # only absent data (None) is excluded.
    avg_freq = median([a["frequency"] for a in spending
                       if a["platform"] == "meta" and a["frequency"] is not None])

    return {
        "n_ads":         len(spending),
        "total_spend":   total_spend,
        "total_rev":     total_rev,
        "total_purch":   total_purch,
        "blended_roas":  blended_roas,
        "avg_freq":      avg_freq,
        "sym":           sym,
    }
