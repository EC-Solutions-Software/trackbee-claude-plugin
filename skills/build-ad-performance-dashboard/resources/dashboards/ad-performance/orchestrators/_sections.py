"""Per-store section builder + missing-data card emitter.

Split out of `assemble.py` so each file stays under the orchestrator
size limit. All HTML-template substitution for a single store lives here.

`render_store(...)` returns:
    (
        {"id": int, "name_html": str, "html": str},
        [<issue dict>, ...]
    )

Issues bubble up so the orchestrator can group them into a global
"Data we couldn't load" banner. The orchestrator passes in its own
`load_raw`, `load_module` and `read_file` helpers so this file remains
standalone (no inter-component imports).
"""

from __future__ import annotations

import html as _html
import math
import re
from pathlib import Path


def _safe_float(v, d=0.0):
    try:
        f = float(v or 0)
        return f if not (math.isnan(f) or math.isinf(f)) else d
    except (TypeError, ValueError): return d


def _fmt_money(v, sym="", d=0):
    if v is None: return "—"
    try:
        f = float(v)
        return "—" if (math.isnan(f) or math.isinf(f)) else f"{sym}{f:,.{d}f}"
    except (TypeError, ValueError): return "—"


def _fmt_float(v, d=2):
    if v is None: return "—"
    try:
        f = float(v)
        return "—" if (math.isnan(f) or math.isinf(f)) else f"{f:,.{d}f}"
    except (TypeError, ValueError): return "—"


def _fmt_int(v):
    if v is None: return "—"
    try: return f"{int(v):,}"
    except (TypeError, ValueError): return "—"


def _esc(t, q=False): return _html.escape(t or "", quote=q)


def _roas_class(roas, t):
    if roas is None: return ""
    r = _safe_float(roas)
    if r >= t["roas_good"]: return "good"
    if r >= t["roas_ok"]:   return "ok"
    return "bad" if r > 0 else ""


# 20-column header manifest — adding/renaming a column is a one-line edit.
CAMPAIGN_HEADERS: list[tuple[str, str, str]] = [
    ("Name","name",""), ("Status","status",""), ("Platform","platform",""),
    ("Spend","spend","Total spend in the window"),
    ("Revenue","revenue","1d-click revenue (Meta) / Conversion value (Google)"),
    ("ROAS","roas","Return on ad spend (platform-reported)"),
    ("Action","action","Suggested next move"),
    ("Results","results","Purchases (Meta) / Conversions (Google)"),
    ("Reach","reach","Unique people reached"),
    ("Impressions","impr","Total impressions"),
    ("Freq","freq","Average frequency (impressions ÷ reach)"),
    ("CPM","cpm","Cost per 1,000 impressions"),
    ("CTR","ctr","Click-through rate"),
    ("CPC","cpc","Cost per click"),
    ("Clicks","clicks","Total link clicks"),
    ("ATC","atc","Add-to-cart events"),
    ("Cost/ATC","cost_atc","Spend ÷ add-to-cart"),
    ("New Cust.","nc","New customer purchases"),
    ("NC Revenue","nc_rev","New customer revenue"),
    ("Avg Daily","daily","Average daily spend (total ÷ days)"),
]


def _th(label, sort_key, tip):
    tip_attr = f' title="{_esc(tip, q=True)}"' if tip else ""
    sk_attr = f' data-sort="{sort_key}"' if sort_key else ""
    ind = ('<span class="sort-ind" aria-hidden="true">'
           '<span class="ar ar-up">▲</span><span class="ar ar-down">▼</span></span>'
           if sort_key else "")
    return f"<th{sk_attr}{tip_attr}>{label}{ind}</th>"


