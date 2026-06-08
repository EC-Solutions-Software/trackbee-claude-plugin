"""Build the six KPI tiles for a store's pulse card.

Tiles: revenue, orders, MER, ROAS, PoAS, CAC. Each tile carries yesterday's
value, the trailing-7-day baseline, and a delta painted by whether the move is
*good* or *bad* (not merely up or down — CAC falling is good).

Level metrics (revenue, orders) baseline = baseline-window total / baseline
days, i.e. an average day. Ratio metrics (MER, ROAS, PoAS, CAC) baseline = the
baseline window's own ratio, compared to yesterday's directly.
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


def _poas(margin, roas):
    """PoAS = profit-on-ad-spend = (profit/revenue) * (revenue/spend)."""
    if margin is None or roas is None:
        return None
    return margin * roas


def _tile(label, value_str, base_str, delta_pct, *, lower_is_better=False):
    return {
        "label":       label,
        "value":       value_str,
        "base":        base_str,
        "delta_str":   _FH.signed_pct(delta_pct),
        "delta_class": _FH.delta_class(delta_pct, lower_is_better=lower_is_better),
    }


def build(summary, baseline_days):
    ccy = summary.get("currency") or ""
    y = summary.get("yday") or {}
    b = summary.get("base") or {}
    days = baseline_days or 7

    def per_day(window_total):
        v = _FH.safe_float(window_total)
        return None if v is None else v / days

    tiles = []

    # ---- Revenue (level) ----
    y_rev = y.get("revenue")
    b_rev_day = per_day(b.get("revenue"))
    tiles.append(_tile(
        "Revenue",
        _FH.compact_money(y_rev, ccy),
        "avg " + _FH.compact_money(b_rev_day, ccy),
        _FH.pct_change(y_rev, b_rev_day),
    ))

    # ---- Orders (level) ----
    y_ord = y.get("orders")
    b_ord_day = per_day(b.get("orders"))
    tiles.append(_tile(
        "Orders",
        _FH.integer(y_ord),
        "avg " + _FH.integer(round(b_ord_day) if b_ord_day is not None else None),
        _FH.pct_change(y_ord, b_ord_day),
    ))

    # ---- MER (ratio) ----
    tiles.append(_tile(
        "MER",
        _FH.ratio(y.get("mer")),
        "avg " + _FH.ratio(b.get("mer")),
        _FH.pct_change(y.get("mer"), b.get("mer")),
    ))

    # ---- ROAS (ratio) ----
    tiles.append(_tile(
        "ROAS",
        _FH.ratio(y.get("roas")),
        "avg " + _FH.ratio(b.get("roas")),
        _FH.pct_change(y.get("roas"), b.get("roas")),
    ))

    # ---- PoAS (ratio, derived from profit margin × ROAS) ----
    poas_y = _poas(summary.get("margin_yday"), y.get("roas"))
    poas_b = _poas(summary.get("margin_base"), b.get("roas"))
    tiles.append(_tile(
        "PoAS",
        _FH.ratio(poas_y),
        "avg " + _FH.ratio(poas_b),
        _FH.pct_change(poas_y, poas_b),
    ))

    # ---- CAC (ratio, lower is better) ----
    tiles.append(_tile(
        "CAC",
        _FH.money(y.get("cac"), ccy, digits=2),
        "avg " + _FH.money(b.get("cac"), ccy, digits=2),
        _FH.pct_change(y.get("cac"), b.get("cac")),
        lower_is_better=True,
    ))

    return tiles
