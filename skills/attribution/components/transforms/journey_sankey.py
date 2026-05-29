"""Customer-journey sankey.

Reads per-channel journey patterns (one ``j_<platform>.json`` file per
channel, each the response of ``tool__get_platform_journeys(platform=...)``)
and pre-renders four sankey filter views as inline SVG:

  - "multi"  : journeys with 2+ channel touches
  - "top5"   : the 5 highest-share journeys overall
  - "single" : single-touch journeys
  - "all"    : every unique journey

Input shape per file: {"patterns": [{"pattern": ["<a>", "<b>", ..., "order"],
                                     "share_of_orders": 0.0..1.0}]}.

Output: {"views": {"multi": "<svg>", "top5": "<svg>", "single": "<svg>", "all": "<svg>"}}.
JS innerHTML-swaps the SVG for the active filter — no layout maths on the
client.
"""

from __future__ import annotations

import html as _html_mod
import re

MAX_DEPTH = 5

PLATFORM_COLOR = {
    "meta": "#1877F2",
    "google": "#4285F4",
    "klaviyo": "#7C3AED",
    "tiktok": "#000000",
    "pinterest": "#E60023",
    "email": "#737373",
    "bing": "#0078D7",
}

# Order (terminal) node uses TrackBee Navy (brand v3 #0D1245).
_NODE_COLORS = {
    **PLATFORM_COLOR,
    "Order": "#0D1245",
}


def _parse_sankey_label(lbl: str):
    """'meta @ step 1' -> ('meta', 1). 'Order' -> ('Order', None)."""
    m = re.match(r"^(.*?)\s*@\s*step\s*(\d+)$", lbl)
    if m:
        return m.group(1), int(m.group(2))
    return lbl, None


def _build_sankey(paths):
    """Build a sankey graph dict (labels/source/target/value) from a list of
    {sequence, weight} dicts. Sequence is truncated to MAX_DEPTH steps; a
    terminal 'Order' node is appended after every sequence so the diagram
    always lands on the conversion."""
    nodes: dict = {}
    node_meta: list = []
    flows: dict = {}

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
        add_node("Order", "#0D1245")
        tagged.append("Order")
        for a, b in zip(tagged, tagged[1:]):
            k = (nodes[a], nodes[b])
            flows[k] = flows.get(k, 0.0) + float(p["weight"])

    return {
        "labels": [n[0] for n in node_meta],
        "colors": [n[1] for n in node_meta],
        "source": [k[0] for k in flows],
        "target": [k[1] for k in flows],
        "value": list(flows.values()),
    }


