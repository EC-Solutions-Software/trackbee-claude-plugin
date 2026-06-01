"""Google campaign + ad / asset-group row builders.

Google's API contract differs from Meta — no `reach` or `frequency`, no
`add_to_carts`, and PMAX returns `asset_groups` instead of `ads` (the
asset groups carry creative info but no per-spend metrics). The cells
still follow the canonical column order in `table_meta.CAMPAIGN_HEADERS`,
just with em-dashes where data isn't available.
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


def campaign_row(c: dict, sym: str, g_fx: float, n_days: int, store_id) -> str:
    """One <tr> for one Google campaign."""
    spend = _fh.safe_float(c.get("spend")) * g_fx
    daily = spend / n_days if n_days else 0
    impr = _fh.safe_float(c.get("impressions"))
    clicks = _fh.safe_float(c.get("clicks"))
    # Google returns CTR as a fraction (0.0–1.0). Multiply once here.
    ctr = _fh.safe_float(c.get("ctr")) * 100
    cpc = _fh.safe_float(c.get("average_cpc")) * g_fx
    cpm = _fh.safe_float(c.get("average_cpm")) * g_fx
    conv = _fh.safe_float(c.get("conversions"))
    conv_val = _fh.safe_float(c.get("conversions_value")) * g_fx
    roas = _fh.google_roas(c)
    nc = _fh.safe_float(c.get("new_customer_conversions"))
    nc_rev = _fh.safe_float(c.get("new_customer_conversions_value")) * g_fx

    cid = c.get("campaign_id", "")
    status = c.get("campaign_status", "")
    ctype = c.get("campaign_type", "")
    name = c.get("campaign_name", "")
    has_ads = bool(c.get("_has_ads"))

    expand_btn = ""
    if has_ads:
        expand_btn = (
            f'<button class="expand-btn" data-action="toggle-ads" '
            f'data-store="{_fh.attr(store_id)}" data-campaign="{_fh.attr(cid)}" '
            f'data-platform="google" title="Show ads/asset groups">▶</button> '
        )

    name_cell = (
        f'{expand_btn}<span class="camp-name" title="{_fh.attr(name)}">'
        f'{_fh.text(_fh.short(name, 50))}</span>'
        f'<span class="camp-type">{_fh.text(ctype)}</span>'
    )

    cells = (
        _tm.cell(name_cell)
        + _tm.cell(_fh.status_badge(status))
        + _tm.cell('<span class="plat-badge google">Google</span>')
        + _tm.cell(_fh.money(spend, sym), "num")
        + _tm.cell(_fh.money(conv_val, sym), "num")
        + _tm.cell(_fh.number(roas, 2) if roas else "—", f"num {_fh.roas_class(roas)}")
        # Google has no frequency, so the action badge gets freq=0.
        + _tm.cell(_tm.action_badge(roas, 0, spend))
        + _tm.cell(_fh.number(conv, 1) if conv else "—", "num")
        + _tm.cell("—", "num")  # reach — not in Google API
        + _tm.cell(_fh.integer(impr) if impr else "—", "num")
        + _tm.cell("—", "num")  # frequency — not in Google API
        + _tm.cell(_fh.money(cpm, sym, 2), "num")
        + _tm.cell(_fh.percent(ctr), "num")
        + _tm.cell(_fh.money(cpc, sym, 2), "num")
        + _tm.cell(_fh.integer(clicks) if clicks else "—", "num")
        + _tm.cell("—", "num")  # ATC — not in Google API
        + _tm.cell("—", "num")  # Cost/ATC — derived from ATC
        + _tm.cell(_fh.number(nc, 1) if nc else "—", "num")
        + _tm.cell(_fh.money(nc_rev, sym) if nc_rev else "—", "num")
        + _tm.cell(_fh.money(daily, sym), "num")
    )

    return (
        f'<tr class="camp-row" data-store="{_fh.attr(store_id)}" '
        f'data-platform="google" data-campaign="{_fh.attr(cid)}" '
        f'data-status="{_fh.attr(status)}">{cells}</tr>'
    )


def ad_rows(items: list, sym: str, g_fx: float, n_days: int, store_id, campaign_id, is_pmax: bool = False) -> str:
    """N <tr>s, one per Google ad (or PMAX asset group). Hidden by default."""
    out: list[str] = []
    for a in items:
        if is_pmax:
            # PMAX asset groups carry creative info only — no per-spend metrics.
            ag_name = a.get("asset_group_name", "Asset Group")
            headlines = " / ".join((a.get("headlines") or [])[:2])
            name_cell = (
                f'<span class="ad-indent">↳ '
                f'<strong>{_fh.text(_fh.short(ag_name, 44))}</strong>'
                f'<span class="adset-label"> {_fh.text(_fh.short(headlines, 60))}</span></span>'
            )
            # 17 filler cells after the 3 label columns.
            out.append(
                f'<tr class="ad-row hidden" data-store="{_fh.attr(store_id)}" '
                f'data-platform="google" data-campaign="{_fh.attr(campaign_id)}">'
                + _tm.cell(name_cell)
                + _tm.cell('<span class="badge other">PMAX Asset Group</span>')
                + _tm.cell('<span class="plat-badge google" style="opacity:.6;font-size:10px">Group</span>')
                + ("<td class='num'>—</td>" * 17)
                + "</tr>"
            )
            continue

        spend = _fh.safe_float(a.get("spend")) * g_fx
        daily = spend / n_days if n_days else 0
        impr = _fh.safe_float(a.get("impressions"))
        clicks = _fh.safe_float(a.get("clicks"))
        ctr = _fh.safe_float(a.get("ctr")) * 100
        cpc = _fh.safe_float(a.get("average_cpc")) * g_fx
        cpm = _fh.safe_float(a.get("average_cpm")) * g_fx
        conv = _fh.safe_float(a.get("conversions"))
        conv_val = _fh.safe_float(a.get("conversions_value")) * g_fx
        roas = (conv_val / spend) if spend > 0 else None
        nc = _fh.safe_float(a.get("new_customer_conversions"))
        nc_rev = _fh.safe_float(a.get("new_customer_conversions_value")) * g_fx
        ad_name = a.get("ad_name") or a.get("ad_id") or "Ad"
        ag_name = a.get("ad_group_name", "")
        status = a.get("effective_status", "")

        name_cell = (
            f'<span class="ad-indent">↳ '
            f'<strong>{_fh.text(_fh.short(ad_name, 44))}</strong>'
            f'<span class="adset-label"> ({_fh.text(_fh.short(ag_name, 30))})</span></span>'
        )

        cells = (
            _tm.cell(name_cell)
            + _tm.cell(_fh.status_badge(status))
            + _tm.cell('<span class="plat-badge google" style="opacity:.6;font-size:10px">Ad</span>')
            + _tm.cell(_fh.money(spend, sym), "num")
            + _tm.cell(_fh.money(conv_val, sym), "num")
            + _tm.cell(_fh.number(roas, 2) if roas else "—", f"num {_fh.roas_class(roas)}")
            + _tm.cell(_tm.action_badge(roas, 0, spend))
            + _tm.cell(_fh.number(conv, 1) if conv else "—", "num")
            + _tm.cell("—", "num")
            + _tm.cell(_fh.integer(impr) if impr else "—", "num")
            + _tm.cell("—", "num")
            + _tm.cell(_fh.money(cpm, sym, 2), "num")
            + _tm.cell(_fh.percent(ctr), "num")
            + _tm.cell(_fh.money(cpc, sym, 2), "num")
            + _tm.cell(_fh.integer(clicks) if clicks else "—", "num")
            + _tm.cell("—", "num")
            + _tm.cell("—", "num")
            + _tm.cell(_fh.number(nc, 1) if nc else "—", "num")
            + _tm.cell(_fh.money(nc_rev, sym) if nc_rev else "—", "num")
            + _tm.cell(_fh.money(daily, sym), "num")
        )

        out.append(
            f'<tr class="ad-row hidden" data-store="{_fh.attr(store_id)}" '
            f'data-platform="google" data-campaign="{_fh.attr(campaign_id)}">'
            f"{cells}</tr>"
        )

    return "\n".join(out)
