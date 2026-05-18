"""Google campaign + ad/asset-group row emitter.

Mirror of `transforms/meta_rows.py` for the Google side. Differences:
* No reach / frequency / ATC at campaign-insights level (those cells "—").
* ROAS computed as `conversions_value / spend` (Google has no
  `purchase_roas` field).
* PMAX asset groups render with just creative names + dashes — they
  carry no per-asset spend.

Standalone — helpers inlined to match the repo convention.
"""

from __future__ import annotations

import html as _html
import math
from typing import Optional


def _safe_float(v, d=0.0):
    try:
        f = float(v or 0)
        return f if not (math.isnan(f) or math.isinf(f)) else d
    except (TypeError, ValueError): return d


def _fmt_float(v, d=2):
    if v is None: return "—"
    try:
        f = float(v)
        return "—" if (math.isnan(f) or math.isinf(f)) else f"{f:,.{d}f}"
    except (TypeError, ValueError): return "—"


def _fmt_pct(v, d=2):
    if v is None: return "—"
    try: return f"{float(v):.{d}f}%"
    except (TypeError, ValueError): return "—"


def _fmt_money(v, sym="", d=0):
    if v is None: return "—"
    try:
        f = float(v)
        return "—" if (math.isnan(f) or math.isinf(f)) else f"{sym}{f:,.{d}f}"
    except (TypeError, ValueError): return "—"


def _fmt_int(v):
    if v is None: return "—"
    try: return f"{int(v):,}"
    except (TypeError, ValueError): return "—"


def _short(t, n=52):
    if not t: return "—"
    return t[:n] + "…" if len(t) > n else t


def _esc(t, q=False): return _html.escape(t or "", quote=q)


def _status_badge(status):
    s = (status or "").upper()
    if s in ("ACTIVE", "ENABLED"): return '<span class="badge active">Active</span>'
    if s == "PAUSED": return '<span class="badge paused">Paused</span>'
    return f'<span class="badge other">{_esc(status or "—")}</span>'


def _roas_class(roas, t):
    if roas is None: return ""
    r = _safe_float(roas)
    if r >= t["roas_good"]: return "good"
    if r >= t["roas_ok"]:   return "ok"
    return "bad" if r > 0 else ""


_ACTION_PILLS = {
    "SCALE":   ("act-scale",   "Strong ROAS — increase budget"),
    "REFRESH": ("act-refresh", "Frequency high but ROAS holds — refresh creative"),
    "HOLD":    ("act-hold",    "Performance OK — hold steady"),
    "PAUSE":   ("act-pause",   "Below break-even at meaningful spend — review or pause"),
    None:      ("act-none",    "Not enough spend to act on"),
}


def _action_for(roas, freq, spend, t) -> Optional[str]:
    r, fq, s = _safe_float(roas), _safe_float(freq), _safe_float(spend)
    if s < t["action_min_spend"] or r <= 0: return None
    if r >= t["scale_roas"] and (fq == 0 or fq < t["scale_max_freq"]): return "SCALE"
    if fq >= t["refresh_min_freq"] and r >= t["refresh_min_roas"]:     return "REFRESH"
    if r < t["pause_roas"] and s > t["pause_min_spend"]:               return "PAUSE"
    return "HOLD"


def _action_pill(roas, freq, spend, t):
    label = _action_for(roas, freq, spend, t)
    cls, tip = _ACTION_PILLS.get(label, _ACTION_PILLS[None])
    return f'<span class="act-pill {cls}" title="{tip}">{label or "—"}</span>'


