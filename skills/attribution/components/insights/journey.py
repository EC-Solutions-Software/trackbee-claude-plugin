"""Customer-journey insights (the sankey companion list) for the Attribution
Overview report. Built from the journey-shape stats and the touchpoint
summary. Pure string formatting — self-contained, stdlib only.
"""


def _ins(obs, act):
    return {"obs": obs, "act": act}


def build(stats, touchpoints):
    top_opener = stats["top_opener"]
    top_closer = stats["top_closer"]
    total_mt = stats["total_mt"]
    top_path = stats["top_path"]
    xplat_share = stats["xplat_share"]
    median_depth = stats["median_depth"]

    out = []
    if top_opener[0]:
        pct = top_opener[1] / total_mt * 100 if total_mt else 0
        out.append(_ins(
            f"<strong>{top_opener[0].capitalize()}</strong> initiates {pct:.1f}% of multi-touch journeys "
            f"({int(top_opener[1]):,} of {total_mt:,}). It is the dominant top-of-funnel channel.",
            f"Evaluate {top_opener[0].capitalize()} on its assist contribution, not last-click ROAS. "
            f"Cutting upper-funnel spend often surfaces as drops in other channels' performance 30–60 days later."
        ))
    if top_closer[0]:
        pct = top_closer[1] / total_mt * 100 if total_mt else 0
        out.append(_ins(
            f"<strong>{top_closer[0].capitalize()}</strong> closes {pct:.1f}% of multi-touch journeys.",
            f"A high closer share does not equal incremental contribution. Run a holdout test on {top_closer[0].capitalize()} "
            f"to measure the orders that would have happened anyway."
        ))
    if top_path:
        seq = " → ".join(s.capitalize() for s in top_path["sequence"]) + " → Order"
        out.append(_ins(
            f"The most frequent journey is <strong>{seq}</strong> ({top_path['count']:,} converted journeys).",
            f"Optimise creative and retargeting around this sequence. It is the highest-volume path to revenue."
        ))
    out.append(_ins(
        f"<strong>{xplat_share*100:.1f}%</strong> of multi-touch journeys involve two or more channels.",
        f"Channels operate as a portfolio. Use the touch-points matrix below to identify which pairs are "
        f"interdependent before adjusting budgets."
    ))
    out.append(_ins(
        f"Median journey depth is <strong>{median_depth} touches</strong>.",
        f"Plan retargeting frequency caps around this depth. Capping below the median risks missing the closer touch."
    ))
    out.append(_ins(
        f"<strong>{touchpoints['single_touch_share']*100:.1f}%</strong> of orders are single-touch.",
        f"These conversions do not appear in the path map. Treat the sankey as a multi-touch view, not a "
        f"complete picture of acquisition."
    ))
    return out
