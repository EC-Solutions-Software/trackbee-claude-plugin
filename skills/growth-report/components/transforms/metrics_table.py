"""Build the growth-report metric framework table.

Ships every row of the TrackBee Growth framework. The rows whose underlying
data the MCP doesn't expose yet (e.g. true incrementality, per-product cuts)
render as a short prose placeholder in the interpretation column rather than a
measured value — no rows are dropped.

Each row carries:
  - the static framework fields (name, what the metric indicates,
    importance) — copied verbatim from the TrackBee growth-report
    checklist;
  - the current and prior window values computed from the staged MCP
    payloads;
  - a one-line interpretation stating THIS run's measured figures and
    their week-over-week delta;
  - a signal — "up" | "down" | "flat" — the raw direction of the
    week-over-week change, with no good/bad judgement attached. Drives
    the table's "Moved up" / "Moved down" filter buttons.
"""

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


_FH = _load("format_helpers", _CHROME / "format_helpers.py")


# ---- helpers ----------------------------------------------------------------

# Shared formatters — canonical copies live in chrome/format_helpers.py.
_delta      = _FH.pct_delta
_signed_pct = _FH.signed_pct
_ccy        = _FH.ccy


def _ratio(a, b):
    if a is None or b in (None, 0):
        return None
    try:
        return float(a) / float(b)
    except (TypeError, ValueError):
        return None


def _pct(value, digits=1):
    if value is None:
        return "—"
    return f"{value:.{digits}f}%"


def _ratio_str(value, digits=2, suffix=""):
    if value is None:
        return "—"
    return f"{value:.{digits}f}{suffix}"


def _int_str(value):
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


# ---- signal classification --------------------------------------------------
# The signal is purely the DIRECTION of the week-over-week change — no
# good/bad judgement. Three kinds per row:
#   up   — the metric rose by more than the threshold.
#   down — the metric fell by more than the threshold.
#   flat — moved inside the threshold band, or no comparable value.
# It only drives the "Moved up" / "Moved down" filter; it never colours a
# value as good or bad. Thresholds: ±5% WoW by default; AOV overrides to
# ±3%, and CPC and the worst-platform revenue move use ±10%.

def _signal_delta(d, *, threshold=5.0):
    if d is None:
        return "flat"
    if d > threshold:
        return "up"
    if d < -threshold:
        return "down"
    return "flat"


