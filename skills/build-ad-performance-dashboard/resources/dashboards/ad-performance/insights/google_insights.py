"""Google ad performance insights + recommendations.

Standalone (no inter-component imports). Mirrors `meta_insights.py` but
for the Google side: brand cannibalisation, non-branded CPA,
ROAS-driven scale/pause decisions.
"""

from __future__ import annotations

import math


def _safe_float(v, d=0.0):
    try:
        f = float(v or 0)
        return f if not (math.isnan(f) or math.isinf(f)) else d
    except (TypeError, ValueError): return d


def _short(t, n=52):
    if not t: return "—"
    return t[:n] + "…" if len(t) > n else t


def _google_roas(camp: dict):
    spend = _safe_float(camp.get("spend"))
    rev = _safe_float(camp.get("conversions_value"))
    return (rev / spend) if spend > 0 else None


def insights(campaigns: list[dict], symbol: str, g_fx: float, thresholds: dict
             ) -> tuple[list[str], list[str]]:
    active = [c for c in campaigns if _safe_float(c.get("spend")) > 0]
    if not active:
        return (["No spending Google campaigns in this window."], [])

    obs: list[str] = []
    recs: list[str] = []

    pmax   = [c for c in active if c.get("campaign_type") == "PERFORMANCE_MAX"]
    search = [c for c in active if c.get("campaign_type") == "SEARCH"]
    shop   = [c for c in active if c.get("campaign_type") == "SHOPPING"]

    parts: list[str] = []
    if pmax:   parts.append(f"{len(pmax)} PMAX")
    if search: parts.append(f"{len(search)} Search")
    if shop:   parts.append(f"{len(shop)} Shopping")
    if parts:
        obs.append(f"Campaign mix: {', '.join(parts)}.")

    conv_list = [(c, _safe_float(c.get("conversions_value"))) for c in active
                 if _safe_float(c.get("conversions_value")) > 0]
    if conv_list:
        best_c, best_rev = max(conv_list, key=lambda x: x[1])
        best_roas = _google_roas(best_c)
        if best_roas is not None:
            obs.append(
                f"Top revenue driver: <strong>{_short(best_c['campaign_name'], 44)}</strong> — "
                f"{symbol}{best_rev * g_fx:,.0f} at {best_roas:.1f}× ROAS."
            )
        else:
            obs.append(
                f"Top revenue driver: <strong>{_short(best_c['campaign_name'], 44)}</strong> — "
                f"{symbol}{best_rev * g_fx:,.0f}."
            )

    cann = [c for c in search
            if (c.get("branded_search_analysis") or {}).get("cannibalization_risk") == "high"]
    for c in cann[:2]:
        bsa = c.get("branded_search_analysis", {})
        branded_pct = _safe_float(bsa.get("branded_spend_share", 0)) * 100
        obs.append(
            f"High brand cannibalization: <strong>{_short(c['campaign_name'], 40)}</strong> "
            f"— {branded_pct:.0f}% of spend on branded terms. Add negative keywords."
        )

    nb = [c for c in search
          if (c.get("branded_search_analysis") or {}).get("cannibalization_risk") == "low"
          and _safe_float(c.get("spend")) > 0]
    if nb:
        nb_spend = sum(_safe_float(c.get("spend")) for c in nb)
        nb_conv = sum(_safe_float(c.get("conversions")) for c in nb)
        if nb_conv > 0:
            nb_cpa = nb_spend / nb_conv * g_fx
            obs.append(
                f"Non-branded search average CPA: {symbol}{nb_cpa:.0f} "
                f"across {len(nb)} campaign(s)."
            )

    for c in active:
        roas = _google_roas(c)
        spend = _safe_float(c.get("spend"))
        if roas is None:
            continue
        if roas >= thresholds["google_scale_roas"] and spend > thresholds["google_scale_min_spend"]:
            recs.append(
                f"<strong>Scale:</strong> {_short(c['campaign_name'], 44)} — "
                f"{roas:.1f}× ROAS. Strong efficiency. Increase budget 20–40%."
            )
        elif roas < thresholds["google_pause_roas"] and spend > thresholds["google_pause_min_spend"]:
            recs.append(
                f"<strong>Review:</strong> {_short(c['campaign_name'], 44)} — "
                f"{roas:.2f}× ROAS (below break-even) on "
                f"{symbol}{spend * g_fx:,.0f}. "
                f"Audit conversion tracking and bid strategy."
            )

    if not recs:
        recs.append("All spending Google campaigns are within healthy ranges.")
    return obs, recs
