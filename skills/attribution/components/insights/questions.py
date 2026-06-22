"""Suggested follow-up questions for the Attribution Overview report — the
clickable "Where to go next" prompts. Computed from the 28d window so the
copy references the store's real top channel, biggest funnel leak, etc.

In a live artifact (``window.sendPrompt`` defined) clicking sends the prompt;
otherwise the card copies it to the clipboard. Pure string formatting —
self-contained, stdlib only.
"""


def build(ref, has_profiles, top_opener):
    """ref: the assembled 28d window dict. top_opener: (platform, count)."""
    ref_paying = [r for r in ref["channels"] if r.get("spend", 0) > 0 and r["channel"] != "Overall"]
    ref_worst = ref["funnel_summary"]
    ref_top_paying = max(ref_paying, key=lambda r: r["spend"]) if ref_paying else None
    ref_best_roas = max((r for r in ref_paying if r.get("roas")),
                        key=lambda r: r["roas"], default=None)
    ref_top_channel = max(
        (r for r in ref["channels"] if r["channel"] != "Overall"),
        key=lambda r: ((r.get("rev_in") if r.get("rev_in") is not None else r.get("rev_tb")) or 0),
        default=None,
    )

    out = []

    # 1) Funnel deep-dive (always present — the headline section).
    if ref_worst.get("worst_to_label") and ref_worst.get("worst_rate") is not None:
        out.append({
            "label": "Break down the biggest funnel leak",
            "prompt": (
                f"My biggest funnel drop in the last 28 days is between the previous step and "
                f"{ref_worst['worst_to_label']} at {(ref_worst['worst_rate'] or 0)*100:.1f}% conversion. "
                f"Break this step down by device, channel, and new-vs-returning visitors, and show how "
                f"the conversion rate at this step has trended over the window."
            ),
        })

    # 2) Top paying channel — surface its per-campaign figures.
    if ref_top_paying and (ref_top_paying.get("roas") or 0) >= 1.5:
        out.append({
            "label": f"Break down {ref_top_paying['channel']} campaigns",
            "prompt": (
                f"Show me the campaign-level breakdown for {ref_top_paying['channel']} over the last 28 days. "
                f"Group by campaign objective and show spend, ROAS, and the new-vs-returning ROAS split "
                f"for each campaign."
            ),
        })
    elif ref_best_roas:
        out.append({
            "label": f"Break down {ref_best_roas['channel']}",
            "prompt": (
                f"{ref_best_roas['channel']} is showing the highest ROAS of any paid channel "
                f"({ref_best_roas['roas']:.2f}x). Show its current spend, ROAS, frequency, and CPM, and how "
                f"each has trended across the spend levels it has run at over the last 28 days."
            ),
        })

    # 3) Channel reconciliation — always relevant.
    out.append({
        "label": "Reconcile platform vs. TrackBee numbers",
        "prompt": (
            "Why do my Meta and Google in-platform purchase/revenue numbers differ from what TrackBee "
            "reports? Break down the most likely sources of the gap (attribution windows, view-through, "
            "click-id matching, deduping) and quantify how much of the gap each source accounts for."
        ),
    })

    # 4) Journey-led question if profiles exist, otherwise a creative-led one.
    if has_profiles and top_opener[0]:
        out.append({
            "label": f"Measure {top_opener[0].capitalize()} incrementality",
            "prompt": (
                f"{top_opener[0].capitalize()} starts most multi-touch journeys on my store. Design a "
                f"holdout or geo-lift test I could run in the next 4 weeks to measure its true incremental "
                f"contribution, with sample-size guidance and a success threshold."
            ),
        })
    elif ref_top_channel:
        out.append({
            "label": f"Why is {ref_top_channel['channel']} my top channel?",
            "prompt": (
                f"{ref_top_channel['channel']} is the largest revenue contributor in the last 28 days. "
                f"Pull the creative-level breakdown so I can see which ads and audiences are driving it, "
                f"and show CTR, frequency, and ROAS per creative over time."
            ),
        })

    return out[:4]
