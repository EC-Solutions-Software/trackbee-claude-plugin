"""KPI tile computation + tile-bar HTML.

Takes a loaded store dict (see `store_data.load_all_stores`) and returns
both the computed KPI numbers and the HTML for the five-tile KPI bar.
The KPI bar is a fixed set: Total Ad Spend, Blended ROAS, MER, Conversions,
Avg Daily Spend.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "format_helpers",
    _HERE.parent / "chrome" / "format_helpers.py",
)
assert _spec is not None and _spec.loader is not None
_fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fh)


def compute(store: dict, n_days: int) -> dict:
    """Return the KPI numbers in store currency. Pure math; no formatting."""
    sym = store["symbol"]
    g_fx = store["g_fx"]
    m_fx = store["m_fx"]
    meta_c = store["meta_campaigns"]
    goog_c = store["goog_campaigns"]

    meta_spend = sum(
        _fh.safe_float(c.get("spend")) * m_fx
        for c in meta_c
        if _fh.safe_float(c.get("spend")) > 0
    )
    goog_spend = sum(
        _fh.safe_float(c.get("spend")) * g_fx
        for c in goog_c
        if _fh.safe_float(c.get("spend")) > 0
    )
    total_spend = meta_spend + goog_spend

    meta_rev = sum(_fh.safe_float(c.get("revenue_1d_click")) * m_fx for c in meta_c)
    goog_rev = sum(_fh.safe_float(c.get("conversions_value")) * g_fx for c in goog_c)
    total_rev = meta_rev + goog_rev

    blended_roas = (total_rev / total_spend) if total_spend > 0 else 0.0
    # Meta's blended ROAS is spend-weighted across campaigns that report
    # purchase_roas — same definition Meta's UI uses.
    weighted_meta = sum(
        _fh.safe_float(c.get("purchase_roas")) * _fh.safe_float(c.get("spend"))
        for c in meta_c
        if c.get("purchase_roas") and c.get("spend")
    )
    meta_roas = (weighted_meta / meta_spend) if meta_spend > 0 else 0.0
    goog_roas = (goog_rev / goog_spend) if goog_spend > 0 else 0.0

    meta_purch = sum(int(c.get("purchases") or 0) for c in meta_c)
    goog_conv = sum(_fh.safe_float(c.get("conversions")) for c in goog_c)

    return {
        "sym": sym,
        "n_days": n_days,
        "meta_spend":   meta_spend,
        "goog_spend":   goog_spend,
        "total_spend":  total_spend,
        "meta_rev":     meta_rev,
        "goog_rev":     goog_rev,
        "total_rev":    total_rev,
        "blended_roas": blended_roas,
        "meta_roas":    meta_roas,
        "goog_roas":    goog_roas,
        "meta_purch":   meta_purch,
        "goog_conv":    goog_conv,
        "mer":          store["ov_mer"],
    }


_VIEWS = Path(__file__).resolve().parent.parent / "views"


def render_tiles_html(kpis: dict) -> str:
    """Render the KPI bar as one HTML string from a computed `kpis` dict.

    Loads the template from `components/views/kpi_bar.html` and stamps in
    pre-formatted values. The template owns the markup; this function
    owns the formatting.
    """
    sym = kpis["sym"]
    n_days = kpis["n_days"]
    template = (_VIEWS / "kpi_bar.html").read_text(encoding="utf-8")
    return (
        template
        .replace("{TOTAL_SPEND}",   _fh.money(kpis["total_spend"], sym))
        .replace("{META_SPEND}",    _fh.money(kpis["meta_spend"], sym))
        .replace("{GOOG_SPEND}",    _fh.money(kpis["goog_spend"], sym))
        .replace("{BLENDED_CLASS}", _fh.roas_class(kpis["blended_roas"]))
        .replace("{BLENDED_ROAS}",  _fh.number(kpis["blended_roas"], 2))
        .replace("{META_ROAS}",     _fh.number(kpis["meta_roas"], 2))
        .replace("{GOOG_ROAS}",     _fh.number(kpis["goog_roas"], 2))
        .replace("{MER}",           _fh.number(kpis["mer"], 2))
        .replace("{CONVERSIONS}",   _fh.integer(kpis["meta_purch"] + kpis["goog_conv"]))
        .replace("{META_PURCH}",    _fh.integer(kpis["meta_purch"]))
        .replace("{GOOG_CONV}",     _fh.number(kpis["goog_conv"], 0))
        .replace("{AVG_DAILY}",     _fh.money(kpis["total_spend"] / n_days, sym))
        .replace("{N_DAYS}",        str(n_days))
    )
