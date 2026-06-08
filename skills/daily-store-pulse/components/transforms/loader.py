"""Normalize one store's raw MCP payloads into a clean summary dict.

The pulse compares **yesterday** against a **trailing 7-day daily average**.
Two windows feed every efficiency figure:
  - ``overview_yday``  — get_dashboard_overview over yesterday (1 day).
  - ``overview_base``  — get_dashboard_overview over the 7 days before yesterday.
Level metrics (revenue, orders, profit) compare yesterday against the baseline
window's per-day average (window total / 7). Ratio metrics (MER, ROAS, CAC,
PoAS) compare yesterday's window ratio against the baseline window ratio
directly — ratios are already per-window averages.

All monetary fields come back from the MCP in *cents* of the store currency;
this module divides by 100 once so every downstream consumer sees units.

Field names mirror the verified parser shipped in the growth-report skill
(``overview.total_revenue``, ``overview.platform_statistics[].*``, etc.). The
profit/anomaly/campaign shapes are read defensively across the candidate key
names documented by each tool, so a minor shape difference degrades to "—"
rather than crashing the build.
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
_cents = _FH.cents_to_units
_f = _FH.safe_float


# ---- overview ---------------------------------------------------------------

def _overview(ov):
    """Pull the canonical store-currency figures out of a get_dashboard_overview
    payload. Returns levels (in units) + ratios. Empty dict when absent."""
    o = (ov or {}).get("overview") or {}
    if not o:
        return {}
    return {
        "revenue":   _cents(o.get("total_revenue")),
        "orders":    _f(o.get("total_orders")),
        "spend":     _cents(o.get("ad_account_spend")),
        "new_orders": _f(o.get("total_new_customer_orders")),
        "new_revenue": _cents(o.get("total_new_customer_revenue")),
        "mer":       _f(o.get("marketing_efficiency_ratio")),
        "roas":      _f(o.get("return_on_ad_spend")),
        "roas_new":  _f(o.get("return_on_ad_spend_new")),
        "cac":       _cents(o.get("customer_acquisition_cost")),
        "cpc":       _cents(o.get("cost_per_click")),
        "platform_statistics": o.get("platform_statistics") or [],
        "store_currency": (ov or {}).get("store_currency") or (ov or {}).get("currency"),
    }


# ---- profit on ad spend -----------------------------------------------------
# The tool returns the unitless ratio profit/revenue per group (PoAS / ROAS).
# Shape isn't fixed across versions, so read it defensively: find the list of
# groups, then the ratio field on each, and blend (order-weighted if counts are
# present, else simple mean). PoAS itself = (profit/revenue) * ROAS, computed by
# the KPI transform which has the matching-window ROAS.

# The tool returns profit/revenue per group under `poas_over_roas` (PoAS ÷ ROAS
# = (profit/spend) ÷ (revenue/spend) = profit/revenue), in a `groups` list keyed
# by `utm_source`, weighted by `order_count`. The other key names are kept as
# defensive fallbacks against shape drift.
_GROUP_KEYS = ("groups", "results", "rows", "data", "platforms", "items")
_RATIO_KEYS = (
    "poas_over_roas", "poas", "ratio", "poas_ratio", "profit_on_ad_spend",
    "profit_to_revenue_ratio", "profit_to_revenue", "profit_ratio", "value",
)
_COUNT_KEYS = ("order_count", "orders", "n_orders", "count", "num_orders")


def _profit_margin_ratio(poas_payload):
    """Blended profit/revenue ratio from a get_profit_on_ad_spend payload, or
    None when no usable group is present."""
    if not isinstance(poas_payload, dict):
        return None
    groups = None
    for k in _GROUP_KEYS:
        v = poas_payload.get(k)
        if isinstance(v, list) and v:
            groups = v
            break
    if groups is None:
        # Some shapes may put the ratio at the top level for a single group.
        for k in _RATIO_KEYS:
            if k in poas_payload:
                return _f(poas_payload.get(k))
        return None

    num = 0.0
    den = 0.0
    simple = []
    for g in groups:
        if not isinstance(g, dict):
            continue
        ratio = None
        for rk in _RATIO_KEYS:
            if rk in g:
                ratio = _f(g.get(rk))
                break
        if ratio is None:
            continue
        weight = None
        for ck in _COUNT_KEYS:
            if ck in g:
                weight = _f(g.get(ck))
                break
        simple.append(ratio)
        if weight and weight > 0:
            num += ratio * weight
            den += weight
    if den > 0:
        return num / den
    if simple:
        return sum(simple) / len(simple)
    return None


# ---- daily store statistics -------------------------------------------------

_DATE_KEYS = ("date", "day", "statistic_date", "stat_date", "report_date", "ds")


def _daily_rows(daily_payload):
    """Return the list of daily rows from a get_daily_store_statistics payload."""
    if not isinstance(daily_payload, dict):
        return []
    rows = daily_payload.get("rows")
    return rows if isinstance(rows, list) else []


def _row_date(row):
    for k in _DATE_KEYS:
        if k in row and row[k]:
            return str(row[k])
    return None


def _daily_revenue_series(daily_payload):
    """[(date, revenue_units)] sorted by date — drives the sparkline + trend."""
    out = []
    for r in _daily_rows(daily_payload):
        if not isinstance(r, dict):
            continue
        out.append((_row_date(r), _cents(r.get("total_revenue")) or 0.0))
    # Sort by date when present; otherwise preserve payload order.
    if all(d for d, _ in out):
        out.sort(key=lambda t: t[0])
    return out


def normalize(store_cfg, raws, windows):
    """Build the normalized per-store summary the card transforms consume."""
    ccy = (store_cfg.get("store_currency")
           or (raws.get("overview_yday") or {}).get("store_currency")
           or (raws.get("overview_base") or {}).get("store_currency") or "")

    yday = _overview(raws.get("overview_yday"))
    base = _overview(raws.get("overview_base"))
    mtd = _overview(raws.get("overview_mtd"))
    # Month-over-month pacing: last month's same-day window + last month's full total.
    mtd_prev = _overview(raws.get("overview_prev_month_mtd"))
    mtd_prev_full = _overview(raws.get("overview_prev_month_full"))

    margin_yday = _profit_margin_ratio(raws.get("poas_yday"))
    margin_base = _profit_margin_ratio(raws.get("poas_base"))

    daily_series = _daily_revenue_series(raws.get("daily"))

    return {
        "store_id":       str(store_cfg.get("store_id")),
        "store_name":     store_cfg.get("store_name") or f"Store {store_cfg.get('store_id')}",
        "store_url":      store_cfg.get("store_url") or "",
        "onboarding_date": store_cfg.get("onboarding_date") or "",
        "currency":       ccy,
        "yday":           yday,
        "base":           base,
        "mtd":            mtd,
        "mtd_prev":       mtd_prev,
        "mtd_prev_full":  mtd_prev_full,
        "margin_yday":    margin_yday,
        "margin_base":    margin_base,
        "daily_revenue":  daily_series,
        # Pass raw payloads the insight modules parse directly.
        "anomalies":      raws.get("anomalies") or {},
        "meta_recs":      raws.get("meta_recs") or {},
        "campaigns":      raws.get("campaigns") or {},
        "has_overview":   bool(yday) or bool(base),
    }
