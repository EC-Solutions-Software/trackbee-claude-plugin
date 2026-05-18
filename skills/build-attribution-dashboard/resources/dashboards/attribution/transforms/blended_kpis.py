"""Blended Overview KPIs — Python data transform.

Reads raw MCP outputs (get_dashboard_overview, get_daily_store_statistics,
get_funnel_overview with compare_previous_period=true) and returns the
payload that the view layer reads via window.TB_DATA.windows.<key>.blended.

All monetary values in overview/daily are store-currency CENTS.
Output values are store-currency UNITS (cents / 100).
"""

from __future__ import annotations


# ISO 4217 → display symbol. Mirrors the Intl.NumberFormat output the JS
# side produces via format_helpers.js so the exec summary text matches the
# KPI tiles. Unknown codes fall back to the raw ISO code + space.
_CURRENCY_SYMBOL: dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "CHF": "CHF ",
    "SEK": "kr ",
    "NOK": "kr ",
    "DKK": "kr ",
    "AUD": "A$",
    "CAD": "C$",
    "NZD": "NZ$",
    "BRL": "R$",
    "INR": "₹",
    "MXN": "Mex$",
    "ZAR": "R",
    "PLN": "zł ",
    "TRY": "₺",
    "RUB": "₽",
    "KRW": "₩",
    "SGD": "S$",
    "HKD": "HK$",
    "TWD": "NT$",
    "ILS": "₪",
    "AED": "د.إ ",
    "SAR": "﷼ ",
    "THB": "฿",
    "PHP": "₱",
    "IDR": "Rp ",
    "MYR": "RM ",
    "VND": "₫",
    "CZK": "Kč ",
    "HUF": "Ft ",
    "RON": "lei ",
    "BGN": "лв ",
    "HRK": "kn ",
    "UAH": "₴",
    "ARS": "AR$",
    "CLP": "CL$",
    "COP": "CO$",
    "PEN": "S/ ",
}


def _step_count(funnel_obj: dict, step: str) -> int:
    for entry in funnel_obj.get("funnel", []):
        if entry.get("step") == step:
            count = entry.get("count")
            return int(count) if count is not None else 0
    return 0


def _sum_field(rows: list[dict], field: str) -> int:
    """Sum a field across daily rows, treating missing/None as zero."""
    total = 0
    for row in rows:
        value = row.get(field)
        if value is not None:
            total += int(value)
    return total


def transform(inputs: dict, config: dict) -> dict:
    overview: dict = inputs.get("overview") or {}
    daily:    dict = inputs.get("daily")    or {"rows": []}
    funnel:   dict = inputs.get("funnel")   or {}

    rows: list[dict] = daily.get("rows") or []

    cur  = (funnel.get("current")  or {}).get("funnel") and funnel["current"] or {"funnel": []}
    prev = (funnel.get("previous") or {}).get("funnel") and funnel["previous"] or {"funnel": []}

    # Spend: prefer overview's ad_account_spend (FX-converted), fall back to 0.
    ad_spend = (overview.get("ad_account_spend") or 0) / 100

    # Revenue / orders: overview is primary; daily-row sum is fallback.
    revenue   = ((overview.get("total_revenue") or 0) / 100) or (_sum_field(rows, "total_revenue") / 100)
    orders    = overview.get("total_orders") or _sum_field(rows, "total_orders")
    nc_orders = overview.get("total_new_customer_orders") or _sum_field(rows, "total_new_customer_orders")
    nc_rev    = ((overview.get("total_new_customer_revenue") or 0) / 100) or \
                (_sum_field(rows, "total_new_customer_revenue") / 100)

    # Previous-period figures for delta arrows
    revenue_prev = float(prev.get("total_revenue") or 0) / 100
    orders_prev: int = int(prev.get("total_orders") or 0)

    pv       = _step_count(cur,  "total_page_view_events")
    pv_prev  = _step_count(prev, "total_page_view_events")
    atc      = _step_count(cur,  "total_add_to_cart_events")
    atc_prev = _step_count(prev, "total_add_to_cart_events")
    co       = _step_count(cur,  "total_checkout_started_events")
    co_prev  = _step_count(prev, "total_checkout_started_events")

    currency_code = (config.get("store_currency") or "EUR").upper()
    currency_symbol = _CURRENCY_SYMBOL.get(currency_code, currency_code + " ")

    return {
        "currency": currency_code,
        "currency_symbol": currency_symbol,
        "ad_spend": ad_spend,
        "revenue": revenue,
        "orders": orders,
        "new_customers": nc_orders,
        "nc_rev": nc_rev,
        "aov":     revenue / orders     if orders     else 0,
        "roas":    revenue / ad_spend   if ad_spend   else 0,
        "cpa":     ad_spend / orders    if orders     else 0,
        "nc_cpa":  ad_spend / nc_orders if nc_orders  else 0,
        "nc_roas": nc_rev   / ad_spend  if ad_spend   else 0,
        "sessions": pv,
        "rev_per_session": revenue / pv if pv else 0,
        "atc_rate": atc / pv if pv else 0,
        "co_rate":  co  / pv if pv else 0,
        "cvr":      orders / pv if pv else 0,
        "_revenue_prev":  revenue_prev,
        "_orders_prev":   orders_prev,
        "_pv_prev":       pv_prev,
        "_atc_rate_prev": atc_prev / pv_prev if pv_prev else 0,
        "_co_rate_prev":  co_prev  / pv_prev if pv_prev else 0,
        "_cvr_prev":      orders_prev / pv_prev if pv_prev else 0,
    }
