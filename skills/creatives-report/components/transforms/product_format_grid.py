"""Creatives Report — product × format performance grid.

For each inferred product (or ``"Uncategorised"``) we group ads by
format and compute median ROAS / CTR / CPA, total spend, and a status
mix. When the leading format's median ROAS is measurably above the
next-best (both at meaningful sample size and spend), we attach the
two figures so the row can state the gap as numbers — e.g. the top
format's median ROAS next to the runner-up's. No verdict or label is
applied; we only surface the measured comparison."""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


median = _load("format_helpers", _CHROME / "format_helpers.py").median


def grid(ads: list[dict]) -> dict[str, list[dict]]:
    """Return ``{product → list of format-row dicts}``."""
    by_pf = defaultdict(lambda: defaultdict(list))
    for a in ads:
        # Spending ads only — a zero-spend ad has no performance to grid.
        # It still appears in the ad table (inventory view), so the two
        # sections intentionally cover different populations; the grid
        # section's caption states this so the difference isn't silent.
        if a["spend"] <= 0:
            continue
        by_pf[a["product"]][a["format"]].append(a)

    out: dict[str, list[dict]] = {}
    for product, by_fmt in by_pf.items():
        rows: list[dict] = []
        for fmt, lst in by_fmt.items():
            if len(lst) < 1:
                continue
            # None means "no defined value" (e.g. ROAS on a zero-spend ad)
            # and is excluded; a genuine 0 (spend but no revenue/clicks)
            # must stay in the median or every all-zero cell would look
            # better than it is.
            roas_list = [a["roas"] for a in lst if a["roas"] is not None]
            ctr_list  = [a["ctr"]  for a in lst if a["ctr"]  is not None]
            cpa_list  = [a["cpa"]  for a in lst if a["cpa"]  is not None]
            spend = sum(a["spend"]     for a in lst)
            purch = sum(a["purchases"] for a in lst)
            rows.append({
                "format":      fmt,
                "n":           len(lst),
                "median_roas": median(roas_list) if roas_list else None,
                "median_ctr":  median(ctr_list)  if ctr_list  else None,
                "median_cpa":  median(cpa_list)  if cpa_list  else None,
                "total_spend": spend,
                "total_purch": purch,
                "insufficient": len(lst) < 3,
            })
        rows.sort(key=lambda r: (-(r.get("median_roas") or 0), -r["total_spend"]))
        # Lead comparison: when the leading format's median ROAS is ≥ 20%
        # above the next on meaningful sample + spend, record both figures
        # so the row can state the gap factually. This is a measured
        # comparison only — no verdict or "winner" label is attached.
        # The leader needs a positive median; the runner-up only needs a
        # defined one.
        if (len(rows) >= 2
                and not rows[0]["insufficient"]
                and not rows[1]["insufficient"]
                and rows[0].get("median_roas")
                and rows[1].get("median_roas") is not None):
            if (rows[0]["median_roas"] >= rows[1]["median_roas"] * 1.2
                    and rows[0]["total_spend"] > 200):
                rows[0]["lead_roas"] = rows[0]["median_roas"]
                rows[0]["next_format"] = rows[1]["format"]
                rows[0]["next_roas"] = rows[1]["median_roas"]
        out[product] = rows
    return out