def _kpi_html(read_file, views_dir, kpis, store_cfg, thresholds):
    sym = store_cfg.get("currency_symbol", store_cfg.get("currency", ""))
    return (read_file(views_dir / "kpi_bar.html")
            .replace("{TOTAL_SPEND}", _fmt_money(kpis["total_spend"], sym))
            .replace("{META_SPEND}",  _fmt_money(kpis["meta_spend"], sym))
            .replace("{GOOG_SPEND}",  _fmt_money(kpis["goog_spend"], sym))
            .replace("{BLENDED_CLASS}", _roas_class(kpis["blended_roas"], thresholds))
            .replace("{BLENDED_ROAS}", _fmt_float(kpis["blended_roas"], 2))
            .replace("{META_ROAS}",    _fmt_float(kpis["meta_roas"], 2))
            .replace("{GOOG_ROAS}",    _fmt_float(kpis["goog_roas"], 2))
            .replace("{MER}",          _fmt_float(kpis["mer"], 2))
            .replace("{CONVERSIONS}",  _fmt_int(kpis["conversions"]))
            .replace("{META_PURCH}",   _fmt_int(kpis["meta_purch"]))
            .replace("{GOOG_CONV}",    _fmt_float(kpis["goog_conv"], 0))
            .replace("{AVG_DAILY}",    _fmt_money(kpis["avg_daily"], sym))
            .replace("{N_DAYS}",       str(kpis["n_days"])))


def _placeholder(read_file, views_dir, issue):
    return (read_file(views_dir / "placeholder_card.html")
            .replace("{TITLE}", _esc(issue.get("title", "Data unavailable")))
            .replace("{BODY}",  _esc(issue.get("body", "")))
            .replace("{FIX}",   _esc(issue.get("fix", ""))))


def _ins_li(items): return "".join(f"<li>{i}</li>" for i in items)


def _q_card(i, q):
    plain = re.sub(r"<[^>]+>", "", q["q"]).strip()
    return (f'<div class="q-card"><div class="q-num">Q{i+1}</div>'
            f'<div class="q-body"><div class="q-text">{q["q"]}</div>'
            f'<div class="q-why">{q["why"]}</div></div>'
            f'<button class="q-copy" type="button" data-q="{_esc(plain, q=True)}" '
            f'onclick="copyQuestion(this)" aria-label="Copy question">'
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>'
            f'<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
            f'<span class="q-copy-label">Copy</span></button></div>')


