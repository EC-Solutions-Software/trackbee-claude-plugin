"""Month-to-date pacing for a store's pulse card — measured against last month.

Two reads per metric (revenue, ad spend):
  1. **Where we are now** — this month's MTD total vs the *same number of days*
     last month (e.g. pulled on Jun 6 → Jun 1-5 vs May 1-5).
  2. **How we're projecting** — this month's on-pace full-month projection
     (MTD ÷ days elapsed × days in month) vs last month's actual full total.

The bar visualises the projection against last month's full total: the tick
marks last month (100%); the fill is this month's projection, so overshooting
the tick means we're pacing to beat last month.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FH = _load("format_helpers", _CHROME / "format_helpers.py")


def _pace_row(name, kind, actual, same_last, last_full, elapsed, days_total, ccy):
    """One metric row comparing this month against last month.
    ``actual`` = MTD this month; ``same_last`` = same-day window last month;
    ``last_full`` = last month's full actual. All in store units."""
    vs_delta = _FH.pct_change(actual, same_last)
    projected = None
    if actual is not None and elapsed and days_total:
        projected = actual / elapsed * days_total
    proj_delta = _FH.pct_change(projected, last_full)

    # Bar: track spans 0 → 1.6× of last month's full total; tick at 1.0×.
    fill = None
    if projected is not None and last_full not in (None, 0):
        fill = max(0.0, min(projected / last_full, 1.6))

    # Spend pacing above last month isn't inherently good; only revenue is.
    return {
        "name":        name,
        "kind":        kind,            # "rev" | "spend" — bar color
        "actual_str":  _FH.compact_money(actual, ccy),
        "same_last_str": _FH.compact_money(same_last, ccy),
        "vs_delta_str": _FH.signed_pct(vs_delta),
        "vs_delta_class": _FH.delta_class(vs_delta) if kind == "rev" else "delta-flat",
        "projected_str": _FH.compact_money(projected, ccy),
        "last_full_str": _FH.compact_money(last_full, ccy),
        "proj_delta_str": _FH.signed_pct(proj_delta),
        "proj_delta_class": _FH.delta_class(proj_delta) if kind == "rev" else "delta-flat",
        "fill_pct":    None if fill is None else round(fill / 1.6 * 100, 1),
        "tick_pct":    round(1.0 / 1.6 * 100, 1) if fill is not None else None,
    }


def build(summary, mtd_meta):
    ccy = summary.get("currency") or ""
    mtd = summary.get("mtd") or {}
    prev = summary.get("mtd_prev") or {}
    prev_full = summary.get("mtd_prev_full") or {}
    elapsed = mtd_meta.get("days_elapsed") or 0
    days_total = mtd_meta.get("days_total") or 0
    this_label = mtd_meta.get("this_month_label") or "this month"
    prev_label = mtd_meta.get("prev_month_label") or "last month"

    rows = [
        _pace_row("Revenue", "rev", mtd.get("revenue"), prev.get("revenue"),
                  prev_full.get("revenue"), elapsed, days_total, ccy),
        _pace_row("Ad spend", "spend", mtd.get("spend"), prev.get("spend"),
                  prev_full.get("spend"), elapsed, days_total, ccy),
    ]

    if elapsed:
        note = (f"{this_label} so far vs the same {elapsed} "
                f"day{'s' if elapsed != 1 else ''} of {prev_label}. The bar projects "
                f"{this_label}'s full month against {prev_label}'s actual total "
                f"(tick = {prev_label}).")
    else:
        note = (f"{this_label} vs {prev_label}. The bar projects {this_label}'s "
                f"full month against {prev_label}'s actual total.")

    return {"rows": rows, "note": note,
            "this_label": this_label, "prev_label": prev_label}
