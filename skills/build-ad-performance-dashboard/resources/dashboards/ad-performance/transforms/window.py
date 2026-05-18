"""Date-window helper for the Ad Performance dashboard.

Takes the `window` block from config.json and returns a clean
``{start, end, n_days, label, pill}`` bundle. Centralised so the date
pill ("7 days · May 8–14") isn't reinvented in three places.

Standalone — no imports outside the stdlib. Matches the repo's
no-inter-component-imports convention.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional


def _format_pill(start: dt.date, end: dt.date, n_days: int) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{n_days} days · {start.strftime('%b %-d')}–{end.strftime('%-d')}"
    if start.year == end.year:
        return f"{n_days} days · {start.strftime('%b %-d')} – {end.strftime('%b %-d')}"
    return f"{n_days} days · {start.strftime('%b %-d, %Y')} – {end.strftime('%b %-d, %Y')}"


def transform(inputs: dict, config: Optional[dict] = None) -> dict:
    """Return ``{start, end, n_days, label, pill}``.

    Raises:
        ValueError if ``config['window'].start`` / ``end`` are missing or
        not ISO dates. The orchestrator catches this and surfaces a global
        error banner.
    """
    del inputs  # unused
    window = (config or {}).get("window") or {}
    start_str = window.get("start")
    end_str = window.get("end")
    if not start_str or not end_str:
        raise ValueError(
            "config.window is missing `start` and/or `end` dates — the "
            "dashboard can't compute a reporting window without them."
        )
    try:
        start = dt.date.fromisoformat(start_str)
        end = dt.date.fromisoformat(end_str)
    except ValueError as e:
        raise ValueError(
            f"config.window dates aren't valid ISO dates (YYYY-MM-DD): {e}"
        ) from e
    if end < start:
        raise ValueError(
            f"config.window.end ({end_str}) is before config.window.start "
            f"({start_str}). Swap them or fix the date range."
        )
    n_days = (end - start).days + 1
    label = window.get("label") or _format_pill(start, end, n_days)
    return {
        "start": start_str,
        "end": end_str,
        "n_days": n_days,
        "label": label,
        "pill": _format_pill(start, end, n_days),
    }
