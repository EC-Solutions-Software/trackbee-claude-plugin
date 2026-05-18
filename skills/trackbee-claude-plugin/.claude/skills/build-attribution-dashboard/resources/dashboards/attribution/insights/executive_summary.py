"""Executive Summary takeaways — pure-Python rule pack.

Produces 3-5 HTML-formatted strings that the view renders inside an <ol>
at the top of the dashboard. Each string may contain <strong> tags — the
view interpolates the raw HTML.

Inputs:
    inputs["blended"]  — blended KPI payload from transforms/blended_kpis.py
    inputs["channels"] — channel rows from transforms/channel_attribution.py
                         (either {"rows": [...]} or the rows list directly).
"""

from __future__ import annotations


def _delta_phrase(current: float, previous: float | None) -> str:
    if not previous:
        return ""
    pct = ((current - previous) / previous) * 100
    if pct > 5:
        return f", up {pct:+.0f}% vs the previous period"
    if pct < -5:
        return f", down {abs(pct):.0f}% vs the previous period"
    return ", flat vs the previous period"


def takeaways(inputs: dict) -> list[str]:
    blended = inputs.get("blended") or {}
    channels_in = inputs.get("channels") or []

    if isinstance(channels_in, dict) and "rows" in channels_in:
        rows = channels_in["rows"]
    else:
        rows = channels_in

    # Strip Overall — takeaways are per-channel.
    rows = [r for r in rows if r.get("channel") != "Overall"]

    out: list[str] = []

    revenue   = blended.get("revenue") or 0
    orders    = blended.get("orders") or 0
    ad_spend  = blended.get("ad_spend") or 0
    roas      = blended.get("roas") or 0
    rev_prev  = blended.get("_revenue_prev")

    # 1. Headline performance
    delta = _delta_phrase(revenue, rev_prev)
    out.append(
        f"Generated <strong>€{revenue:,.0f}</strong> in revenue from "
        f"<strong>{int(orders):,}</strong> orders on "
        f"<strong>€{ad_spend:,.0f}</strong> of ad spend "
        f"(Blended ROAS <strong>{roas:.2f}</strong>){delta}."
    )

    if not rows:
        return out

    total_tb_rev = sum((r.get("rev_tb") or 0) for r in rows)
    paying       = [r for r in rows if (r.get("spend") or 0) > 0]
    earned       = [r for r in rows if (r.get("spend") or 0) == 0 and (r.get("rev_tb") or 0) > 0]

    # 2. Top contributing channel
    top_rev = max(rows, key=lambda r: r.get("rev_tb") or 0)
    if (top_rev.get("rev_tb") or 0) > 0 and total_tb_rev:
        share = top_rev["rev_tb"] / total_tb_rev * 100
        out.append(
            f"<strong>{top_rev['channel']}</strong> is the top contributor at "
            f"<strong>{share:.0f}%</strong> of attributed revenue. Protect its budget."
        )

    # 3. Scale candidate (best ROAS ≥ 2)
    if paying:
        best_p = max(paying, key=lambda r: r.get("roas") or 0)
        if best_p.get("roas") and best_p["roas"] >= 2:
            out.append(
                f"Test scaling <strong>{best_p['channel']}</strong> "
                f"(ROAS {best_p['roas']:.2f}, the highest of any paid channel)."
            )

    # 4. Over-credit risk OR earned-revenue flag
    over_reporters = []
    for r in rows:
        purch_in = r.get("purch_in")
        purch_tb = r.get("purch_tb") or 0
        if purch_in is not None and purch_tb > 0 and purch_in > purch_tb:
            over_reporters.append((r, purch_in / purch_tb))

    if over_reporters:
        r, ratio = max(over_reporters, key=lambda x: x[1])
        out.append(
            f"<strong>{r['channel']}</strong> is over-reporting purchases by "
            f"<strong>{(ratio - 1) * 100:.0f}%</strong> vs first-party tracking. "
            f"Use TrackBee numbers when reallocating budget."
        )
    elif earned:
        er = max(earned, key=lambda r: r.get("rev_tb") or 0)
        out.append(
            f"<strong>{er['channel']}</strong> contributes "
            f"<strong>€{er['rev_tb']:,.0f}</strong> in assisted revenue with no media spend — "
            f"investigate its incremental contribution."
        )

    return out
