"""Meta campaign + ad-row HTML emitter.

Both rows share the same 20-column shape. The campaign row gets the
expand-button + platform badge; the ad row indents under it and shows the
ad set name in muted text.

All thresholds and FX rates are passed in via parameters — no hard-coded
constants inside this module.
"""

from __future__ import annotations

from . import _fmt as f
from . import action_rules as rules


def _td(content: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def _common_metric_cells(row: dict, sym: str, fx: float, n_days: int, thresholds: dict) -> str:
    """Render the shared metric cells (cols 4-20). Used by both camp + ad rows."""
    spend = f.safe_float(row.get("spend")) * fx
    daily = spend / n_days if n_days else 0
    reach = f.safe_float(row.get("reach"))
    impr = f.safe_float(row.get("impressions"))
    freq = f.safe_float(row.get("frequency"))
    cpm = f.safe_float(row.get("cpm")) * fx
    ctr = f.safe_float(row.get("ctr"))
    cpc = f.safe_float(row.get("cpc")) * fx
    clicks = f.safe_float(row.get("clicks"))
    atc = f.safe_float(row.get("add_to_carts"))
    purch = f.safe_float(row.get("purchases"))
    rev = f.safe_float(row.get("revenue_1d_click")) * fx
    roas = f.safe_float(row.get("purchase_roas"))
    c_atc = (spend / atc) if atc > 0 else None
    nc = f.safe_float(row.get("new_customer_purchases"))
    nc_rev = f.safe_float(row.get("new_customer_revenue")) * fx
    action_label = rules.action_for(roas, freq, spend, thresholds)

    return (
        _td(f.fmt_money(spend, sym), "num")
      + _td(f.fmt_money(rev, sym), "num")
      + _td(f.fmt_float(roas, 2) if roas else "—", f"num {f.roas_class(roas, thresholds)}")
      + _td(rules.action_pill_html(action_label))
      + _td(f.fmt_int(purch)  if purch  else "—", "num")
      + _td(f.fmt_int(reach)  if reach  else "—", "num")
      + _td(f.fmt_int(impr)   if impr   else "—", "num")
      + _td(f.fmt_float(freq, 1) if freq else "—", f"num {f.freq_class(freq, thresholds)}")
      + _td(f.fmt_money(cpm, sym, 2), "num")
      + _td(f.fmt_pct(ctr), "num")
      + _td(f.fmt_money(cpc, sym, 2), "num")
      + _td(f.fmt_int(clicks) if clicks else "—", "num")
      + _td(f.fmt_int(atc)    if atc    else "—", "num")
      + _td(f.fmt_money(c_atc, sym, 2) if c_atc else "—", "num")
      + _td(f.fmt_int(nc)     if nc     else "—", "num")
      + _td(f.fmt_money(nc_rev, sym) if nc_rev else "—", "num")
      + _td(f.fmt_money(daily, sym), "num")
    )


def campaign_row(camp: dict, sym: str, fx: float, n_days: int,
                 store_id: int, has_ads: bool, thresholds: dict) -> str:
    cid = camp.get("campaign_id", "")
    status = camp.get("effective_status", "")
    name = camp.get("campaign_name", "") or ""
    expand_btn = ""
    if has_ads:
        expand_btn = (f'<button class="expand-btn" data-store="{store_id}" '
                      f'data-campaign="{cid}" data-platform="meta" '
                      f'onclick="toggleAds(this)" title="Show ads">▶</button> ')
    name_cell = (
        f'{expand_btn}<span class="camp-name" title="{f.html_escape(name)}">'
        f'{f.html_escape(f.short(name, 50))}</span>'
    )
    return (
        f'<tr class="camp-row" data-store="{store_id}" data-platform="meta" '
        f'data-campaign="{cid}" data-status="{status}">'
        + _td(name_cell)
        + _td(f.status_badge(status))
        + _td('<span class="plat-badge meta">Meta</span>')
        + _common_metric_cells(camp, sym, fx, n_days, thresholds)
        + "</tr>"
    )


def ad_rows(ads: list[dict], sym: str, fx: float, n_days: int,
            store_id: int, campaign_id: str, thresholds: dict) -> str:
    parts: list[str] = []
    for a in ads:
        adset = a.get("adset_name", "") or ""
        status = a.get("effective_status", "")
        name = a.get("ad_name", "") or ""
        name_cell = (
            f'<span class="ad-indent">↳ <strong>{f.html_escape(f.short(name, 44))}</strong>'
            f'<span class="adset-label"> ({f.html_escape(f.short(adset, 30))})</span></span>'
        )
        parts.append(
            f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="meta" '
            f'data-campaign="{campaign_id}">'
            + _td(name_cell)
            + _td(f.status_badge(status))
            + _td('<span class="plat-badge meta" style="opacity:.6;font-size:10px">Ad</span>')
            + _common_metric_cells(a, sym, fx, n_days, thresholds)
            + "</tr>"
        )
    return "\n".join(parts)
