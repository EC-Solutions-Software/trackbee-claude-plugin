"""Currency, number, and delta formatters for the Attribution Overview build.

``build(store_currency, fx)`` returns a small ``Formatters`` namespace that
the orchestrator passes into the transform / insight components, so no
component has to reach for a shared global or import a sibling module.

Two currency-symbol maps are kept on purpose:

* ``_CCY_SYMBOLS`` — the broad map behind ``fmt_eur`` / ``fmt_eur2`` (used by
  the build's stdout summary).
* ``_INSIGHT_SYMBOLS`` — the narrower map behind ``fmt_ccy``, the zero-decimal
  currency formatter baked into the channel-attribution and executive-summary
  insight strings. The page's KPI tiles and tables format on the client side
  via ``Intl.NumberFormat`` driven by the store currency; only the baked-in
  insight prose needs a server-side currency symbol, and it uses this map.
"""

# Despite the historical ``_eur`` naming, every monetary value the build
# carries is already in the store's currency.
_CCY_SYMBOLS = {
    "EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥",
    "CHF": "CHF ", "SEK": "kr ", "NOK": "kr ", "DKK": "kr ",
    "AUD": "A$", "CAD": "C$", "NZD": "NZ$",
}

_INSIGHT_SYMBOLS = {
    "EUR": "€", "GBP": "£", "USD": "$", "SEK": "kr", "DKK": "kr", "NOK": "kr",
}


class Formatters:
    def __init__(self, store_currency, fx):
        self.store_currency = (store_currency or "EUR")
        self.fx = fx or {}
        self.ccy = self._ccy_symbol(self.store_currency)
        # Zero-decimal symbol used inside baked-in insight prose.
        self.insight_sym = _INSIGHT_SYMBOLS.get(
            self.store_currency.upper(), self.store_currency.upper() + " ")

    def _ccy_symbol(self, code=None):
        code = (code or self.store_currency or "EUR").upper()
        return _CCY_SYMBOLS.get(code, code + " ")

    def fx_to_eur(self, currency):
        """How many *store-currency* units one unit of ``currency`` is worth.

        The ``fx`` dict is keyed on the ad-account currency code and reads as
        "convert FROM this currency TO the store's currency". Missing → 1.0.
        """
        if not currency:
            return 1.0
        return float(self.fx.get(currency.upper(), 1.0))

    # Monetary — store currency, not a hardcoded symbol.
    def fmt_eur(self, v):
        return "—" if v in (None, 0) else f"{self.ccy}{v:,.0f}"

    def fmt_eur2(self, v):
        return "—" if v is None else f"{self.ccy}{v:,.2f}"

    def fmt_int(self, v):
        return "—" if v is None else f"{int(round(v)):,}"

    def fmt_pct(self, v):
        return "—" if v is None else f"{v*100:.2f}%"

    def fmt_num(self, v, d=2):
        return "—" if v in (None, 0) else f"{v:,.{d}f}"

    def fmt_ccy(self, v):
        """Zero-decimal store-currency value for insight prose."""
        return f"{self.insight_sym}{v:,.0f}"

    def delta_arrow(self, cur, prev):
        if not prev or prev == 0 or cur is None:
            return ""
        pct = (cur - prev) / prev
        cls = "delta-up" if pct >= 0 else "delta-dn"
        arr = "▲" if pct >= 0 else "▼"
        return f"<span class='{cls}'>{arr} {abs(pct)*100:.1f}%</span>"


def build(store_currency, fx):
    return Formatters(store_currency, fx)
