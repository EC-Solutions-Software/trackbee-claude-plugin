#!/usr/bin/env python3
"""TrackBee Attribution Overview — full-page assembler.

Loads the staged input dumps, runs every transform + insight against each of
the three windows (3d / 7d / 28d), pre-renders the charts and heatmap as
inline SVG/HTML, bakes the union into ``PAGE_DATA`` and stamps it into the
self-contained ``chrome/shell.html`` shell. The JS-side filter button
rehydrates the windowed sections on click; Customer Journeys is server-rendered
and fixed at a 90-day lookback.

Every renderable piece lives under ``../`` and is loaded here by relative
path — no component imports another. ``build()`` is the single entry point;
the thin ``scripts/build_dashboard.py`` parses args and calls it.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # .../components/
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"
CHARTS = HERE / "charts"

MIN_SAMPLE = 50  # per-platform attributed-order floor for touch-point insights


def _load_module(path: Path):
    """Import a sibling component module by absolute path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_static(path: Path) -> str:
    """Read a carved CSS/JS file, dropping the single trailing newline so it
    stamps into ``<style>\\n{TOKEN}\\n</style>`` (and the script wrappers)
    without introducing an extra blank line."""
    txt = path.read_text(encoding="utf-8")
    return txt[:-1] if txt.endswith("\n") else txt


def _step_count(funnel_obj, step):
    for s in (funnel_obj or {}).get("funnel", []):
        if s["step"] == step:
            return s["count"]
    return 0


_INSIGHT_LI_OBS = (
    '<li class="insight-item"><span class="insight-bullet"></span><div>'
    '<div class="insight-obs">{obs}</div></div></li>'
)


def _insight_lis(insights) -> str:
    # Insights are factual observations only — no TrackBee-authored action
    # line is rendered.
    return "".join(_INSIGHT_LI_OBS.format(obs=i["obs"]) for i in insights)


