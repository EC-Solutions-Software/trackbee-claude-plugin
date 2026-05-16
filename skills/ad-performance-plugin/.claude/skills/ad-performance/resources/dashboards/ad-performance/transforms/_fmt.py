"""TrackBee Ad Performance — server-side formatting + numeric helpers.

Used by every transform / insight / view-emitter to format numbers the
same way. Keeps `_safe_float`, `_money`, `_pct`, `_f`, `_n` in one place.

These return `'—'` for missing values so they're safe to drop straight into
HTML. The dashboard never imports them with a None default — call sites pass
real numbers or `None` from the upstream MCP payload.
"""

from __future__ import annotations

import html as _html
import math


def safe_float(value, default: float = 0.0) -> float:
    """Coerce to float, treating None / '' / NaN / inf as `default`."""
    try:
        v = float(value or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


def fmt_float(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_money(value, symbol: str = "", decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{symbol}{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_int(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def short(text: str | None, max_chars: int = 52) -> str:
    if not text:
        return "—"
    return text[:max_chars] + "…" if len(text) > max_chars else text


def html_escape(text: str | None, quote: bool = False) -> str:
    return _html.escape(text or "", quote=quote)


def status_badge(status: str | None) -> str:
    s = (status or "").upper()
    if s in ("ACTIVE", "ENABLED"):
        return '<span class="badge active">Active</span>'
    if s == "PAUSED":
        return '<span class="badge paused">Paused</span>'
    return f'<span class="badge other">{html_escape(status or "—")}</span>'


def roas_class(roas, thresholds: dict) -> str:
    if roas is None:
        return ""
    r = safe_float(roas)
    if r >= thresholds["roas_good"]:
        return "good"
    if r >= thresholds["roas_ok"]:
        return "ok"
    if r > 0:
        return "bad"
    return ""


def freq_class(freq, thresholds: dict) -> str:
    f = safe_float(freq)
    if f >= thresholds["freq_bad"]:
        return "bad"
    if f >= thresholds["freq_ok"]:
        return "ok"
    return ""
