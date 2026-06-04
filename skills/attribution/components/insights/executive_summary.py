"""Executive-summary takeaways for the Attribution Overview report.

Three-to-four headline lines built from the 28d (or selected) window: overall
performance, the top contributing channel, where to scale, and the
over-credit / assisted-revenue risk. Pure string formatting over the ``_ctx``
block. Self-contained — stdlib only.

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

    # 2. Top contributing channel.
    if top_rev_val > 0 and top_rev.get("channel") and top_rev["channel"] != "Overall":
        share = top_rev_val / total_rev_all * 100 if total_rev_all else 0
        out.append(
            f"<strong>{top_rev['channel']}</strong> is the top contributor at "
            f"<strong>{share:.0f}%</strong> of attributed revenue. Protect its budget."
        )

    # 3. Where to scale or cut.
    scale_msg = None
    if paying:
        best_p = max(paying, key=lambda r: r["roas"] or 0)
        if best_p.get("roas") and best_p["roas"] >= 2:
            scale_msg = (f"Test scaling <strong>{best_p['channel']}</strong> "
                         f"(ROAS {best_p['roas']:.2f}, the highest of any paid channel).")
    if scale_msg:
        out.append(scale_msg)

    # 4. Over-credit risk.
    if over_reporters:
        r, ratio = max(over_reporters, key=lambda x: x[1])
        out.append(
            f"<strong>{r['channel']}</strong> is over-reporting purchases by "
            f"<strong>{(ratio-1)*100:.0f}%</strong> vs first-party tracking. "
            f"Use TrackBee numbers when reallocating budget."
        )
    elif earned:
        er = max(earned, key=lambda r: r["rev_tb"])
        out.append(
            f"<strong>{er['channel']}</strong> contributes <strong>{fmt_ccy(er['rev_tb'])}</strong> "
            f"in assisted revenue with no media spend — investigate its incremental contribution."
        )

    return out
