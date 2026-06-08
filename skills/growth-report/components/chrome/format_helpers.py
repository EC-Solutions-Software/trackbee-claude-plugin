"""Format helpers for the Growth Report build.

Pure functions, no side effects. Loaded by the transform / insight
modules (via the orchestrator's relative-path loader) that turn a
numeric value into a string for the HTML.

Currency formatting requires an explicit symbol — there is no default.
Each module resolves the store's symbol once via ``currency_symbol_for``
and formats with it, so a non-EUR/USD/GBP store never renders a blank
symbol.
"""

from __future__ import annotations

import html
import math


def safe_float(val, default: float = 0.0) -> float:
    # `val or 0` (not an `is None` check) so falsy non-numerics like ""
    # coerce to 0 — matches analyze-ad-performance's copy so identical
    # MCP payloads parse the same across skills.
    try:
        v = float(val or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


# Ad platforms exactly as ``platform_statistics`` reports them
# (conversion_provider key → display label). Every per-platform signal
# and metric iterates this one list; a site that intentionally covers a
# subset filters it explicitly so the divergence is visible at the call
# site, and adding a platform here propagates everywhere at once.
AD_PLATFORMS = (
    ("facebook",  "Meta"),
    ("google",    "Google"),
    ("pinterest", "Pinterest"),
    ("tiktok",    "TikTok"),
)


def pct_delta(cur, prv):
    """WoW % delta. None when either side is missing or the prior is 0
    (a % move off a zero baseline is undefined)."""
    if cur is None or prv in (None, 0):
        return None
    try:
        return (float(cur) - float(prv)) / float(prv) * 100.0
    except (TypeError, ValueError):
        return None


def signed_pct(value, digits: int = 1) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def ccy(value, sym: str, digits: int = 0) -> str:
    """Format a store-currency amount with a pre-resolved symbol
    (each module resolves it once via ``resolve_currency_symbol``)."""
    if value is None:
        return "—"
    return f"{sym}{value:,.{digits}f}"


def currency_symbol_for(code: str) -> str:
    """Symbol for a 3-letter ISO code. Falls back to the code itself
    (e.g. "BRL") when no symbol is known, so the user always sees the
    real currency rather than a guessed-wrong symbol.

    The fallback is HTML-escaped: the symbol is stamped into a couple of
    intentional raw-HTML fragments (the answer block, the actions list)
    that don't re-escape it, so an unexpected non-ISO currency string
    can't splice markup into the report. Known symbols contain no HTML
    metacharacters, so they pass through unchanged.

    Keep the table in sync with the identical one in
    skills/creatives-report/components/chrome/format_helpers.py (skills
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
    key = (code or "").upper()
    return table.get(key, html.escape(code or ""))


def resolve_currency_symbol(config: dict, code: str) -> str:
    """Pick the display symbol for the store, preferring an explicit
    ``currency_symbol`` from config (MCP/config-provided) over the
    hand-maintained ISO table. Mirrors creatives-report's stores_cfg pattern.

    The config override is HTML-escaped for the same reason as the table
    fallback (see ``currency_symbol_for``): the symbol lands in a couple of
    intentional raw-HTML fragments that don't re-escape it."""
    override = (config or {}).get("currency_symbol")
    if override:
        return html.escape(str(override))
    return currency_symbol_for(code)
