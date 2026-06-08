"""Go-deeper dock — store-aware follow-up prompts.

The pulse answers "is this store healthy today?" — it deliberately does NOT do
deep analysis. Each dock item routes the user to the skill that does, with a
ready-made prompt scoped to this store. In a live artifact clicking sends the
prompt (window.sendPrompt); otherwise it copies to the clipboard.

Which links appear is tailored to what the pulse saw: a flagged store leads with
diagnosis, a store running ads leads with scaling, etc. Capped so the dock stays
a short, confident set of next moves — not a menu.
"""

from __future__ import annotations


def build(summary, verdict, attention, limit=4):
    name = summary.get("store_name") or "this store"
    y = summary.get("yday") or {}
    has_spend = (y.get("spend") or 0) > 0
    flagged = verdict.get("class") in ("act", "watch")
    creative_flag = any("creative" in (i.get("title", "").lower()) for i in attention.get("items", []))

    items = []

    # Diagnosis first when the store is flagged.
    if flagged:
        items.append({
            "cmd": "/performance",
            "desc": "Diagnose what changed and why",
            "prompt": (f"Investigate {name}'s ad-account performance over the last 7 days. "
                       f"What changed versus the prior week, what's driving it, and what should I do next?"),
        })

    if has_spend:
        items.append({
            "cmd": "/scale-ads-profitably",
            "desc": "Find what to scale and at what cadence",
            "prompt": (f"For {name}, which ads should I scale profitably right now, by how much, "
                       f"and at what cadence — based on ROAS, spend headroom, and audience saturation?"),
        })

    items.append({
        "cmd": "/attribution",
        "desc": "Channel mix, journeys, and funnel leaks",
        "prompt": (f"Build the attribution overview for {name} — blended and per-platform contribution, "
                   f"customer journeys, and where the funnel is leaking."),
    })

    if creative_flag or has_spend:
        items.append({
            "cmd": "/creatives-report",
            "desc": "Spot fatigue and what to make next",
            "prompt": (f"Audit {name}'s ad creatives — which are fatiguing, which to refresh or kill, "
                       f"and what to produce next."),
        })

    if not flagged:
        items.append({
            "cmd": "/growth-report",
            "desc": "Score the full profitable-growth picture",
            "prompt": (f"Build the growth report for {name} — what's actually driving profitable growth "
                       f"this week, and what's working versus breaking?"),
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
