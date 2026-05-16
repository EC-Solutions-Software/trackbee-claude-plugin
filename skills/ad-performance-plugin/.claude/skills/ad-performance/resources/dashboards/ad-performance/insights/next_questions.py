"""Generate up to 3 data-driven follow-up questions for a store.

Each item is `{"q": <question html>, "why": <rationale html>}`. The views
layer wraps these into Q-cards with a copy-to-clipboard button.

Thresholds for "high frequency", "underperforming spender" and "scaling
lane" come from `thresholds` — no magic numbers in this module.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from transforms import _fmt as f  # noqa: E402


def _google_roas(c: dict) -> float | None:
    s = f.safe_float(c.get("spend"))
    r = f.safe_float(c.get("conversions_value"))
    return (r / s) if s > 0 else None


def _q1_freq(meta_active, sym, m_fx, t):
    high_freq = [c for c in meta_active
                 if f.safe_float(c.get("frequency")) >= t["q_freq_min"]
                 and f.safe_float(c.get("spend")) > t["q_freq_min_spend"]]
    if not high_freq:
        return None
    c = sorted(high_freq, key=lambda x: -f.safe_float(x.get("spend")))[0]
    cname = f.short(c.get("campaign_name", ""), 44)
    freq = f.safe_float(c.get("frequency"))
    spend = f.safe_float(c.get("spend")) * m_fx
    roas = f.safe_float(c.get("purchase_roas"))
    return {
        "q":  (f"Which ad inside {cname} is driving frequency to {freq:.1f}× "
               f"— and is it still carrying ROAS, or coasting on past performance?"),
        "why": (f"Frequency {freq:.1f} on {sym}{spend:,.0f} of spend at "
                f"{roas:.2f}× ROAS. Ad-level fatigue typically surfaces several days "
                f"before campaign ROAS drops. Review retention and CTR at the ad level "
                f"to identify which creative to refresh."),
    }


def _q2_underperformer(meta_active, goog_active, sym, m_fx, g_fx, t):
    pool = []
    for c in meta_active:
        r = f.safe_float(c.get("purchase_roas"))
        if (f.safe_float(c.get("spend")) > t["q_underp_min_spend"]
                and 0 < r < t["q_underp_max_roas"]):
            pool.append((c, r, True))
    for c in goog_active:
        r = _google_roas(c) or 0
        if f.safe_float(c.get("spend")) > t["q_underp_min_spend"] and 0 < r < t["q_underp_max_roas"]:
            pool.append((c, r, False))
    if not pool:
        return None
    c, roas, is_meta = sorted(pool, key=lambda x: -f.safe_float(x[0].get("spend")))[0]
    cname = f.short(c.get("campaign_name", ""), 44)
    fx = m_fx if is_meta else g_fx
    spend = f.safe_float(c.get("spend")) * fx
    plat = "Meta" if is_meta else "Google"
    return {
        "q":  (f"Is the {roas:.2f}× ROAS on {cname} a creative, audience, "
               f"or landing-page issue?"),
        "why": (f"{plat} delivered {sym}{spend:,.0f} below break-even. Before pausing, "
                f"isolate the cause: CTR signals creative, frequency signals audience, "
                f"and ATC-to-purchase rate signals landing page or checkout."),
    }


def _q3_scaling(meta_active, goog_active, sym, m_fx, g_fx, t):
    scaling = []
    for c in meta_active:
        r = f.safe_float(c.get("purchase_roas"))
        fq = f.safe_float(c.get("frequency"))
        s = f.safe_float(c.get("spend"))
        if r >= t["q_meta_scale_roas"] and (fq == 0 or fq < t["q_meta_scale_max_freq"]) and s > t["q_scale_min_spend"]:
            scaling.append((c, r, s, "Meta"))
    for c in goog_active:
        r = _google_roas(c) or 0
        s = f.safe_float(c.get("spend"))
        if r >= t["q_google_scale_roas"] and s > t["q_scale_min_spend"]:
            scaling.append((c, r, s, "Google"))
    if not scaling:
        return None
    c, r, s, plat = sorted(scaling, key=lambda x: -x[1])[0]
    fx = m_fx if plat == "Meta" else g_fx
    cname = f.short(c.get("campaign_name", ""), 44)
    return {
        "q":  f"How far can {cname} scale before efficiency degrades?",
        "why": (f"This {plat} campaign holds {r:.2f}× ROAS on {sym}{s*fx:,.0f} of spend. "
                f"Increase daily budget 20–30%, then monitor CPM, frequency, and "
                f"new-customer share over 48 hours before scaling further."),
    }


def _q4_new_vs_returning(meta_active):
    nc_total = sum(int(c.get("new_customer_purchases") or 0)
                   for c in meta_active if c.get("new_customer_purchases"))
    purch_total = sum(int(c.get("purchases") or 0) for c in meta_active)
    if purch_total <= 0:
        return None
    ratio = nc_total / purch_total if purch_total else 0
    return {
        "q":  "What share of revenue this week came from new customers, "
              "and which campaigns drove the acquisition?",
        "why": (f"{nc_total:,} of {purch_total:,} Meta purchases ({ratio*100:.0f}%) "
                f"flagged as new-customer this window. Separating new-customer ROAS "
                f"from blended ROAS clarifies whether growth is coming from acquisition "
                f"or from retargeting existing buyers."),
    }


def questions(meta_campaigns: list[dict], goog_campaigns: list[dict],
              symbol: str, m_fx: float, g_fx: float, thresholds: dict
              ) -> list[dict]:
    meta_active = [c for c in meta_campaigns if f.safe_float(c.get("spend")) > 0]
    goog_active = [c for c in goog_campaigns if f.safe_float(c.get("spend")) > 0]
    out: list[dict] = []
    for q in (_q1_freq(meta_active, symbol, m_fx, thresholds),
              _q2_underperformer(meta_active, goog_active, symbol, m_fx, g_fx, thresholds),
              _q3_scaling(meta_active, goog_active, symbol, m_fx, g_fx, thresholds)):
        if q:
            out.append(q)
    if len(out) < 2:
        q4 = _q4_new_vs_returning(meta_active)
        if q4:
            out.append(q4)
    return out[:3]
