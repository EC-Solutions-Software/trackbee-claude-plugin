"""Store-level KPI tile data for the Ad Performance dashboard.

Reads: `overview` (get_dashboard_overview), `meta`
(get_meta_campaign_insights), `google` (get_google_campaign_insights).
Returns one ``{tiles, totals}`` dict the kpi_bar.html view can stamp.

Currency conversion happens here using `meta_fx_to_store` /
`google_fx_to_store` from the store config — no FX rate hard-coded
inside this module.

Standalone — `_safe_float` is inlined to match the repo convention of
no inter-component imports.
"""

from __future__ import annotations

import math


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce to float, treating None / '' / NaN / inf as `default`."""
    try:
        v = float(value or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


def _sum_spend(rows: list[dict], fx: float) -> float:
    return sum(_safe_float(r.get("spend")) * fx
               for r in rows if _safe_float(r.get("spend")) > 0)


def _weighted_meta_roas(rows: list[dict], total_spend: float) -> float:
    if total_spend <= 0:
        return 0.0
    weighted = sum(
        _safe_float(r.get("purchase_roas")) * _safe_float(r.get("spend"))
        for r in rows
        if r.get("purchase_roas") and r.get("spend")
    )
    return weighted / total_spend


def transform(inputs: dict, config: dict) -> dict:
    """Return ``{tiles, totals}`` for the store.

    `inputs` keys: ``overview``, ``meta``, ``google`` (each may be `{}`).
    `config` is the per-store row from config.json (FX + symbol +
    ``_window_n_days`` injected by the orchestrator).
    """
    overview = inputs.get("overview") or {}
    meta = inputs.get("meta") or {}
    google = inputs.get("google") or {}
    m_fx = _safe_float(config.get("meta_fx_to_store", 1.0), 1.0)
    g_fx = _safe_float(config.get("google_fx_to_store", 1.0), 1.0)
    n_days = max(int(config.get("_window_n_days") or 1), 1)

    meta_rows = meta.get("campaigns") or []
    goog_rows = google.get("campaigns") or []

    meta_spend = _sum_spend(meta_rows, m_fx)
    goog_spend = _sum_spend(goog_rows, g_fx)
    total_spend = meta_spend + goog_spend

    meta_rev = sum(_safe_float(c.get("revenue_1d_click")) * m_fx for c in meta_rows)
    goog_rev = sum(_safe_float(c.get("conversions_value")) * g_fx for c in goog_rows)
    total_rev = meta_rev + goog_rev

    blended_roas = (total_rev / total_spend) if total_spend > 0 else 0.0
    meta_roas = _weighted_meta_roas(meta_rows, meta_spend)
    goog_roas = (goog_rev / goog_spend) if goog_spend > 0 else 0.0

    meta_purch = sum(int(c.get("purchases") or 0) for c in meta_rows)
    goog_conv = sum(_safe_float(c.get("conversions")) for c in goog_rows)

    # Overview KPIs (cents of store currency → units).
    ov = overview.get("overview") or {}
    ov_total_rev = _safe_float(ov.get("total_revenue")) / 100
    ov_total_orders = _safe_float(ov.get("total_orders"))
    ov_mer = _safe_float(ov.get("marketing_efficiency_ratio"))

    return {
        "tiles": {
            "total_spend":   total_spend,
            "meta_spend":    meta_spend,
            "goog_spend":    goog_spend,
            "blended_roas":  blended_roas,
            "meta_roas":     meta_roas,
            "goog_roas":     goog_roas,
            "mer":           ov_mer,
            "conversions":   meta_purch + int(goog_conv),
            "meta_purch":    meta_purch,
            "goog_conv":     goog_conv,
            "avg_daily":     total_spend / n_days if n_days else 0.0,
            "n_days":        n_days,
        },
        "totals": {
            "meta_rev":      meta_rev,
            "goog_rev":      goog_rev,
            "total_rev":     total_rev,
            "ov_total_rev":  ov_total_rev,
            "ov_total_orders": ov_total_orders,
        },
    }
