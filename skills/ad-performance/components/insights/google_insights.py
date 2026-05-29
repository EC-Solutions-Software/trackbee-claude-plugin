"""Google key insights + recommendations.

Mirrors `meta_insights.build` for Google's API surface. Surfaces campaign
mix, top revenue driver, brand-cannibalization warnings, non-branded
search efficiency, and scale / review recommendations.
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


_fh = _load("format_helpers", _CHROME / "format_helpers.py")
_t = _load("thresholds", _HERE / "thresholds.py")


def build(campaigns: list[dict], sym: str, g_fx: float) -> tuple[list[str], list[str]]:
    active = [c for c in campaigns if _fh.safe_float(c.get("spend")) > 0]
    if not active:
        return ["No spending Google campaigns in this window."], []

    insights: list[str] = []
    recs: list[str] = []

    pmax = [c for c in active if c.get("campaign_type") == "PERFORMANCE_MAX"]
    search = [c for c in active if c.get("campaign_type") == "SEARCH"]
    shop = [c for c in active if c.get("campaign_type") == "SHOPPING"]

    parts: list[str] = []
    if pmax:
        parts.append(f"{len(pmax)} PMAX")
    if search:
        parts.append(f"{len(search)} Search")
    if shop:
        parts.append(f"{len(shop)} Shopping")
    if parts:
        insights.append(f"Campaign mix: {', '.join(parts)}.")

    # Best revenue contributor (in native ad-account currency before FX).
    conv_list = [
        (c, _fh.safe_float(c.get("conversions_value")))
        for c in active
        if _fh.safe_float(c.get("conversions_value")) > 0
    ]
    if conv_list:
        best_c, best_rev = max(conv_list, key=lambda x: x[1])
        best_roas = _fh.google_roas(best_c)
        revenue_str = _fh.money(best_rev * g_fx, sym)
        name = _fh.text(_fh.short(best_c["campaign_name"], 44))
        if best_roas:
            insights.append(
                f"Top revenue driver: <strong>{name}</strong> — "
                f"{revenue_str} at {best_roas:.1f}× ROAS."
            )
        else:
            insights.append(
                f"Top revenue driver: <strong>{name}</strong> — {revenue_str}."
            )

    # Brand cannibalisation flags (Search campaigns only).
    canni = [
        c for c in search
        if (c.get("branded_search_analysis") or {}).get("cannibalization_risk") == "high"
    ]
    for c in canni[:2]:
        bsa = c.get("branded_search_analysis", {})
        branded_pct = _fh.safe_float(bsa.get("branded_spend_share", 0)) * 100
        insights.append(
            f"High brand cannibalization: "
            f"<strong>{_fh.text(_fh.short(c['campaign_name'], 40))}</strong> "
            f"— {branded_pct:.0f}% of spend on branded terms. Add negative keywords."
        )

    # Non-branded search efficiency.
    nb = [
        c for c in search
        if (c.get("branded_search_analysis") or {}).get("cannibalization_risk") == "low"
        and _fh.safe_float(c.get("spend")) > 0
    ]
    if nb:
        nb_spend = sum(_fh.safe_float(c.get("spend")) for c in nb)
        nb_conv = sum(_fh.safe_float(c.get("conversions")) for c in nb)
        if nb_conv > 0:
            nb_cpa = (nb_spend / nb_conv) * g_fx
            insights.append(
                f"Non-branded search average CPA: {_fh.money(nb_cpa, sym)} "
                f"across {len(nb)} campaign(s)."
            )

    # Scale and review recommendations.
    for c in active:
        roas = _fh.google_roas(c)
        spend = _fh.safe_float(c.get("spend"))
        name = _fh.text(_fh.short(c["campaign_name"], 44))
        if roas and roas >= _t.ROAS_GOOGLE_SCALE and spend > _t.SPEND_FLOOR_BADGE:
            recs.append(
                f"<strong>Scale:</strong> {name} — {roas:.1f}× ROAS. "
                "Strong efficiency. Increase budget 20–40%."
            )
        elif roas and roas < 1.0 and spend > _t.SPEND_FLOOR_PAUSE:
            recs.append(
                f"<strong>Review:</strong> {name} — {roas:.2f}× ROAS "
                f"(below break-even) on {_fh.money(spend * g_fx, sym)}. "
                "Audit conversion tracking and bid strategy."
            )

    if not recs:
        recs.append("All spending Google campaigns are within healthy ranges.")

    return insights, recs
