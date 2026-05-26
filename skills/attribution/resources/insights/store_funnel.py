"""Store Funnel insights — pure-Python rule pack.

Takes the drops list from transforms/store_funnel.py and emits a focused
brief: the worst non-browse drop, a PV → PDP callout when browsing is
unusually weak, and one secondary leak when a distinct step is also
clearly underperforming. Each entry is a stage-specific observation +
action so the section reads as advice rather than generic "you have a
drop, fix it" copy.
"""

from __future__ import annotations


def _stage_insight(drop: dict) -> dict:
    """Generate `{obs, act}` for a given drop based on its destination stage."""
    rate_pct = (drop["rate"] or 0) * 100
    lost_n = drop["lost"]
    to_step = drop["to_step"]

    if to_step == "total_product_view_events":
        obs = (f"Only <strong>{rate_pct:.1f}%</strong> of sessions reach a product page — "
               f"<strong>{lost_n:,}</strong> visitors left before opening a single SKU.")
        act = ("Tighten the path from landing to product: feature your best sellers on "
               "the homepage, shorten collection navigation to one or two clicks, surface "
               "bestseller and review badges on category thumbnails, and confirm collection "
               "pages load fast on mobile.")
    elif to_step == "total_add_to_cart_events":
        if rate_pct >= 20:
            obs = (f"<strong>{rate_pct:.1f}%</strong> of product views convert to "
                   f"add-to-cart — strong product-page performance.")
            act = ("Keep the formula intact. Test small wins like variant pickers, "
                   "lifestyle imagery, or bundle suggestions, but don't redesign what "
                   "is already working.")
        else:
            obs = (f"Only <strong>{rate_pct:.1f}%</strong> of product views become "
                   f"add-to-carts — <strong>{lost_n:,}</strong> shoppers viewed a "
                   f"product and left without adding it.")
            act = ("Audit the product detail page for buying-intent blockers: add "
                   "lifestyle images and video, surface reviews and trust badges above "
                   "the fold, clarify shipping and return policy near the buy button, "
                   "and test a sticky add-to-cart on mobile.")
    elif to_step == "total_checkout_started_events":
        obs = (f"Only <strong>{rate_pct:.1f}%</strong> of add-to-cart events start "
               f"checkout — <strong>{lost_n:,}</strong> filled carts but never opened "
               f"the checkout.")
        act = ("Reduce cart-to-checkout friction: show shipping cost in the cart drawer "
               "(no surprises on the checkout page), make 'guest checkout' the default, "
               "add express-checkout buttons (Shop Pay, Apple Pay, Google Pay, and your "
               "region's preferred methods) in the cart, and trigger an abandoned-cart "
               "email within an hour. Note: TrackBee tracks checkout_started "
               "client-side, so the true rate is likely higher.")
    elif to_step == "total_orders":
        obs = (f"<strong>{rate_pct:.1f}%</strong> of checkout starts complete an order. "
               f"<strong>{lost_n:,}</strong> shoppers entered checkout and abandoned "
               f"before paying.")
        act = ("Investigate payment friction: confirm your region's preferred payment "
               "methods are live (Apple Pay, Google Pay, and the local options your "
               "shoppers expect), test the checkout on slow mobile networks, watch for "
               "input-validation errors on the phone and postcode fields, and verify "
               "that discount codes apply without a page reload.")
    else:
        obs = f"<strong>{rate_pct:.1f}%</strong> conversion from the previous stage."
        act = ("Investigate this transition for friction points specific to your "
               "store's UX.")
    return {"obs": obs, "act": act}


def insights(drops: list[dict]) -> list[dict]:
    """Return up to three {obs, act} bullets describing the worst drops."""
    if not drops:
        return []

    non_browse_drops = [d for d in drops
                        if d["to_step"] != "total_product_view_events"]
    worst_drop = (min(non_browse_drops, key=lambda d: d["rate"])
                  if non_browse_drops
                  else min(drops, key=lambda d: d["rate"]))
    browse_drop = next((d for d in drops
                        if d["to_step"] == "total_product_view_events"), None)

    out: list[dict] = [_stage_insight(worst_drop)]

    # Surface PV → PDP when browsing is unusually weak (<25%, i.e. 3-in-4
    # sessions never see a product). Skip otherwise so the section doesn't
    # stuff every dashboard with generic "improve discoverability" advice.
    if (browse_drop
            and (browse_drop["rate"] or 0) < 0.25
            and browse_drop["to_step"] != worst_drop["to_step"]):
        out.append(_stage_insight(browse_drop))

    # Secondary leak: a distinct step also clearly weak (<25%). One at
    # most so the section stays focused.
    for d in drops:
        if d["to_step"] == worst_drop["to_step"]:
            continue
        if browse_drop and d["to_step"] == browse_drop["to_step"]:
            continue
        if (d["rate"] or 0) < 0.25:
            out.append(_stage_insight(d))
            break

    return out
