"""Compute headline KPI tile values from the per-window overview + funnel payloads.

The dashboard overview already returns the canonical store-currency numbers
we want (revenue, MER, ROAS, CAC, LTV, new/returning splits). This transform's
job is to extract them, derive a few simple ratios (AOV, share of new), and
emit a list of tile dicts ready for the chrome to render.

All monetary values come back from the MCP in *cents* of `store_currency` —
the transform divides by 100 once here so every downstream consumer sees the
same units.
"""

from __future__ import annotations
from typing import Any


def _cents(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x) / 100.0
    except (TypeError, ValueError):
        return None


def _ratio(num: Any, den: Any) -> float | None:
    try:
        n = float(num); d = float(den)
        if d == 0:
            return None
        return n / d
    except (TypeError, ValueError):
        return None


def _clamp_share(x: float | None) -> float | None:
    """Clamp a share to [0, 1]. Source payloads occasionally report a
    numerator larger than its denominator (e.g. more new-customer orders
    than total orders); without the clamp the new/returning mix renders
    a negative returning share downstream."""
    if x is None:
        return None
    return min(max(x, 0.0), 1.0)


def _summary_from_overview(ov: dict) -> dict:
    o = (ov or {}).get("overview") or {}
    if not o:
        return {}
    revenue = _cents(o.get("total_revenue"))
    new_rev = _cents(o.get("total_new_customer_revenue"))
    ret_rev = _cents(o.get("total_returning_customer_revenue"))
    spend   = _cents(o.get("ad_account_spend"))
    new_ord = o.get("total_new_customer_orders") or 0
    ret_ord = o.get("total_returning_customer_orders") or 0
    orders  = o.get("total_orders") or 0
    cac     = _cents(o.get("customer_acquisition_cost"))
    ltv     = _cents(o.get("customer_life_time_value"))
    return {
        "revenue":        revenue,
        "spend":          spend,
        "orders":         orders,
        "new_revenue":    new_rev,
        "new_orders":     new_ord,
        "ret_revenue":    ret_rev,
        "ret_orders":     ret_ord,
        "cac":            cac,
        "ltv":            ltv,
        "ltv_cac":        o.get("customer_life_time_value_to_acquisition_cost_ratio"),
        "mer":            o.get("marketing_efficiency_ratio"),
        "roas":           o.get("return_on_ad_spend"),
        "roas_new":       o.get("return_on_ad_spend_new"),
        "aov":            _ratio(revenue, orders) if revenue is not None else None,
        "aov_new":        _ratio(new_rev, new_ord),
        "aov_ret":        _ratio(ret_rev, ret_ord),
        # Order-based mix per the metric-map spec
        # (total_new_customer_orders / total_orders). The new_ret_mix row
        # renders this as a "% new / % returning" customer split, so it must
        # be order-based — a revenue split would mislabel the figure whenever
        # new- and returning-customer AOV differ.
        "new_share":      _clamp_share(_ratio(new_ord, orders)),
        "platform_statistics": o.get("platform_statistics") or [],
        "ad_account_spend":   spend,
        "ad_account_revenue": _cents(o.get("ad_account_revenue")),
        "store_currency":  (ov or {}).get("store_currency") or (ov or {}).get("currency"),
    }


def transform(inputs: dict, config: dict) -> dict:
    """Build the headline KPI payload.

    Returns the per-window summary metrics consumed by the metrics table
    and the narrative answer:
      {
        "current":  {<summary metrics>},
        "prior":    {<summary metrics>},
        "currency": "<store currency code>",
      }
    """
    cur_ov = inputs.get("overview_current") or {}
    prv_ov = inputs.get("overview_prior")   or {}
    ccy = (config.get("store_currency") or
           cur_ov.get("store_currency") or cur_ov.get("currency") or "")

    cur = _summary_from_overview(cur_ov)
    prv = _summary_from_overview(prv_ov)

    return {
        "current":  cur,
        "prior":    prv,
        "currency": ccy,
    }
