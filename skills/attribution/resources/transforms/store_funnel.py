"""Store Funnel — Python data transform.

Reads the per-window funnel payload (get_funnel_overview with
compare_previous_period=true) and returns the per-stage counts, the
step-to-step drops, and a headline summary that the view layer reads via
window.TB_DATA.windows.<key>.{funnel_stages,funnel_drops,funnel_summary}.

The page-view → product-view → add-to-cart → checkout-started → orders
ladder is shared across stores. Counts come straight from the funnel
JSON; rates are passed through when present and recomputed from the
adjacent stages otherwise.
"""

from __future__ import annotations


_STEP_LABELS: dict[str, str] = {
    "total_page_view_events":         "Page views",
    "total_product_view_events":      "Product views",
    "total_add_to_cart_events":       "Add to cart",
    "total_checkout_started_events":  "Checkout started",
    "total_orders":                   "Orders",
}


def transform(inputs: dict, config: dict) -> dict:
    del config  # currency is rendered client-side from window.TB_DATA.store
    funnel: dict = inputs.get("funnel") or {}

    # funnel JSON has shape {"current": {"funnel": [...]}, "previous": {...}}
    # when compare_previous_period=true; un-wrap to the current funnel list.
    cur = funnel.get("current") or funnel  # tolerate already-unwrapped input
    stages_in = (cur.get("funnel") if isinstance(cur, dict) else None) or []

    stages: list[dict] = []
    for entry in stages_in:
        step = entry.get("step")
        if step not in _STEP_LABELS:
            continue
        stages.append({
            "step":               step,
            "label":              _STEP_LABELS[step],
            "count":              int(entry.get("count") or 0),
            "rate_from_previous": entry.get("rate_from_previous"),
            "rate_from_top":      entry.get("rate_from_top"),
        })

    # Step-to-step drops, with absolute people lost between adjacent stages.
    drops: list[dict] = []
    for i, s in enumerate(stages):
        if i == 0:
            continue
        prev = stages[i - 1]
        rate = s.get("rate_from_previous")
        if rate is None and prev["count"]:
            rate = s["count"] / prev["count"]
        drops.append({
            "from_step":  prev["step"],  "from_label": prev["label"],
            "to_step":    s["step"],     "to_label":   s["label"],
            "rate":       rate or 0,
            "lost":       max(0, prev["count"] - s["count"]),
        })

    # Pick the biggest leak. PV → PDP is excluded from the "worst" pick by
    # default because a low rate there is usually browsing behaviour
    # (people land on the homepage / collection and never click into a
    # product) rather than a fixable UX leak.
    non_browse_drops = [d for d in drops
                        if d["to_step"] != "total_product_view_events"]
    worst_drop = (min(non_browse_drops, key=lambda d: d["rate"])
                  if non_browse_drops
                  else (min(drops, key=lambda d: d["rate"]) if drops else None))

    orders_step = next((s for s in stages if s["step"] == "total_orders"), None)
    pv_step     = next((s for s in stages if s["step"] == "total_page_view_events"), None)
    summary = {
        "top_to_order_rate": ((orders_step["count"] / pv_step["count"])
                              if (orders_step and pv_step and pv_step["count"])
                              else 0),
        "worst_to_label":    worst_drop["to_label"] if worst_drop else None,
        "worst_rate":        worst_drop["rate"]     if worst_drop else None,
    }

    return {
        "stages":  stages,
        "drops":   drops,
        "summary": summary,
    }
