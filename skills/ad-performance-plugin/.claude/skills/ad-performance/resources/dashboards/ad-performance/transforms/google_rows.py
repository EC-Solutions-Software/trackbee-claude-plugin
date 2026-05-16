"""Google campaign + ad/asset-group row emitter.

Google has no reach / frequency / ATC at the campaign-insights level — those
cells render as "—". ROAS is computed as `conversions_value / spend`.

PMAX asset groups have no per-asset spend data, so they render with just
the creative name + a label and dashes in every metric cell.
"""

from __future__ import annotations

from . import _fmt as f
from . import action_rules as rules


def _td(content: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def _google_roas(row: dict) -> float | None:
    spend = f.safe_float(row.get("spend"))
    rev = f.safe_float(row.get("conversions_value"))
    if spend <= 0:
        return None
    return rev / spend


def _metric_cells(row: dict, sym: str, fx: float, n_days: int, thresholds: dict) -> str:
    spend = f.safe_float(row.get("spend")) * fx
    daily = spend / n_days if n_days else 0
    impr = f.safe_float(row.get("impressions"))
    clicks = f.safe_float(row.get("clicks"))
    ctr_raw = f.safe_float(row.get("ctr"))
    ctr = ctr_raw * 100 if ctr_raw and ctr_raw < 2 else ctr_raw
    cpc = f.safe_float(row.get("average_cpc")) * fx
    cpm = f.safe_float(row.get("average_cpm")) * fx
    conv = f.safe_float(row.get("conversions"))
    conv_val = f.safe_float(row.get("conversions_value")) * fx
    roas = _google_roas(row)
    nc = f.safe_float(row.get("new_customer_conversions"))
    nc_rev = f.safe_float(row.get("new_customer_conversions_value")) * fx
    action_label = rules.action_for(roas, 0, spend, thresholds)

    return (
        _td(f.fmt_money(spend, sym), "num")
      + _td(f.fmt_money(conv_val, sym), "num")
      + _td(f.fmt_float(roas, 2) if roas else "—", f"num {f.roas_class(roas, thresholds)}")
      + _td(rules.action_pill_html(action_label))
      + _td(f.fmt_float(conv, 1) if conv else "—", "num")
      + _td("—", "num")                        # Reach — not in Google API
      + _td(f.fmt_int(impr) if impr else "—", "num")
      + _td("—", "num")                        # Frequency — not in Google API
      + _td(f.fmt_money(cpm, sym, 2), "num")
      + _td(f.fmt_pct(ctr), "num")
      + _td(f.fmt_money(cpc, sym, 2), "num")
      + _td(f.fmt_int(clicks) if clicks else "—", "num")
      + _td("—", "num")                        # ATC — not in Google API
      + _td("—", "num")                        # Cost/ATC
      + _td(f.fmt_float(nc, 1) if nc else "—", "num")
      + _td(f.fmt_money(nc_rev, sym) if nc_rev else "—", "num")
      + _td(f.fmt_money(daily, sym), "num")
    )


def campaign_row(camp: dict, sym: str, fx: float, n_days: int,
                 store_id: int, has_ads: bool, thresholds: dict) -> str:
    cid = camp.get("campaign_id", "")
    status = camp.get("campaign_status", "")
    name = camp.get("campaign_name", "") or ""
    ctype = camp.get("campaign_type", "")
    expand_btn = ""
    if has_ads:
        expand_btn = (f'<button class="expand-btn" data-store="{store_id}" '
                      f'data-campaign="{cid}" data-platform="google" '
                      f'onclick="toggleAds(this)" title="Show ads/asset groups">▶</button> ')
    name_cell = (
        f'{expand_btn}<span class="camp-name" title="{f.html_escape(name)}">'
        f'{f.html_escape(f.short(name, 50))}</span>'
        f'<span class="camp-type">{f.html_escape(ctype)}</span>'
    )
    return (
        f'<tr class="camp-row" data-store="{store_id}" data-platform="google" '
        f'data-campaign="{cid}" data-status="{status}">'
        + _td(name_cell)
        + _td(f.status_badge(status))
        + _td('<span class="plat-badge google">Google</span>')
        + _metric_cells(camp, sym, fx, n_days, thresholds)
        + "</tr>"
    )


def ad_rows(items: list[dict], sym: str, fx: float, n_days: int, store_id: int,
            campaign_id: str, is_pmax: bool, thresholds: dict) -> str:
    parts: list[str] = []
    for a in items:
        if is_pmax:
            ag_name = a.get("asset_group_name", "Asset Group")
            headlines = " / ".join((a.get("headlines") or [])[:2])
            name_cell = (
                f'<span class="ad-indent">↳ <strong>{f.html_escape(f.short(ag_name, 44))}</strong>'
                f'<span class="adset-label"> {f.html_escape(f.short(headlines, 60))}</span></span>'
            )
            parts.append(
                f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="google" '
                f'data-campaign="{campaign_id}">'
                + _td(name_cell)
                + _td('<span class="badge other">PMAX Asset Group</span>')
                + _td('<span class="plat-badge google" style="opacity:.6;font-size:10px">Group</span>')
                + ("<td class='num'>—</td>" * 17)
                + "</tr>"
            )
        else:
            status = a.get("effective_status", "")
            ad_name = a.get("ad_name") or a.get("ad_id") or "Ad"
            ag_name = a.get("ad_group_name", "") or ""
            name_cell = (
                f'<span class="ad-indent">↳ <strong>{f.html_escape(f.short(ad_name, 44))}</strong>'
                f'<span class="adset-label"> ({f.html_escape(f.short(ag_name, 30))})</span></span>'
            )
            parts.append(
                f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="google" '
                f'data-campaign="{campaign_id}">'
                + _td(name_cell)
                + _td(f.status_badge(status))
                + _td('<span class="plat-badge google" style="opacity:.6;font-size:10px">Ad</span>')
                + _metric_cells(a, sym, fx, n_days, thresholds)
                + "</tr>"
            )
    return "\n".join(parts)
