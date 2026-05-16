"""TrackBee Ad Performance — date-window helpers.

A single helper that turns the `config.window` dict into a clean
{start_date, end_date, n_days, label, pill} bundle used by every other
transform. Centralised so the human-readable date pill ("7 days · May 8–14")
isn't reinvented in three places.
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
    """Return the window descriptor.

    Args:
        inputs: ignored — kept for transform-signature parity.
        config: dashboard config dict; expects `config["window"]` with
                `start` (ISO date string), `end` (ISO date string), and
                optional `label` override.

    Returns:
        ``{"start": "2026-05-04", "end": "2026-05-10", "n_days": 7,
            "label": "...", "pill": "7 days · May 4–10"}``

    Raises:
        ValueError if start/end are missing or unparseable. The orchestrator
        catches this and surfaces a global error banner.
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
    pill = _format_pill(start, end, n_days)

    return {
        "start": start_str,
        "end": end_str,
        "n_days": n_days,
        "label": label,
        "pill": pill,
    }
