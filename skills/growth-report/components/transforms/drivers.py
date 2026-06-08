"""Build the 'What's working' and 'What's breaking' lists.

Every item in either list must cite a metric from the staged payloads.
Items are ordered by materiality — biggest absolute Δ first within each list.

Each item is shaped:
  { "title": "<short headline>",
    "why":   "<one-sentence explanation grounded in numbers>" }
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

# Shared formatters — canonical copies live in chrome/format_helpers.py.
_pct_delta = _FH.pct_delta
_signed    = _FH.signed_pct
_ccy       = _FH.ccy

# ---- Signal gates ------------------------------------------------------------
# WoW % thresholds and store-currency spend gates for the working / breaking
# panels. Documented in references/dashboard-spec.md §Driver signal gates —
# keep the two in sync.
GROWTH_MIN_PCT       = 5      # new-orders / MER / LTV improvement
ROAS_GAIN_MIN_PCT    = 10     # per-platform ROAS improvement
ROAS_GAIN_MIN_SPEND  = 100    # spend gate for the ROAS-gain signal
KLAVIYO_MIN_SHARE    = 0.10   # footprint share for the email-assist signal
REVENUE_DROP_PCT     = -5
RET_REVENUE_DROP_PCT = -10
AOV_DROP_PCT         = -5     # must hit both customer segments
CPC_RISE_MIN_PCT     = 20
CPC_MIN_SPEND        = 500
ROAS_DROP_PCT        = -15
ROAS_DROP_MIN_SPEND  = 500
LTV_CAC_FLOOR        = 2.0


def _platform_stats(overview):
    out = {}
    for row in ((overview or {}).get("overview") or {}).get("platform_statistics") or []:
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


def _mer_move(prv_mer, cur_mer):
    """MER move sentence, only when both windows actually have a MER.

    MER is None for any window with no/zero ad spend — formatting None with
    ``:.2f`` would raise TypeError and crash the whole report build. Returns
    an empty string (leading space included when present) when either side
    is missing.
    """
    if prv_mer is None or cur_mer is None:
        return ""
    return f" MER moved from {prv_mer:.2f} to {cur_mer:.2f}."


def transform(inputs: dict, config: dict) -> dict:
    headline = inputs.get("headline") or {}
    cur = headline.get("current") or {}
    prv = headline.get("prior") or {}
    # Resolve the display symbol once — prefer a config-provided currency_symbol
    # over the ISO table, then thread the symbol through the driver sentences.
    code = headline.get("currency") or (config or {}).get("store_currency") or ""
    ccy = _FH.resolve_currency_symbol(config, code)

    cur_ov_raw = inputs.get("overview_current") or {}
    prv_ov_raw = inputs.get("overview_prior")   or {}
    fp_cur     = inputs.get("platform_footprints_current") or {}

    cur_plats = _platform_stats(cur_ov_raw)
    prv_plats = _platform_stats(prv_ov_raw)

    working = []
    breaking = []

    # ---- POSITIVE SIGNALS ---------------------------------------------------

    # New-customer order growth
    d = _pct_delta(cur.get("new_orders"), prv.get("new_orders"))
    if d is not None and d > GROWTH_MIN_PCT:
        working.append({
            "title": f"New-customer order volume {_signed(d, 1)}",
            "why":   f"{int(cur.get('new_orders') or 0):,} new-customer orders this window "
                     f"vs {int(prv.get('new_orders') or 0):,} prior. Acquisition volume is expanding "
                     "regardless of revenue direction.",
        })

    # MER improvement
    d = _pct_delta(cur.get("mer"), prv.get("mer"))
    if d is not None and d > GROWTH_MIN_PCT and cur.get("mer") is not None:
        working.append({
            "title": f"MER improved {_signed(d, 1)} ({prv.get('mer'):.2f} → {cur.get('mer'):.2f})",
            "why":   "Marketing efficiency ratio is increasing — paid media is producing more revenue per "
                     "unit of spend than the prior window.",
        })

    # Channels with materially improved ROAS
    for name, label in _FH.AD_PLATFORMS:
        c_info = cur_plats.get(name) or {}
        p_info = prv_plats.get(name) or {}
        c_roas = c_info.get("roas")
        p_roas = p_info.get("roas")
        d = _pct_delta(c_roas, p_roas)
        if d is not None and d > ROAS_GAIN_MIN_PCT and c_info.get("spend", 0) >= ROAS_GAIN_MIN_SPEND:
            working.append({
                "title": f"{label} platform ROAS {_signed(d, 0)} ({p_roas:.2f} → {c_roas:.2f})",
                "why":   f"Reported on {_ccy(c_info.get('spend'), ccy)} of spend. Test incremental "
                         f"budget if the improvement is sustained across multiple windows.",
            })

    # LTV improvement
    d = _pct_delta(cur.get("ltv"), prv.get("ltv"))
    if d is not None and d > GROWTH_MIN_PCT:
        working.append({
            "title": f"LTV {_signed(d, 1)} ({_ccy(prv.get('ltv'), ccy)} → {_ccy(cur.get('ltv'), ccy)})",
            "why":   "Modelled customer lifetime value is increasing — supports continued paid acquisition reinvestment.",
        })

    # Cross-channel assist signal — only when grounded in footprint share
    items = (fp_cur or {}).get("items") or []
    klav = next((i for i in items if (i.get("id") or "").lower() == "klaviyo"), None)
    klav_share = (klav or {}).get("share_of_orders") if klav else None
    if klav_share is not None and klav_share > KLAVIYO_MIN_SHARE:
        working.append({
            "title": f"Klaviyo present in {klav_share*100:.1f}% of order journeys",
            "why":   "Email is materially represented in the multi-touch path. Sustaining Klaviyo flow "
                     "activity protects retention revenue against paid auction pressure.",
        })

    # ---- NEGATIVE SIGNALS ---------------------------------------------------

    # Revenue down
    d = _pct_delta(cur.get("revenue"), prv.get("revenue"))
    if d is not None and d < REVENUE_DROP_PCT:
        spend_d = _pct_delta(cur.get("spend"), prv.get("spend"))
        spend_context = (
            "on roughly flat spend" if spend_d is not None and abs(spend_d) < 5
            else (f"on spend {_signed(spend_d, 1)}" if spend_d is not None else "")
        )
        breaking.append({
            "title": f"Revenue {_signed(d, 1)} WoW",
            "why":   f"{_ccy(cur.get('revenue'), ccy)} this window vs {_ccy(prv.get('revenue'), ccy)} prior "
                     f"{spend_context}.{_mer_move(prv.get('mer'), cur.get('mer'))}",
        })

    # Returning revenue
    d = _pct_delta(cur.get("ret_revenue"), prv.get("ret_revenue"))
    if d is not None and d < RET_REVENUE_DROP_PCT:
        rev_drop = (prv.get("revenue") or 0) - (cur.get("revenue") or 0)
        ret_drop = (prv.get("ret_revenue") or 0) - (cur.get("ret_revenue") or 0)
        share_str = ""
        if rev_drop > 0 and ret_drop > 0:
            share_str = f" — {ret_drop / rev_drop * 100:.0f}% of the total revenue shortfall"
        breaking.append({
            "title": f"Returning-customer revenue {_signed(d, 1)}",
            "why":   f"{_ccy(cur.get('ret_revenue'), ccy)} vs {_ccy(prv.get('ret_revenue'), ccy)} prior{share_str}. "
                     "Retention activity should be the first diagnostic — Klaviyo flows, recent campaign send schedule, "
                     "and any prior-week promo that may have pulled demand forward.",
        })

    # AOV decline in both segments
    d_aov_new = _pct_delta(cur.get("aov_new"), prv.get("aov_new"))
    d_aov_ret = _pct_delta(cur.get("aov_ret"), prv.get("aov_ret"))
    if (d_aov_new is not None and d_aov_new < AOV_DROP_PCT
            and d_aov_ret is not None and d_aov_ret < AOV_DROP_PCT):
        breaking.append({
            "title": f"AOV {_signed(d_aov_new, 1)} (new) and {_signed(d_aov_ret, 1)} (returning)",
            "why":   "Symmetric AOV decline across both segments points to promotional pressure or a "
                     "product-mix shift rather than a customer-composition effect. Review active offers "
                     "and the SKU-level revenue breakdown.",
        })

    # CPC inflation per channel. Intentional subset of _FH.AD_PLATFORMS:
    # only Meta and Google carry the click volume for a stable CPC read.
    for name, label in [p for p in _FH.AD_PLATFORMS if p[0] in ("facebook", "google")]:
        c_info = cur_plats.get(name) or {}
        p_info = prv_plats.get(name) or {}
        c_cpc = c_info.get("cpc")
        p_cpc = p_info.get("cpc")
        d_cpc = _pct_delta(c_cpc, p_cpc)
        if d_cpc is not None and d_cpc > CPC_RISE_MIN_PCT and c_info.get("spend", 0) >= CPC_MIN_SPEND:
            breaking.append({
                "title": f"{label} CPC {_signed(d_cpc, 0)} ({_ccy(p_cpc, ccy)} → {_ccy(c_cpc, ccy)})",
                "why":   "Cost per click is rising materially on similar spend — consistent with auction "
                         "pressure or creative fatigue. Verify against Meta's recommendations panel for the account.",
            })

    # Channels with ROAS collapse — same platform set as the improvement
    # signal above, so a channel can never gain on the way up but vanish
    # on the way down.
    for name, label in _FH.AD_PLATFORMS:
        c_info = cur_plats.get(name) or {}
        p_info = prv_plats.get(name) or {}
        c_roas = c_info.get("roas")
        p_roas = p_info.get("roas")
        d_roas = _pct_delta(c_roas, p_roas)
        spend = c_info.get("spend", 0)
        if d_roas is not None and d_roas < ROAS_DROP_PCT and spend > ROAS_DROP_MIN_SPEND:
            breaking.append({
                "title": f"{label} platform ROAS {_signed(d_roas, 0)} ({p_roas:.2f} → {c_roas:.2f})",
                "why":   f"On {_ccy(spend, ccy)} of spend. Drill into the campaign mix — non-branded "
                         "demand-generation campaigns are usually the largest driver of channel-level ROAS swings.",
            })

    # LTV:CAC warning
    ltv_cac = cur.get("ltv_cac")
    if ltv_cac is not None and ltv_cac < LTV_CAC_FLOOR:
        breaking.append({
            "title": f"LTV:CAC at {ltv_cac:.2f}× (sub-2× target)",
            "why":   "Acquisition unit economics are at or near break-even before COGS and overhead. "
                     "Any auction-cost increase or AOV softness compresses contribution further.",
        })

    return {"working": working[:6], "breaking": breaking[:6]}
