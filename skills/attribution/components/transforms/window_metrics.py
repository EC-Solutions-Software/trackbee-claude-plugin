"""Per-window aggregation for the Attribution Overview report.

Everything that responds to the 3d / 7d / 28d filter is computed here:
blended KPIs, per-platform tiles, channel-attribution rows, the daily NC-ROAS
series, and the store-funnel stages. The raw numbers and the intermediate
sets the insight components need are returned together; the insight prose
itself is built by the ``insights/`` components from the ``_ctx`` block.

Self-contained — stdlib only; the FX dict is passed in, not imported.
"""

import datetime as dt


def _fx_to_eur(fx, currency):
    if not currency:
        return 1.0
    return float((fx or {}).get(currency.upper(), 1.0))


def _step_count(funnel_obj, step):
    for s in funnel_obj.get("funnel", []):
        if s["step"] == step:
            return s["count"]
    return 0


def _platform_stat(overview_obj, provider_key):
    """Per-platform stats from overview's platform_statistics[].

    Overview values are store-currency cents; divide by 100 to match the
    scale the rest of the build uses. Zeros when the platform isn't listed.
    """
    provider_key = (provider_key or "").upper()
    for stat in (overview_obj or {}).get("platform_statistics", []):
        if (stat.get("conversion_provider") or "").upper() == provider_key:
            spend_ccy = (stat.get("spend") or 0) / 100
            rev_ccy = (stat.get("revenue") or 0) / 100
            roas = stat.get("return_on_ad_spend") or (rev_ccy / spend_ccy if spend_ccy else 0)
            clicks = stat.get("clicks") or 0
            cpc_ccy = (stat.get("cost_per_click") or 0) / 100
            return {"spend": spend_ccy, "revenue": rev_ccy, "roas": roas,
                    "clicks": clicks, "cpc": cpc_ccy}
    return {"spend": 0, "revenue": 0, "roas": 0, "clicks": 0, "cpc": 0}


def _sum_spend_eur(insights, fx):
    """Sum campaign spend, converting each row to store currency via its own
    ad_account_currency (falling back to the payload's ad-account currency)."""
    default_ccy = None
    if insights.get("ad_accounts"):
        default_ccy = insights["ad_accounts"][0].get("ad_account_currency")
    total = 0.0
    for c in insights["campaigns"]:
        ccy = c.get("ad_account_currency") or default_ccy
        total += float(c.get("spend") or 0) * _fx_to_eur(fx, ccy)
    return total


def _ov_spend(window, fx):
    """Overview's ad_account_spend is authoritative; campaign-sum is fallback."""
    ov = window.get("overview") or {}
    v = ov.get("ad_account_spend")
    if v:
        return v / 100
    return _sum_spend_eur(window["meta"], fx) + _sum_spend_eur(window["google"], fx)


def _daily_spend_for(windows, fx):
    """Build the calendar-day → daily-spend function used by the NC-ROAS line.

    We don't get per-day ad spend from the MCP, but we have window totals at
    three granularities. Subtracting them gives three tiers so the same
    calendar day produces the same NC-ROAS regardless of which window is
    selected.
    """
    total_3d = _ov_spend(windows["3d"], fx)
    total_7d = _ov_spend(windows["7d"], fx)
    total_28d = _ov_spend(windows["28d"], fx)

    d3_start = dt.date.fromisoformat(windows["3d"]["start"])
    d3_end = dt.date.fromisoformat(windows["3d"]["end"])
    d7_start = dt.date.fromisoformat(windows["7d"]["start"])
    d7_end = dt.date.fromisoformat(windows["7d"]["end"])
    d28_start = dt.date.fromisoformat(windows["28d"]["start"])
    d28_end = dt.date.fromisoformat(windows["28d"]["end"])

    n_3d = (d3_end - d3_start).days + 1
    n_7d = (d7_end - d7_start).days + 1
    n_28d = (d28_end - d28_start).days + 1
    gap_3_to_7 = max(1, n_7d - n_3d)
    gap_7_to_28 = max(1, n_28d - n_7d)

    tiers = [
        (d3_start, d3_end, (total_3d / n_3d) if n_3d else 0),
        (d7_start, d3_start - dt.timedelta(days=1),
            (total_7d - total_3d) / gap_3_to_7),
        (d28_start, d7_start - dt.timedelta(days=1),
            (total_28d - total_7d) / gap_7_to_28),
    ]

    def daily_spend_for(date):
        for start, end, avg in tiers:
            if start <= date <= end:
                return avg
        return total_28d / 28  # fallback

    return daily_spend_for


