"""Store-funnel insights for the Attribution Overview report.

One factual observation per leaking stage — the step's conversion rate and
the count of shoppers lost at that step — ordered worst-first (with a
secondary leak and an optional browse-stage callout). Pure string formatting
over the ``_ctx`` block. Self-contained — stdlib only.

Observations only; no recommended fix is attached. The checkout step keeps
the factual tracking caveat (checkout_started is client-side).
"""


def _funnel_insight(drop):
    """Generate `{obs}` for a given drop based on its stage — rate + lost count."""
    rate_pct = (drop["rate"] or 0) * 100
    lost_n = drop["lost"]
    to_step = drop["to_step"]

    if to_step == "total_product_view_events":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of sessions reach a product page — "
               f"<strong>{lost_n:,}</strong> visitors left before opening a single SKU.")
    elif to_step == "total_add_to_cart_events":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of product views become add-to-carts — "
               f"<strong>{lost_n:,}</strong> shoppers viewed a product and did not add it.")
    elif to_step == "total_checkout_started_events":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of add-to-cart events start checkout — "
               f"<strong>{lost_n:,}</strong> filled carts but did not open the checkout. "
               f"Note: TrackBee tracks checkout_started client-side, so the true rate is likely higher.")
    elif to_step == "total_orders":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of checkout starts complete an order — "
               f"<strong>{lost_n:,}</strong> shoppers entered checkout and did not pay.")
    else:
        obs = f"<strong>{rate_pct:.1f}%</strong> conversion from the previous stage."
    return {"obs": obs, "act": ""}


def build(ctx, fmt=None):
    worst_drop = ctx["worst_drop"]
    browse_drop = ctx["browse_drop"]
    funnel_drops = ctx["funnel_drops"]

    out = []
    if worst_drop:
        out.append(_funnel_insight(worst_drop))
    # Browse-stage callout only when browsing is unusually weak (<25%).
    if (browse_drop and (browse_drop["rate"] or 0) < 0.25
            and (not worst_drop or browse_drop["to_step"] != worst_drop["to_step"])):
        out.append(_funnel_insight(browse_drop))
    # One secondary leak at most, if also clearly weak and distinct.
    for d in funnel_drops:
        if worst_drop and d["to_step"] == worst_drop["to_step"]:
            continue
        if browse_drop and d["to_step"] == browse_drop["to_step"]:
            continue
        if (d["rate"] or 0) < 0.25:
            out.append(_funnel_insight(d))
            break

    return out
