"""Customer-journey insights — pure observation/action rules.

Reads the deduplicated union of journey sequences (assembled by
journey_sankey from per-channel ``tool__get_platform_journeys`` payloads)
plus the channel-interactions envelope shares, and emits a list of
{obs, act} dicts about openers, closers, top journey, cross-channel
share, median depth, single-touch share, and organic share.

Weights are shares of orders (0.0..1.0) — listed shares across journeys
will not sum to 1.0 because only short, interpretable paths are surfaced
by the journeys tool.
"""

from __future__ import annotations


def _ins(obs: str, act: str) -> dict:
    return {"obs": obs, "act": act}


def _weighted(items) -> dict:
    out: dict = {}
    for k, w in items:
        out[k] = out.get(k, 0.0) + w
    return out


def insights(unioned_paths: list[dict], touchpoints: dict) -> list[dict]:
    """unioned_paths: [{sequence: [...], weight: float}] deduped across channels.
    touchpoints: the channel-interactions payload — envelope shares only."""
    unioned = unioned_paths or []
    touchpoints = touchpoints or {}

    multi = [p for p in unioned if len(p["sequence"]) > 1]
    total_mt_weight = sum(p["weight"] for p in multi)

    opener = _weighted((p["sequence"][0], p["weight"]) for p in multi)
    closer = _weighted((p["sequence"][-1], p["weight"]) for p in multi)
    top_opener = max(opener.items(), key=lambda x: x[1]) if opener else (None, 0.0)
    top_closer = max(closer.items(), key=lambda x: x[1]) if closer else (None, 0.0)
    sorted_paths = sorted(unioned, key=lambda p: -p["weight"])
    top_path = sorted_paths[0] if sorted_paths else None

    xplat_weight = sum(p["weight"] for p in multi if len(set(p["sequence"])) >= 2)
    xplat_share = xplat_weight / total_mt_weight if total_mt_weight else 0

    # Weighted median journey depth — bucket weights by depth, walk cumulative
    # share until 50%.
    depth_weight: dict[int, float] = {}
    for p in unioned:
        depth_weight[len(p["sequence"])] = depth_weight.get(len(p["sequence"]), 0.0) + p["weight"]
    total_w = sum(depth_weight.values())
    median_depth = 0
    if total_w:
        running = 0.0
        for d in sorted(depth_weight):
            running += depth_weight[d]
            if running >= total_w / 2:
                median_depth = d
                break

    single_touch_share = float(touchpoints.get("single_touch_share") or 0.0)
    organic_share = float(touchpoints.get("organic_share") or 0.0)

    out: list[dict] = []
    if top_opener[0]:
        pct = top_opener[1] / total_mt_weight * 100 if total_mt_weight else 0
        out.append(_ins(
            f"<strong>{top_opener[0].capitalize()}</strong> opens {pct:.1f}% of multi-touch journeys. "
            f"It is the dominant top-of-funnel channel.",
            f"Evaluate {top_opener[0].capitalize()} on its assist contribution, not last-click ROAS. "
            f"Cutting upper-funnel spend often surfaces as drops in other channels' performance 30–60 days later."
        ))
    if top_closer[0]:
        pct = top_closer[1] / total_mt_weight * 100 if total_mt_weight else 0
        out.append(_ins(
            f"<strong>{top_closer[0].capitalize()}</strong> closes {pct:.1f}% of multi-touch journeys.",
            f"A high closer share does not equal incremental contribution. Run a holdout test on {top_closer[0].capitalize()} "
            f"to measure the orders that would have happened anyway."
        ))
    if top_path:
        seq = " → ".join(s.capitalize() for s in top_path["sequence"]) + " → Order"
        out.append(_ins(
            f"The most frequent journey is <strong>{seq}</strong> ({top_path['weight']*100:.1f}% of orders).",
            "Optimise creative and retargeting around this sequence. It is the highest-volume path to revenue."
        ))
    out.append(_ins(
        f"<strong>{xplat_share*100:.1f}%</strong> of multi-touch journeys involve two or more channels.",
        "Channels operate as a portfolio. Use the touch-points matrix below to identify which pairs are "
        "interdependent before adjusting budgets."
    ))
    out.append(_ins(
        f"Median journey depth is <strong>{median_depth} touch{'es' if median_depth != 1 else ''}</strong>.",
        "Plan retargeting frequency caps around this depth. Capping below the median risks missing the closer touch."
    ))
    out.append(_ins(
        f"<strong>{single_touch_share*100:.1f}%</strong> of orders are single-touch.",
        "These conversions do not appear in the path map. Treat the sankey as a multi-touch view, not a "
        "complete picture of acquisition."
    ))
    if organic_share > 0:
        out.append(_ins(
            f"<strong>{organic_share*100:.1f}%</strong> of orders had no tracked ad touch.",
            "These are direct / organic / untagged conversions. A high share here may signal underinvestment "
            "in paid acquisition or a tracking gap upstream."
        ))
    return out
