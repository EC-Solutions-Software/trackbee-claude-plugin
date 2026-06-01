"""Date-pill formatting for the header.

Renders the window range as `"7 days · May 8–14"` style strings, with
sensible fallbacks for cross-month and cross-year windows.
"""

from __future__ import annotations

import datetime as dt


def format_date_pill(window: dict) -> str:
    """Return a short, human-friendly date range for the header pill."""
    try:
        s = dt.date.fromisoformat(window["start"])
        e = dt.date.fromisoformat(window["end"])
    except (KeyError, ValueError, TypeError):
        return window.get("label") or f"{window.get('start','?')} → {window.get('end','?')}"

    n = (e - s).days + 1

    # Use %-d on Linux/macOS; fall back to %#d on Windows; both → day-without-zero.
    def day(d: dt.date) -> str:
        try:
            return d.strftime("%-d")
        except ValueError:
            return d.strftime("%#d")

    if s.year == e.year and s.month == e.month:
        range_str = f"{s.strftime('%b')} {day(s)}–{day(e)}"
    elif s.year == e.year:
        range_str = f"{s.strftime('%b')} {day(s)} – {e.strftime('%b')} {day(e)}"
    else:
        range_str = f"{s.strftime('%b')} {day(s)}, {s.year} – {e.strftime('%b')} {day(e)}, {e.year}"

    return f"{n} days · {range_str}"