def _compute_window(window_key, windows, daily, daily_spend_for, fx):
    w = windows[window_key]
    rows = daily["rows"][w["daily_slice"]:] if w["daily_slice"] else daily["rows"]
    s = lambda f: sum((r.get(f) or 0) for r in rows)
    n_days = len(rows)

    cur = (w.get("funnel") or {}).get("current") or {"funnel": []}
    prev = (w.get("funnel") or {}).get("previous") or {"funnel": []}

    # ---- Ad spend + revenue — from overview (authoritative) ------------------
    ov = w.get("overview") or {}
    _meta_ov = _platform_stat(ov, "FACEBOOK")
    _google_ov = _platform_stat(ov, "GOOGLE")

    meta_spend_eur = _meta_ov["spend"] if _meta_ov["spend"] else _sum_spend_eur(w["meta"], fx)
    meta_in_rev_eur = _meta_ov["revenue"]
    google_spend_eur = _google_ov["spend"] if _google_ov["spend"] else _sum_spend_eur(w["google"], fx)
    google_in_rev_eur = _google_ov["revenue"]
    _ov_total = (ov.get("ad_account_spend") or 0) / 100
    ad_spend_eur = _ov_total if _ov_total else (meta_spend_eur + google_spend_eur)

    meta_purchases = sum((c.get("purchases") or 0) for c in w["meta"]["campaigns"])
    meta_imp = sum(int(c.get("impressions") or 0) for c in w["meta"]["campaigns"])
    meta_clk = sum(int(c.get("clicks") or 0) for c in w["meta"]["campaigns"])

    google_conv = sum((c.get("conversions") or 0) for c in w["google"]["campaigns"])
    google_imp = sum(int(c.get("impressions") or 0) for c in w["google"]["campaigns"])
    google_clk = sum(int(c.get("clicks") or 0) for c in w["google"]["campaigns"])

    # ---- Daily NC-ROAS series (Acquisition MER over time) --------------------
    end_date = dt.date.fromisoformat(w["end"])
    daily_nc_roas = []
    for i, r in enumerate(rows):
        offset_from_end = (n_days - 1) - i
        d = end_date - dt.timedelta(days=offset_from_end)
        nc_rev_day = (r.get("total_new_customer_revenue") or 0) / 100
        spend_day = daily_spend_for(d)
        nc_roas_day = nc_rev_day / spend_day if spend_day else 0
        daily_nc_roas.append({"date": d.isoformat(), "value": round(nc_roas_day, 3),
                              "nc_revenue": round(nc_rev_day, 2),
                              "daily_spend": round(spend_day, 2)})

    # ---- Blended — overview primary; daily-row sum is fallback ---------------
    revenue = ((ov.get("total_revenue") or 0) / 100) or (s("total_revenue") / 100)
    orders = ov.get("total_orders") or s("total_orders")
    nc_orders = ov.get("total_new_customer_orders") or s("total_new_customer_orders")
    nc_rev = ((ov.get("total_new_customer_revenue") or 0) / 100) or (s("total_new_customer_revenue") / 100)

    revenue_prev = prev.get("total_revenue", 0) / 100
    orders_prev = prev.get("total_orders", 0)
    pv = _step_count(cur, "total_page_view_events")
    pv_prev = _step_count(prev, "total_page_view_events")
    atc = _step_count(cur, "total_add_to_cart_events")
    atc_prev = _step_count(prev, "total_add_to_cart_events")
    co = _step_count(cur, "total_checkout_started_events")
    co_prev = _step_count(prev, "total_checkout_started_events")

    blended = {
        "ad_spend": ad_spend_eur, "revenue": revenue, "orders": orders,
        "new_customers": nc_orders, "nc_rev": nc_rev,
        "aov": revenue / orders if orders else 0,
        "roas": revenue / ad_spend_eur if ad_spend_eur else 0,
        "cpa": ad_spend_eur / orders if orders else 0,
        "nc_cpa": ad_spend_eur / nc_orders if nc_orders else 0,
        "nc_roas": nc_rev / ad_spend_eur if ad_spend_eur else 0,
        "sessions": pv,
        "rev_per_session": revenue / pv if pv else 0,
        "atc_rate": atc / pv if pv else 0,
        "co_rate": co / pv if pv else 0,
        "cvr": orders / pv if pv else 0,
        "_revenue_prev": revenue_prev,
        "_orders_prev": orders_prev,
        "_pv_prev": pv_prev,
        "_atc_rate_prev": atc_prev / pv_prev if pv_prev else 0,
        "_co_rate_prev": co_prev / pv_prev if pv_prev else 0,
        "_cvr_prev": orders_prev / pv_prev if pv_prev else 0,
    }

    # ---- Per-platform --------------------------------------------------------
    platforms = {
        "meta": {"label": "Meta", "color": "#1877F2", "logo": "meta",
                 "spend": meta_spend_eur, "revenue": meta_in_rev_eur,
                 "impressions": meta_imp, "clicks": meta_clk,
                 "purchases": meta_purchases},
        "google": {"label": "Google", "color": "#4285F4", "logo": "google",
                   "spend": google_spend_eur, "revenue": google_in_rev_eur,
                   "impressions": google_imp, "clicks": google_clk,
                   "purchases": round(google_conv)},
    }
    for p in platforms.values():
        p["roas"] = (p["revenue"] / p["spend"]) if p["spend"] else 0
        p["ctr"] = (p["clicks"] / p["impressions"] * 100) if p["impressions"] else 0
        p["cpc"] = (p["spend"] / p["clicks"]) if p["clicks"] else 0
        p["cpm"] = (p["spend"] / p["impressions"] * 1000) if p["impressions"] else 0

    # ---- Channel attribution rows --------------------------------------------
    pf = w["platform_funnel"]["platforms"]

    def ch_row(label, key, plat_purchases, plat_revenue, spend, logo=None):
        f = pf.get(key, {})
        sessions = _step_count(f, "page_view_events")
        purch_tb = _step_count(f, "orders")
        rev_tb = (f.get("revenue") or 0) / 100
        cpa = (spend / plat_purchases) if (spend and plat_purchases) else None
        roas = (plat_revenue / spend) if (spend and plat_revenue) else None
        return {
            "channel": label, "logo": logo,
            "sessions": sessions,
            "purch_tb": purch_tb, "purch_in": plat_purchases,
            "rev_tb": rev_tb, "rev_in": plat_revenue,
            "spend": spend,
            "cpa": cpa,
            "roas": roas,
        }

    channel_defs = {
        "facebook": ("Meta", "meta", meta_purchases, meta_in_rev_eur, meta_spend_eur),
        "google": ("Google", "google", round(google_conv), google_in_rev_eur, google_spend_eur),
        "klaviyo": ("Klaviyo", "klaviyo", None, None, 0),
        "tiktok": ("TikTok", "tiktok", None, None, 0),
        "pinterest": ("Pinterest", "pinterest", None, None, 0),
        "microsoft": ("Microsoft Ads", "microsoft", None, None, 0),
        "calendly": ("Calendly", "calendly", None, None, 0),
        "email": ("Email", "klaviyo", None, None, 0),
    }
    rows_out = []
    for plat_key in pf.keys():
        if plat_key in channel_defs:
            label, logo, p_purch, p_rev, p_spend = channel_defs[plat_key]
            rows_out.append(ch_row(label, plat_key, p_purch, p_rev, p_spend, logo))
        else:
            rows_out.append(ch_row(plat_key.replace("_", " ").title(), plat_key, None, None, 0, None))

    # ---- Channel-attribution intermediate sets (insight prose built later) ---
    paying = [r for r in rows_out if r["spend"] > 0]
    earned = [r for r in rows_out if r["spend"] == 0 and r["rev_tb"] > 0]
    total_tb_rev = sum(r["rev_tb"] for r in rows_out)
    over_reporters = []

    overall = {
        "channel": "Overall", "logo": None,
        "sessions": sum(r["sessions"] for r in rows_out),
        "purch_tb": sum(r["purch_tb"] for r in rows_out),
        "purch_in": meta_purchases + round(google_conv),
        "rev_tb": sum(r["rev_tb"] for r in rows_out),
        "rev_in": meta_in_rev_eur + google_in_rev_eur,
        "spend": sum(r["spend"] for r in rows_out),
    }
    overall["cpa"] = (overall["spend"] / overall["purch_in"]) if (overall["spend"] and overall["purch_in"]) else None
    overall["roas"] = (overall["rev_in"] / overall["spend"]) if (overall["spend"] and overall["rev_in"]) else None

    rows_out.append(overall)

    top_rev = max(
        rows_out,
        key=lambda r: (r["rev_in"] or 0) if r["rev_in"] is not None else (r["rev_tb"] or 0)
    ) if rows_out else {"channel": "", "rev_tb": 0, "rev_in": None}
    top_rev_val = (top_rev["rev_in"] if top_rev.get("rev_in") is not None else top_rev.get("rev_tb", 0)) or 0
    total_rev_all = sum(
        ((r["rev_in"] if r.get("rev_in") is not None else r.get("rev_tb", 0)) or 0)
        for r in rows_out if r["channel"] != "Overall"
    )

    # ---- Store funnel stages -------------------------------------------------
    step_labels = {
        "total_page_view_events": "Page views",
        "total_product_view_events": "Product views",
        "total_add_to_cart_events": "Add to cart",
        "total_checkout_started_events": "Checkout started",
        "total_orders": "Orders",
    }
    funnel_stages = []
    for st in (cur.get("funnel") or []):
        if st.get("step") in step_labels:
            funnel_stages.append({
                "step": st["step"],
                "label": step_labels[st["step"]],
                "count": int(st.get("count") or 0),
                "rate_from_previous": st.get("rate_from_previous"),
                "rate_from_top": st.get("rate_from_top"),
            })

    funnel_drops = []
    for i, st in enumerate(funnel_stages):
        if i == 0:
            continue
        prv = funnel_stages[i - 1]
        rate = st.get("rate_from_previous")
        if rate is None and prv["count"]:
            rate = st["count"] / prv["count"]
        funnel_drops.append({
            "from_step": prv["step"], "from_label": prv["label"],
            "to_step": st["step"], "to_label": st["label"],
            "rate": rate or 0,
            "lost": max(0, prv["count"] - st["count"]),
        })

    non_browse_drops = [d for d in funnel_drops if d["to_step"] != "total_product_view_events"]
    worst_drop = (min(non_browse_drops, key=lambda d: d["rate"])
                  if non_browse_drops else
                  (min(funnel_drops, key=lambda d: d["rate"]) if funnel_drops else None))
    browse_drop = next((d for d in funnel_drops if d["to_step"] == "total_product_view_events"), None)

    orders_step = next((st for st in funnel_stages if st["step"] == "total_orders"), None)
    pv_step = next((st for st in funnel_stages if st["step"] == "total_page_view_events"), None)
    funnel_summary = {
        "top_to_order_rate": ((orders_step["count"] / pv_step["count"])
                              if (orders_step and pv_step and pv_step["count"]) else 0),
        "worst_to_label": worst_drop["to_label"] if worst_drop else None,
        "worst_rate": worst_drop["rate"] if worst_drop else None,
    }

    return {
        "label": w["label"], "start": w["start"], "end": w["end"],
        "blended": blended, "platforms": platforms, "channels": rows_out,
        "daily_nc_roas": daily_nc_roas,
        "funnel_stages": funnel_stages, "funnel_drops": funnel_drops,
        "funnel_summary": funnel_summary,
        "_ctx": {
            "paying": paying, "earned": earned, "total_tb_rev": total_tb_rev,
            "over_reporters": over_reporters,
            "revenue": revenue, "revenue_prev": revenue_prev, "orders": orders,
            "ad_spend_eur": ad_spend_eur, "blended_roas": blended["roas"],
            "top_rev": top_rev, "top_rev_val": top_rev_val, "total_rev_all": total_rev_all,
            "worst_drop": worst_drop, "browse_drop": browse_drop, "funnel_drops": funnel_drops,
        },
    }


def compute_windows(windows, daily, fx):
    """Compute the per-window data for all three windows (3d / 7d / 28d)."""
    daily_spend_for = _daily_spend_for(windows, fx)
    return {k: _compute_window(k, windows, daily, daily_spend_for, fx)
            for k in ("3d", "7d", "28d")}
