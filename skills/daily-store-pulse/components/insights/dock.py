"""Go-deeper dock — store-aware follow-up prompts.

The pulse answers "is this store healthy today?" — it deliberately does NOT do
deep analysis. Each dock item routes the user to the skill that does, with a
ready-made prompt scoped to this store. In a live artifact clicking sends the
prompt (window.sendPrompt); otherwise it copies to the clipboard.

Which links appear is tailored to what the pulse saw: a flagged store leads with
diagnosis, a store running ads leads with its ad metrics, etc. Capped so the
dock stays a short set of next analyses to pull — not a menu.
"""

from __future__ import annotations


def build(summary, attention, limit=4):
    name = summary.get("store_name") or "this store"
    y = summary.get("yday") or {}
    has_spend = (y.get("spend") or 0) > 0
    # "Flagged" means the store has at least one high/medium anomaly or
    # spend-efficiency recommendation today — derived from the (factual)
    # attention list, not from a verdict classifier.
    flagged = (attention.get("high", 0) + attention.get("medium", 0)) > 0
    creative_flag = any("creative" in (i.get("title", "").lower()) for i in attention.get("items", []))

    items = []

    # Diagnosis first when the store is flagged.
    if flagged:
        items.append({
            "cmd": "/performance",
            "desc": "See what changed and why",
            "prompt": (f"Show {name}'s ad-account performance over the last 7 days. "
                       f"What changed versus the prior week, broken down by campaign and metric?"),
        })

    if has_spend:
        items.append({
            "cmd": "/scale-ads-profitably",
            "desc": "See per-ad ROAS, headroom, and saturation",
            "prompt": (f"For {name}, show each ad's ROAS, spend, frequency, and new-customer share, "
                       f"and how efficiency tracks with spend level."),
        })

    items.append({
        "cmd": "/attribution",
        "desc": "Channel mix, journeys, and funnel rates",
        "prompt": (f"Build the attribution overview for {name} — blended and per-platform contribution, "
                   f"customer journeys, and the conversion rate at each funnel step."),
    })

    if creative_flag or has_spend:
        items.append({
            "cmd": "/creatives-report",
            "desc": "See per-creative fatigue metrics",
            "prompt": (f"Audit {name}'s ad creatives — show CTR, frequency, ROAS, and spend per creative "
                       f"and how each has trended over time."),
        })

    if not flagged:
        items.append({
            "cmd": "/growth-report",
            "desc": "See the full profitable-growth metrics",
            "prompt": (f"Build the growth report for {name} — the full metric framework with this week's "
                       f"values versus last week and the week-over-week change for each."),
        })

    # De-dup by command, preserve order, cap.
    seen = set()
    deduped = []
    for it in items:
        if it["cmd"] in seen:
            continue
        seen.add(it["cmd"])
        deduped.append(it)
    return deduped[:limit]
