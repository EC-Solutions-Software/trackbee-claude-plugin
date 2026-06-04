"""Customer-journey transform: union the per-platform path breakdowns, build
the four sankey filter views, and derive the journey-shape stats the journey
insight component reads.

Journeys use a fixed 90-day server-side lookback and do not change with the
3d / 7d / 28d filter. Self-contained — stdlib only.
"""

MAX_DEPTH = 5
MAX_SEQ = 3  # truncate all journey paths to at most 3 touchpoints

PLATFORM_COLOR = {
    "meta": "#1877F2", "google": "#4285F4", "klaviyo": "#7C3AED",
    "tiktok": "#000000", "pinterest": "#E60023", "email": "#696E7C",
}


def _union(breakdowns):
    """Aggregate paths across the named breakdowns, collapsing to a 3-step
    prefix so paths sharing the same first three touches sum together."""
    seen = {}
    for b in breakdowns:
        for p in b.get("paths", []):
            seq = list(p["sequence"])[:MAX_SEQ]
            key = tuple(seq)
            seen[key] = seen.get(key, 0) + p["count"]
    return [{"sequence": list(k), "count": v} for k, v in seen.items()]


def build_sankey(paths):
    nodes, node_meta, flows = {}, [], {}

    def add_node(label, color):
        if label not in nodes:
            nodes[label] = len(node_meta)
            node_meta.append((label, color))
        return nodes[label]

    for p in paths:
        seq = list(p["sequence"])
        if len(seq) > MAX_DEPTH:
            seq = seq[:MAX_DEPTH]
        tagged = []
        for i, plat in enumerate(seq):
            label = f"{plat} @ step {i+1}"
            add_node(label, PLATFORM_COLOR.get(plat, "#9CA3AF"))
            tagged.append(label)
        add_node("Order", "#040F24")
        tagged.append("Order")
        for a, b in zip(tagged, tagged[1:]):
            k = (nodes[a], nodes[b])
            flows[k] = flows.get(k, 0) + p["count"]
    return {
        "labels": [n[0] for n in node_meta],
        "colors": [n[1] for n in node_meta],
        "source": [k[0] for k in flows],
        "target": [k[1] for k in flows],
        "value": list(flows.values()),
    }


def _wcount(items):
    out = {}
    for k, c in items:
        out[k] = out.get(k, 0) + c
    return out


def transform(breakdowns):
    """breakdowns: ordered list of per-platform journey payloads
    (meta, google, klaviyo, tiktok, pinterest, email)."""
    unioned = _union(breakdowns)

    multi_paths = [p for p in unioned if len(p["sequence"]) >= 2]
    single_paths = [p for p in unioned if len(p["sequence"]) == 1]
    top5_paths = sorted(unioned, key=lambda p: -p["count"])[:5]
    sankey_views = {
        "multi": build_sankey(multi_paths),
        "single": build_sankey(single_paths),
        "top5": build_sankey(top5_paths),
        "all": build_sankey(unioned),
    }

    opener = _wcount((p["sequence"][0], p["count"]) for p in unioned if len(p["sequence"]) > 1)
    closer = _wcount((p["sequence"][-1], p["count"]) for p in unioned if len(p["sequence"]) > 1)
    total_mt = sum(p["count"] for p in unioned if len(p["sequence"]) > 1)
    top_opener = max(opener.items(), key=lambda x: x[1]) if opener else (None, 0)
    top_closer = max(closer.items(), key=lambda x: x[1]) if closer else (None, 0)
    sorted_paths = sorted(unioned, key=lambda p: -p["count"])
    top_path = sorted_paths[0] if sorted_paths else None

    xplat = sum(p["count"] for p in unioned if len(p["sequence"]) > 1 and len(set(p["sequence"])) >= 2)
    xplat_share = xplat / total_mt if total_mt else 0

    depths = [len(p["sequence"]) for p in unioned for _ in range(p["count"])]
    depths.sort()
    median_depth = depths[len(depths) // 2] if depths else 0

    return {
        "unioned": unioned,
        "sankey_views": sankey_views,
        "stats": {
            "top_opener": top_opener, "top_closer": top_closer,
            "total_mt": total_mt, "top_path": top_path,
            "xplat_share": xplat_share, "median_depth": median_depth,
        },
    }
