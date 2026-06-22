"""Format helpers for the Ad Performance dashboard build.

Pure functions, no side effects. Imported by every transform / insight /
orchestrator module that turns a numeric value into a string for the HTML.

Currency formatting requires an explicit symbol argument — there is no
default. Defaulting to a single currency (the old code defaulted to £)
silently mis-formats every other store's money. The caller passes the
store's symbol from `config.json`.
"""

from __future__ import annotations

import html as _html
import math


def value_or(val, default=None):
    """Return val if not None, else default."""
    return val if val is not None else default


def number(val, decimals: int = 2) -> str:
    """Format a float with thousands separators; em-dash for missing."""
    if val is None:
        return "—"
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def percent(val, decimals: int = 2) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def money(val, symbol: str, decimals: int = 0) -> str:
    """Format a monetary value with the explicit store currency symbol.

    No default symbol — pass the store's symbol from config explicitly.
    Empty / unparseable values render as em-dash.
    """
    if val is None:
        return "—"
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{symbol}{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def integer(val) -> str:
    if val is None:
        return "—"
    try:
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return "—"


def safe_float(val, default: float = 0.0) -> float:
    try:
        v = float(val or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


def short(text, n: int = 52) -> str:
    if not text:
        return "—"
    return text[:n] + "…" if len(text) > n else text


def attr(text) -> str:
    """Escape a string for safe interpolation inside an HTML attribute."""
    return _html.escape("" if text is None else str(text), quote=True)


def text(text) -> str:
    """Escape a string for safe interpolation inside HTML body text."""
    return _html.escape("" if text is None else str(text), quote=False)


def roas_class(roas) -> str:
    # Neutral by design: we present the measured number only and never
    # colour-code it good/bad, so this returns no semantic class. Kept as a
    # function so callers don't need to change.
    return ""


def freq_class(freq) -> str:
    # Neutral by design — see roas_class. No good/ok/bad colour-coding.
    return ""


def status_badge(status) -> str:
    s = (status or "").upper()
    if s in ("ACTIVE", "ENABLED"):
        return '<span class="badge active">Active</span>'
    if s == "PAUSED":
        return '<span class="badge paused">Paused</span>'
    return f'<span class="badge other">{attr(status or "—")}</span>'


def google_roas(campaign: dict):
    """Compute Google ROAS from a campaign dict; None for zero-spend rows."""
    spend = safe_float(campaign.get("spend"))
    rev = safe_float(campaign.get("conversions_value"))
    if spend <= 0:
        return None
    return rev / spend
