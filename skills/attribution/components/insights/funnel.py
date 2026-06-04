"""Store-funnel insights for the Attribution Overview report.

One observation/action pair per leaking stage, tuned to that step's UX
levers, ordered worst-first (with a secondary leak and an optional
browse-stage callout). Pure string formatting over the ``_ctx`` block.
Self-contained — stdlib only.
"""


def _funnel_insight(drop):
    """Generate `{obs, act}` for a given drop based on its stage."""
    rate_pct = (drop["rate"] or 0) * 100
    lost_n = drop["lost"]
    to_step = drop["to_step"]

    if to_step == "total_product_view_events":
        obs = (f"Only <strong>{rate_pct:.1f}%</strong> of sessions reach a product page — "
               f"<strong>{lost_n:,}</strong> visitors left before opening a single SKU.")
        act = ("Tighten the path from landing to product: feature your best sellers on the homepage, "
               "shorten collection navigation to one or two clicks, surface bestseller and review "
               "badges on category thumbnails, and confirm collection pages load fast on mobile.")
    elif to_step == "total_add_to_cart_events":
        if rate_pct >= 20:
            obs = (f"<strong>{rate_pct:.1f}%</strong> of product views convert to add-to-cart — "
                   f"strong product-page performance.")
            act = ("Keep the formula intact. Test small wins like variant pickers, lifestyle imagery, "
                   "or bundle suggestions, but don't redesign what is already working.")
        else:
            obs = (f"Only <strong>{rate_pct:.1f}%</strong> of product views become add-to-carts — "
                   f"<strong>{lost_n:,}</strong> shoppers viewed a product and left without adding it.")
            act = ("Audit the product detail page for buying-intent blockers: add lifestyle images and "
                   "video, surface reviews and trust badges above the fold, clarify shipping and "
                   "return policy near the buy button, and test a sticky add-to-cart on mobile.")
    elif to_step == "total_checkout_started_events":
        obs = (f"Only <strong>{rate_pct:.1f}%</strong> of add-to-cart events start checkout — "
               f"<strong>{lost_n:,}</strong> filled carts but never opened the checkout. "
               f"This is the dashboard's biggest single revenue leak.")
        act = ("Reduce cart-to-checkout friction: show shipping cost in the cart drawer (no surprises "
               "on the checkout page), make 'guest checkout' the default, add Shop Pay / Apple Pay / "
               "Klarna express buttons in the cart, and trigger an abandoned-cart email within an hour. "
               "Note: TrackBee tracks checkout_started client-side, so the true rate is likely higher.")
    elif to_step == "total_orders":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of checkout starts complete an order. "
               f"<strong>{lost_n:,}</strong> shoppers entered checkout and abandoned before paying.")
        act = ("Investigate payment friction: confirm Apple Pay / Google Pay / Klarna / iDEAL are live, "
               "test the checkout on slow mobile networks, watch for input-validation errors on the "
               "phone and postcode fields, and verify that discount codes apply without a page reload.")
    else:
        obs = f"<strong>{rate_pct:.1f}%</strong> conversion from the previous stage."
        act = "Investigate this transition for friction points specific to your store's UX."
    return {"obs": obs, "act": act}


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
