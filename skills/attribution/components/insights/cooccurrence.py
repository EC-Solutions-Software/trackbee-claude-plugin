"""Channel touch-point (co-occurrence) insights for the Attribution Overview
report — most-coupled pair, channels that never convert alone, channels that
can stand alone, and asymmetric dependencies. A per-platform order-count
sample guard excludes thin channels. Pure string formatting — self-contained,
stdlib only.
"""


def _ins(obs, act):
    return {"obs": obs, "act": act}


def build(touchpoints, plat_orders_28d, min_sample=50):
    co = touchpoints["co_occurrence"]

    co_pairs = []
    for src_p, row in co.items():
        if src_p == "no_platform" or plat_orders_28d.get(src_p, 0) < min_sample:
            continue
        for tgt_p, v in row.items():
            if tgt_p == "no_other_platform" or tgt_p == src_p:
                continue
            co_pairs.append(((src_p, tgt_p), v))
    co_pairs.sort(key=lambda x: -x[1])

    isolation = {p: row.get("no_other_platform", 0) for p, row in co.items()
                 if p != "no_platform" and plat_orders_28d.get(p, 0) >= min_sample}
    most_isolated = max(isolation.items(), key=lambda x: x[1]) if isolation else (None, 0)
    least_isolated = min(isolation.items(), key=lambda x: x[1]) if isolation else (None, 0)

    asym_best = None
    for (a, b), v in co_pairs:
        rev_v = co.get(b, {}).get(a, 0)
        if rev_v > 0 and (v - rev_v) > 20:
            if asym_best is None or (v - rev_v) > asym_best[2]:
                asym_best = (a, b, v - rev_v, v, rev_v)

    out = []
    if co_pairs:
        a, b = co_pairs[0][0]
        v = co_pairs[0][1]
        out.append(_ins(
            f"<strong>{v:.0f}% of customers who interact with {a.capitalize()} also interact with {b.capitalize()}</strong> — "
            f"the most coupled pair on the store.",
            f"Treat {a.capitalize()} and {b.capitalize()} as a joint investment. Run an incrementality "
            f"test by pausing one for two weeks to measure overlap."
        ))
    if least_isolated[0]:
        p, v = least_isolated
        out.append(_ins(
            f"<strong>{p.capitalize()}</strong> rarely converts in isolation: only {v:.1f}% of "
            f"{p.capitalize()} journeys have no other tracked touchpoint.",
            f"Do not measure {p.capitalize()} on standalone ROAS. Its contribution comes from the assists "
            f"it provides to other channels."
        ))
    if most_isolated[0] and most_isolated[1] > 20:
        p, v = most_isolated
        out.append(_ins(
            f"<strong>{p.capitalize()}</strong> can convert independently: {v:.1f}% of its journeys involve "
            f"no other channel.",
            f"{p.capitalize()} is the strongest standalone-acquisition channel. Use it as the baseline when "
            f"calibrating other channels' incremental contribution."
        ))
    if asym_best:
        a, b, gap, v_ab, v_ba = asym_best
        out.append(_ins(
            f"<strong>Asymmetric dependency: {a.capitalize()} → {b.capitalize()}</strong> ({v_ab:.0f}%) "
            f"is far higher than the reverse ({v_ba:.0f}%).",
            f"{a.capitalize()} relies on {b.capitalize()} more than {b.capitalize()} relies on {a.capitalize()}. "
            f"If consolidating spend, cut {a.capitalize()} before {b.capitalize()}."
        ))
    out.append(_ins(
        f"Off-diagonal values quantify how often two channels appear in the same customer journey.",
        f"Use this matrix to prioritise tests. High-overlap pairs benefit most from incrementality "
        f"experiments; low-overlap pairs can be optimised independently."
    ))
    return out
