"""Top movers — the 2-3 campaigns that changed most since the day before.

Reads Meta (get_meta_campaign_insights) and Google (get_google_campaign_insights)
campaign data for yesterday vs the day before. Movers are ranked by the size of
their day-over-day **spend** swing — the clearest "what changed in the account
overnight" signal — and each mover also surfaces its current ROAS and the ROAS
swing, so a campaign that quietly halved its return shows it.

Spend and revenue from these tools are in **units** of the ad-account currency
(NOT cents). They're converted to store currency via the optional per-platform
``fx_to_store`` multiplier so a single card reads in one currency. ROAS is a
unitless ratio and is unaffected by FX.

Meta reports ROAS directly as ``purchase_roas``; Google reports
``conversions_value`` and ``spend`` from which ROAS is derived.
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

_LIST_KEYS = ("campaigns", "rows", "data", "results", "items")
_ID_KEYS = ("campaign_id", "id", "campaignId")
_NAME_KEYS = ("campaign_name", "name", "campaignName")
_SPEND_KEYS = ("spend", "cost", "amount_spent")
_ROAS_KEYS = ("purchase_roas", "roas", "return_on_ad_spend")
_REVENUE_KEYS = ("conversions_value", "all_conversions_value", "revenue",
                 "revenue_7d_click", "purchase_revenue")

_PLATFORM_LABEL = {
    "facebook": "Meta", "meta": "Meta", "google": "Google",
    "tiktok": "TikTok", "pinterest": "Pinterest",
}


def _rows(payload):
    if not isinstance(payload, dict):
        return []
    for k in _LIST_KEYS:
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []


def _first(d, keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _roas_of(row, spend):
    """ROAS for one campaign row. Prefer an explicit ROAS field (Meta's
    purchase_roas, which may arrive as a number or a [{value}] list); otherwise
    derive revenue / spend (Google). For Google, conversions_value is the strict
    direct value and is often 0 on Performance Max / Demand Gen campaigns that
    report under all_conversions_value instead — so take the first *positive*
    revenue field rather than the first present one."""
    raw = _first(row, _ROAS_KEYS)
    if isinstance(raw, list) and raw:
        first = raw[0]
        raw = first.get("value") if isinstance(first, dict) else first
    val = _FH.safe_float(raw)
    if val is not None and val > 0:
        return val
    rev = None
    for k in _REVENUE_KEYS:
        v = _FH.safe_float(row.get(k))
        if v is not None and v > 0:
            rev = v
            break
    if rev is not None and spend:
        return rev / spend
    return None


def _index(payload):
    """campaign key -> {name, spend_units, roas} for one window."""
    out = {}
    for r in _rows(payload):
        if not isinstance(r, dict):
            continue
        cid = _first(r, _ID_KEYS)
        name = _first(r, _NAME_KEYS) or (str(cid) if cid is not None else "Unnamed campaign")
        key = str(cid) if cid is not None else name
        spend = _FH.safe_float(_first(r, _SPEND_KEYS)) or 0.0   # units, ad-acct ccy
        out[key] = {"name": name, "spend": spend, "roas": _roas_of(r, spend)}
    return out


def build(summary, fx_map, limit=5):
    ccy = summary.get("currency") or ""
    campaigns = summary.get("campaigns") or {}
    fx_map = fx_map or {}

    candidates = []
    for platform, windows in campaigns.items():
        if not isinstance(windows, dict):
            continue
        fx = _FH.safe_float(fx_map.get(platform), 1.0) or 1.0
        cur = _index(windows.get("yday"))
        prev = _index(windows.get("prev"))
        for key in set(cur) | set(prev):
            c = cur.get(key) or {}
            p = prev.get(key) or {}
            now_spend = (c.get("spend") or 0.0) * fx          # store units
            prev_spend = (p.get("spend") or 0.0) * fx
            # Ignore campaigns that were and stayed effectively dark.
            if now_spend < 1 and prev_spend < 1:
                continue
            spend_delta = _FH.pct_change(now_spend, prev_spend)
            roas_now = c.get("roas")
            roas_prev = p.get("roas")
            roas_delta = _FH.pct_change(roas_now, roas_prev)

            # Platform subtitle carries the current ROAS + its swing.
            sub = _PLATFORM_LABEL.get(platform, platform.title())
            if roas_now is not None:
                sub += f" · ROAS {roas_now:.2f}"
                if roas_delta is not None and abs(roas_delta) >= 2:
                    sub += f" ({_FH.signed_pct(roas_delta)})"

            candidates.append({
                "name":      c.get("name") or p.get("name") or "Unnamed campaign",
                "platform":  sub,
                "now_str":   _FH.compact_money(now_spend, ccy) + " spend",
                "delta_str": ("new" if prev_spend < 1 else
                              "paused" if now_spend < 1 else
                              _FH.signed_pct(spend_delta)),
                # Spend going up isn't inherently good/bad — keep the spend delta
                # neutral in color; the ROAS swing in the subtitle carries quality.
                "delta_class": "delta-flat",
                "_mag":      abs(now_spend - prev_spend),
            })

    candidates.sort(key=lambda m: m["_mag"], reverse=True)
    movers = candidates[:limit]
    for m in movers:
        m.pop("_mag", None)
    return movers