def render_store(store_cfg, window, inputs_dir: Path, transforms_dir: Path,
                 insights_dir: Path, views_dir: Path, thresholds: dict,
                 load_raw, load_module, read_file):
    sid = store_cfg["id"]
    name = store_cfg.get("name", f"Store {sid}")
    sym = store_cfg.get("currency_symbol", store_cfg.get("currency", ""))
    m_fx = float(store_cfg.get("meta_fx_to_store", 1.0) or 1.0)
    g_fx = float(store_cfg.get("google_fx_to_store", 1.0) or 1.0)

    issues: list[dict] = []
    overview = load_raw(inputs_dir, f"{sid}_overview.json", issues)
    meta = load_raw(inputs_dir, f"{sid}_meta.json", issues)
    google = load_raw(inputs_dir, f"{sid}_google.json", issues)

    if not (overview or meta or google):
        msg = {
            "title": f"No ad data found for {name}",
            "body": ("None of the expected input files were present. The "
                     "dashboard can't render this store without at least one "
                     "of: overview, Meta campaigns, or Google campaigns."),
            "fix": ("Re-run the MCP data collection step and make sure "
                    f"`{sid}_overview.json`, `{sid}_meta.json` and "
                    f"`{sid}_google.json` are written to the inputs folder."),
        }
        html = (f'<section class="store-section" id="store-{sid}" style="display:none">'
                + _placeholder(read_file, views_dir, msg) + '</section>')
        return ({"id": sid, "name_html": _esc(name), "html": html}, issues)

    store_kpis = load_module(transforms_dir / "store_kpis.py")
    meta_rows = load_module(transforms_dir / "meta_rows.py")
    goog_rows = load_module(transforms_dir / "google_rows.py")

    kpi_payload = store_kpis.transform(
        inputs={"overview": overview, "meta": meta, "google": google},
        config=dict(store_cfg, _window_n_days=window["n_days"]),
    )
    kpis = kpi_payload["tiles"]

    meta_campaigns = meta.get("campaigns") or []
    goog_campaigns = google.get("campaigns") or []

    meta_ads: dict[str, list] = {}
    for p in sorted(inputs_dir.glob(f"{sid}_meta_ads_*.json")):
        cid = p.stem.split(f"{sid}_meta_ads_")[1]
        data = load_raw(inputs_dir, p.name, [])  # silent — missing ads ≠ issue
        meta_ads[cid] = data.get("ads") or []
    goog_ads: dict[str, list] = {}
    for p in sorted(inputs_dir.glob(f"{sid}_google_ads_*.json")):
        cid = p.stem.split(f"{sid}_google_ads_")[1]
        data = load_raw(inputs_dir, p.name, [])
        goog_ads[cid] = data.get("ads") or data.get("asset_groups") or []

    meta_sorted = sorted(meta_campaigns, key=lambda c: -_safe_float(c.get("spend")))
    goog_sorted = sorted(goog_campaigns, key=lambda c: -_safe_float(c.get("spend")))

    rows: list[str] = []
    for c in meta_sorted:
        cid = c.get("campaign_id", "")
        rows.append(meta_rows.campaign_row(
            c, sym, m_fx, window["n_days"], sid,
            has_ads=bool(meta_ads.get(cid)), thresholds=thresholds,
        ))
        if meta_ads.get(cid):
            rows.append(meta_rows.ad_rows(
                meta_ads[cid], sym, m_fx, window["n_days"], sid, cid, thresholds,
            ))
    for c in goog_sorted:
        cid = c.get("campaign_id", "")
        rows.append(goog_rows.campaign_row(
            c, sym, g_fx, window["n_days"], sid,
            has_ads=bool(goog_ads.get(cid)), thresholds=thresholds,
        ))
        if goog_ads.get(cid):
            rows.append(goog_rows.ad_rows(
                goog_ads[cid], sym, g_fx, window["n_days"], sid, cid,
                is_pmax=(c.get("campaign_type") == "PERFORMANCE_MAX"),
                thresholds=thresholds,
            ))

    mi = load_module(insights_dir / "meta_insights.py")
    gi = load_module(insights_dir / "google_insights.py")
    nq = load_module(insights_dir / "next_questions.py")
    m_obs, m_recs = mi.insights(meta_campaigns, sym, thresholds)
    g_obs, g_recs = gi.insights(goog_campaigns, sym, g_fx, thresholds)
    qs = nq.questions(meta_campaigns, goog_campaigns, sym, m_fx, g_fx, thresholds)

    tiles_html = _kpi_html(read_file, views_dir, kpis, store_cfg, thresholds)
    controls_html = read_file(views_dir / "table_controls.html").replace("{STORE_ID}", str(sid))
    thead = "<tr>" + "".join(_th(h, sk, tip) for h, sk, tip in CAMPAIGN_HEADERS) + "</tr>"
    table_html = (read_file(views_dir / "perf_table.html")
                  .replace("{STORE_ID}", str(sid))
                  .replace("{THEAD}", thead)
                  .replace("{ROWS}", "\n".join(rows)))
    insights_html = (read_file(views_dir / "insights_section.html")
                     .replace("{META_INSIGHTS_LI}", _ins_li(m_obs))
                     .replace("{META_RECS_LI}",     _ins_li(m_recs))
                     .replace("{GOOG_INSIGHTS_LI}", _ins_li(g_obs))
                     .replace("{GOOG_RECS_LI}",     _ins_li(g_recs)))
    questions_html = ""
    if qs:
        cards = "".join(_q_card(i, q) for i, q in enumerate(qs))
        questions_html = (read_file(views_dir / "questions_section.html")
                          .replace("{QUESTION_CARDS}", cards))

    section = (f'<section class="store-section" id="store-{sid}" style="display:none">'
               + tiles_html + controls_html + table_html
               + insights_html + questions_html + '</section>')
    return ({"id": sid, "name_html": _esc(name), "html": section}, issues)


def render_global_alerts(issues: list[dict], views_dir: Path, read_file) -> str:
    if not issues: return ""
    tpl = read_file(views_dir / "placeholder_card.html")
    cards = []
    for iss in issues:
        cards.append(tpl
                     .replace("{TITLE}", _esc(iss.get("title", "Data unavailable")))
                     .replace("{BODY}",  _esc(iss.get("body", "")))
                     .replace("{FIX}",   _esc(iss.get("fix", ""))))
    return ('<div class="main" style="padding-top:18px;padding-bottom:0">'
            + "".join(cards) + '</div>')