def _td(content, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def _google_roas(row):
    s = _safe_float(row.get("spend"))
    r = _safe_float(row.get("conversions_value"))
    return (r / s) if s > 0 else None


def _metric_cells(row, sym, fx, n_days, t):
    spend = _safe_float(row.get("spend")) * fx
    daily = spend / n_days if n_days else 0
    impr = _safe_float(row.get("impressions"))
    clicks = _safe_float(row.get("clicks"))
    ctr_raw = _safe_float(row.get("ctr"))
    ctr = ctr_raw * 100 if ctr_raw and ctr_raw < 2 else ctr_raw
    cpc = _safe_float(row.get("average_cpc")) * fx
    cpm = _safe_float(row.get("average_cpm")) * fx
    conv = _safe_float(row.get("conversions"))
    conv_val = _safe_float(row.get("conversions_value")) * fx
    roas = _google_roas(row)
    nc = _safe_float(row.get("new_customer_conversions"))
    nc_rev = _safe_float(row.get("new_customer_conversions_value")) * fx
    return (
        _td(_fmt_money(spend, sym), "num") + _td(_fmt_money(conv_val, sym), "num")
      + _td(_fmt_float(roas, 2) if roas else "—", f"num {_roas_class(roas, t)}")
      + _td(_action_pill(roas, 0, spend, t))
      + _td(_fmt_float(conv, 1) if conv else "—", "num")
      + _td("—", "num") + _td(_fmt_int(impr) if impr else "—", "num") + _td("—", "num")
      + _td(_fmt_money(cpm, sym, 2), "num") + _td(_fmt_pct(ctr), "num")
      + _td(_fmt_money(cpc, sym, 2), "num")
      + _td(_fmt_int(clicks) if clicks else "—", "num")
      + _td("—", "num") + _td("—", "num")
      + _td(_fmt_float(nc, 1) if nc else "—", "num")
      + _td(_fmt_money(nc_rev, sym) if nc_rev else "—", "num")
      + _td(_fmt_money(daily, sym), "num")
    )


def campaign_row(camp, sym, fx, n_days, store_id, has_ads, thresholds):
    cid = camp.get("campaign_id", "")
    status = camp.get("campaign_status", "")
    name = camp.get("campaign_name", "") or ""
    ctype = camp.get("campaign_type", "")
    btn = ""
    if has_ads:
        btn = (f'<button class="expand-btn" data-store="{store_id}" data-campaign="{cid}" '
               f'data-platform="google" onclick="toggleAds(this)" '
               f'title="Show ads/asset groups">▶</button> ')
    name_cell = (f'{btn}<span class="camp-name" title="{_esc(name)}">'
                 f'{_esc(_short(name, 50))}</span>'
                 f'<span class="camp-type">{_esc(ctype)}</span>')
    return (
        f'<tr class="camp-row" data-store="{store_id}" data-platform="google" '
        f'data-campaign="{cid}" data-status="{status}">'
        + _td(name_cell) + _td(_status_badge(status))
        + _td('<span class="plat-badge google">Google</span>')
        + _metric_cells(camp, sym, fx, n_days, thresholds) + "</tr>"
    )


def ad_rows(items, sym, fx, n_days, store_id, campaign_id, is_pmax, thresholds):
    parts = []
    for a in items:
        if is_pmax:
            ag_name = a.get("asset_group_name", "Asset Group")
            headlines = " / ".join((a.get("headlines") or [])[:2])
            nc = (f'<span class="ad-indent">↳ <strong>{_esc(_short(ag_name, 44))}</strong>'
                  f'<span class="adset-label"> {_esc(_short(headlines, 60))}</span></span>')
            parts.append(
                f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="google" '
                f'data-campaign="{campaign_id}">'
                + _td(nc) + _td('<span class="badge other">PMAX Asset Group</span>')
                + _td('<span class="plat-badge google" style="opacity:.6;font-size:10px">Group</span>')
                + ("<td class='num'>—</td>" * 17) + "</tr>"
            )
        else:
            status = a.get("effective_status", "")
            ad_name = a.get("ad_name") or a.get("ad_id") or "Ad"
            ag_name = a.get("ad_group_name", "") or ""
            nc = (f'<span class="ad-indent">↳ <strong>{_esc(_short(ad_name, 44))}</strong>'
                  f'<span class="adset-label"> ({_esc(_short(ag_name, 30))})</span></span>')
            parts.append(
                f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="google" '
                f'data-campaign="{campaign_id}">'
                + _td(nc) + _td(_status_badge(status))
                + _td('<span class="plat-badge google" style="opacity:.6;font-size:10px">Ad</span>')
                + _metric_cells(a, sym, fx, n_days, thresholds) + "</tr>"
            )
    return "\n".join(parts)
