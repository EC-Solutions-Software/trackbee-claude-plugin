"""Shared numeric / date / HTML helpers used across creatives-report
transforms and insights. Single source of truth — every other component
imports from here rather than redefining its own helpers."""

from __future__ import annotations

import datetime as dt
import html as _html
import math
import statistics


def safe_float(val, default: float = 0.0) -> float:
    # `val or 0` (not an `is None` check) so falsy non-numerics like ""
    # coerce to 0 — matches analyze-ad-performance's copy so identical
    # MCP payloads parse the same across skills.
    try:
        v = float(val or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


def fmt_float(val, decimals: int = 2) -> str:
    if val is None:
        return "—"
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{v:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(val, decimals: int = 2) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_money(val, symbol: str = "", decimals: int = 0) -> str:
    """Format ``val`` as money with the supplied currency symbol.

    The default symbol is the empty string — we never guess £/€/$ for
    an unknown store. Callers should pass the store's currency symbol
    explicitly (every transform receives ``store.sym`` for this).
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


def fmt_int(val) -> str:
    if val is None:
        return "—"
    try:
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return "—"


def short(text: str, n: int = 52) -> str:
    if not text:
        return "—"
    text = str(text)  # tolerate a non-string name (e.g. a numeric id)
    return text[:n] + "…" if len(text) > n else text


def median(values):
    """statistics.median() that tolerates None / NaN / mixed-type inputs."""
    vals = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            continue
        vals.append(v)
    if not vals:
        return None
    return statistics.median(vals)


def parse_date(s):
    if not s:
        return None
    try:
        if "T" in s:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return dt.date.fromisoformat(s[:10])
    except Exception:
        return None


def roas_class(roas) -> str:
    # Class names and thresholds mirror analyze-ad-performance's
    # format_helpers.py so the same value gets the same status across
    # dashboards — keep the two in sync.
    if roas is None:
        return ""
    r = safe_float(roas)
    if r >= 2.5:
        return "good"
    if r >= 1.5:
        return "ok"
    if r > 0:
        return "bad"
    return ""


def freq_class(freq) -> str:
    # Mirrors analyze-ad-performance — see roas_class above.
    f = safe_float(freq)
    if f >= 4.0:
        return "bad"
    if f >= 3.0:
        return "ok"
    return ""


def html_escape(text) -> str:
    return _html.escape(str(text or ""))


def html_attr(text) -> str:
    return _html.escape(str(text or ""), quote=True)


def currency_symbol_for(code: str) -> str:
    """Return the symbol for a 3-letter ISO code, falling back to the
    code itself (e.g. "BRL") so the user always sees something
    meaningful, never a guessed wrong symbol. Keep this in sync with
    the currencies supported by Intl.NumberFormat in
    render_formatters.js, and with the identical table in
    skills/growth-report/components/chrome/format_helpers.py (skills
    are self-contained, so the table is deliberately duplicated)."""
    table = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "AUD": "A$",
        "NZD": "NZ$",
        "CAD": "C$",
        "CHF": "CHF",
        "JPY": "¥",
        "CNY": "¥",
        "INR": "₹",
        "PLN": "zł",
        "CZK": "Kč",
        "HUF": "Ft",
        "SEK": "kr",
        "DKK": "kr",
        "NOK": "kr",
        "ISK": "kr",
        "RON": "lei",
        "BGN": "лв",
        "TRY": "₺",
        "BRL": "R$",
        "MXN": "MX$",
        "ARS": "$",
        "ZAR": "R",
        "ILS": "₪",
        "AED": "د.إ",
        "SAR": "ر.س",
        "KRW": "₩",
        "SGD": "S$",
        "HKD": "HK$",
        "TWD": "NT$",
        "THB": "฿",
        "MYR": "RM",
        "IDR": "Rp",
        "PHP": "₱",
        "VND": "₫",
    }
    return table.get((code or "").upper(), _html.escape(code or ""))