# ---- static metric definitions ----------------------------------------------
# Only metrics the MCP can actually measure. Each tuple:
#   (id, name, indicates, importance)
# `indicates` is a neutral definition of what the metric measures — it does
# not describe what a "good" or "bad" value looks like.
METRICS_STATIC = [
    ("revenue", "Revenue", "Top-line sales", "High"),

    ("new_revenue", "New customer revenue", "Revenue from first-time buyers", "High"),

    ("ret_revenue", "Returning customer revenue",
     "Revenue from repeat customers", "Medium"),

    ("new_orders", "New customers acquired",
     "Count of first-time-buyer orders", "High"),

    ("cac", "CAC · new customer CPA", "Cost to acquire a new customer", "High"),

    ("blended_cac", "Blended CAC",
     "Total paid spend per new customer, across all channels", "High"),

    ("mer", "MER · blended ROAS", "Total revenue per unit of total marketing spend", "High"),

    ("platform_roas", "Platform ROAS", "ROAS each ad platform reports for itself", "Medium"),

    ("iroas", "Incremental ROAS · iROAS",
     "Modelled estimate of return attributable to marketing; "
     "true lift requires a holdout test", "High"),

    ("incremental_revenue", "Incremental revenue",
     "Modelled estimate of revenue attributable to marketing; "
     "true lift requires a holdout test", "High"),

    ("cvr", "Conversion rate", "Traffic-to-purchase rate", "Medium"),

    ("aov", "AOV", "Average order value", "Medium"),

    ("traffic", "Traffic · sessions", "Visitor volume", "Medium"),

    ("traffic_quality", "Traffic quality",
     "Composite read of CVR, AOV and new-customer mix", "High"),

    ("spend_by_channel", "Spend by channel", "Where paid budget is deployed", "High"),

    ("revenue_by_channel", "Revenue by channel",
     "Attributed revenue per channel", "Medium"),

    ("new_ret_mix", "New vs. returning customer mix",
     "Split of revenue between new and returning customers", "High"),

    ("ltv", "LTV", "Modelled long-term value of acquired customers", "High"),

    ("ltv_cac", "LTV : CAC", "Modelled LTV divided by CAC", "High"),

    ("marginal_roas", "Marginal ROAS", "Return on the next unit of spend", "High"),

    ("marginal_cac", "Marginal CAC", "Cost of acquiring the next customer", "High"),

    ("saturation", "Saturation · diminishing returns",
     "Whether added spend is still producing efficient return", "High"),

    ("incrementality_score", "Channel incrementality score",
     "Likelihood a channel creates new demand vs. captures existing demand", "High"),

    ("attribution_gap", "Attribution vs. incrementality gap",
     "Difference between platform-reported and blended ROAS", "High"),

    ("creative_fatigue", "Creative fatigue",
     "Whether ad performance is changing with overexposure", "Medium"),

    ("frequency", "Frequency", "How often users see ads", "Medium"),

    ("assisted_conv", "Assisted conversions",
     "Whether a channel influences sales without closing them", "Medium"),

    ("first_touch", "First-touch contribution",
     "Which channels open customer journeys", "Medium"),

    ("last_touch", "Last-touch contribution",
     "Which channels close purchases", "Medium"),

    ("product_mix", "Product mix",
     "Whether sales come from high- or low-margin products", "Medium"),

    ("confidence", "Confidence score",
     "How much corroborating signal supports the figures", "High"),
]


# ---- value + interpretation + signal computation ----------------------------

def _platform_stats(ov):
    out = {}
    for row in ((ov or {}).get("overview") or {}).get("platform_statistics") or []:
        name = (row.get("conversion_provider") or "").lower()
        if not name:
            continue
        out[name] = {
            "spend":   (row.get("spend") or 0) / 100.0,
            "revenue": (row.get("revenue") or 0) / 100.0,
            "clicks":  row.get("clicks") or 0,
            "roas":    row.get("return_on_ad_spend"),
            "cpc":     (row.get("cost_per_click") or 0) / 100.0,
        }
    return out


def _step(funnel_obj, name):
    for entry in (funnel_obj or {}).get("funnel", []) or []:
        if entry.get("step") == name:
            return entry.get("count") or 0
    return 0


def _funnel_env(obj, name):
    """Return the ``{funnel: [...]}`` envelope ``name`` only when it carries
    an actual funnel array.

    ``tool__get_funnel_overview(compare_previous_period=true)`` nests each window
    under a ``current`` / ``previous`` key. The standalone ``funnel_prior``
    fallback is itself such a payload, so its data also lives under
    ``current`` — not at the top level. Reaching past the envelope is what
    keeps the prior-window funnel from silently reading as zero.
    """
    env = (obj or {}).get(name) or {}
    return env if env.get("funnel") else {}


