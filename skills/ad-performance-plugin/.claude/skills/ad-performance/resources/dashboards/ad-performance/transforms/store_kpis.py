"""Store-level KPI tile data.

Reads:
* get_dashboard_overview         — MER, total revenue, store ad spend
* get_meta_campaign_insights     — spend / revenue rollups for the Meta tile
* get_google_campaign_insights   — spend / revenue rollups for the Google tile

Outputs ONE dict with the numbers the kpi_bar.html view needs to render the
top of every store section. Currency conversion to store currency happens
here using `meta_fx_to_store` / `google_fx_to_store` from the store config —
no FX rate is hard-coded in this module.
"""

from __future__ import annotations

from . import _fmt as f


def _sum_spend(rows: list[dict], fx: float) -> float:
    return sum(f.safe_float(r.get("spend")) * fx for r in rows if f.safe_float(r.get("spend")) > 0)


def _weighted_meta_roas(rows: list[dict], total_spend: float) -> float:
    if total_spend <= 0:
        return 0.0
    weighted = sum(
        f.safe_float(r.get("purchase_roas")) * f.safe_float(r.get("spend"))
        for r in rows
        if r.get("purchase_roas") and r.get("spend")
    )
    return weighted / total_spend


def transform(inputs: dict, config: dict) -> dict:
    """Return ``{tiles: {...}, totals: {...}}`` for the store.

    `inputs` keys:
        overview   — get_dashboard_overview result (may be `{}`)
        meta       — get_meta_campaign_insights result (may be `{}`)
        google     — get_google_campaign_insights result (may be `{}`)

    `config` is the store config row from config.json (has FX + symbol).
    `window.n_days` is read from the top-level config so the avg-daily-spend
    KPI can be computed without re-parsing the date range.
    """
    overview = inputs.get("overview") or {}
    meta = inputs.get("meta") or {}
    google = inputs.get("google") or {}
    m_fx = f.safe_float(config.get("meta_fx_to_store", 1.0), 1.0)
    g_fx = f.safe_float(config.get("google_fx_to_store", 1.0), 1.0)
    n_days = max(int(config.get("_window_n_days") or 1), 1)

    meta_rows = meta.get("campaigns") or []
    goog_rows = google.get("campaigns") or []

    meta_spend = _sum_spend(meta_rows, m_fx)
    goog_spend = _sum_spend(goog_rows, g_fx)
    total_spend = meta_spend + goog_spend

    meta_rev = sum(f.safe_float(c.get("revenue_1d_click")) * m_fx for c in meta_rows)
    goog_rev = sum(f.safe_float(c.get("conversions_value")) * g_fx for c in goog_rows)
    total_rev = meta_rev + goog_rev

    blended_roas = (total_rev / total_spend) if total_spend > 0 else 0.0
    meta_roas = _weighted_meta_roas(meta_rows, meta_spend)
    goog_roas = (goog_rev / goog_spend) if goog_spend > 0 else 0.0

    meta_purch = sum(int(c.get("purchases") or 0) for c in meta_rows)
    goog_conv = sum(f.safe_float(c.get("conversions")) for c in goog_rows)

    # Overview KPIs (in store-currency cents — divide by 100 for display).
    ov = overview.get("overview") or {}
    ov_total_rev = f.safe_float(ov.get("total_revenue")) / 100
    ov_total_orders = f.safe_float(ov.get("total_orders"))
    ov_mer = f.safe_float(ov.get("marketing_efficiency_ratio"))

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
