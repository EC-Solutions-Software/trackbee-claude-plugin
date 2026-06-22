"""Channel touch-points heatmap (co-occurrence matrix) + the small-sample
footer caveat for the Attribution Overview report.

Rows and columns are derived from the touchpoint matrix itself, with the
well-known platforms pinned first for readability, so any customer's actual
channel mix renders. Self-contained — stdlib only.
"""

_PREFERRED_ORDER = ["meta", "google", "klaviyo", "email", "tiktok", "pinterest", "bing"]


def _heatmap_cell(value, is_diag):
    if is_diag:
        return f"<td class='hcell diag'>{value:.1f}%</td>"
    t = max(0, min(1, value / 100))
    r = int(0xF0 + t * (0x00 - 0xF0))
    g = int(0xF2 + t * (0x66 - 0xF2))
    b = int(0xFF + t * (0xCC - 0xFF))
    txt = "#0D1245" if t < 0.55 else "#FFFFFF"
    return f"<td class='hcell' style='background:rgb({r},{g},{b});color:{txt}'>{value:.1f}%</td>"


def transform(touchpoints, plat_orders_28d, min_sample=50):
    co = touchpoints.get("co_occurrence", {}) or {}
    all_row_keys = list(co.keys())
    heatmap_rows = (
        [p for p in _PREFERRED_ORDER if p in co]
        + [p for p in all_row_keys if p not in _PREFERRED_ORDER and p != "no_platform"]
    )
    if "no_platform" in co:
        heatmap_rows.append("no_platform")

    seen_cols = []
    for r in co.values():
        for c in r.keys():
            if c not in seen_cols:
                seen_cols.append(c)
    heatmap_cols = (
        [p for p in _PREFERRED_ORDER if p in seen_cols]
        + [c for c in seen_cols if c not in _PREFERRED_ORDER and c != "no_other_platform"]
    )
    if "no_other_platform" in seen_cols:
        heatmap_cols.append("no_other_platform")

    html = ["<table class='heatmap'>"]
    html.append("<tr><th></th>" + "".join(
        f"<th>{c.replace('_other_platform','solo').replace('_',' ').title()}</th>" for c in heatmap_cols) + "</tr>")
    for rk in heatmap_rows:
        if rk not in co:
            continue
        row_data = co[rk]
        cells = []
        for ck in heatmap_cols:
            v = row_data.get(ck, 0)
            is_diag = (ck == rk) or (ck == "no_other_platform" and rk == "no_platform")
            cells.append(_heatmap_cell(v, is_diag))
        html.append(f"<tr><th>{rk.replace('_',' ').title()}</th>{''.join(cells)}</tr>")
    html.append("</table>")

    low_sample = [p for p, n in plat_orders_28d.items()
                  if 0 < n < min_sample and p not in ("no_platform",)]
    if low_sample:
        low_sample_caveat = (
            '<li>Small sample on '
            + ", ".join(p.capitalize() for p in low_sample)
            + f' (fewer than {min_sample} attributed orders in 28 days). These '
            + 'platforms are excluded from the strongest-overlap insight in Channel touch points.</li>'
        )
    else:
        low_sample_caveat = ''

    return {"heatmap_html": "\n".join(html), "low_sample_caveat": low_sample_caveat}