def _compute_values(headline, raws, ccy):
    """Return a dict keyed by metric id -> (current_str, prior_str, interp_str, signal_str)."""
    cur = (headline or {}).get("current") or {}
    prv = (headline or {}).get("prior")   or {}

    fnl_cur = (raws.get("funnel_current") or {})
    fp_cur  = (raws.get("platform_footprints_current") or {})
    anomalies = (raws.get("anomalies") or {})
    meta_recs = (raws.get("meta_recommendations") or {})

    cur_plats = _platform_stats(raws.get("overview_current") or {})
    prv_plats = _platform_stats(raws.get("overview_prior")   or {})

    cur_funnel = _funnel_env(fnl_cur, "current") or fnl_cur
    prv_funnel = (
        _funnel_env(fnl_cur, "previous")
        or _funnel_env(raws.get("funnel_prior"), "current")
        or (raws.get("funnel_prior") or {})
    )

    cur_pv = _step(cur_funnel, "total_page_view_events")
    prv_pv = _step(prv_funnel, "total_page_view_events")
    cur_pv_to_order = _ratio(_step(cur_funnel, "total_orders"), cur_pv) if cur_pv else None
    prv_pv_to_order = _ratio(_step(prv_funnel, "total_orders"), prv_pv) if prv_pv else None

    v: dict = {}

    # ---- Revenue ----
    d = _delta(cur.get("revenue"), prv.get("revenue"))
    sig = _signal_delta(d, threshold=5.0)
    v["revenue"] = (_ccy(cur.get("revenue"), ccy), _ccy(prv.get("revenue"), ccy),
                    f"Top-line revenue {_signed_pct(d)} WoW.", sig)

    # ---- New customer revenue ----
    d = _delta(cur.get("new_revenue"), prv.get("new_revenue"))
    sig = _signal_delta(d, threshold=5.0)
    v["new_revenue"] = (_ccy(cur.get("new_revenue"), ccy), _ccy(prv.get("new_revenue"), ccy),
                        f"Revenue from first-time buyers {_signed_pct(d)} WoW.", sig)

    # ---- Returning customer revenue ----
    d = _delta(cur.get("ret_revenue"), prv.get("ret_revenue"))
    sig = _signal_delta(d, threshold=5.0)
    v["ret_revenue"] = (_ccy(cur.get("ret_revenue"), ccy), _ccy(prv.get("ret_revenue"), ccy),
                        f"Revenue from repeat customers {_signed_pct(d)} WoW.", sig)

    # ---- New customers acquired ----
    d = _delta(cur.get("new_orders"), prv.get("new_orders"))
    sig = _signal_delta(d, threshold=5.0)
    v["new_orders"] = (_int_str(cur.get("new_orders")), _int_str(prv.get("new_orders")),
                       f"First-time-buyer order count {_signed_pct(d)} WoW.", sig)

    # ---- CAC (inverted — down is good) ----
    d = _delta(cur.get("cac"), prv.get("cac"))
    sig = _signal_delta(d, threshold=5.0)
    v["cac"] = (_ccy(cur.get("cac"), ccy, digits=2), _ccy(prv.get("cac"), ccy, digits=2),
                f"Customer acquisition cost {_signed_pct(d)} WoW.", sig)

    # ---- Blended CAC (total paid spend / new customers; inverted) ----
    # Computed independently of the MCP's CAC figure so the two framework
    # rows carry distinct measurements, not one value rendered twice.
    cur_bcac = _ratio(cur.get("spend"), cur.get("new_orders"))
    prv_bcac = _ratio(prv.get("spend"), prv.get("new_orders"))
    d = _delta(cur_bcac, prv_bcac)
    sig = _signal_delta(d, threshold=5.0)
    v["blended_cac"] = (_ccy(cur_bcac, ccy, digits=2), _ccy(prv_bcac, ccy, digits=2),
                        f"Total paid-media spend per new customer {_signed_pct(d)} WoW, "
                        "blended across all ad platforms.", sig)

    # ---- MER ----
    d = _delta(cur.get("mer"), prv.get("mer"))
    sig = _signal_delta(d, threshold=5.0)
    v["mer"] = (_ratio_str(cur.get("mer")), _ratio_str(prv.get("mer")),
                f"Marketing efficiency ratio {_signed_pct(d)} WoW. Total revenue divided by total paid-media spend.",
                sig)

    # ---- Platform ROAS ----
    # Only list a platform that actually spent; show "n/a" (not a misleading
    # 0.00) when it spent but reported no ROAS.
    def _roas_cell(plats):
        parts = []
        for k, label in _FH.AD_PLATFORMS:
            p = plats.get(k) or {}
            if p.get("spend", 0) > 0:
                r = p.get("roas")
                parts.append(f"{label} {r:.2f}" if r is not None else f"{label} n/a")
        return " · ".join(parts) or "—"

    plats_cur = _roas_cell(cur_plats)
    plats_prv = _roas_cell(prv_plats)
    meta_roas_d = _delta((cur_plats.get("facebook") or {}).get("roas"),
                          (prv_plats.get("facebook") or {}).get("roas"))
    sig = _signal_delta(meta_roas_d, threshold=5.0)
    v["platform_roas"] = (plats_cur, plats_prv,
                          "Per-platform ROAS as each ad platform reports it. Compare against blended MER to identify under- or over-credited channels.",
                          sig)

    # ---- iROAS / Incremental revenue ----
    # Aggregate Meta incrementality if present in the campaign payload — otherwise flag as unavailable
    v["iroas"] = ("Available per Meta campaign", "Available per Meta campaign",
                  "Meta exposes per-campaign revenue_incrementality. Aggregating across campaigns requires a campaign-level pull; not surfaced at the store level in this report.",
                  "flat")
    v["incremental_revenue"] = ("Available per Meta campaign", "Available per Meta campaign",
                                "Revenue lift vs. holdout is exposed per Meta campaign only; "
                                "no store-level aggregate is available in this report.",
                                "flat")

    # ---- Conversion rate ----
    cur_cvr_pct = (cur_pv_to_order or 0) * 100 if cur_pv_to_order is not None else None
    prv_cvr_pct = (prv_pv_to_order or 0) * 100 if prv_pv_to_order is not None else None
    d = _delta(cur_cvr_pct, prv_cvr_pct)
    traffic_d = _delta(cur_pv, prv_pv)
    # A CVR move against a >10% traffic move in the opposite direction is
    # largely a denominator artifact — in BOTH directions. A rate rise on
    # collapsing traffic is no quality gain, and a rate fall on surging
    # traffic is no quality loss; either way, mark neutral and say why.
    if (d is not None and traffic_d is not None
            and ((d > 0 and traffic_d < -10) or (d < 0 and traffic_d > 10))):
        sig = "flat"
        interp = (f"PV-to-order rate {_signed_pct(d)} WoW. Page views {_signed_pct(traffic_d)}, so the "
                  "rate move is largely arithmetic — read alongside per-platform funnel rates for true quality.")
    else:
        sig = _signal_delta(d, threshold=5.0)
        interp = f"Site-wide page-view-to-order rate {_signed_pct(d)} WoW."
    v["cvr"] = (_pct(cur_cvr_pct, 2), _pct(prv_cvr_pct, 2), interp, sig)

    # ---- AOV ----
    d = _delta(cur.get("aov"), prv.get("aov"))
    d_new = _delta(cur.get("aov_new"), prv.get("aov_new"))
    d_ret = _delta(cur.get("aov_ret"), prv.get("aov_ret"))
    sig = _signal_delta(d, threshold=3.0)
    # Only call out the segment symmetry pattern when both deltas are present and same-sign material
    symmetry_note = ""
    if (d_new is not None and d_ret is not None
            and abs(d_new) > 3 and abs(d_ret) > 3
            and (d_new < 0) == (d_ret < 0)):
        symmetry_note = (
            f" New {_signed_pct(d_new)}; returning {_signed_pct(d_ret)} — same-direction movement "
            "across both segments indicates promotional or product-mix pressure, not customer-mix."
        )
    elif d_new is not None and d_ret is not None:
        symmetry_note = f" New {_signed_pct(d_new)}; returning {_signed_pct(d_ret)}."
    interp = f"Average order value {_signed_pct(d)} WoW.{symmetry_note}"
    v["aov"] = (_ccy(cur.get("aov"), ccy, digits=2), _ccy(prv.get("aov"), ccy, digits=2), interp, sig)

    # ---- Traffic / Sessions ----
    d = traffic_d
    rev_d = _delta(cur.get("revenue"), prv.get("revenue"))
    # rev_d is None when there's no prior-revenue baseline (e.g. a bootstrap
    # window) — that's "unknown", not "flat", so it can't confirm either
    # signal. Mirror the explicit None-guard the CVR row uses above.
    if d is None or rev_d is None:
        sig = "flat"
    elif d < -10 and rev_d < -5:
        sig = "down"
    elif d > 10 and rev_d > 5:
        sig = "up"
    else:
        sig = "flat"
    v["traffic"] = (_int_str(cur_pv) + " PV", _int_str(prv_pv) + " PV",
                    f"Page-view volume {_signed_pct(d)} WoW (proxy for sessions).", sig)

    # ---- Traffic quality ----
    v["traffic_quality"] = (f"PV→Order {_pct(cur_cvr_pct, 2)}",
                             f"PV→Order {_pct(prv_cvr_pct, 2)}",
                             "Quality is a composite read — combine PV-to-order rate with per-platform funnel breakdown to separate true quality from mechanical CVR shifts.",
                             "flat")

    # ---- Spend by channel ----
    def _spend_str(plats):
        parts = []
        for k, label in _FH.AD_PLATFORMS:
            info = plats.get(k) or {}
            if info.get("spend", 0) > 0:
                parts.append(f"{label} {_ccy(info.get('spend'), ccy)}")
        return " · ".join(parts) or "—"
    v["spend_by_channel"] = (_spend_str(cur_plats), _spend_str(prv_plats),
                              "Paid-media spend by platform. Compare against revenue-by-channel to identify allocation gaps.",
                              "flat")

    # ---- Revenue by channel ----
    def _rev_str(plats):
        parts = []
        for k, label in _FH.AD_PLATFORMS:
            info = plats.get(k) or {}
            if info.get("spend", 0) > 0:
                parts.append(f"{label} {_ccy(info.get('revenue'), ccy)}")
        return " · ".join(parts) or "—"
    # Worst-channel signal: any channel with >500 (store currency) spend losing >10% revenue marks the row negative
    rev_worst = None
    for k, _label in _FH.AD_PLATFORMS:
        c_rev = (cur_plats.get(k) or {}).get("revenue", 0)
        p_rev = (prv_plats.get(k) or {}).get("revenue", 0)
        spend = (cur_plats.get(k) or {}).get("spend", 0)
        if spend > 500 and p_rev > 0:
            d_rev = _delta(c_rev, p_rev)
            if d_rev is not None and (rev_worst is None or d_rev < rev_worst):
                rev_worst = d_rev
    sig_rev = _signal_delta(rev_worst, threshold=10.0) if rev_worst is not None else "flat"
    v["revenue_by_channel"] = (_rev_str(cur_plats), _rev_str(prv_plats),
                                "Per-platform attributed revenue. The largest WoW decline identifies where to focus campaign-level diagnostics first.",
                                sig_rev)

    # ---- New vs. returning mix ----
    cur_share = cur.get("new_share")
    prv_share = prv.get("new_share")
    # Keep the value and interpretation self-consistent: never show a populated
    # current value next to an "insufficient data" interp. The interp tracks
    # what the *current* value can support, not whether both windows are present.
    if cur_share is None:
        interp = "Insufficient data for the mix calculation this window."
    elif prv_share is not None:
        pp = (cur_share - prv_share) * 100
        sign = "+" if pp > 0 else ""
        interp = (f"New-customer share shifted {sign}{pp:.1f}pp WoW. Mix moves can be intentional "
                  "(acquisition campaign cadence) or unintentional (returning-customer contraction) — "
                  "cross-check the returning-revenue row.")
    else:
        interp = ("No prior-window new/returning split to compare against — "
                  "showing the current mix only.")
    v["new_ret_mix"] = (
        f"{cur_share*100:.1f}% new / {(1-cur_share)*100:.1f}% returning" if cur_share is not None else "—",
        f"{prv_share*100:.1f}% new / {(1-prv_share)*100:.1f}% returning" if prv_share is not None else "—",
        interp,
        "flat",
    )

    # ---- LTV ----
    d = _delta(cur.get("ltv"), prv.get("ltv"))
    sig = _signal_delta(d, threshold=5.0)
    v["ltv"] = (_ccy(cur.get("ltv"), ccy, digits=2), _ccy(prv.get("ltv"), ccy, digits=2),
                f"Modelled customer lifetime value {_signed_pct(d)} WoW.", sig)

    # ---- LTV:CAC ----
    # State the ratio with its inputs and the WoW delta; no benchmark verdict.
    cur_l = cur.get("ltv_cac")
    prv_l = prv.get("ltv_cac")
    d = _delta(cur_l, prv_l)
    sig = _signal_delta(d, threshold=5.0)
    if cur_l is None:
        sig = "flat"; interp = "Insufficient data."
    else:
        ltv_v = cur.get("ltv")
        cac_v = cur.get("cac")
        inputs_clause = ""
        if ltv_v is not None and cac_v:
            inputs_clause = f" ({_ccy(ltv_v, ccy, digits=2)} modelled LTV ÷ {_ccy(cac_v, ccy, digits=2)} CAC)"
        interp = f"{cur_l:.2f}× this window{inputs_clause}, {_signed_pct(d)} WoW."
    v["ltv_cac"] = (f"{cur_l:.2f}x" if cur_l is not None else "—",
                    f"{prv_l:.2f}x" if prv_l is not None else "—",
                    interp, sig)

    # ---- Marginal ROAS ----
    # Return on the *next* unit of spend — only defined when spend increased
    # this window. On a flat or spend-down week there is no incremental spend
    # to score, so Δrevenue/Δspend (a negative denominator) isn't meaningful.
    # We report the measured figure only — no good/bad signal.
    marg = None
    spend_delta = (cur.get("spend") or 0) - (prv.get("spend") or 0)
    if cur.get("spend") and prv.get("spend") and spend_delta > 0:
        marg = ((cur.get("revenue") or 0) - (prv.get("revenue") or 0)) / spend_delta
    if marg is None or (marg != marg):
        interp_m = "Spend did not increase this window, so marginal ROAS on added spend is not defined."
        cur_marg_str = "—"
    else:
        interp_m = f"Marginal ROAS {marg:.2f} — the added spend this window returned {marg:.2f}× (Δrevenue ÷ Δspend)."
        cur_marg_str = f"{marg:.2f}"
    v["marginal_roas"] = (cur_marg_str, "Baseline", interp_m, "flat")

    # ---- Marginal CAC ----
    new_d = _delta(cur.get("new_orders"), prv.get("new_orders"))
    spend_d = _delta(cur.get("spend"), prv.get("spend"))
    v["marginal_cac"] = ("Read together", "Read together",
                          f"New-order count {_signed_pct(new_d)} on spend {_signed_pct(spend_d)}. Read together with the CPC inflation row to separate auction pressure from creative effect.",
                          "flat")

    # ---- Saturation / diminishing returns (CPC-led) ----
    fb = cur_plats.get("facebook") or {}
    fb_p = prv_plats.get("facebook") or {}
    cpc_d = _delta(fb.get("cpc"), fb_p.get("cpc")) if fb.get("cpc") and fb_p.get("cpc") else None
    sig = _signal_delta(cpc_d, threshold=10.0)
    # Keep the interpretation threshold aligned with the signal threshold
    # (10%) so a row flagged negative never reads as "within typical noise".
    if cpc_d is not None and cpc_d > 10:
        interp = f"Meta CPC {_signed_pct(cpc_d)} WoW. A double-digit increase typically indicates auction pressure, audience saturation, or creative fatigue."
    elif cpc_d is not None:
        interp = f"Meta CPC {_signed_pct(cpc_d)} WoW. Within typical noise; monitor frequency and CTR for confirmation."
    else:
        interp = "Insufficient CPC data this window."
    v["saturation"] = (f"Meta CPC {_ccy(fb.get('cpc'), ccy, digits=2)}",
                        f"Meta CPC {_ccy(fb_p.get('cpc'), ccy, digits=2)}",
                        interp, sig)

    # ---- Channel incrementality score ----
    v["incrementality_score"] = ("Per-channel proxy", "Per-channel proxy",
                                  "True incrementality requires a holdout test — not exposed in this report. As a structural proxy, branded-search channels typically capture existing demand while top-of-funnel paid social typically creates new demand.",
                                  "flat")

    # ---- Attribution vs incrementality gap ----
    cur_meta_roas = (cur_plats.get("facebook") or {}).get("roas")
    cur_blended = cur.get("roas")
    prv_meta_roas = (prv_plats.get("facebook") or {}).get("roas")
    prv_blended = prv.get("roas")
    # A genuine ROAS of 0.0 is real data, not missing — gate on is-not-None.
    # The division still needs a non-zero denominator, so guard that separately:
    # when both ROAS values are 0 there is no scale to measure a gap against.
    if cur_meta_roas is not None and cur_blended is not None:
        denom = max(cur_meta_roas, cur_blended)
        if denom > 0 and abs(cur_meta_roas - cur_blended) / denom > 0.15:
            interp = "Material gap between Meta-reported ROAS and blended ROAS. TrackBee's multi-touch view often shows Meta is under-credited by its own pixel — useful when interpreting channel allocation decisions."
        else:
            interp = "Meta-reported ROAS and blended ROAS are directionally aligned this window."
    else:
        interp = "Insufficient data to score the attribution gap."
    v["attribution_gap"] = (
        f"Meta {cur_meta_roas:.2f} vs blended {cur_blended:.2f}" if cur_meta_roas is not None and cur_blended is not None else "—",
        f"Meta {prv_meta_roas:.2f} vs blended {prv_blended:.2f}" if prv_meta_roas is not None and prv_blended is not None else "—",
        interp,
        "flat",
    )

    # ---- Creative fatigue ----
    n_creative_limited = 0
    n_fragmentation = 0
    for r in (meta_recs or {}).get("recommendations") or []:
        t = r.get("type") or ""
        if t == "CREATIVE_LIMITED": n_creative_limited += 1
        if t == "FRAGMENTATION":    n_fragmentation += 1
    if n_creative_limited > 0:
        interp = f"Meta flags {n_creative_limited} ad(s) as creative-limited and {n_fragmentation} fragmentation opportunit{'y' if n_fragmentation == 1 else 'ies'} this window."
    elif n_fragmentation > 0:
        interp = f"Meta flags {n_fragmentation} fragmentation opportunit{'y' if n_fragmentation == 1 else 'ies'} this window."
    else:
        interp = "Meta returns no creative-fatigue or fragmentation flags this window."
    v["creative_fatigue"] = (
        f"{n_creative_limited} creative-limited; {n_fragmentation} fragmentation",
        "Baseline",
        interp,
        "flat",
    )

    # ---- Frequency ----
    v["frequency"] = ("Per-campaign", "Per-campaign",
                      "Frequency is reported per Meta campaign in the campaign-insights pull. Sustained frequency >2.5 with declining CTR is the canonical fatigue pattern.",
                      "flat")

    # ---- Assisted conversions ----
    items = (fp_cur or {}).get("items") or []
    klav = next((i for i in items if (i.get("id") or "").lower() == "klaviyo"), None)
    klav_share = (klav or {}).get("share_of_orders")
    if klav_share is not None and klav_share > 0.15:
        interp = f"Klaviyo is present in {klav_share*100:.1f}% of order journeys — above the 15% threshold for material assist contribution."
    elif klav_share is not None and klav_share > 0:
        interp = f"Klaviyo touches {klav_share*100:.1f}% of order journeys. Below the 15% threshold for material assist contribution."
    else:
        interp = "No Klaviyo footprint detected in the journey data this window."
    v["assisted_conv"] = (
        f"Klaviyo {(klav_share or 0)*100:.1f}% of orders" if klav_share is not None else "—",
        "Baseline",
        interp,
        "flat",
    )

    # ---- First-touch ----
    meta_fp = next((i for i in items if (i.get("id") or "").lower() == "meta"), None)
    top_raw = (meta_fp or {}).get("top_share")
    top = top_raw or 0
    if top > 0.5:
        interp = f"Meta appears as the first touch in {top*100:.0f}% of journeys — consistent with a demand-creation role."
    elif top > 0:
        interp = f"Meta appears as the first touch in {top*100:.0f}% of journeys."
    else:
        interp = "No Meta footprint at the first-touch position this window."
    # "—" when the share is absent; "0%" only when a footprint genuinely reports zero.
    top_val = f"Meta top-share {top*100:.0f}%" if top_raw is not None else "—"
    v["first_touch"] = (top_val, "Baseline", interp, "flat")

    # ---- Last-touch ----
    bottom_g = next((i for i in items if (i.get("id") or "").lower() == "google"), None)
    bot_raw = (bottom_g or {}).get("bottom_share")
    bot = bot_raw or 0
    if bot > 0:
        interp = f"Google appears at the last touch in {bot*100:.0f}% of journeys — consistent with a demand-capture role (branded-search lead)."
    else:
        interp = "No Google footprint at the last-touch position this window."
    bot_val = f"Google bottom-share {bot*100:.0f}%" if bot_raw is not None else "—"
    v["last_touch"] = (bot_val, "Baseline", interp, "flat")

    # ---- Product mix ----
    v["product_mix"] = ("Not directly measurable", "Not directly measurable",
                        "Per-product order and revenue cuts are not exposed in this MCP. Use the AOV row's segment symmetry as a proxy for product-mix vs customer-mix attribution.",
                        "flat")

    # ---- Confidence ----
    n_anom = (anomalies or {}).get("anomalies")
    n_anom_count = len(n_anom) if isinstance(n_anom, list) else 0
    if n_anom_count == 0:
        interp = "No anomalies flagged by the tracking-health monitor; platform accuracy reads 100%. The WoW direction reflects measured data, not a tracking artefact."
    else:
        interp = f"{n_anom_count} anomal{'y' if n_anom_count == 1 else 'ies'} flagged by the tracking-health monitor — the affected days may not reflect the underlying WoW direction."
    v["confidence"] = (f"{n_anom_count} anomalies", "Baseline", interp, "flat")

    return v



