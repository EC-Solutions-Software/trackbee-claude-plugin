"""Inline SVG renderer for the customer-journey sankey.

Pre-rendered server-side (column-based layout, cubic-bezier links coloured by
source platform, hover tooltips via data-tip) so the page needs no external
chart library. Self-contained — stdlib only.
"""

import html as _html_mod
import re

_SVG_PLATFORM_COLORS = {
    "meta": "#1877F2",
    "google": "#4285F4",
    "klaviyo": "#7C3AED",
    "tiktok": "#000000",
    "pinterest": "#E60023",
    "email": "#737373",
    "bing": "#0078D7",
    "Order": "#0D1245",
    "ORDER": "#0D1245",
}


def _parse_sankey_label(lbl):
    """'meta @ step 1' -> ('meta', 1). 'Order' -> ('Order', None)."""
    m = re.match(r"^(.*?)\s*@\s*step\s*(\d+)$", lbl)
    if m:
        return m.group(1), int(m.group(2))
    return lbl, None


def render_sankey_svg(view):
    """Render a sankey diagram for a single SANKEY_VIEWS entry as SVG.

    Layout is column-based: nodes are grouped by step number (1, 2, 3 ...)
    and Order goes in the rightmost column. Links are cubic-bezier paths
    coloured by source platform. Tooltips on rect and path via data-tip.
    """
    labels = view.get("labels", [])
    sources = view.get("source", [])
    targets = view.get("target", [])
    values = view.get("value", [])
    if not labels or not sources:
        return ('<div style="padding:24px;color:#737373;background:#FAFAFA;'
                'border:1px solid #E5E5E5;border-radius:8px;font-size:13px;'
                'text-align:center">No journeys match this filter.</div>')
    parsed = [_parse_sankey_label(l) for l in labels]
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

    nodes_in_col = {c: [] for c in range(n_cols)}
    for i in range(n):
        nodes_in_col[col_of[i]].append(i)
    col_total = {c: sum(node_total[i] for i in nodes_in_col[c]) for c in nodes_in_col}
    max_col_total = max(col_total.values()) if col_total else 1
    avail_h = H - 2 * PAD_Y
    densest = max(col_total, key=col_total.get)
    n_gaps = max(0, len(nodes_in_col[densest]) - 1)
    y_scale = (avail_h - n_gaps * gap_y) / max_col_total if max_col_total else 0

    node_pos = {}
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
    link_paths = []
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
        color = _SVG_PLATFORM_COLORS.get(plat, "#737373")
        tip = (
            f'<strong>{_html_mod.escape(labels[s])} → '
            f'{_html_mod.escape(labels[t])}</strong>{int(v):,} journeys'
        )
        link_paths.append(
            f'<path d="M{x0:.1f},{sy:.1f} C{cx0:.1f},{sy:.1f} '
            f'{cx1:.1f},{ty:.1f} {x1:.1f},{ty:.1f}" '
            f'stroke="{color}" stroke-opacity="0.28" '
            f'stroke-width="{max(thick, 1):.1f}" fill="none" '
            f'pointer-events="stroke" '
            f'data-tip="{tip}"></path>'
        )

    rects = []
    for i in range(n):
        if i not in node_pos:
            continue
        x_pos, y0, y1 = node_pos[i]
        plat = parsed[i][0]
        color = _SVG_PLATFORM_COLORS.get(plat, "#737373")
        h = max(1.0, y1 - y0)
        rect_tip = (
            f'<strong>{_html_mod.escape(labels[i])}</strong>'
            f'{int(node_total[i]):,} journeys'
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
                f'<text x="{lbl_x:.1f}" y="{(y0+y1)/2 + 4:.1f}" font-size="11" '
                f'fill="#0D1245" text-anchor="{anchor}" '
                f'font-family="Plus Jakarta Sans, system-ui">'
                f'{_html_mod.escape(labels[i])}</text>'
            )

    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Customer journey sankey">'
        f'<g>{"".join(link_paths)}</g>'
        f'<g>{"".join(rects)}</g>'
        f'</svg>'
    )
