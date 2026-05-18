"""Channel touch-points heatmap.

Reads the channel-interactions payload (saved as ``touchpoints.json``) and
returns the heatmap as a pre-rendered HTML <table> string with inline
background colours. Each off-diagonal cell shows the share of orders in
which BOTH the row channel and the column channel appeared anywhere in the
shopper's path. The diagonal shows the share of orders where the same
channel touched the shopper more than once in the same path — pulled from
the ``<X> -> <X>`` self-loop rows in ``transitions[]``.

Input shape (from ``tool__get_platform_interactions``):

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
        return f"<td class='hcell diag'>{value:.1f}%</td>"
    t = max(0.0, min(1.0, value / 100.0))
    r = int(0xDF + t * (0x00 - 0xDF))
    g = int(0xEA + t * (0x72 - 0xEA))
    b = int(0xFB + t * (0xFF - 0xFB))
    txt = "#040F24" if t < 0.55 else "#FFFFFF"
    return (
        f"<td class='hcell' style='background:rgb({r},{g},{b});color:{txt}'>"
        f"{value:.1f}%</td>"
    )


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _platforms_from(touchpoints: dict) -> list[str]:
    """Union of every channel in the payload.

    ``transitions`` rows are directional and use ``leading``/``related``;
    ``cooccurrence`` rows are symmetric and use ``a``/``b``. We walk all
    four keys so channels that appear only in cooccurrence (not in
    transitions) still make the list.
    """
    seen: list[str] = []
    for bucket in ("cooccurrence", "transitions"):
        for row in touchpoints.get(bucket) or []:
            for side in ("leading", "related", "a", "b"):
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

    # Pairwise overlap from cooccurrence — share_of_orders for each {a, b}
    # pair. cooccurrence rows are symmetric and use "a"/"b"; we also accept
    # "leading"/"related" as a fallback in case a future payload variant
    # reuses the directional keys for symmetric pairs.
    overlap: dict[tuple[str, str], float] = {}
    for row in touchpoints.get("cooccurrence") or []:
        a = row.get("a") or row.get("leading")
        b = row.get("b") or row.get("related")
        if not a or not b or a == "order" or b == "order":
            continue
        share = float(row.get("share_of_orders") or 0.0) * 100.0
        overlap[(a, b)] = share
        overlap.setdefault((b, a), share)

    # Per-channel self-cooccurrence — the diagonal. The interactions payload
    # exposes ``<X> -> <X>`` self-loop rows in ``transitions[]``, where
    # ``share_of_orders`` is the fraction of all orders whose path contains
    # a self-transition (i.e. the channel touched the shopper more than
    # once). This is the natural mate of the off-diagonal cooccurrence
    # values: it answers "what share of orders saw this channel touch more
    # than once?". Channels with no self-loop row (one-touch-only channels
    # like shop_app or judgeme) correctly stay at 0.0% — that's accurate.
    self_share: dict[str, float] = {}
    for row in touchpoints.get("transitions") or []:
        a = row.get("leading")
        b = row.get("related")
        if not a or a != b or a in ("order", "organic"):
            continue
        self_share[a] = float(row.get("share_of_orders") or 0.0) * 100.0

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
                v = self_share.get(rk, 0.0)
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
