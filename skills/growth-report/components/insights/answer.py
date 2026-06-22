"""Build the hero answer narrative.

Everything here is sourced from the headline KPI summary and the drivers
output. We avoid asserting anything we can't back with a number on this
run, and we never prescribe an action — only describe the measured figures.

  - hero_headline: fixed question ("What is actually driving growth?")
  - answer_block:  HTML — lead-answer paragraph + "Why this is happening"
                   H2 + paragraph, all built from this run's metrics
"""

from __future__ import annotations

import html
import importlib.util
from pathlib import Path
from typing import List


_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FH = _load("format_helpers", _CHROME / "format_helpers.py")


# ----- formatters -----------------------------------------------------------
# Shared formatters — canonical copies live in chrome/format_helpers.py.

_signed_pct = _FH.signed_pct
_ccy        = _FH.ccy
_pct_delta  = _FH.pct_delta


# ----- lead-answer assembly --------------------------------------------------

def _build_lead_answer(cur: dict, prv: dict, ccy: str) -> str:
    """Lead-answer paragraph — every claim is backed by a number.

    Reports revenue Δ, MER move, ROAS move, order-count Δ, new-order Δ. Then
    names the largest negative contributor from {returning revenue, AOV} only
    when that contributor is actually present in the data this window.
    """
    # No prior window — a store onboarded <7 days ago, OR the prior overview
    # call errored / returned nothing (verified in production: a long-running
    # store's report once asserted "first reporting window" off a failed prior
    # fetch). The two cases are indistinguishable here, so don't assert
    # either — state what's missing and report the current-window levels.
    if prv.get("revenue") is None:
        lead = (
            "No prior-window data is available to compare against, so the "
            "figures below are current-window levels, not week-over-week "
            f"moves. Revenue {_ccy(cur.get('revenue'), ccy)}"
        )
        if cur.get("orders"):
            lead += f" across {int(cur['orders']):,} orders"
        if cur.get("mer") is not None:
            lead += f", at MER {cur['mer']:.2f}"
        lead += "."
        return f'<p class="lead-answer">{lead}</p>'

    rev_d  = _pct_delta(cur.get("revenue"),    prv.get("revenue"))
    ord_d  = _pct_delta(cur.get("orders"),     prv.get("orders"))
    new_d  = _pct_delta(cur.get("new_orders"), prv.get("new_orders"))
    aov_d  = _pct_delta(cur.get("aov"),        prv.get("aov"))
    ret_d  = _pct_delta(cur.get("ret_revenue"),prv.get("ret_revenue"))
    new_rev_d = _pct_delta(cur.get("new_revenue"), prv.get("new_revenue"))
    mer_cur = cur.get("mer")
    mer_prv = prv.get("mer")
    roas_cur = cur.get("roas")
    roas_prv = prv.get("roas")
    spend_d = _pct_delta(cur.get("spend"), prv.get("spend"))

    # Opener — revenue direction grounds the rest
    parts: List[str] = []
    # A real prior week with exactly €0 revenue is a valid baseline, but a
    # percentage move off zero is undefined (_pct_delta returns None), which
    # would otherwise stamp a dangling em-dash. Phrase it as a zero-baseline
    # recovery instead.
    if (prv.get("revenue") == 0) and (cur.get("revenue") or 0) > 0:
        parts.append(
            "Revenue is <strong>up from a zero-revenue prior week</strong> "
            f"({_ccy(prv.get('revenue'), ccy)} → {_ccy(cur.get('revenue'), ccy)})"
        )
    elif (prv.get("revenue") == 0) and (cur.get("revenue") or 0) == 0:
        # Dormant store: zero in both windows — a % move is undefined either way.
        parts.append(
            "Revenue is <strong>flat at zero</strong> — no revenue in either "
            f"window ({_ccy(prv.get('revenue'), ccy)} → {_ccy(cur.get('revenue'), ccy)})"
        )
    else:
        parts.append(
            f"Revenue is <strong>{_signed_pct(rev_d)}</strong> "
            f"({_ccy(prv.get('revenue'), ccy)} → {_ccy(cur.get('revenue'), ccy)})"
        )

    # Spend context — only mention if spend changed materially OR if it didn't (which is the story)
    if spend_d is not None:
        if abs(spend_d) < 5:
            parts.append("on roughly flat ad spend")
        elif spend_d > 0:
            parts.append(f"on ad spend up {_signed_pct(spend_d)}")
        else:
            parts.append(f"on ad spend down {_signed_pct(spend_d)}")

    # MER + ROAS move
    if mer_cur is not None and mer_prv is not None:
        parts.append(
            f"so MER moved from <strong>{mer_prv:.2f}</strong> to "
            f"<strong>{mer_cur:.2f}</strong>"
        )
        if roas_cur is not None and roas_prv is not None:
            parts.append(f"and blended ROAS moved from {roas_prv:.2f} to {roas_cur:.2f}")

    # Compose sentence 1
    s1 = ", ".join(parts) + "."

    # Sentence 2 — order volume vs new-order volume context
    s2_parts = []
    if ord_d is not None:
        s2_parts.append(f"Order volume {_signed_pct(ord_d)}")
    if new_d is not None:
        s2_parts.append(f"new-customer orders {_signed_pct(new_d)}")
    s2 = "; ".join(s2_parts) + "." if s2_parts else ""

    # Sentence 3 — call out the negative driver(s), ordered by severity so
    # "primarily" always names the largest contraction. Thresholds: revenue
    # contributors are named at ≥10% WoW declines, AOV at ≥5%.
    contributors: List[tuple] = []
    if ret_d is not None and ret_d < -10:
        contributors.append((ret_d, "returning-customer revenue"))
    if new_rev_d is not None and new_rev_d < -10:
        contributors.append((new_rev_d, "new-customer revenue"))
    if aov_d is not None and aov_d < -5:
        contributors.append((aov_d, "AOV"))
    contributors.sort(key=lambda c: c[0])  # most negative first
    drivers: List[str] = [label for _, label in contributors]
    s3 = ""
    if rev_d is not None and rev_d < -5 and drivers:
        if len(drivers) == 1:
            s3 = f" The shortfall traces primarily to {drivers[0]}."
        else:
            s3 = (f" The shortfall traces primarily to {drivers[0]}, "
                  f"with {' and '.join(drivers[1:])} also down.")
    elif rev_d is not None and rev_d > 5:
        if new_d is not None and new_d > 5:
            s3 = " New-customer acquisition is doing the heavy lifting."
        elif ret_d is not None and ret_d > 5:
            s3 = " Returning customers are doing the heavy lifting."

    return f'<p class="lead-answer">{s1} {s2}{s3}</p>'


