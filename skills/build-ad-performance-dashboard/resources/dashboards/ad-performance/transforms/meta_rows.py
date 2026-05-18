"""Meta campaign + ad-row HTML emitter.

Renders a campaign row (with expand button when ad-level data exists) and
its child ad rows. Both share the same 20-column shape — only the name
cell + platform badge differ.

Standalone module per repo convention: format helpers, action-rule logic,
and tiny HTML helpers are all inlined here. Mirror file:
`transforms/google_rows.py` (same shape, different field names).
"""

from __future__ import annotations

import html as _html
import math
from typing import Optional


# ── Inlined helpers (no inter-component imports) ─────────────────────
def _safe_float(value, default: float = 0.0) -> float:
    try:
        v = float(value or 0)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except (TypeError, ValueError):
        return default


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


def _freq_class(freq, t):
    f = _safe_float(freq)
    if f >= t["freq_bad"]: return "bad"
    if f >= t["freq_ok"]:  return "ok"
    return ""


_ACTION_PILLS = {
    "SCALE":   ("act-scale",   "Strong ROAS, frequency still healthy — increase budget"),
    "REFRESH": ("act-refresh", "Frequency high but ROAS holds — refresh creative"),
    "HOLD":    ("act-hold",    "Performance OK but not exceptional — hold steady"),
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
    cls, tip = _ACTION_PILLS.get(_action_for(roas, freq, spend, t), _ACTION_PILLS[None])
    return f'<span class="act-pill {cls}" title="{tip}">{_action_for(roas, freq, spend, t) or "—"}</span>'


def _td(content, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


# ── Shared metric cells (cols 4-20). Used by both campaign + ad row. ──
def _metric_cells(row, sym, fx, n_days, t):
    spend = _safe_float(row.get("spend")) * fx
    daily = spend / n_days if n_days else 0
    reach = _safe_float(row.get("reach"))
    impr = _safe_float(row.get("impressions"))
    freq = _safe_float(row.get("frequency"))
    cpm = _safe_float(row.get("cpm")) * fx
    ctr = _safe_float(row.get("ctr"))
    cpc = _safe_float(row.get("cpc")) * fx
    clicks = _safe_float(row.get("clicks"))
    atc = _safe_float(row.get("add_to_carts"))
    purch = _safe_float(row.get("purchases"))
    rev = _safe_float(row.get("revenue_1d_click")) * fx
    roas = _safe_float(row.get("purchase_roas"))
    c_atc = (spend / atc) if atc > 0 else None
    nc = _safe_float(row.get("new_customer_purchases"))
    nc_rev = _safe_float(row.get("new_customer_revenue")) * fx
    return (
        _td(_fmt_money(spend, sym), "num")
      + _td(_fmt_money(rev, sym), "num")
      + _td(_fmt_float(roas, 2) if roas else "—", f"num {_roas_class(roas, t)}")
      + _td(_action_pill(roas, freq, spend, t))
      + _td(_fmt_int(purch)  if purch  else "—", "num")
      + _td(_fmt_int(reach)  if reach  else "—", "num")
      + _td(_fmt_int(impr)   if impr   else "—", "num")
      + _td(_fmt_float(freq, 1) if freq else "—", f"num {_freq_class(freq, t)}")
      + _td(_fmt_money(cpm, sym, 2), "num") + _td(_fmt_pct(ctr), "num")
      + _td(_fmt_money(cpc, sym, 2), "num")
      + _td(_fmt_int(clicks) if clicks else "—", "num")
      + _td(_fmt_int(atc) if atc else "—", "num")
      + _td(_fmt_money(c_atc, sym, 2) if c_atc else "—", "num")
      + _td(_fmt_int(nc) if nc else "—", "num")
      + _td(_fmt_money(nc_rev, sym) if nc_rev else "—", "num")
      + _td(_fmt_money(daily, sym), "num")
    )


def campaign_row(camp, sym, fx, n_days, store_id, has_ads, thresholds):
    cid = camp.get("campaign_id", "")
    status = camp.get("effective_status", "")
    name = camp.get("campaign_name", "") or ""
    btn = ""
    if has_ads:
        btn = (f'<button class="expand-btn" data-store="{store_id}" data-campaign="{cid}" '
               f'data-platform="meta" onclick="toggleAds(this)" title="Show ads">▶</button> ')
    return (
        f'<tr class="camp-row" data-store="{store_id}" data-platform="meta" '
        f'data-campaign="{cid}" data-status="{status}">'
        + _td(f'{btn}<span class="camp-name" title="{_esc(name)}">{_esc(_short(name, 50))}</span>')
        + _td(_status_badge(status))
        + _td('<span class="plat-badge meta">Meta</span>')
        + _metric_cells(camp, sym, fx, n_days, thresholds)
        + "</tr>"
    )


def ad_rows(ads, sym, fx, n_days, store_id, campaign_id, thresholds):
    parts = []
    for a in ads:
        name = a.get("ad_name", "") or ""
        adset = a.get("adset_name", "") or ""
        status = a.get("effective_status", "")
        name_cell = (f'<span class="ad-indent">↳ <strong>{_esc(_short(name, 44))}</strong>'
                     f'<span class="adset-label"> ({_esc(_short(adset, 30))})</span></span>')
        parts.append(
            f'<tr class="ad-row hidden" data-store="{store_id}" data-platform="meta" '
            f'data-campaign="{campaign_id}">'
            + _td(name_cell)
            + _td(_status_badge(status))
            + _td('<span class="plat-badge meta" style="opacity:.6;font-size:10px">Ad</span>')
            + _metric_cells(a, sym, fx, n_days, thresholds)
            + "</tr>"
        )
    return "\n".join(parts)
