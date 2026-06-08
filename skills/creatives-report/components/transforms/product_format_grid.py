"""Creatives Report — product × format performance grid.

For each inferred product (or ``"Uncategorised"``) we group ads by
format and compute median ROAS / CTR / CPA, total spend, and a status
mix. A "winner" tag is applied when one format leads the next-best by
≥ 20% on median ROAS at meaningful spend — but only when both rows
have at least 3 ads (no winners off a sample of one)."""

from __future__ import annotations

import importlib.util
from collections import Counter, defaultdict
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
            # and is excluded; a genuine 0 (spend but no revenue/clicks —
            # the textbook KILL case) must stay in the median or every
            # all-zero cell would look better than it is.
            roas_list = [a["roas"] for a in lst if a["roas"] is not None]
            ctr_list  = [a["ctr"]  for a in lst if a["ctr"]  is not None]
            cpa_list  = [a["cpa"]  for a in lst if a["cpa"]  is not None]
            spend = sum(a["spend"]     for a in lst)
            purch = sum(a["purchases"] for a in lst)
            counts = Counter(a["status_tag"] for a in lst)
            rows.append({
                "format":      fmt,
                "n":           len(lst),
                "median_roas": median(roas_list) if roas_list else None,
                "median_ctr":  median(ctr_list)  if ctr_list  else None,
                "median_cpa":  median(cpa_list)  if cpa_list  else None,
                "total_spend": spend,
                "total_purch": purch,
                "status_counts": counts,
                "insufficient": len(lst) < 3,
            })
        rows.sort(key=lambda r: (-(r.get("median_roas") or 0), -r["total_spend"]))
        # Winner: only when both rows have N >= 3 and the leader's ROAS
        # is ≥ 20% above the next on meaningful spend.
        # The leader needs a positive median; the runner-up only needs a
        # defined one — beating a zero-ROAS format is still a win.
        if (len(rows) >= 2
                and not rows[0]["insufficient"]
                and not rows[1]["insufficient"]
                and rows[0].get("median_roas")
                and rows[1].get("median_roas") is not None):
            if (rows[0]["median_roas"] >= rows[1]["median_roas"] * 1.2
                    and rows[0]["total_spend"] > 200):
                rows[0]["is_winner"] = True
        out[product] = rows
    return out
