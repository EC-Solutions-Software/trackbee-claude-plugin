"""Per-store section builder + missing-data card emitter.

Split out of `assemble.py` to keep the top-level orchestrator under
~200 lines (per CLAUDE.md). All HTML-template substitution for a single
store lives here.

Each call to `render_store(...)` returns:
    (
        {"id": int, "name_html": str, "html": str},
        [<issue dict>, ...]
    )

Issues are propagated upward so the orchestrator can group them into a
"Data we couldn't load" banner at the top of the page.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from transforms import _fmt as f
from transforms import _io as io


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TRANSFORMS = ROOT / "transforms"
INSIGHTS = ROOT / "insights"


# 20-column table headers + their sort keys + tooltips. Adding/renaming a
# column is a one-line edit here.
CAMPAIGN_HEADERS: list[tuple[str, str, str]] = [
    ("Name",        "name",     ""),
    ("Status",      "status",   ""),
    ("Platform",    "platform", ""),
    ("Spend",       "spend",    "Total spend in the window"),
    ("Revenue",     "revenue",  "1d-click revenue (Meta) / Conversion value (Google)"),
    ("ROAS",        "roas",     "Return on ad spend (platform-reported)"),
    ("Action",      "action",   "Suggested next move"),
    ("Results",     "results",  "Purchases (Meta) / Conversions (Google)"),
    ("Reach",       "reach",    "Unique people reached"),
    ("Impressions", "impr",     "Total impressions"),
    ("Freq",        "freq",     "Average frequency (impressions ÷ reach)"),
    ("CPM",         "cpm",      "Cost per 1,000 impressions"),
    ("CTR",         "ctr",      "Click-through rate"),
    ("CPC",         "cpc",      "Cost per click"),
    ("Clicks",      "clicks",   "Total link clicks"),
    ("ATC",         "atc",      "Add-to-cart events"),
    ("Cost/ATC",    "cost_atc", "Spend ÷ add-to-cart"),
    ("New Cust.",   "nc",       "New customer purchases"),
    ("NC Revenue",  "nc_rev",   "New customer revenue"),
    ("Avg Daily",   "daily",    "Average daily spend (total ÷ days)"),
]


def _th(label: str, sort_key: str, tip: str) -> str:
    tip_attr = f' title="{f.html_escape(tip, quote=True)}"' if tip else ""
    sk_attr = f' data-sort="{sort_key}"' if sort_key else ""
    indicator = (
        '<span class="sort-ind" aria-hidden="true">'
        '<span class="ar ar-up">▲</span><span class="ar ar-down">▼</span></span>'
    ) if sort_key else ""
    return f"<th{sk_attr}{tip_attr}>{label}{indicator}</th>"


def _load(path: Path, pkg: str):
    """Import a sibling module under a unique package name."""
    spec = importlib.util.spec_from_file_location(pkg, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[pkg] = m
    spec.loader.exec_module(m)
    return m


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _kpi_html(views_dir: Path, kpis: dict, store_cfg: dict, thresholds: dict) -> str:
    sym = store_cfg.get("currency_symbol", store_cfg.get("currency", ""))
    tpl = _read(views_dir / "kpi_bar.html")
    return (tpl
            .replace("{TOTAL_SPEND}",  f.fmt_money(kpis["total_spend"], sym))
            .replace("{META_SPEND}",   f.fmt_money(kpis["meta_spend"], sym))
            .replace("{GOOG_SPEND}",   f.fmt_money(kpis["goog_spend"], sym))
            .replace("{BLENDED_CLASS}", f.roas_class(kpis["blended_roas"], thresholds))
            .replace("{BLENDED_ROAS}", f.fmt_float(kpis["blended_roas"], 2))
            .replace("{META_ROAS}",    f.fmt_float(kpis["meta_roas"], 2))
            .replace("{GOOG_ROAS}",    f.fmt_float(kpis["goog_roas"], 2))
            .replace("{MER}",          f.fmt_float(kpis["mer"], 2))
            .replace("{CONVERSIONS}",  f.fmt_int(kpis["conversions"]))
            .replace("{META_PURCH}",   f.fmt_int(kpis["meta_purch"]))
            .replace("{GOOG_CONV}",    f.fmt_float(kpis["goog_conv"], 0))
            .replace("{AVG_DAILY}",    f.fmt_money(kpis["avg_daily"], sym))
            .replace("{N_DAYS}",       str(kpis["n_days"])))


def _placeholder(views_dir: Path, issue: dict) -> str:
    tpl = _read(views_dir / "placeholder_card.html")
    return (tpl
            .replace("{TITLE}", f.html_escape(issue.get("title", "Data unavailable")))
            .replace("{BODY}",  f.html_escape(issue.get("body", ""))
                                .replace("&#x60;", "`"))
            .replace("{FIX}",   f.html_escape(issue.get("fix", ""))))


def _ins_li(items: list[str]) -> str:
    return "".join(f"<li>{i}</li>" for i in items)


def _q_card_html(i: int, q: dict) -> str:
    import re
    plain = re.sub(r"<[^>]+>", "", q["q"]).strip()
    plain_attr = f.html_escape(plain, quote=True)
    return (
        '<div class="q-card">'
        f'<div class="q-num">Q{i+1}</div>'
        '<div class="q-body">'
        f'<div class="q-text">{q["q"]}</div>'
        f'<div class="q-why">{q["why"]}</div>'
        '</div>'
        f'<button class="q-copy" type="button" data-q="{plain_attr}" '
        'onclick="copyQuestion(this)" aria-label="Copy question">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
        '<span class="q-copy-label">Copy</span></button></div>'
    )


def render_store(store_cfg: dict, window: dict, inputs_dir: Path,
                 views_dir: Path, thresholds: dict) -> tuple[dict, list[dict]]:
    """Return ``({"id", "name_html", "html"}, issues)`` for one store."""
    sid = store_cfg["id"]
    name = store_cfg.get("name", f"Store {sid}")
    sym = store_cfg.get("currency_symbol", store_cfg.get("currency", ""))
    m_fx = float(store_cfg.get("meta_fx_to_store", 1.0) or 1.0)
    g_fx = float(store_cfg.get("google_fx_to_store", 1.0) or 1.0)

    # Load raw MCP outputs — every missing/malformed file appends to `issues`.
    issues: list[dict] = []
    overview = io.load_json(inputs_dir, f"{sid}_overview.json", issues)
    meta = io.load_json(inputs_dir, f"{sid}_meta.json", issues)
    google = io.load_json(inputs_dir, f"{sid}_google.json", issues)

    if not (overview or meta or google):
        # All three were missing — render only an error card for this store.
        msg = {
            "title": f"No ad data found for {name}",
            "body": ("None of the expected input files were present. The "
                     "dashboard can't render this store without at least one "
                     "of: overview, Meta campaigns, or Google campaigns."),
            "fix": ("Re-run the MCP data collection step from SKILL.md and "
                    "make sure `<store_id>_overview.json`, `<store_id>_meta.json` "
                    "and `<store_id>_google.json` are all written to the inputs folder."),
        }
        html = (f'<section class="store-section" id="store-{sid}" style="display:none">'
                + _placeholder(views_dir, msg)
                + '</section>')
        return ({"id": sid, "name_html": f.html_escape(name), "html": html}, issues)

    # Run transforms.
    store_kpis = _load(TRANSFORMS / "store_kpis.py", f"transforms.store_kpis_{sid}")
    meta_rows = _load(TRANSFORMS / "meta_rows.py", f"transforms.meta_rows_{sid}")
    goog_rows = _load(TRANSFORMS / "google_rows.py", f"transforms.google_rows_{sid}")

    store_cfg_with_window = dict(store_cfg, _window_n_days=window["n_days"])
    kpi_payload = store_kpis.transform(
        inputs={"overview": overview, "meta": meta, "google": google},
        config=store_cfg_with_window,
    )
    kpis = kpi_payload["tiles"]

    meta_campaigns = (meta.get("campaigns") or [])
    goog_campaigns = (google.get("campaigns") or [])

    # Ad-level data per campaign (glob the inputs folder).
    meta_ads_by_cid: dict[str, list[dict]] = {}
    for p in sorted(inputs_dir.glob(f"{sid}_meta_ads_*.json")):
        cid = p.stem.split(f"{sid}_meta_ads_")[1]
        data = io.load_json(inputs_dir, p.name, issues=[])  # silent — missing ads ≠ issue
        meta_ads_by_cid[cid] = data.get("ads") or []
    goog_ads_by_cid: dict[str, list[dict]] = {}
    for p in sorted(inputs_dir.glob(f"{sid}_google_ads_*.json")):
        cid = p.stem.split(f"{sid}_google_ads_")[1]
        data = io.load_json(inputs_dir, p.name, issues=[])
        goog_ads_by_cid[cid] = data.get("ads") or data.get("asset_groups") or []

    # Sort each platform by spend, then emit rows.
    meta_sorted = sorted(meta_campaigns, key=lambda c: -f.safe_float(c.get("spend")))
    goog_sorted = sorted(goog_campaigns, key=lambda c: -f.safe_float(c.get("spend")))

    rows_html: list[str] = []
    for c in meta_sorted:
        cid = c.get("campaign_id", "")
        rows_html.append(meta_rows.campaign_row(
            c, sym, m_fx, window["n_days"], sid,
            has_ads=bool(meta_ads_by_cid.get(cid)),
            thresholds=thresholds,
        ))
        if meta_ads_by_cid.get(cid):
            rows_html.append(meta_rows.ad_rows(
                meta_ads_by_cid[cid], sym, m_fx, window["n_days"], sid, cid, thresholds,
            ))
    for c in goog_sorted:
        cid = c.get("campaign_id", "")
        rows_html.append(goog_rows.campaign_row(
            c, sym, g_fx, window["n_days"], sid,
            has_ads=bool(goog_ads_by_cid.get(cid)),
            thresholds=thresholds,
        ))
        if goog_ads_by_cid.get(cid):
            rows_html.append(goog_rows.ad_rows(
                goog_ads_by_cid[cid], sym, g_fx, window["n_days"], sid, cid,
                is_pmax=(c.get("campaign_type") == "PERFORMANCE_MAX"),
                thresholds=thresholds,
            ))

    # Insights + next questions.
    mi_mod = _load(INSIGHTS / "meta_insights.py", f"insights.meta_insights_{sid}")
    gi_mod = _load(INSIGHTS / "google_insights.py", f"insights.google_insights_{sid}")
    nq_mod = _load(INSIGHTS / "next_questions.py", f"insights.next_questions_{sid}")
    meta_obs, meta_recs = mi_mod.insights(meta_campaigns, sym, thresholds)
    goog_obs, goog_recs = gi_mod.insights(goog_campaigns, sym, g_fx, thresholds)
    questions = nq_mod.questions(meta_campaigns, goog_campaigns, sym, m_fx, g_fx, thresholds)

    # Compose section HTML.
    tiles_html = _kpi_html(views_dir, kpis, store_cfg, thresholds)
    controls_html = _read(views_dir / "table_controls.html").replace("{STORE_ID}", str(sid))
    thead = "<tr>" + "".join(_th(h, sk, tip) for h, sk, tip in CAMPAIGN_HEADERS) + "</tr>"
    table_html = (_read(views_dir / "perf_table.html")
                  .replace("{STORE_ID}", str(sid))
                  .replace("{THEAD}", thead)
                  .replace("{ROWS}", "\n".join(rows_html)))
    insights_html = (_read(views_dir / "insights_section.html")
                     .replace("{META_INSIGHTS_LI}", _ins_li(meta_obs))
                     .replace("{META_RECS_LI}",     _ins_li(meta_recs))
                     .replace("{GOOG_INSIGHTS_LI}", _ins_li(goog_obs))
                     .replace("{GOOG_RECS_LI}",     _ins_li(goog_recs)))
    questions_html = ""
    if questions:
        cards = "".join(_q_card_html(i, q) for i, q in enumerate(questions))
        questions_html = (_read(views_dir / "questions_section.html")
                          .replace("{QUESTION_CARDS}", cards))

    section = (f'<section class="store-section" id="store-{sid}" style="display:none">'
               + tiles_html
               + controls_html
               + table_html
               + insights_html
               + questions_html
               + '</section>')
    return ({"id": sid, "name_html": f.html_escape(name), "html": section}, issues)


def render_global_alerts(issues: list[dict], views_dir: Path) -> str:
    """Top-of-page banner listing every input file we couldn't load.

    Empty list → empty string (nothing to render). The shell template
    swallows that without leaving a stray empty div.
    """
    if not issues:
        return ""
    tpl = _read(views_dir / "placeholder_card.html")
    cards = []
    for iss in issues:
        cards.append(tpl
                     .replace("{TITLE}", f.html_escape(iss.get("title", "Data unavailable")))
                     .replace("{BODY}",  f.html_escape(iss.get("body", "")))
                     .replace("{FIX}",   f.html_escape(iss.get("fix", ""))))
    return ('<div class="main" style="padding-top:18px;padding-bottom:0">'
            + "".join(cards) + '</div>')
