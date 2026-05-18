"""Channel co-occurrence insights — pure observation/action rules.

Reads the cooccurrence list from ``tool__get_platform_interactions`` and
emits a list of {obs, act} dicts surfacing the strongest cross-channel
pair, the most coupled channel, the most independent channel, and any
asymmetric A→B vs B→A dependency in the transitions.

Sample-size guard: a channel is skipped when it has fewer than
``MIN_SAMPLE`` attributed orders in the recent window (when the caller
passes ``orders_per_platform``). Without that data, every channel is fair
game.
"""

from __future__ import annotations


MIN_SAMPLE = 50


def _ins(obs: str, act: str) -> dict:
    return {"obs": obs, "act": act}


def insights(touchpoints: dict, orders_per_platform: dict | None = None) -> list[dict]:
    cooccur = (touchpoints or {}).get("cooccurrence") or []
    transitions = (touchpoints or {}).get("transitions") or []
    orders_per_platform = orders_per_platform or {}

    # TrackBee uses "facebook" in the platform funnel but "meta" in the
    # journey payload — normalise to "meta" for the sample-size guard.
    orders_normalised = dict(orders_per_platform)
    if "facebook" in orders_normalised:
        orders_normalised["meta"] = orders_normalised.pop("facebook")

    def _passes_sample(p: str) -> bool:
        if not orders_normalised:
            return True
        return int(orders_normalised.get(p, 0) or 0) >= MIN_SAMPLE

    # Pairwise overlap from cooccurrence — keep one direction per pair.
    pair_overlap: dict[tuple[str, str], float] = {}
    for row in cooccur:
        a, b = row.get("leading"), row.get("related")
        if not a or not b or a == "order" or b == "order":
            continue
        if not _passes_sample(a) or not _passes_sample(b):
            continue
        key = tuple(sorted([a, b]))
        share_pct = float(row.get("share_of_orders") or 0.0) * 100.0
        pair_overlap[key] = max(pair_overlap.get(key, 0.0), share_pct)

    co_pairs = sorted(pair_overlap.items(), key=lambda x: -x[1])

    # Per-channel total share across its appearances on any pair.
    channel_overlap: dict[str, float] = {}
    for (a, b), v in pair_overlap.items():
        channel_overlap[a] = channel_overlap.get(a, 0.0) + v
        channel_overlap[b] = channel_overlap.get(b, 0.0) + v

    most_coupled = max(channel_overlap.items(), key=lambda x: x[1]) if channel_overlap else (None, 0.0)
    most_independent = min(channel_overlap.items(), key=lambda x: x[1]) if channel_overlap else (None, 0.0)

    # Asymmetric dependency from directional transitions — pick the largest
    # gap between share_of_leading(A→B) and share_of_leading(B→A) where both
    # are positive and the gap exceeds 20 percentage points.
    leading_share: dict[tuple[str, str], float] = {}
    for row in transitions:
        a, b = row.get("leading"), row.get("related")
        if not a or not b or b == "order":
            continue
        if not _passes_sample(a):
            continue
        leading_share[(a, b)] = float(row.get("share_of_leading") or 0.0) * 100.0

    asym_best = None
    for (a, b), v_ab in leading_share.items():
        v_ba = leading_share.get((b, a), 0.0)
        if v_ba > 0 and (v_ab - v_ba) > 20:
            if asym_best is None or (v_ab - v_ba) > asym_best[2]:
                asym_best = (a, b, v_ab - v_ba, v_ab, v_ba)

    out: list[dict] = []
    if co_pairs:
        (a, b), v = co_pairs[0]
        out.append(_ins(
            f"<strong>{v:.1f}% of orders involve both {a.capitalize()} and {b.capitalize()}</strong> — "
            f"the most coupled channel pair on the store.",
            f"Treat {a.capitalize()} and {b.capitalize()} as a joint investment. Run an incrementality "
            f"test by pausing one for two weeks to measure the overlap."
        ))
    if most_independent[0] is not None and most_independent[1] < (most_coupled[1] or 0) * 0.5:
        p, v = most_independent
        out.append(_ins(
            f"<strong>{p.capitalize()}</strong> rarely overlaps with other channels.",
            f"{p.capitalize()} is the strongest standalone-acquisition channel. Use it as the baseline when "
            f"calibrating other channels' incremental contribution."
        ))
    if most_coupled[0] is not None and most_coupled[1] > 0:
        p, v = most_coupled
        out.append(_ins(
            f"<strong>{p.capitalize()}</strong> overlaps with other channels more than any other channel "
            f"in your stack.",
            f"Do not measure {p.capitalize()} on standalone ROAS. Its contribution comes from the assists "
            f"it provides to other channels."
        ))
    if asym_best:
        a, b, _gap, v_ab, v_ba = asym_best
        out.append(_ins(
            f"<strong>Asymmetric dependency: {a.capitalize()} → {b.capitalize()}</strong> "
            f"({v_ab:.0f}%) is far higher than the reverse ({v_ba:.0f}%).",
            f"{a.capitalize()} reliably leads shoppers into {b.capitalize()}, but the reverse is rare. "
            f"If consolidating spend, prioritise the lead-in channel."
        ))
    out.append(_ins(
        "Off-diagonal values quantify how often two channels appear in the same customer journey.",
        "Use this matrix to prioritise tests. High-overlap pairs benefit most from incrementality "
        "experiments; low-overlap pairs can be optimised independently."
    ))
    return out
