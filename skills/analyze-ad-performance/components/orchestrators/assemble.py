"""Ad Performance — full-page assembler.

Reads the staged JSON, runs the transforms + insights per store, stitches
the KPI bar / performance table / insights / questions into a
`<section class="store-section">` per store, then stamps everything into
`chrome/shell.html` along with the inline CSS + JS.

This is the only module that knows the full pipeline order. Each
component upstream is single-responsibility.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # .../analyze-ad-performance/components/
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"
VIEWS = HERE / "views"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _ins_list(items: list[str]) -> str:
    return "".join(f"<li>{i}</li>" for i in items)


def _insights_grid(m_ins: list[str], m_recs: list[str],
                   g_ins: list[str], g_recs: list[str]) -> str:
    """Two-column grid: Meta insights / Google insights. Markup lives in views/."""
    template = _read(VIEWS / "insights_section.html")
    return (
        template
        .replace("{META_INSIGHTS}",   _ins_list(m_ins))
        .replace("{META_RECS}",       _ins_list(m_recs))
        .replace("{GOOGLE_INSIGHTS}", _ins_list(g_ins))
        .replace("{GOOGLE_RECS}",     _ins_list(g_recs))
    )


def _nav_tabs(rendered_stores: list[dict], fh) -> str:
    return "".join(
        f'<button class="store-tab" data-action="switch-store" '
        f'data-sid="{fh.attr(rs["id"])}">{fh.text(rs["name"])}</button>'
        for rs in rendered_stores
    )


def _store_section(rs: dict, thead_html: str, fh) -> str:
    """One <section> per store — KPI bar, table controls, table, insights, questions.
    Markup lives in views/store_section.html; this just stamps placeholders."""
    template = _read(VIEWS / "store_section.html")
    return (
        template
        .replace("{STORE_ID}",  fh.attr(rs["id"]))
        .replace("{KPI_BAR}",   rs["tiles"])
        .replace("{THEAD}",     thead_html)
        .replace("{ROWS}",      rs["rows"])
        .replace("{INSIGHTS}",  rs["insights"])
        .replace("{QUESTIONS}", rs["questions"])
    )


def build(inputs_dir: Path, skill_dir: Path) -> str:
    """Render the full Ad Performance HTML page."""
    fh = _load_module("format_helpers", CHROME / "format_helpers.py")
    logos = _load_module("logos", CHROME / "logos.py")
    cfg_mod = _load_module("config_mod", TRANSFORMS / "config.py")
    store_data = _load_module("store_data", TRANSFORMS / "store_data.py")
    store_kpis = _load_module("store_kpis", TRANSFORMS / "store_kpis.py")
    meta_rows = _load_module("meta_rows", TRANSFORMS / "meta_rows.py")
    google_rows = _load_module("google_rows", TRANSFORMS / "google_rows.py")
    window_mod = _load_module("window_mod", TRANSFORMS / "window.py")
    table_meta = _load_module("table_meta", TRANSFORMS / "table_meta.py")
    meta_ins = _load_module("meta_insights", INSIGHTS / "meta_insights.py")
    google_ins = _load_module("google_insights", INSIGHTS / "google_insights.py")
    next_q = _load_module("next_questions", INSIGHTS / "next_questions.py")

    stores_cfg, window, n_days = cfg_mod.load_config(inputs_dir)
    stores = store_data.load_all_stores(inputs_dir, stores_cfg)

    rendered: list[dict] = []
    for s in stores:
        sid = s["id"]
        sym = s["symbol"]
        m_fx = s["m_fx"]
        g_fx = s["g_fx"]
        meta_c = s["meta_campaigns"]
        goog_c = s["goog_campaigns"]
        m_ads = s["meta_ads"]
        g_ads = s["goog_ads"]

        # Mark which campaigns have ad-level data staged.
        for c in meta_c:
            c["_has_ads"] = c.get("campaign_id") in m_ads
        for c in goog_c:
            c["_has_ads"] = c.get("campaign_id") in g_ads

        # KPI tiles.
        kpis = store_kpis.compute(s, n_days)
        tiles = store_kpis.render_tiles_html(kpis)

        # Sort campaigns by spend descending.
        meta_sorted = sorted(meta_c, key=lambda c: -fh.safe_float(c.get("spend")))
        goog_sorted = sorted(goog_c, key=lambda c: -fh.safe_float(c.get("spend")))

        rows_buf: list[str] = []
        for c in meta_sorted:
            rows_buf.append(meta_rows.campaign_row(c, sym, m_fx, n_days, sid))
            cid = c.get("campaign_id", "")
            if cid in m_ads and m_ads[cid]:
                rows_buf.append(meta_rows.ad_rows(m_ads[cid], sym, m_fx, n_days, sid, cid))

        for c in goog_sorted:
            rows_buf.append(google_rows.campaign_row(c, sym, g_fx, n_days, sid))
            cid = c.get("campaign_id", "")
            if cid in g_ads and g_ads[cid]:
                is_pmax = c.get("campaign_type") == "PERFORMANCE_MAX"
                rows_buf.append(
                    google_rows.ad_rows(g_ads[cid], sym, g_fx, n_days, sid, cid, is_pmax)
                )

        # Insights + questions.
        m_ins, m_recs = meta_ins.build(meta_c, sym)
        g_ins, g_recs = google_ins.build(goog_c, sym, g_fx)
        qs = next_q.build(meta_c, goog_c, sym, m_fx, g_fx)

        rendered.append({
            "id":        sid,
            "name":      s["name"],
            "tiles":     tiles,
            "rows":      "\n".join(rows_buf),
            "insights":  _insights_grid(m_ins, m_recs, g_ins, g_recs),
            "questions": next_q.render_questions_html(qs),
        })

    # Stitch the shell.
    thead = table_meta.thead_html()
    nav_tabs = _nav_tabs(rendered, fh)
    sections = "\n".join(_store_section(rs, thead, fh) for rs in rendered)

    icon_b64 = logos.load_icon_b64(skill_dir)
    logo_block = logos.render_logo_block(icon_b64)
    date_pill = window_mod.format_date_pill(window)
    date_label = window.get("label") or f'{window["start"]} → {window["end"]}'
    generated = dt.datetime.now().strftime("%b %d, %Y %H:%M")
    first_store = rendered[0]["id"] if rendered else "null"

    shell = _read(CHROME / "shell.html")
    theme = _read(CHROME / "theme.css")
    js_filters = _read(CHROME / "render_filters.js")
    js_table = _read(CHROME / "render_table.js")
    js_questions = _read(CHROME / "render_questions.js")

    return (
        shell
        .replace("{INLINE_THEME_CSS}", theme)
        .replace("{LOGO_BLOCK}", logo_block)
        .replace("{DATE_PILL}", fh.attr(date_pill))
        .replace("{GENERATED_AT}", fh.attr(generated))
        .replace("{NAV_TABS}", nav_tabs)
        .replace("{STORE_SECTIONS}", sections)
        .replace("{DATE_LABEL}", fh.attr(date_label))
        .replace("{FIRST_STORE_ID}", fh.attr(first_store))
        .replace("{INLINE_FILTERS_JS}", js_filters)
        .replace("{INLINE_TABLE_JS}", js_table)
        .replace("{INLINE_QUESTIONS_JS}", js_questions)
    )