# ----- "Why this is happening" assembly --------------------------------------

def _build_why_paragraph(cur: dict, drivers_payload: dict, ccy: str) -> str:
    """Structural paragraph. We don't invent a thesis; we describe the channel
    mix this store actually has and the warning lights (if any) the data fires.
    """
    parts: List[str] = []

    # 1) Channel concentration — based on platform_statistics
    cur_plats = (cur or {}).get("platform_statistics") or []
    if cur_plats:
        # Total paid spend across the channels with any spend
        total = sum((p.get("spend") or 0) for p in cur_plats) / 100.0 if cur_plats else 0
        if total > 0:
            # Sort by spend desc, name top 1-2
            sorted_plats = sorted(cur_plats, key=lambda p: -(p.get("spend") or 0))
            top = sorted_plats[0]
            _provider = (top.get("conversion_provider") or "").lower()
            _brand = {"facebook": "Meta"}.get(_provider, _provider.capitalize())
            top_name = html.escape(_brand)
            top_share = (top.get("spend") or 0) / 100.0 / total * 100
            parts.append(
                f"{top_name} accounts for {top_share:.0f}% of paid spend this window — "
                "channel concentration is the dominant structural feature."
            )

    # 2) LTV:CAC — state the ratio with the inputs behind it, no benchmark verdict.
    ltv_cac = cur.get("ltv_cac")
    if ltv_cac is not None:
        ltv = cur.get("ltv")
        cac = cur.get("cac")
        if ltv is not None and cac:
            parts.append(
                f"LTV:CAC is <strong>{ltv_cac:.2f}×</strong> "
                f"({_ccy(ltv, ccy)} modelled LTV ÷ {_ccy(cac, ccy)} CAC)."
            )
        else:
            parts.append(f"LTV:CAC is <strong>{ltv_cac:.2f}×</strong>.")

    # 3) Where the working/breaking signals concentrate
    breaking = drivers_payload.get("breaking") or []
    working  = drivers_payload.get("working")  or []
    if breaking and working:
        parts.append(
            f"The data fires {len(breaking)} negative signal(s) and {len(working)} positive signal(s) "
            "this window — itemised in the panels below."
        )
    elif breaking and not working:
        parts.append(f"The data fires {len(breaking)} negative signal(s) and no positive signals this window.")
    elif working and not breaking:
        parts.append(f"The data fires {len(working)} positive signal(s) and no negative signals this window.")

    # 4) Acknowledge the COGS gap (always relevant; framework metric the report can't measure)
    parts.append(
        "Gross margin, contribution profit, and per-channel profit aren't measurable here "
        "until Shopify product cost sync is enabled in TrackBee."
    )

    body = " ".join(parts) if parts else "Insufficient data this window."
    return "<h2>Why this is happening</h2><p>" + body + "</p>"



# ----- public entry ----------------------------------------------------------

def build(headline: dict, drivers_payload: dict, config: dict, raws: dict | None = None) -> dict:
    cur = (headline or {}).get("current") or {}
    prv = (headline or {}).get("prior")   or {}
    # Resolve the display symbol once — prefer a config-provided currency_symbol
    # over the ISO table, then thread the symbol through the narrative.
    code = (headline or {}).get("currency") or (config or {}).get("store_currency") or ""
    ccy = _FH.resolve_currency_symbol(config, code)

    lead_answer_html = _build_lead_answer(cur, prv, ccy)
    why_html = _build_why_paragraph(cur, drivers_payload or {}, ccy)
    answer_block = lead_answer_html + why_html

    return {
        "hero_headline": "What is actually driving growth?",
        "answer_block":  answer_block,
    }
