"""Customer-journey insights (the sankey companion list) for the Attribution
Overview report. Built from the journey-shape stats and the touchpoint
summary. Pure string formatting — self-contained, stdlib only.

Each line states a measured journey figure (opener/closer share, top path,
cross-channel share, median depth, single-touch share); no recommended action
is attached.
"""


def _ins(obs, act=""):
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
            f"({int(top_opener[1]):,} of {total_mt:,})."
        ))
    if top_closer[0]:
        pct = top_closer[1] / total_mt * 100 if total_mt else 0
        out.append(_ins(
            f"<strong>{top_closer[0].capitalize()}</strong> closes {pct:.1f}% of multi-touch journeys."
        ))
    if top_path:
        seq = " → ".join(s.capitalize() for s in top_path["sequence"]) + " → Order"
        out.append(_ins(
            f"The most frequent journey is <strong>{seq}</strong> ({top_path['count']:,} converted journeys)."
        ))
    out.append(_ins(
        f"<strong>{xplat_share*100:.1f}%</strong> of multi-touch journeys involve two or more channels."
    ))
    out.append(_ins(
        f"Median journey depth is <strong>{median_depth} touches</strong>."
    ))
    out.append(_ins(
        f"<strong>{touchpoints['single_touch_share']*100:.1f}%</strong> of orders are single-touch — "
        f"these do not appear in the multi-touch path map."
    ))
    return out
