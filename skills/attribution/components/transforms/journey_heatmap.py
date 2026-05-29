"""Channel touch-points heatmap.

Reads the channel-interactions payload (saved as ``touchpoints.json``) and
returns the heatmap as a pre-rendered HTML <table> string with inline
background colours. Each off-diagonal cell shows the share of orders in
which BOTH the row channel and the column channel appeared anywhere in the
shopper's path. The diagonal is a visual marker only — per-channel
single-touch share is not in the interactions payload.

Input shape (channel-interactions payload assembled in
``touchpoints.json`` from ``tool__get_platform_footprints`` + per-platform
``tool__get_platform_breakdown``):

  cooccurrence = [
    {"leading": "<a>", "related": "<b>", "share_of_orders": 0.0..1.0},
    ...
  ]
  transitions = [
    {"leading": "<a>", "related": "<b>" | "order",
     "share_of_leading": 0.0..1.0, "share_of_orders": 0.0..1.0},
    ...
  ]

Output: {"html": "<table>...</table>", "platforms": [...], "columns": [...], "low_sample": [...]}
"""

from __future__ import annotations


_PREFERRED_ORDER = ["meta", "google", "klaviyo", "email", "tiktok", "pinterest", "bing"]
_MIN_SAMPLE = 50


def _heatmap_cell(value: float, is_diag: bool) -> str:
    if is_diag:
        return "<td class='hcell diag'>—</td>"
    # Brand v3 heatmap gradient: Lavender #F0F2FF (low) → Navy #0D1245 (high).
    # Lavender is the soft brand fill, navy is the brand body-text/CTA color —
    # both live on the brand display palette, so the heatmap reads as TrackBee.
    t = max(0.0, min(1.0, value / 100.0))
    r = int(0xF0 + t * (0x0D - 0xF0))
    g = int(0xF2 + t * (0x12 - 0xF2))
    b = int(0xFF + t * (0x45 - 0xFF))
    txt = "#0D1245" if t < 0.55 else "#FFFFFF"
    return (
        f"<td class='hcell' style='background:rgb({r},{g},{b});color:{txt}'>"
        f"{value:.1f}%</td>"
    )


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _platforms_from(touchpoints: dict) -> list[str]:
    """Union of every channel that appears as leading or related in the payload."""
    seen: list[str] = []
    for bucket in ("cooccurrence", "transitions"):
        for row in touchpoints.get(bucket) or []:
            for side in ("leading", "related"):
                name = row.get(side)
                if not name or name == "order" or name == "organic":
                    continue
                if name not in seen:
                    seen.append(name)
    return seen


def transform(inputs: dict, config: dict) -> dict:
    del config
    touchpoints: dict = inputs.get("touchpoints") or {}

    platforms = _platforms_from(touchpoints)

    # Pairwise overlap from cooccurrence — share_of_orders for each {a, b} pair.
    overlap: dict[tuple[str, str], float] = {}
    for row in touchpoints.get("cooccurrence") or []:
        a, b = row.get("leading"), row.get("related")
        if not a or not b or a == "order" or b == "order":
            continue
        share = float(row.get("share_of_orders") or 0.0) * 100.0
        overlap[(a, b)] = share
        overlap.setdefault((b, a), share)

    # The diagonal renders as 0 by design. Per-channel single-touch share
    # is not in the channel-interactions payload — only the cross-store
    # `single_touch_share` envelope value is — and we don't fabricate a
    # per-channel approximation. The diagonal is treated as a structural
    # marker in the grid (styled with the brand fill in `_heatmap_cell`)
    # rather than a data value.

    # Ordering: well-known first, then any others.
    ordered = [p for p in _PREFERRED_ORDER if p in platforms]
    ordered += [p for p in platforms if p not in _PREFERRED_ORDER]
    rows = cols = ordered

    parts: list[str] = ["<table class='heatmap'>"]
    parts.append("<tr><th></th>" + "".join(f"<th>{_pretty(c)}</th>" for c in cols) + "</tr>")
    for rk in rows:
        cells: list[str] = []
        for ck in cols:
            if rk == ck:
                v = 0.0  # diagonal — see comment above
                cells.append(_heatmap_cell(v, is_diag=True))
            else:
                v = overlap.get((rk, ck), 0.0)
                cells.append(_heatmap_cell(v, is_diag=False))
        parts.append(f"<tr><th>{_pretty(rk)}</th>{''.join(cells)}</tr>")
    parts.append("</table>")

    low_sample: list[str] = []
    orders_per_platform = inputs.get("orders_per_platform") or {}
    for p, n in orders_per_platform.items():
        if p == "no_platform":
            continue
        try:
            n_int = int(n)
        except (TypeError, ValueError):
            continue
        if 0 < n_int < _MIN_SAMPLE:
            low_sample.append(p)

    return {
        "html": "\n".join(parts),
        "platforms": rows,
        "columns": cols,
        "low_sample": low_sample,
    }