def _render_sankey_svg(view: dict) -> str:
    """Render one sankey view as inline SVG. Nodes are grouped by step
    number, the terminal Order node lands in the rightmost column, and
    links are cubic-bezier paths coloured by source channel."""
    labels = view.get("labels", [])
    sources = view.get("source", [])
    targets = view.get("target", [])
    values = view.get("value", [])
    if not labels or not sources:
        return (
            '<div style="padding:24px;color:#737373;background:#FAFAFA;'
            'border:1px solid #E5E5E5;border-radius:8px;font-size:14px;'
            'font-family:\'Plus Jakarta Sans\', Inter, system-ui;'
            'text-align:center">No journeys match this filter.</div>'
        )
    parsed = [_parse_sankey_label(label_str) for label_str in labels]
    steps = [s for _, s in parsed if s is not None]
    max_step = max(steps) if steps else 1
    col_of = [max_step if plat == "Order" else (st - 1) for plat, st in parsed]
    n_cols = max_step + 1
    n = len(labels)

    W, H = 760, 720
    PAD_X, PAD_Y = 20, 20
    col_w = (W - 2 * PAD_X) / n_cols
    node_w = 14
    gap_y = 6

    in_v = [0.0] * n
    out_v = [0.0] * n
    for s, t, v in zip(sources, targets, values):
        out_v[s] += v
        in_v[t] += v
    node_total = [max(in_v[i], out_v[i]) for i in range(n)]

    nodes_in_col: dict = {c: [] for c in range(n_cols)}
    for i in range(n):
        nodes_in_col[col_of[i]].append(i)
    col_total = {c: sum(node_total[i] for i in nodes_in_col[c]) for c in nodes_in_col}
    max_col_total = max(col_total.values()) if col_total else 1
    avail_h = H - 2 * PAD_Y
    densest = max(col_total, key=col_total.get)
    n_gaps = max(0, len(nodes_in_col[densest]) - 1)
    y_scale = (avail_h - n_gaps * gap_y) / max_col_total if max_col_total else 0

    node_pos: dict = {}
    for c, ids in nodes_in_col.items():
        ids_sorted = sorted(ids, key=lambda i: -node_total[i])
        heights = [node_total[i] * y_scale for i in ids_sorted]
        total_h = sum(heights) + max(0, len(ids_sorted) - 1) * gap_y
        y_cursor = PAD_Y + (avail_h - total_h) / 2
        x_pos = PAD_X + c * col_w + (col_w - node_w) / 2
        for nid, hgt in zip(ids_sorted, heights):
            node_pos[nid] = (x_pos, y_cursor, y_cursor + hgt)
            y_cursor += hgt + gap_y

    src_off = {i: 0.0 for i in range(n)}
    tgt_off = {i: 0.0 for i in range(n)}
    link_paths: list = []
    for k in sorted(range(len(sources)), key=lambda k: -values[k]):
        s, t, v = sources[k], targets[k], values[k]
        if s not in node_pos or t not in node_pos:
            continue
        sx, sy0, _sy1 = node_pos[s]
        tx, ty0, _ty1 = node_pos[t]
        thick = v * y_scale
        sy = sy0 + src_off[s] + thick / 2
        ty = ty0 + tgt_off[t] + thick / 2
        src_off[s] += thick
        tgt_off[t] += thick
        x0 = sx + node_w
        x1 = tx
        cx0 = x0 + (x1 - x0) * 0.5
        cx1 = x0 + (x1 - x0) * 0.5
        plat = parsed[s][0]
        color = _NODE_COLORS.get(plat, "#9aa0aa")
        tip = (
            f"<strong>{_html_mod.escape(labels[s])} → "
            f"{_html_mod.escape(labels[t])}</strong>{v*100:.2f}% of orders"
        )
        link_paths.append(
            f'<path d="M{x0:.1f},{sy:.1f} C{cx0:.1f},{sy:.1f} '
            f'{cx1:.1f},{ty:.1f} {x1:.1f},{ty:.1f}" '
            f'stroke="{color}" stroke-opacity="0.28" '
            f'stroke-width="{max(thick, 1):.1f}" fill="none" '
            f'pointer-events="stroke" '
            f'data-tip="{tip}"></path>'
        )

    rects: list = []
    for i in range(n):
        if i not in node_pos:
            continue
        x_pos, y0, y1 = node_pos[i]
        plat = parsed[i][0]
        color = _NODE_COLORS.get(plat, "#737373")
        h = max(1.0, y1 - y0)
        rect_tip = (
            f"<strong>{_html_mod.escape(labels[i])}</strong>"
            f"{node_total[i]*100:.2f}% of orders"
        )
        rects.append(
            f'<rect x="{x_pos:.1f}" y="{y0:.1f}" width="{node_w}" '
            f'height="{h:.1f}" fill="{color}" rx="2" '
            f'data-tip="{rect_tip}"></rect>'
        )
        if h >= 12:
            last_col = col_of[i] == n_cols - 1
            lbl_x = x_pos - 6 if last_col else x_pos + node_w + 6
            anchor = "end" if last_col else "start"
            rects.append(
                f'<text x="{lbl_x:.1f}" y="{(y0+y1)/2 + 4:.1f}" font-size="12" '
                f'fill="#0D1245" text-anchor="{anchor}" font-weight="500" '
                f'font-family="Plus Jakarta Sans, Inter, system-ui">'
                f"{_html_mod.escape(labels[i])}</text>"
            )

    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Customer journey sankey">'
        f'<g>{"".join(link_paths)}</g>'
        f'<g>{"".join(rects)}</g>'
        f"</svg>"
    )


def _union_journeys(breakdowns: list[dict]) -> list[dict]:
    """Merge per-platform journey breakdowns into a deduplicated list of
    {sequence, weight} dicts. A given sequence may appear in several
    per-channel breakdowns — keep the first observed share to avoid
    double-counting it across channels."""
    seen: dict = {}
    for b in breakdowns:
        for p in (b or {}).get("patterns", []):
            pattern = p.get("pattern") or []
            # Strip the trailing "order" sentinel — _build_sankey re-adds it.
            seq = [step for step in pattern if step != "order"]
            share = p.get("share_of_orders")
            if not seq or share is None:
                continue
            key = tuple(seq)
            if key not in seen:
                seen[key] = float(share)
    return [{"sequence": list(k), "weight": v} for k, v in seen.items()]


def transform(inputs: dict, config: dict) -> dict:
    del config

    # Collect every per-channel journey breakdown the orchestrator supplied.
    # Keys look like ``j_meta``, ``j_google``, … one per channel.
    breakdowns = [v for k, v in inputs.items() if k.startswith("j_")]
    unioned = _union_journeys(breakdowns)

    multi_paths = [p for p in unioned if len(p["sequence"]) >= 2]
    single_paths = [p for p in unioned if len(p["sequence"]) == 1]
    top5_paths = sorted(unioned, key=lambda p: -p["weight"])[:5]

    graphs = {
        "multi": _build_sankey(multi_paths),
        "single": _build_sankey(single_paths),
        "top5": _build_sankey(top5_paths),
        "all": _build_sankey(unioned),
    }
    views = {k: _render_sankey_svg(g) for k, g in graphs.items()}

    return {
        "views": views,
        # The orchestrator pops these before exposing the payload to the
        # browser — they're a private side-channel so the journey insights
        # module can read the same paths the SVG was built from.
        "_paths": unioned,
        "_multi_paths": multi_paths,
    }
