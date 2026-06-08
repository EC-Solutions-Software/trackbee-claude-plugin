"""Interactive inline-SVG sparkline of daily revenue — no external chart libs.

Renders the trailing daily-revenue series as a navy line with a soft fill and a
dot on the most recent day. Each point also ships its date label and formatted
revenue as a JSON payload on the wrapper, so the paired ``spark.js`` can show a
tooltip + marker on hover. Returns an empty string when there are too few points
to draw a meaningful line.

get_daily_store_statistics rows carry no date field, so the date labels are
computed by the orchestrator (counting back from the trend window's end) and
passed in here aligned to the series.
"""

from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FH = _load("format_helpers", _CHROME / "format_helpers.py")

_W = 480.0
_H = 56.0
_PAD = 4.0


def svg(series, labels=None, currency="", aria=""):
    """series: [(date_or_None, value)] in store units. labels: per-point date
    strings aligned to series (optional). Returns an <svg>-in-wrapper string."""
    pts = [(d, float(v)) for d, v in (series or []) if v is not None]
    if len(pts) < 2:
        return ""

    values = [v for _, v in pts]
    vmin, vmax = min(values), max(values)
    span = (vmax - vmin) or 1.0
    n = len(pts)
    labels = labels or []

    def x(i):
        return _PAD + (i / (n - 1)) * (_W - 2 * _PAD)

    def y(v):
        return _PAD + (1 - (v - vmin) / span) * (_H - 2 * _PAD)

    line_pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(pts))
    area_pts = f"{x(0):.1f},{_H - _PAD:.1f} " + line_pts + f" {x(n - 1):.1f},{_H - _PAD:.1f}"
    last_x, last_y = x(n - 1), y(values[-1])
    aria_label = html.escape(aria or "Daily revenue trend")

    # Per-point data for the hover layer: x as a percent of width (the SVG
    # stretches horizontally to fill the card), y in px (height is fixed, 1:1).
    points = []
    for i, (_, v) in enumerate(pts):
        label = labels[i] if i < len(labels) and labels[i] else f"Day {i + 1}"
        points.append({
            "l": label,
            "v": _FH.money(v, currency),
            "x": round(x(i) / _W * 100, 3),
            "y": round(y(v), 2),
        })
    data_attr = html.escape(json.dumps(points, separators=(",", ":")), quote=True)

    return (
        f'<div class="spark-wrap" data-points="{data_attr}" data-h="{_H:.0f}">'
        f'<svg class="spark" viewBox="0 0 {_W:.0f} {_H:.0f}" width="100%" '
        f'height="{_H:.0f}" preserveAspectRatio="none" role="img" '
        f'aria-label="{aria_label}">'
        f'<polygon points="{area_pts}" fill="rgba(13,18,69,0.07)" />'
        f'<polyline points="{line_pts}" fill="none" stroke="#0D1245" '
        f'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" '
        f'vector-effect="non-scaling-stroke" />'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.6" fill="#FF1F6B" />'
        f'</svg>'
        f'<div class="spark-vline" hidden></div>'
        f'<div class="spark-dot" hidden></div>'
        f'<div class="spark-tip" hidden></div>'
        f'</div>'
    )
