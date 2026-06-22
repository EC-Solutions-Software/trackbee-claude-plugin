"""Channel-attribution insights for the Attribution Overview report.

Reports the per-channel figures — ROAS spread across paid channels, CPA
spread, the highest-ROAS low-spend-share channel, zero-spend earned revenue,
and any paid channel below 2× ROAS that holds significant spend — all as
measured figures. Pure string formatting over the ``_ctx`` block the
window-metrics transform produced. Self-contained — stdlib only.

Insights are observations only; no recommended action is attached.
"""


def _insight(observation, action=""):
    return {"obs": observation, "act": action}


def build(ctx, fmt):
    paying = ctx["paying"]
    earned = ctx["earned"]
    fmt_int = fmt.fmt_int
    fmt_ccy = fmt.fmt_ccy

    out = []

    # Q1 — ROAS comparison across paid channels.
    if len(paying) >= 2:
        paying_with_roas = [r for r in paying if r.get("roas")]
        if paying_with_roas:
            by_roas = sorted(paying_with_roas, key=lambda r: r["roas"], reverse=True)
            best_p = by_roas[0]
            worst_p = by_roas[-1]
            total_spend = sum(r["spend"] for r in paying)
            dominant = max(paying, key=lambda r: r["spend"])
            dom_share = dominant["spend"] / total_spend * 100 if total_spend else 0
            out.append(_insight(
                f"<strong>{best_p['channel']}</strong> returns {best_p['roas']:.2f}x ROAS vs "
                f"<strong>{worst_p['channel']}</strong> at {worst_p['roas']:.2f}x. "
                f"<strong>{dominant['channel']}</strong> takes {dom_share:.0f}% of paid spend."
            ))

    # Q2 — CPA comparison (highest vs lowest).
    paying_with_cpa = [r for r in paying if r.get("cpa")]
    if len(paying_with_cpa) >= 2:
        cheapest = min(paying_with_cpa, key=lambda r: r["cpa"])
        priciest = max(paying_with_cpa, key=lambda r: r["cpa"])
        if priciest["channel"] != cheapest["channel"]:
            ratio = priciest["cpa"] / cheapest["cpa"]
            out.append(_insight(
                f"<strong>{cheapest['channel']}</strong> CPA is {fmt_ccy(cheapest['cpa'])} vs "
                f"<strong>{priciest['channel']}</strong> at {fmt_ccy(priciest['cpa'])} "
                f"({ratio:.1f}× difference)."
            ))

    # Q3 — highest-ROAS channel holding a small share of spend (< 15%).
    if paying:
        total_spend = sum(r["spend"] for r in paying)
        dominant_channel = max(paying, key=lambda r: r["spend"])["channel"]
        candidates = [
            r for r in paying
            if r.get("roas") and r["channel"] != dominant_channel
            and (r["spend"] / total_spend * 100 if total_spend else 0) < 15
        ]
        if candidates:
            gem = max(candidates, key=lambda r: r["roas"])
            spend_share = gem["spend"] / total_spend * 100 if total_spend else 0
            out.append(_insight(
                f"<strong>{gem['channel']}</strong> returns {gem['roas']:.2f}x ROAS on "
                f"{fmt_ccy(gem['spend'])} ({spend_share:.0f}% of paid spend) — the "
                f"highest ROAS among channels holding under 15% of spend."
            ))

    # Q4 — Zero-spend channels (Klaviyo etc.) — use TrackBee numbers.
    if earned:
        er = max(earned, key=lambda r: r["rev_tb"])
        purch_str = f"{fmt_int(er['purch_tb'])} orders, " if er.get("purch_tb") else ""
        out.append(_insight(
            f"<strong>{er['channel']}</strong> drove {purch_str}"
            f"{fmt_ccy(er['rev_tb'])} in revenue at zero media cost (TrackBee-reported)."
        ))

    # Q5 — Flag any paid channel below 2× ROAS that holds significant spend.
    if paying:
        total_spend = sum(r["spend"] for r in paying)
        underperformers = [
            r for r in paying
            if r.get("roas") and r["roas"] < 2
            and (r["spend"] / total_spend * 100 if total_spend else 0) > 10
        ]
        if underperformers:
            u = max(underperformers, key=lambda r: r["spend"])
            spend_share = u["spend"] / total_spend * 100 if total_spend else 0
            purch_str = f"{fmt_int(round(u['purch_in']))} purchases, " if u.get("purch_in") else ""
            out.append(_insight(
                f"<strong>{u['channel']}</strong> is below 2× ROAS "
                f"({u['roas']:.2f}x) and holds {spend_share:.0f}% of spend "
                f"({purch_str}{fmt_ccy(u['spend'])} spent)."
            ))

    return out
