"""Executive-summary takeaways for the Attribution Overview report.

A few factual headline lines built from the 28d (or selected) window:
overall performance figures, the top contributing channel's revenue share,
the highest-ROAS paid channel, and the platform-vs-TrackBee purchase-count
gap stated neutrally. Pure string formatting over the ``_ctx`` block —
measured figures only, no recommendations. Self-contained — stdlib only.

Monetary values format through ``fmt.fmt_ccy`` so every currency renders with
its own symbol (the prose used to hardcode a euro sign).
"""


def build(ctx, fmt):
    fmt_ccy = fmt.fmt_ccy

    revenue = ctx["revenue"]
    revenue_prev = ctx["revenue_prev"]
    orders = ctx["orders"]
    ad_spend_eur = ctx["ad_spend_eur"]
    blended_roas = ctx["blended_roas"]
    top_rev = ctx["top_rev"]
    top_rev_val = ctx["top_rev_val"]
    total_rev_all = ctx["total_rev_all"]
    paying = ctx["paying"]
    over_reporters = ctx["over_reporters"]
    earned = ctx["earned"]

    out = []

    # 1. Headline performance.
    rev_delta_pct = ((revenue - revenue_prev) / revenue_prev * 100) if revenue_prev else None
    delta_phrase = ""
    if rev_delta_pct is not None:
        if rev_delta_pct > 5:
            delta_phrase = f", up {rev_delta_pct:+.0f}% vs the previous period"
        elif rev_delta_pct < -5:
            delta_phrase = f", down {abs(rev_delta_pct):.0f}% vs the previous period"
        else:
            delta_phrase = f", flat vs the previous period"
    out.append(
        f"Generated <strong>{fmt_ccy(revenue)}</strong> in revenue from <strong>{int(orders):,}</strong> orders "
        f"on <strong>{fmt_ccy(ad_spend_eur)}</strong> of ad spend (Blended ROAS <strong>{blended_roas:.2f}</strong>){delta_phrase}."
    )

    # 2. Top contributing channel — revenue share, stated as a figure.
    if top_rev_val > 0 and top_rev.get("channel") and top_rev["channel"] != "Overall":
        share = top_rev_val / total_rev_all * 100 if total_rev_all else 0
        out.append(
            f"<strong>{top_rev['channel']}</strong> is the largest contributor at "
            f"<strong>{share:.0f}%</strong> of attributed revenue."
        )

    # 3. Highest-ROAS paid channel — a measured figure, no scaling advice.
    if paying:
        best_p = max(paying, key=lambda r: r["roas"] or 0)
        if best_p.get("roas"):
            out.append(
                f"Highest-ROAS paid channel: <strong>{best_p['channel']}</strong> "
                f"at {best_p['roas']:.2f}× ROAS."
            )

    # 4. Platform-vs-TrackBee purchase-count gap — stated neutrally, no
    #    causal "over-reporting" direction.
    if over_reporters:
        r, _ratio = max(over_reporters, key=lambda x: x[1])
        p_in = r.get("purch_in")
        p_tb = r.get("purch_tb")
        if p_in is not None and p_tb is not None:
            out.append(
                f"<strong>{r['channel']}</strong>: platform reports "
                f"{int(round(p_in)):,} purchases vs TrackBee's {int(round(p_tb)):,}."
            )
    elif earned:
        er = max(earned, key=lambda r: r["rev_tb"])
        out.append(
            f"<strong>{er['channel']}</strong> contributes <strong>{fmt_ccy(er['rev_tb'])}</strong> "
            f"in assisted revenue with no media spend (TrackBee-reported)."
        )

    return out
