"""Scaling-decision rule pack.

One function: `action_for(roas, freq, spend, thresholds)` returns
``("SCALE" | "HOLD" | "REFRESH" | "PAUSE" | None, tooltip)``.

All thresholds are read from the thresholds dict — there are NO numeric
constants inside this module. Keeping it data-driven means a TrackBee
brand-manager who wants to tweak "what counts as scaling material" only
edits one JSON file.
"""

from __future__ import annotations

from typing import Optional

from . import _fmt as f


# Pill-rendering helpers — keep markup co-located with the rule so a label
# change touches one place only.
_PILLS: dict[Optional[str], tuple[str, str]] = {
    "SCALE":   ("act-scale",   "Strong ROAS, frequency still healthy — increase budget"),
    "REFRESH": ("act-refresh", "Frequency high but ROAS holds — refresh creative"),
    "HOLD":    ("act-hold",    "Performance OK but not exceptional — hold steady"),
    "PAUSE":   ("act-pause",   "Below break-even at meaningful spend — review or pause"),
    None:      ("act-none",    "Not enough spend to act on"),
}


def action_for(roas, freq, spend, thresholds: dict) -> Optional[str]:
    """Return the action label (or None if there's not enough signal)."""
    r = f.safe_float(roas)
    fq = f.safe_float(freq)
    s = f.safe_float(spend)

    if s < thresholds["action_min_spend"] or r <= 0:
        return None
    if r >= thresholds["scale_roas"] and (fq == 0 or fq < thresholds["scale_max_freq"]):
        return "SCALE"
    if fq >= thresholds["refresh_min_freq"] and r >= thresholds["refresh_min_roas"]:
        return "REFRESH"
    if r < thresholds["pause_roas"] and s > thresholds["pause_min_spend"]:
        return "PAUSE"
    return "HOLD"


def action_pill_html(label: Optional[str]) -> str:
    """HTML for the inline action pill. The label may be None (no signal)."""
    cls, tip = _PILLS.get(label, _PILLS[None])
    text = label or "—"
    return f'<span class="act-pill {cls}" title="{tip}">{text}</span>'
