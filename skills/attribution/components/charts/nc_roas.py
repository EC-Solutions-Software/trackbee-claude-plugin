"""Inline SVG renderer for the Blended NC ROAS (Acquisition MER) line chart.

Pre-rendered server-side so the page needs no external chart library. Returns
``(svg_markup, period_avg)``. Self-contained — stdlib only.
"""


def render_nc_roas_svg(daily):
    """Render the NC ROAS line chart as inline SVG.

    Includes an area fill under the line, a dashed period-average line,
    discrete data points (with tooltips), light grid lines, and MM-DD x-axis
    labels thinned for readability. No external dependencies.
    """
    W, H = 760, 220
    PT, PB, PL, PR = 14, 30, 38, 14
    n = len(daily)
    if not n:
        return ('<div style="padding:24px;color:#737373;background:#FAFAFA;'
                'border:1px solid #E5E5E5;border-radius:8px;font-size:14px;'
                'text-align:center">No data for this window.</div>'), 0
    vals = [d["value"] for d in daily]
    tot_rev = sum(d.get("nc_revenue", 0) for d in daily)
    tot_sp = sum(d.get("daily_spend", 0) for d in daily)
    avg = (tot_rev / tot_sp) if tot_sp else 0
    vmax = max(vals + [avg, 1])
    vmin = 0
    plot_h = H - PT - PB
    plot_w = W - PL - PR

    def x(i):
        return PL + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)

    def y(v):
        return PT + plot_h * (1 - (v - vmin) / (vmax - vmin)) if vmax > vmin else (PT + plot_h / 2)

    pts_str = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    area_d = f"M{x(0):.1f},{y(0):.1f} L" + " L".join(
        f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals)
    ) + f" L{x(n-1):.1f},{y(0):.1f} Z"
    ticks = []
    for k in range(5):
        gv = vmin + (vmax - vmin) * k / 4
        gy = y(gv)
        ticks.append(
            f'<line x1="{PL}" y1="{gy:.1f}" x2="{W-PR}" y2="{gy:.1f}" '
            f'stroke="rgba(229,229,229,0.9)" stroke-width="1"/>'
        )
        ticks.append(
            f'<text x="{PL-6}" y="{gy+3:.1f}" font-size="10" fill="#737373" '
            f'text-anchor="end" font-family="Plus Jakarta Sans, system-ui">{gv:.1f}</text>'
        )
    step = max(1, n // 7)
    xlabels = []
    for i, d in enumerate(daily):
        if i % step == 0 or i == n - 1:
            xlabels.append(
                f'<text x="{x(i):.1f}" y="{H-PB+16}" font-size="10" fill="#737373" '
                f'text-anchor="middle" font-family="Plus Jakarta Sans, system-ui">{d["date"][5:]}</text>'
            )
    dots_parts = []
    for i, v in enumerate(vals):
        d = daily[i]
        tip = (
            f'<strong>{d["date"]}</strong>'
            f'NC ROAS: <b>{v:.2f}</b>\n'
            f'NC revenue: {d.get("nc_revenue", 0):,.0f}\n'
            f'Daily spend: {d.get("daily_spend", 0):,.0f}'
        )
        # Visible dot
        dots_parts.append(
            f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" '
            f'r="{2.5 if n <= 7 else 1.8}" fill="#FF1F6B"></circle>'
        )
        # Larger transparent hit-target with data-tip so hovering anywhere
        # near the point reveals the tooltip — solves the 1-px-dot problem.
        dots_parts.append(
            f'<circle class="tb-hit" cx="{x(i):.1f}" cy="{y(v):.1f}" r="10" '
            f'pointer-events="all" data-tip="{tip}"></circle>'
        )
    dots = "".join(dots_parts)
    avg_y = y(avg)
    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="240" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="NC ROAS over time">'
        f'{"".join(ticks)}'
        f'<path d="{area_d}" fill="rgba(255,31,107,0.08)" stroke="none"/>'
        f'<polyline points="{pts_str}" fill="none" stroke="#FF1F6B" stroke-width="2"/>'
        f'{dots}'
        f'<line x1="{PL}" y1="{avg_y:.1f}" x2="{W-PR}" y2="{avg_y:.1f}" '
        f'stroke="rgba(122,92,0,0.7)" stroke-width="1.5" stroke-dasharray="4 4"/>'
        f'<text x="{W-PR-4}" y="{avg_y-4:.1f}" font-size="10" '
        f'fill="#7A5C00" text-anchor="end" font-family="Plus Jakarta Sans, system-ui">'
        f'avg {avg:.2f}</text>'
        f'{"".join(xlabels)}'
        f'</svg>'
    ), avg