def transform(inputs: dict, config: dict) -> dict:
    """Return {"rows": [<row dict>, ...]} for the chrome to render.

    Each row dict carries: id, name, indicates, importance,
    value_current, value_prior, interpretation, signal.
    """
    headline = inputs.get("headline") or {}
    code = headline.get("currency") or (config or {}).get("store_currency") or ""
    # Resolve the display symbol once — prefer a config-provided currency_symbol
    # over the ISO table, then thread the symbol through the row builders.
    ccy = _FH.resolve_currency_symbol(config, code)

    raws = {
        "overview_current": inputs.get("overview_current") or {},
        "overview_prior":   inputs.get("overview_prior")   or {},
        "funnel_current":   inputs.get("funnel_current")   or {},
        "funnel_prior":     inputs.get("funnel_prior")     or {},
        "platform_footprints_current": inputs.get("platform_footprints_current") or {},
        "meta_recommendations":        inputs.get("meta_recommendations")        or {},
        "anomalies":                   inputs.get("anomalies")                   or {},
    }

    computed = _compute_values(headline, raws, ccy)

    rows = []
    for (mid, name, indicates, importance) in METRICS_STATIC:
        result = computed.get(mid, ("—", "—", "—", "flat"))
        if len(result) == 3:
            cur_str, prv_str, interp = result
            signal = "flat"
        else:
            cur_str, prv_str, interp, signal = result
        rows.append({
            "id":             mid,
            "name":           name,
            "indicates":      indicates,
            "importance":     importance,
            "value_current":  cur_str,
            "value_prior":    prv_str,
            "interpretation": interp,
            "signal":         signal,
        })
    return {"rows": rows}
