"""Build the hero answer narrative + Next steps actions.

Everything here is sourced from the headline KPI summary and the drivers
output. We avoid asserting anything we can't back with a number on this
run.

  - hero_headline: fixed question ("What is actually driving growth?")
  - answer_block:  HTML — lead-answer paragraph + "Why this is happening"
                   H2 + paragraph, all built from this run's metrics
  - actions_list:  <li>...</li> string for the Next steps list
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


def _safe_anchor(url, label: str) -> str:
    """Render an <a> for an MCP-supplied URL — safely.

    The URL comes from the Meta recommendations payload (merchant/platform
    data), so it must be HTML-attribute-escaped and scheme-restricted before
    it lands in an ``href``. Returns "" for a missing URL or any non-http(s)
    scheme (e.g. ``javascript:``), so nothing unsafe reaches the report.
    """
    if not url:
        return ""
    u = str(url).strip()
    if not (u.lower().startswith("http://") or u.lower().startswith("https://")):
        return ""
    return (f' <a href="{html.escape(u, quote=True)}" '
            f'target="_blank" rel="noopener">{html.escape(label)}</a>')


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

def _build_why_paragraph(cur: dict, drivers_payload: dict) -> str:
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

    # 2) LTV:CAC framing — only state the read if we have the number
    ltv_cac = cur.get("ltv_cac")
    if ltv_cac is not None:
        if ltv_cac < 2.0:
            parts.append(
                f"LTV:CAC is <strong>{ltv_cac:.2f}×</strong> — unit economics are at or near "
                "break-even before COGS and overhead, so contribution is sensitive to small "
                "shifts in AOV or auction costs."
            )
        elif ltv_cac < 3.0:
            parts.append(
                f"LTV:CAC is <strong>{ltv_cac:.2f}×</strong> — below the 3× category benchmark; "
                "improvement requires AOV expansion or CAC reduction."
            )
        else:
            parts.append(
                f"LTV:CAC is <strong>{ltv_cac:.2f}×</strong> — at or above the 3× category benchmark, "
                "supporting continued reinvestment."
            )

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


# ----- Next steps assembly ---------------------------------------------------

def _build_actions(cur: dict, prv: dict, ccy: str, drivers_payload: dict,
                   raws: dict, meta_fx: float = 1.0, google_fx: float = 1.0,
                   exclude_ids=None) -> List[str]:
    """Generate Next steps strictly from the signals the data actually fires.

    Where an action calls out a channel that's underperforming or worth
    scaling, name the specific campaigns the marketer should look at — pulled
    from the Meta and Google campaign-insights payloads.

    `meta_fx` / `google_fx` convert campaign spend from ad-account currency
    into store currency, so the `min_spend` gates compare like-for-like with
    the store-currency thresholds.
    """
    actions: List[str] = []
    breaking = drivers_payload.get("breaking") or []

    # Per-platform spend snapshot
    def _plat_dict(ov):
        out = {}
        for row in ((ov or {}).get("platform_statistics") or []):
            name = (row.get("conversion_provider") or "").lower()
            if not name: continue
            out[name] = {
                "spend":   (row.get("spend") or 0) / 100.0,
                "revenue": (row.get("revenue") or 0) / 100.0,
                "roas":    row.get("return_on_ad_spend"),
                "cpc":     (row.get("cost_per_click") or 0) / 100.0,
            }
        return out
    cur_plats = _plat_dict(cur)

    # Campaign lookups. The MCP returns Meta spend / purchase_roas and Google
    # spend / conversions_value as STRINGS (e.g. "123.45") — Meta passes the
    # Graph API value through verbatim and Google formats micros to a string.
    # The scoring below does arithmetic and comparisons on these, which would
    # TypeError on a str, so coerce numerics to float up front. A genuinely
    # missing purchase_roas / conversions_value must stay None (the loops treat
    # "no data yet" differently from a zero), so only present values convert.
    def _norm_campaign(c):
        # NOTE: spend and conversions_value stay in AD-ACCOUNT currency here.
        # Convert with meta_fx / google_fx at the point of use — currently
        # only spend needs it (the spend gates compare against store-currency
        # thresholds); conversions_value is used solely inside ROAS ratios
        # where FX cancels. Convert it too before any direct display.
        c = dict(c)
        c["spend"] = _FH.safe_float(c.get("spend"))
        if c.get("purchase_roas") is not None:
            c["purchase_roas"] = _FH.safe_float(c.get("purchase_roas"))
        if c.get("conversions_value") is not None:
            c["conversions_value"] = _FH.safe_float(c.get("conversions_value"))
        return c

    # User-excluded campaigns (e.g. test campaigns) are dropped before any
    # selection so they never surface in the worst-spenders or scale-candidate
    # call-outs. Match on campaign_id, mirroring creatives-report's exclusion.
    _exclude = {str(x) for x in (exclude_ids or ())}
    def _keep(c):
        return str(c.get("campaign_id")) not in _exclude

    meta_campaigns = [_norm_campaign(c) for c in
                      ((raws.get("meta_campaigns") or {}).get("campaigns") or [])
                      if _keep(c)]
    google_campaigns = [_norm_campaign(c) for c in
                        ((raws.get("google_campaigns") or {}).get("campaigns") or [])
                        if _keep(c)]

    def _name_clip(name, max_len=110):
        # Campaign names are merchant-authored and rendered straight into
        # <li> markup, so HTML-escape after clipping — never emit raw.
        if not name: return ""
        s = str(name).strip()
        clipped = s if len(s) <= max_len else s[:max_len-1] + "…"
        return html.escape(clipped)

    def _meta_top_spenders_below_roas(threshold=1.0, min_spend=200, limit=3):
        """Meta campaigns with material spend and ROAS below `threshold`,
        ordered by absolute wasted spend (spend × (threshold - ROAS))."""
        rows = []
        for c in meta_campaigns:
            spend = (c.get("spend") or 0) * meta_fx   # → store currency
            roas = c.get("purchase_roas")             # ratio, FX-independent
            # Skip campaigns with no purchase data yet — a missing ROAS
            # is not the same as a poor ROAS, and flagging brand-new
            # campaigns as "worst spenders" is misleading.
            if roas is None:
                continue
            if spend >= min_spend and roas < threshold:
                rows.append((c, spend * (threshold - roas)))
        rows.sort(key=lambda r: -r[1])
        return [r[0] for r in rows[:limit]]

    def _google_top_spenders_below_roas(threshold=1.0, min_spend=200, limit=3):
        rows = []
        for c in google_campaigns:
            # No conversions_value field = no conversion data yet; skip
            # rather than scoring it as zero-return waste.
            if c.get("conversions_value") is None:
                continue
            raw_spend = c.get("spend") or 0
            conv_value = c.get("conversions_value") or 0
            roas = (conv_value / raw_spend) if raw_spend > 0 else 0  # ratio, FX-independent
            spend = raw_spend * google_fx   # → store currency
            if spend >= min_spend and roas < threshold:
                rows.append((c, spend * (threshold - roas), roas))
        rows.sort(key=lambda r: -r[1])
        return [(r[0], r[2]) for r in rows[:limit]]

    def _meta_top_roas_campaigns(min_spend=50, limit=2):
        rows = [(c, c.get("purchase_roas") or 0) for c in meta_campaigns
                if ((c.get("spend") or 0) * meta_fx) >= min_spend and (c.get("purchase_roas") or 0) > 0]
        rows.sort(key=lambda r: -r[1])
        return [r for r in rows[:limit]]

    def _google_top_roas_campaigns(min_spend=50, limit=2):
        rows = []
        for c in google_campaigns:
            raw_spend = c.get("spend") or 0
            conv_value = c.get("conversions_value") or 0
            if raw_spend * google_fx < min_spend: continue   # store-currency gate
            roas = (conv_value / raw_spend) if raw_spend > 0 else 0  # ratio, FX-independent
            if roas <= 0: continue
            rows.append((c, roas))
        rows.sort(key=lambda r: -r[1])
        return rows[:limit]

    # ---- 1) Meta consolidation & creative fatigue (from recommendations) ----
    meta_recs_raw = raws.get("meta_recommendations") or {}
    recs = meta_recs_raw.get("recommendations") or []
    n_frag = sum(1 for r in recs if r.get("type") == "FRAGMENTATION")
    n_creative_limited = sum(1 for r in recs if r.get("type") == "CREATIVE_LIMITED")
    frag_lifts = [r.get("lift_estimate") for r in recs
                  if r.get("type") == "FRAGMENTATION" and r.get("lift_estimate")]
    # Pick the highest-impact fragmentation rec URL to surface as a deep link
    frag_url = None
    for r in recs:
        if r.get("type") == "FRAGMENTATION" and r.get("url"):
            frag_url = r["url"]
            break

    has_meta_cpc_breaking = any(
        "Meta CPC" in b.get("title", "") and "+" in b.get("title", "")
        for b in breaking
    )
    if has_meta_cpc_breaking and n_frag >= 2:
        lift_clause = ""
        if frag_lifts:
            # lift_estimate is Meta-supplied free text → escape before it
            # lands in the raw-spliced actions list.
            strongest = html.escape(str(max(frag_lifts, key=lambda s: len(s))))
            lift_clause = f", with Meta's strongest estimate at \"{strongest}\""
        link_clause = _safe_anchor(frag_url, "View affected ad sets in Meta Ads Manager →")
        actions.append(
            f"Consolidate fragmented Meta ad sets. Meta flags {n_frag} fragmentation "
            f"opportunit{'ies' if n_frag != 1 else 'y'} on this account"
            f"{lift_clause}.{link_clause}"
        )

    if n_creative_limited > 0:
        cl_url = next((r.get("url") for r in recs if r.get("type") == "CREATIVE_LIMITED" and r.get("url")), None)
        link_clause = _safe_anchor(cl_url, "Open in Meta Ads Manager →")
        actions.append(
            f"Refresh fatigued creatives — Meta flags {n_creative_limited} ad(s) as "
            "creative-limited, indicating cost-per-result pressure from over-exposure."
            f"{link_clause}"
        )

    # ---- 2) Worst-performing campaigns by wasted spend (cross-channel) ----
    # Fire independent of channel-level ROAS. Many stores have profitable
    # channels overall but unprofitable individual campaigns inside them — that's
    # exactly where pausing or reducing pays off.
    meta_worst   = _meta_top_spenders_below_roas(threshold=1.0, min_spend=200, limit=3)
    google_worst = _google_top_spenders_below_roas(threshold=1.0, min_spend=200, limit=3)

    if meta_worst:
        rows = "".join(
            f"<li>{_name_clip(c.get('campaign_name'))}</li>"
            for c in meta_worst
        )
        actions.append(
            "Reduce or pause the Meta campaigns running below 1.0 ROAS this window. "
            f"Worst three by wasted spend:<ul class=\"action-detail\">{rows}</ul>"
        )

    if google_worst:
        rows = "".join(
            f"<li>{_name_clip(c.get('campaign_name'))}</li>"
            for c, _ in google_worst
        )
        actions.append(
            "Reduce or pause the Google campaigns running below 1.0 ROAS this window. "
            f"Worst three by wasted spend:<ul class=\"action-detail\">{rows}</ul>"
        )

    # ---- 3) Returning-customer revenue contraction ----
    ret_d = _pct_delta(cur.get("ret_revenue"), prv.get("ret_revenue"))
    if ret_d is not None and ret_d < -10:
        actions.append(
            "Diagnose the returning-customer revenue contraction. Review CRM and email-flow "
            "activity for the window, identify any campaigns or product drops in the prior week "
            "that may have pulled forward demand, and confirm Klaviyo retention automations are "
            "firing as expected."
        )

    # ---- 4) Symmetric AOV decline → promo / product-mix audit ----
    aov_new_d = _pct_delta(cur.get("aov_new"), prv.get("aov_new"))
    aov_ret_d = _pct_delta(cur.get("aov_ret"), prv.get("aov_ret"))
    if (aov_new_d is not None and aov_new_d < -5
            and aov_ret_d is not None and aov_ret_d < -5):
        actions.append(
            "Audit active promotional offers and product mix. A symmetric AOV decline across "
            "new and returning customers indicates structural discount pressure or a shift "
            "toward lower-priced SKUs rather than a customer-mix effect."
        )

    # ---- 5) Sub-spec LTV:CAC ----
    ltv_cac = cur.get("ltv_cac")
    if ltv_cac is not None and ltv_cac < 2.0:
        actions.append(
            f"Address LTV:CAC at {ltv_cac:.2f}×. Options: raise AOV via bundling or upsell, "
            "improve cohort retention to lift LTV, or tighten CAC by reducing spend on "
            "low-incrementality channels."
        )

    # ---- 6) Underweight high-ROAS channel → reallocation test, name top campaign ----
    total_spend = sum((p.get("spend") or 0) for p in (cur.get("platform_statistics") or [])) / 100.0
    # Intentional subset of _FH.AD_PLATFORMS: minor channels only — Meta and
    # Google campaigns are already covered by the worst/top call-outs above.
    # Deriving from the shared list picks up newly added minor channels.
    for name, label in [p for p in _FH.AD_PLATFORMS
                        if p[0] not in ("facebook", "google")]:
        info = cur_plats.get(name) or {}
        roas = info.get("roas")
        spend = info.get("spend", 0)
        if roas and roas > 2.5 and total_spend > 0 and spend / total_spend < 0.05:
            # We don't have per-channel campaign breakdowns for Pinterest/TikTok in this payload,
            # so just frame the test cleanly.
            actions.append(
                f"Test an incremental budget allocation on {label}. Current platform ROAS "
                f"{roas:.2f} on {_ccy(spend, ccy)} spend "
                f"({spend/total_spend*100:.1f}% of total media). A small lift is a low-risk "
                "test of additional efficient scale."
            )

    # ---- 7) Highlight top-performing campaigns worth scaling ----
    # When we have a clear positive ROAS picture, give the marketer the names to scale into.
    top_meta = _meta_top_roas_campaigns(min_spend=200, limit=2)
    top_google = _google_top_roas_campaigns(min_spend=200, limit=2)
    scale_candidates = []
    for c, roas in top_meta:
        if roas > 1.5:
            scale_candidates.append(_name_clip(c.get('campaign_name')))
    for c, roas in top_google:
        if roas > 1.5:
            scale_candidates.append(_name_clip(c.get('campaign_name')))
    if scale_candidates:
        rows = "".join(f"<li>{n}</li>" for n in scale_candidates[:3])
        actions.append(
            "Consider redirecting freed-up budget into the strongest current campaigns:"
            f"<ul class=\"action-detail\">{rows}</ul>"
        )

    # ---- 8) Always-on: enable Shopify product cost sync ----
    actions.append(
        "Enable Shopify product cost sync in TrackBee. Until it is enabled, this report can "
        "show ROAS and MER but cannot measure gross margin, contribution profit, or per-channel profit."
    )

    return actions[:10]



# ----- public entry ----------------------------------------------------------

def build(headline: dict, drivers_payload: dict, config: dict, raws: dict | None = None) -> dict:
    cur = (headline or {}).get("current") or {}
    prv = (headline or {}).get("prior")   or {}
    # Resolve the display symbol once — prefer a config-provided currency_symbol
    # over the ISO table, then thread the symbol through the narrative + actions.
    code = (headline or {}).get("currency") or (config or {}).get("store_currency") or ""
    ccy = _FH.resolve_currency_symbol(config, code)

    lead_answer_html = _build_lead_answer(cur, prv, ccy)
    why_html = _build_why_paragraph(cur, drivers_payload or {})
    answer_block = lead_answer_html + why_html

    # Campaign payloads arrive in ad-account currency; these multipliers
    # convert spend into store currency. Default 1.0 = same-currency store.
    # ``safe_float`` coerces both 0 and None to 0.0, so a config typo like
    # ``"meta_fx_to_store": 0`` would zero out every spend gate below.
    # The ``> 0`` guard restores the identity multiplier in that case.
    meta_fx   = _FH.safe_float((config or {}).get("meta_fx_to_store", 1.0), 1.0)
    google_fx = _FH.safe_float((config or {}).get("google_fx_to_store", 1.0), 1.0)
    meta_fx   = meta_fx if meta_fx > 0 else 1.0
    google_fx = google_fx if google_fx > 0 else 1.0
    scope = (config or {}).get("scope") or {}
    exclude_ids = scope.get("exclude_campaign_ids") or []
    actions = _build_actions(cur, prv, ccy, drivers_payload or {}, raws or {},
                             meta_fx, google_fx, exclude_ids=exclude_ids)
    actions_html = "".join(f"<li>{a}</li>" for a in actions)

    return {
        "hero_headline": "What is actually driving growth?",
        "answer_block":  answer_block,
        "actions_list":  actions_html,
    }