def build(inputs_dir, config: dict, assets_dir, out_path) -> dict:
    inputs_dir = Path(inputs_dir)
    assets_dir = Path(assets_dir)
    out_path = Path(out_path)

    # --- components ----------------------------------------------------------
    loader = _load_module(TRANSFORMS / "loader.py")
    window_metrics = _load_module(TRANSFORMS / "window_metrics.py")
    journeys_mod = _load_module(TRANSFORMS / "journeys.py")
    heatmap_mod = _load_module(TRANSFORMS / "heatmap.py")
    nc_roas = _load_module(CHARTS / "nc_roas.py")
    sankey = _load_module(CHARTS / "sankey_svg.py")
    fmt = _load_module(CHROME / "format_helpers.py").build(
        config["store_currency"], config.get("fx_to_eur", {}))
    logos = _load_module(CHROME / "logos.py")
    ch_attr_ins = _load_module(INSIGHTS / "channel_attribution.py")
    exec_ins = _load_module(INSIGHTS / "executive_summary.py")
    funnel_ins = _load_module(INSIGHTS / "funnel.py")
    journey_ins = _load_module(INSIGHTS / "journey.py")
    cooccur_ins = _load_module(INSIGHTS / "cooccurrence.py")
    questions_ins = _load_module(INSIGHTS / "questions.py")

    store_name = config["store_name"]
    store_ccy = config["store_currency"]
    fx = config.get("fx_to_eur", {})
    cw = config["windows"]

    # --- inputs --------------------------------------------------------------
    daily = loader.load_json(inputs_dir, "daily.json")
    touchpoints = loader.load_json(inputs_dir, "touchpoints.json")

    # Journey breakdowns: the union/sankey/insights read exactly the named
    # platforms, in this order.
    breakdowns = [loader.load_json(inputs_dir, f) for f in (
        "j_meta.json", "j_google.json", "j_klaviyo.json",
        "j_tiktok.json", "j_pinterest.json", "j_email.json")]

    windows = {
        "3d": {"label": "Last 3 days", "start": cw["3d"]["start"], "end": cw["3d"]["end"],
               "overview": loader.load_json(inputs_dir, "overview_3d.json"),
               "funnel": loader.load_json(inputs_dir, "funnel_3d.json"),
               "platform_funnel": loader.load_json(inputs_dir, "platform_funnel_3d.json"),
               "meta": loader.load_json(inputs_dir, "meta_3d.json"),
               "google": loader.load_json(inputs_dir, "google_3d.json"),
               "daily_slice": -3},
        "7d": {"label": "Last 7 days", "start": cw["7d"]["start"], "end": cw["7d"]["end"],
               "overview": loader.load_json(inputs_dir, "overview_7d.json"),
               "funnel": loader.load_json(inputs_dir, "funnel_7d.json"),
               "platform_funnel": loader.load_json(inputs_dir, "platform_funnel_7d.json"),
               "meta": loader.load_json(inputs_dir, "meta_7d.json"),
               "google": loader.load_json(inputs_dir, "google_7d.json"),
               "daily_slice": -7},
        "28d": {"label": "Last 28 days", "start": cw["28d"]["start"], "end": cw["28d"]["end"],
                "overview": loader.load_json(inputs_dir, "overview.json"),
                "funnel": loader.load_json(inputs_dir, "funnel.json"),
                "platform_funnel": loader.load_json(inputs_dir, "platform_funnel.json"),
                "meta": loader.load_json(inputs_dir, "meta.json"),
                "google": loader.load_json(inputs_dir, "google.json"),
                "daily_slice": None},
    }

    # --- per-window metrics + insights ---------------------------------------
    window_data = window_metrics.compute_windows(windows, daily, fx)
    for wd in window_data.values():
        ctx = wd["_ctx"]
        wd["ch_insights"] = ch_attr_ins.build(ctx, fmt)
        wd["exec_takeaways"] = exec_ins.build(ctx, fmt)
        wd["funnel_insights"] = funnel_ins.build(ctx, fmt)

    # --- journeys (90-day, filter-independent) -------------------------------
    jr = journeys_mod.transform(breakdowns)
    sankey_views = jr["sankey_views"]
    stats = jr["stats"]
    journey_insights = journey_ins.build(stats, touchpoints)

    # Per-platform attributed-order counts (28d) drive the sample guards.
    pf28 = (windows["28d"].get("platform_funnel") or {}).get("platforms") or {}
    plat_orders_28d = {p: _step_count(pf28.get(p, {}), "orders") for p in pf28}
    # TrackBee uses "facebook" in platform_funnel but "meta" in co-occurrence.
    if "facebook" in plat_orders_28d:
        plat_orders_28d["meta"] = plat_orders_28d.pop("facebook")

    cooccur_insights = cooccur_ins.build(touchpoints, plat_orders_28d, MIN_SAMPLE)
    hm = heatmap_mod.transform(touchpoints, plat_orders_28d, MIN_SAMPLE)

    has_profiles = bool(
        touchpoints.get("total_journeys")
        or touchpoints.get("multi_touch_journeys")
        or touchpoints.get("co_occurrence")
    )

    suggested_questions = questions_ins.build(window_data["28d"], has_profiles, stats["top_opener"])

    # --- pre-rendered charts -------------------------------------------------
    nc_roas_svgs = {}
    for wk in ("3d", "7d", "28d"):
        svg, _avg = nc_roas.render_nc_roas_svg(window_data[wk]["daily_nc_roas"])
        nc_roas_svgs[wk] = svg
    sankey_svgs = {k: sankey.render_sankey_svg(v) for k, v in sankey_views.items()}

    nc_roas_inline = (
        '<div id="ncRoasInline">'
        + "".join(
            f'<div data-w="{k}" style="display:{"block" if k == "28d" else "none"}">'
            f'{nc_roas_svgs[k]}</div>'
            for k in ("28d", "7d", "3d"))
        + '</div>'
    )
    sankey_inline = (
        '<div id="journeyFallback">'
        + "".join(
            f'<div data-sv="{k}" style="display:{"block" if k == "multi" else "none"}">'
            f'{sankey_svgs[k]}</div>'
            for k in sankey_svgs)
        + '</div>'
    )

    # --- PAGE_DATA -----------------------------------------------------------
    page_data = {
        "store": {"name": store_name, "currency": store_ccy, "fx": fx or {}},
        "has_profiles": has_profiles,
        "windows": {k: {
            "label": v["label"], "start": v["start"], "end": v["end"],
            "blended": v["blended"], "platforms": v["platforms"], "channels": v["channels"],
            "ch_insights": v["ch_insights"], "exec_takeaways": v["exec_takeaways"],
            "daily_nc_roas": v["daily_nc_roas"],
            "funnel_stages": v["funnel_stages"], "funnel_drops": v["funnel_drops"],
            "funnel_insights": v["funnel_insights"], "funnel_summary": v["funnel_summary"],
        } for k, v in window_data.items()},
        "logos": logos.logos_by_key(assets_dir),
        "suggested_questions": suggested_questions,
    }

    # --- stamp the shell -----------------------------------------------------
    html = (CHROME / "shell.html").read_text(encoding="utf-8")
    repl = {
        "{THEME_CSS}": _read_static(CHROME / "theme.css"),
        "{LOGO_WORDMARK}": logos.wordmark_img(assets_dir),
        "{J_TOTAL}": fmt.fmt_int(touchpoints["total_journeys"]),
        "{J_SINGLE_PCT}": fmt.fmt_pct(touchpoints["single_touch_share"]),
        "{J_SINGLE_SUB}": fmt.fmt_int(touchpoints["total_journeys"] - touchpoints["multi_touch_journeys"]),
        "{J_MULTI_PCT}": fmt.fmt_pct(1 - touchpoints["single_touch_share"]),
        "{J_MULTI_SUB}": fmt.fmt_int(touchpoints["multi_touch_journeys"]),
        "{COOCCUR_INSIGHTS}": _insight_lis(cooccur_insights),
        "{JOURNEY_INSIGHTS}": _insight_lis(journey_insights),
        "{BUILD_DATE}": dt.date.today().isoformat(),
        "{HEATMAP}": hm["heatmap_html"],
        "{NC_ROAS_INLINE}": nc_roas_inline,
        "{SANKEY_INLINE}": sankey_inline,
        "{LOW_SAMPLE_CAVEAT}": hm["low_sample_caveat"],
    }
    # STORE_NAME appears in both <title> and the header — replace everywhere.
    html = html.replace("{STORE_NAME}", store_name)
    for token, value in repl.items():
        html = html.replace(token, value)

    # Customer Journeys is hidden entirely when the store has no shopper
    # profiles. Done on the still-tokenised block so the whole section drops
    # cleanly (no empty card, no JS error from the sankey-filter handler).
    if has_profiles:
        html = html.replace("{CUSTOMER_JOURNEYS_OPEN}", '<div class="card">')
        html = html.replace("{CUSTOMER_JOURNEYS_CLOSE}", '</div>')
    else:
        import re
        html = re.sub(
            r"<!-- Customer Journeys -->\s*\{CUSTOMER_JOURNEYS_OPEN\}.*?\{CUSTOMER_JOURNEYS_CLOSE\}",
            "<!-- Customer Journeys section omitted: no shopper profiles for this store yet. -->",
            html, count=1, flags=re.DOTALL,
        )
        html = re.sub(
            r"<li>Window filter affects Blended Overview.*?Customer Journeys uses a fixed.*?</li>\s*",
            "", html, count=1, flags=re.DOTALL,
        )

    # Data + JS last (their content is brace-heavy and must not be rescanned).
    html = html.replace("{PAGE_DATA_JSON}", json.dumps(page_data))
    html = html.replace("{SANKEY_VIEWS_JSON}", json.dumps(sankey_views))
    html = html.replace("{APP_JS}", _read_static(CHROME / "app.js"))
    html = html.replace("{TOOLTIP_JS}", _read_static(CHROME / "tooltip.js"))

    out_path.write_text(html, encoding="utf-8")

    return {
        "out_path": str(out_path),
        "bytes": out_path.stat().st_size,
        "window_data": window_data,
        "journey_insights": journey_insights,
        "cooccur_insights": cooccur_insights,
        "fmt": fmt,
    }
