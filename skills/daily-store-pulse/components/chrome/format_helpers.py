"""Format helpers for the Daily Store Pulse build.

Pure functions, no side effects. Loaded by the transform / insight modules
(via the orchestrator's relative-path loader) that turn a numeric value into a
string for the HTML.

Currency formatting requires an explicit symbol — there is no default. Each
store resolves its symbol once via ``currency_symbol_for`` and formats with it,
so a non-EUR/USD/GBP store never renders a blank symbol.
"""

from __future__ import annotations

import html
import math


def safe_float(val, default=None):
    """Coerce to float, returning ``default`` for None / NaN / inf / junk."""
    if val is None:
        return default
    try:
        v = float(val)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


def currency_symbol_for(code: str) -> str:
    """Symbol for a 3-letter ISO code. Falls back to the code itself
    (e.g. "BRL") when no symbol is known, so the user always sees the real
    currency rather than a guessed-wrong symbol. The fallback is HTML-escaped
    so an unexpected non-ISO string can't splice markup into the page."""
    table = {
        "EUR": "€", "USD": "$", "GBP": "£", "AUD": "A$", "NZD": "NZ$",
        "CAD": "C$", "CHF": "CHF", "JPY": "¥", "CNY": "¥", "INR": "₹",
        "PLN": "zł", "CZK": "Kč", "HUF": "Ft", "SEK": "kr", "DKK": "kr",
        "NOK": "kr", "ISK": "kr", "RON": "lei", "BGN": "лв", "TRY": "₺",
        "BRL": "R$", "MXN": "MX$", "ARS": "$", "ZAR": "R", "ILS": "₪",
        "AED": "د.إ", "SAR": "ر.س", "KRW": "₩", "SGD": "S$", "HKD": "HK$",
        "TWD": "NT$", "THB": "฿", "MYR": "RM", "IDR": "Rp", "PHP": "₱",
        "VND": "₫",
    }
    key = (code or "").upper()
    return table.get(key, html.escape(code or ""))


def cents_to_units(x):
    """All TrackBee monetary fields are in *cents* of the store currency.
    Divide once, here, so every downstream consumer sees the same units."""
    v = safe_float(x)
    return None if v is None else v / 100.0


def money(value, currency, digits=0):
    """Format a (already-in-units) monetary value with the store symbol.
    Renders an em dash for missing data — never a blank symbol or a 0."""
    if value is None:
        return "—"
    sym = currency_symbol_for(currency)
    return f"{sym}{value:,.{digits}f}"


def compact_money(value, currency):
    """Compact monetary value for tight KPI tiles: €1.2k, €34k, €1.1M."""
    if value is None:
        return "—"
    sym = currency_symbol_for(currency)
    a = abs(value)
    if a >= 1_000_000:
        return f"{sym}{value/1_000_000:,.1f}M"
    if a >= 10_000:
        return f"{sym}{value/1_000:,.0f}k"
    if a >= 1_000:
        return f"{sym}{value/1_000:,.1f}k"
    return f"{sym}{value:,.0f}"


def integer(value):
    if value is None:
        return "—"
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "—"


def ratio(value, digits=2, suffix=""):
    v = safe_float(value)
    if v is None:
        return "—"
    return f"{v:.{digits}f}{suffix}"


def pct_change(cur, prior):
    """Signed percent change cur-vs-prior, or None when it can't be computed."""
    c = safe_float(cur)
    p = safe_float(prior)
    if c is None or p is None or p == 0:
        return None
    return (c - p) / abs(p) * 100.0


def signed_pct(value, digits=1):
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}%"


def delta_class(pct, *, lower_is_better=False, flat_band=2.0):
    """Map a percent change to a semantic CSS class. ``lower_is_better`` flips
    the meaning for cost metrics (CAC, CPC) where a drop is good. Moves inside
    ``flat_band`` percent read as flat — daily noise shouldn't paint red/green."""
    if pct is None:
        return "delta-flat"
    if abs(pct) < flat_band:
        return "delta-flat"
    improving = (pct < 0) if lower_is_better else (pct > 0)
    return "delta-good" if improving else "delta-bad"
