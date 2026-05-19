"""Channel Attribution insights — pure-Python rule pack.

Takes the channel-attribution rows from transforms/channel_attribution.py and
returns a list of {obs, act} bullets answering four strategic questions:

  1. Which channel contributes most to revenue?
  2. Where should I scale or cut based on ROAS / CPA?
  3. Which channels look like they're getting credit they didn't earn?
  4. Which channels deliver revenue without media spend?
"""

from __future__ import annotations


def _fmt_int(value) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}"


def _insight(observation: str, action: str) -> dict:
    return {"obs": observation, "act": action}


def insights(channels) -> list[dict]:
    """Return the list of {obs, act} insight bullets.

    `channels` can be either the rows list directly or the transform's
    `{"rows": [...]}` wrapper — both are accepted so the caller doesn't
    have to unwrap.
    """
    if isinstance(channels, dict) and "rows" in channels:
        rows = channels["rows"]
    else:
        rows = channels or []

    # Strip the Overall row — insights are per-channel only.
    rows = [r for r in rows if r.get("channel") != "Overall"]
    if not rows:
        return []

    paying = [r for r in rows if (r.get("spend") or 0) > 0]
    earned = [r for r in rows if (r.get("spend") or 0) == 0 and (r.get("rev_tb") or 0) > 0]
    total_tb_rev = sum((r.get("rev_tb") or 0) for r in rows)

    out: list[dict] = []

    # Q1 — top contributor to revenue
    top_rev = max(rows, key=lambda r: r.get("rev_tb") or 0)
    if (top_rev.get("rev_tb") or 0) > 0:
        share = (top_rev["rev_tb"] / total_tb_rev * 100) if total_tb_rev else 0
        out.append(_insight(
            f"<strong>{top_rev['channel']}</strong> contributes the most attributed revenue: "
            f"€{top_rev['rev_tb']:,.0f} ({share:.1f}% of tracked total).",
            f"Treat {top_rev['channel']} as a core channel. Protect its budget; "
            f"any cuts here will compound across funnel positions."
        ))

    # Q2 — highest ROAS among paid channels (scale candidate)
    best = None
    if paying:
        best = max(paying, key=lambda r: r.get("roas") or 0)
        if best.get("roas"):
            out.append(_insight(
                f"<strong>{best['channel']}</strong> delivers the highest return: "
                f"ROAS <strong>{best['roas']:.2f}</strong> on €{best['spend']:,.0f} of spend.",
                f"Test a 10–20% budget increase on {best['channel']} and monitor ROAS for "
                f"diminishing returns after 7–14 days."
            ))

    # Q2/Q3 — highest CPA (efficiency check)
    if paying:
        worst = max(paying, key=lambda r: r.get("cpa") or 0)
        if worst.get("cpa") and (best is None or worst["channel"] != best["channel"]):
            out.append(_insight(
                f"<strong>{worst['channel']}</strong> is the most expensive channel: "
                f"CPA <strong>€{worst['cpa']:.2f}</strong> per attributed order.",
                f"Investigate {worst['channel']} placements and audiences before scaling further. "
                f"Consider reallocating part of its spend to higher-ROAS channels."
            ))

    # Q3 — over-reporters (in-platform > TrackBee first-party purchases)
    over_reporters = []
    for r in rows:
        purch_in = r.get("purch_in")
        purch_tb = r.get("purch_tb") or 0
        if purch_in is not None and purch_tb > 0 and purch_in > purch_tb:
            over_reporters.append((r, purch_in / purch_tb))

    if over_reporters:
        r, ratio = max(over_reporters, key=lambda x: x[1])
        excess_pct = (ratio - 1) * 100
        out.append(_insight(
            f"<strong>{r['channel']}</strong> reports {excess_pct:.0f}% more purchases than TrackBee attributes "
            f"({_fmt_int(r['purch_in'])} platform-reported vs {_fmt_int(r['purch_tb'])} first-party). "
            f"Likely view-through or attribution-window credit.",
            f"Discount {r['channel']}'s in-platform ROAS by ~{excess_pct:.0f}% when comparing across channels. "
            f"Use TrackBee's first-party numbers as the reference for budget decisions."
        ))

    # Q1 / Q3 — earned revenue without spend
    if earned:
        er = max(earned, key=lambda r: r.get("rev_tb") or 0)
        out.append(_insight(
            f"<strong>{er['channel']}</strong> contributes €{er['rev_tb']:,.0f} in assisted revenue without media spend.",
            f"Audit the upstream paid channels feeding {er['channel']} — its conversions may already be "
            f"counted by Meta or Google. Test list-only segmentation to measure {er['channel']}'s incremental lift."
        ))

    return out
