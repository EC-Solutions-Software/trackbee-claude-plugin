"""Meta campaign and ad row builders.

Each function returns one `<tr>` (or many) for the performance table.
The cells follow the column order declared in `table_meta.CAMPAIGN_HEADERS`
— if you change that list, update both row builders.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fh = _load("format_helpers", _CHROME / "format_helpers.py")
_tm = _load("table_meta", _HERE / "table_meta.py")


def campaign_row(c: dict, sym: str, m_fx: float, n_days: int, store_id) -> str:
    """One <tr> for one Meta campaign."""
    spend = _fh.safe_float(c.get("spend")) * m_fx
    daily = spend / n_days if n_days else 0
    reach = _fh.safe_float(c.get("reach"))
    impr = _fh.safe_float(c.get("impressions"))
    freq = _fh.safe_float(c.get("frequency"))
    cpm = _fh.safe_float(c.get("cpm")) * m_fx
    ctr = _fh.safe_float(c.get("ctr"))
    cpc = _fh.safe_float(c.get("cpc")) * m_fx
    clicks = _fh.safe_float(c.get("clicks"))
    atc = _fh.safe_float(c.get("add_to_carts"))
    purch = _fh.safe_float(c.get("purchases"))
    rev = _fh.safe_float(c.get("revenue_1d_click")) * m_fx
    roas = _fh.safe_float(c.get("purchase_roas"))
    c_atc = (spend / atc) if atc > 0 else None
    nc = _fh.safe_float(c.get("new_customer_purchases"))
    nc_rev = _fh.safe_float(c.get("new_customer_revenue")) * m_fx

    cid = c.get("campaign_id", "")
    status = c.get("effective_status", "")
    has_ads = bool(c.get("_has_ads"))
    name = c.get("campaign_name", "")

    expand_btn = ""
    if has_ads:
        expand_btn = (
            f'<button class="expand-btn" data-action="toggle-ads" '
            f'data-store="{_fh.attr(store_id)}" data-campaign="{_fh.attr(cid)}" '
            f'data-platform="meta" title="Show ads">▶</button> '
        )

    name_cell = (
        f'{expand_btn}<span class="camp-name" title="{_fh.attr(name)}">'
        f'{_fh.text(_fh.short(name, 50))}</span>'
    )

    cells = (
        _tm.cell(name_cell)
        + _tm.cell(_fh.status_badge(status))
        + _tm.cell('<span class="plat-badge meta">Meta</span>')
        + _tm.cell(_fh.money(spend, sym), "num")
        + _tm.cell(_fh.money(rev, sym), "num")
        + _tm.cell(_fh.number(roas, 2) if roas else "—", f"num {_fh.roas_class(roas)}")
        + _tm.cell(_fh.integer(purch) if purch else "—", "num")
        + _tm.cell(_fh.integer(reach) if reach else "—", "num")
        + _tm.cell(_fh.integer(impr) if impr else "—", "num")
        + _tm.cell(_fh.number(freq, 1) if freq else "—", f"num {_fh.freq_class(freq)}")
        + _tm.cell(_fh.money(cpm, sym, 2), "num")
        + _tm.cell(_fh.percent(ctr), "num")
        + _tm.cell(_fh.money(cpc, sym, 2), "num")
        + _tm.cell(_fh.integer(clicks) if clicks else "—", "num")
        + _tm.cell(_fh.integer(atc) if atc else "—", "num")
        + _tm.cell(_fh.money(c_atc, sym, 2) if c_atc else "—", "num")
        + _tm.cell(_fh.integer(nc) if nc else "—", "num")
        + _tm.cell(_fh.money(nc_rev, sym) if nc_rev else "—", "num")
        + _tm.cell(_fh.money(daily, sym), "num")
    )

    return (
        f'<tr class="camp-row" data-store="{_fh.attr(store_id)}" '
        f'data-platform="meta" data-campaign="{_fh.attr(cid)}" '
        f'data-status="{_fh.attr(status)}">{cells}</tr>'
    )


def ad_rows(ads: list, sym: str, m_fx: float, n_days: int, store_id, campaign_id) -> str:
    """N <tr>s, one per ad nested under a Meta campaign. Hidden by default."""
    out: list[str] = []
    for a in ads:
        spend = _fh.safe_float(a.get("spend")) * m_fx
        daily = spend / n_days if n_days else 0
        reach = _fh.safe_float(a.get("reach"))
        impr = _fh.safe_float(a.get("impressions"))
        freq = _fh.safe_float(a.get("frequency"))
        cpm = _fh.safe_float(a.get("cpm")) * m_fx
        ctr = _fh.safe_float(a.get("ctr"))
        cpc = _fh.safe_float(a.get("cpc")) * m_fx
        clicks = _fh.safe_float(a.get("clicks"))
        atc = _fh.safe_float(a.get("add_to_carts"))
        purch = _fh.safe_float(a.get("purchases"))
        rev = _fh.safe_float(a.get("revenue_1d_click")) * m_fx
        roas = _fh.safe_float(a.get("purchase_roas"))
        c_atc = (spend / atc) if atc > 0 else None
        nc = _fh.safe_float(a.get("new_customer_purchases"))
        nc_rev = _fh.safe_float(a.get("new_customer_revenue")) * m_fx
        adset = a.get("adset_name", "")
        status = a.get("effective_status", "")
        ad_name = a.get("ad_name", "")

        name_cell = (
            f'<span class="ad-indent">↳ '
            f'<strong>{_fh.text(_fh.short(ad_name, 44))}</strong>'
            f'<span class="adset-label"> ({_fh.text(_fh.short(adset, 30))})</span></span>'
        )

        cells = (
            _tm.cell(name_cell)
            + _tm.cell(_fh.status_badge(status))
            + _tm.cell('<span class="plat-badge meta" style="opacity:.6;font-size:10px">Ad</span>')
            + _tm.cell(_fh.money(spend, sym), "num")
            + _tm.cell(_fh.money(rev, sym), "num")
            + _tm.cell(_fh.number(roas, 2) if roas else "—", f"num {_fh.roas_class(roas)}")
            + _tm.cell(_fh.integer(purch) if purch else "—", "num")
            + _tm.cell(_fh.integer(reach) if reach else "—", "num")
            + _tm.cell(_fh.integer(impr) if impr else "—", "num")
            + _tm.cell(_fh.number(freq, 1) if freq else "—", f"num {_fh.freq_class(freq)}")
            + _tm.cell(_fh.money(cpm, sym, 2), "num")
            + _tm.cell(_fh.percent(ctr), "num")
            + _tm.cell(_fh.money(cpc, sym, 2), "num")
            + _tm.cell(_fh.integer(clicks) if clicks else "—", "num")
            + _tm.cell(_fh.integer(atc) if atc else "—", "num")
            + _tm.cell(_fh.money(c_atc, sym, 2) if c_atc else "—", "num")
            + _tm.cell(_fh.integer(nc) if nc else "—", "num")
            + _tm.cell(_fh.money(nc_rev, sym) if nc_rev else "—", "num")
            + _tm.cell(_fh.money(daily, sym), "num")
        )

        out.append(
            f'<tr class="ad-row hidden" data-store="{_fh.attr(store_id)}" '
            f'data-platform="meta" data-campaign="{_fh.attr(campaign_id)}">'
            f"{cells}</tr>"
        )

    return "\n".join(out)
