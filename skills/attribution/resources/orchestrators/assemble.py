#!/usr/bin/env python3
"""TrackBee Attribution Report — full-page assembler.

Reads raw MCP JSON dumps, runs every transform + insight against each of
the three windows (3d / 7d / 28d), bakes the union into a single
self-contained HTML file that the JS-side filter button rehydrates on
click.

CLI:

    python3 assemble.py \\
        --inputs  /path/to/inputs/ \\
        --out     /path/to/output.html

Where the inputs directory holds the MCP dumps (overview.json + per-window
variants, daily.json, funnel*.json, platform_funnel*.json, meta*.json,
google*.json, touchpoints.json, j_<platform>.json) and a config.json
carrying the store metadata:

    {"store_name": "...", "store_currency": "EUR",
     "fx_to_eur": {...},
     "windows": {"3d": {"start": ..., "end": ...},
                  "7d": {...},
                  "28d": {...}}}

All build-time inputs live in one directory; no out-of-band config path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent  # .../attribution/
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"


def _load_module(path: Path):
    """Import a sibling component module by absolute path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_raw(inputs_dir: Path, name: str) -> dict:
    """Load `<name>.json` and return the inner MCP payload.

    Tolerates three shapes so this works regardless of how Claude saved the
    file:

      1. ``{"result": {...}}``           — JSON-RPC envelope
      2. ``{"overview": {...}, ...}``    — get_dashboard_overview native shape
      3. ``{...}``                       — already-unwrapped payload

    Missing file → empty dict so transforms degrade to em-dash output
    instead of erroring.
    """
    path = inputs_dir / name
    if not path.is_file():
        return {}
    data = _read_json(path)
    if not isinstance(data, dict):
        return {}
    # JSON-RPC envelope
    if "result" in data and isinstance(data["result"], dict):
        data = data["result"]
    # get_dashboard_overview wraps its payload under an "overview" key.
    # Only unwrap for overview files so we don't accidentally flatten other
    # payloads that may carry a top-level "overview" field for a different
    # reason. Currency context lives on the outer envelope — copy it down
    # so the inner payload remains self-describing.
    if name.startswith("overview") and isinstance(data.get("overview"), dict):
        inner = dict(data["overview"])
        for k in ("store_currency", "currency"):
            if k in data and k not in inner:
                inner[k] = data[k]
        return inner
    return data


def _step_count(funnel_obj: dict, step: str) -> int:
    for entry in (funnel_obj or {}).get("funnel", []) or []:
        if entry.get("step") == step:
            count = entry.get("count")
            return int(count) if count is not None else 0
    return 0


def _load_all_raws(inputs_dir: Path) -> dict:
    raws = {
        "overview":              _load_raw(inputs_dir, "overview.json"),
        "overview_3d":           _load_raw(inputs_dir, "overview_3d.json"),
        "overview_7d":           _load_raw(inputs_dir, "overview_7d.json"),
        "daily":                 _load_raw(inputs_dir, "daily.json"),
        "funnel":                _load_raw(inputs_dir, "funnel.json"),
        "funnel_3d":             _load_raw(inputs_dir, "funnel_3d.json"),
        "funnel_7d":             _load_raw(inputs_dir, "funnel_7d.json"),
        "platform_funnel":       _load_raw(inputs_dir, "platform_funnel.json"),
        "platform_funnel_3d":    _load_raw(inputs_dir, "platform_funnel_3d.json"),
        "platform_funnel_7d":    _load_raw(inputs_dir, "platform_funnel_7d.json"),
        "meta":                  _load_raw(inputs_dir, "meta.json"),
        "meta_3d":               _load_raw(inputs_dir, "meta_3d.json"),
        "meta_7d":               _load_raw(inputs_dir, "meta_7d.json"),
        "google":                _load_raw(inputs_dir, "google.json"),
        "google_3d":             _load_raw(inputs_dir, "google_3d.json"),
        "google_7d":             _load_raw(inputs_dir, "google_7d.json"),
        "touchpoints":           _load_raw(inputs_dir, "touchpoints.json"),
    }
    # Journey breakdowns: load one j_<platform>.json per channel that
    # appeared in the interactions payload. ``transitions`` rows are
    # directional ("leading"/"related"); ``cooccurrence`` rows are
    # symmetric ("a"/"b"). Walk all four keys so channels that appear
    # only in cooccurrence still get a journey file loaded.
    # Missing files are tolerated — the transform skips them.
    touchpoints = raws.get("touchpoints") or {}
    seen: list[str] = []
    for bucket in ("cooccurrence", "transitions"):
        for row in touchpoints.get(bucket) or []:
            for side in ("leading", "related", "a", "b"):
                name = row.get(side)
                if not name or name in ("order", "organic") or name in seen:
                    continue
                seen.append(name)
    for plat in seen:
        raws[f"j_{plat}"] = _load_raw(inputs_dir, f"j_{plat}.json")
    return raws


def _window_inputs(raws: dict, key: str) -> dict:
    """Return the per-window slice of raws keyed by window suffix.

    28d uses the un-suffixed files (overview.json, funnel.json, ...).
    7d / 3d use the `_7d` / `_3d` suffixed files; fall back to 28d when the
    suffixed file is missing so the slot still renders something.
    """
    if key == "28d":
        suffix = ""
    else:
        suffix = "_" + key
    def pick(name: str):
        return raws.get(name + suffix) or raws.get(name) or {}
    return {
        "overview":        pick("overview"),
        "funnel":          pick("funnel"),
        "platform_funnel": pick("platform_funnel"),
        "meta":            pick("meta"),
        "google":          pick("google"),
        "daily":           raws.get("daily") or {"rows": []},
    }


def _build_blended(window_inputs: dict, config: dict) -> dict:
    mod = _load_module(TRANSFORMS / "blended_kpis.py")
    return mod.transform(
        inputs={
            "overview": window_inputs["overview"],
            "daily":    window_inputs["daily"],
            "funnel":   window_inputs["funnel"],
        },
        config=config,
    )


def _build_platforms(window_inputs: dict, config: dict) -> dict:
    mod = _load_module(TRANSFORMS / "platform_tiles.py")
    return mod.transform(
        inputs={
            "overview": window_inputs["overview"],
            "meta":     window_inputs["meta"],
            "google":   window_inputs["google"],
        },
        config=config,
    )


def _build_channels(window_inputs: dict, config: dict) -> list[dict]:
    mod = _load_module(TRANSFORMS / "channel_attribution.py")
    result = mod.transform(
        inputs={
            "overview":        window_inputs["overview"],
            "platform_funnel": window_inputs["platform_funnel"],
            "meta":            window_inputs["meta"],
            "google":          window_inputs["google"],
        },
        config=config,
    )
    return result.get("rows") or []


def _build_channel_insights(channels: list[dict]) -> list[dict]:
    mod = _load_module(INSIGHTS / "channel_attribution.py")
    return mod.insights(channels)


def _build_exec_takeaways(blended: dict, channels: list[dict]) -> list[str]:
    mod = _load_module(INSIGHTS / "executive_summary.py")
    return mod.takeaways(inputs={"blended": blended, "channels": channels})


def _build_daily_nc_roas_28d(raws: dict, config: dict) -> list[dict]:
    """Run the daily_nc_roas transform once for the 28d window."""
    mod = _load_module(TRANSFORMS / "daily_nc_roas.py")
    return mod.transform(
        inputs={
            "daily":        raws.get("daily") or {"rows": []},
            "overview_3d":  raws.get("overview_3d") or raws.get("overview") or {},
            "overview_7d":  raws.get("overview_7d") or raws.get("overview") or {},
            "overview_28d": raws.get("overview") or {},
        },
        config=config,
    )


def _slice_nc_roas(series_28d: list[dict], window_key: str) -> list[dict]:
    """Slice the 28d NC ROAS series to the active window's tail."""
    if window_key == "3d":
        return series_28d[-3:]
    if window_key == "7d":
        return series_28d[-7:]
    return series_28d


def _build_journeys(raws: dict, config: dict, orders_per_platform: dict) -> dict:
    """Assemble the journey KPIs + heatmap + sankey SVGs from the
    channel-interactions payload and per-channel journey breakdowns."""
    touchpoints = raws.get("touchpoints") or {}
    out: dict = {}

    kpis_mod = _load_module(TRANSFORMS / "journey_kpis.py")
    out["kpis"] = kpis_mod.transform(inputs={"touchpoints": touchpoints}, config=config)

    hm_mod = _load_module(TRANSFORMS / "journey_heatmap.py")
    out["heatmap"] = hm_mod.transform(
        inputs={"touchpoints": touchpoints, "orders_per_platform": orders_per_platform},
        config=config,
    )

    # Pre-render the four sankey filter views. Every j_<platform> key the
    # _load_all_raws pass attached is forwarded to the transform.
    sankey_inputs: dict = {"touchpoints": touchpoints}
    for jkey, jval in raws.items():
        if jkey.startswith("j_"):
            sankey_inputs[jkey] = jval or {}
    sk_mod = _load_module(TRANSFORMS / "journey_sankey.py")
    sankey_payload = sk_mod.transform(inputs=sankey_inputs, config=config)
    unioned_paths = sankey_payload.pop("_paths", [])
    sankey_payload.pop("_multi_paths", None)
    out["sankey"] = sankey_payload

    co_mod = _load_module(INSIGHTS / "cooccurrence.py")
    out["cooccur_insights"] = co_mod.insights(touchpoints, orders_per_platform)

    j_mod = _load_module(INSIGHTS / "journey.py")
    out["journey_insights"] = j_mod.insights(unioned_paths, touchpoints)

    return out


def _orders_per_platform_28d(raws: dict) -> dict:
    """Pull TrackBee first-party order counts per platform from 28d funnel."""
    platforms = ((raws.get("platform_funnel") or {}).get("platforms") or {})
    return {p: _step_count(f, "orders") for p, f in platforms.items()}


def _low_sample_caveat(orders_per_platform: dict, min_sample: int = 50) -> str:
    """Return a footer <li> naming any platform with too few attributed orders.

    Empty string when every platform clears the threshold (or has 0).
    """
    low = [p for p, n in orders_per_platform.items()
           if 0 < int(n or 0) < min_sample and p != "no_platform"]
    if not low:
        return ""
    names = ", ".join(p.capitalize() for p in low)
    return (
        f'<br><span style="font-size:10px">Small sample on {names} '
        f"(fewer than {min_sample} attributed orders in 28 days). "
        f"These platforms are excluded from the strongest-overlap insight "
        f"in Channel touch points.</span>"
    )


def _sankey_inline_html(sankey_views: dict) -> str:
    """Wrap each sankey view in a data-sv toggle div (multi shown by default)."""
    parts = ['<div id="journeyFallback">']
    for key in ("multi", "top5", "single", "all"):
        svg = sankey_views.get(key, "")
        display = "block" if key == "multi" else "none"
        parts.append(f'<div data-sv="{key}" style="display:{display}">{svg}</div>')
    parts.append("</div>")
    return "".join(parts)


def _window_filter_html(available_windows: list[str]) -> str:
    """Render the 3d/7d/28d button row.

    Only emits a button for a window when we actually have data for it. If
    only 28d data is loaded (Step 1 of the build flow) the buttons collapse
    to a single-window pill so the user never clicks a button that would
    show em-dashes. When the row has just one window we hide it entirely —
    nothing to filter between.
    """
    if len(available_windows) <= 1:
        return ""
    button_label = {"3d": "3 days", "7d": "7 days", "28d": "28 days"}
    buttons = []
    for key in ("3d", "7d", "28d"):
        if key not in available_windows:
            continue
        active = ' class="active"' if key == "28d" else ""
        buttons.append(f'<button data-w="{key}"{active}>{button_label[key]}</button>')
    return (
        '<div class="filter" id="windowFilter" role="tablist">'
        + "".join(buttons)
        + "</div>"
    )


def _journeys_section_html(touchpoints: dict, heatmap_html: str,
                            sankey_inline: str) -> str:
    """Render the Customer Journeys card.

    Always emits the section markup so the skeleton phase has a complete
    layout; when touchpoints is empty the KPI tiles render zeros, the
    heatmap is an empty table, and the sankey shows its empty-state
    message. Real numbers light up the same card after the sync.
    """
    del touchpoints  # kept in the signature for callsite clarity
    return f'''
    <div class="card">
      <h2>Customer Journeys</h2>

      <div class="kpis" id="journeyKpis" style="grid-template-columns:repeat(3, minmax(180px, 1fr));max-width:680px"></div>

      <h3 style="font-family:var(--font-display);font-weight:500;font-size:14px;margin:22px 0 4px;color:var(--ink-2)">
        Channel touch points
      </h3>
      <div class="meta" style="margin-bottom:10px">When a customer interacts with platform A, how often do they interact with platform B?</div>
      {heatmap_html}

      <div class="insight-card">
        <h3>Key insights from your channel touch points</h3>
        <ul id="cooccurInsights" class="insight-list"></ul>
      </div>

      <div class="card sankey-card" style="margin-top:18px">
        <div class="sankey-filter" id="sankeyFilter" role="tablist" style="margin-bottom:12px">
          <button data-sf="multi" class="active">Multi-touch only</button>
          <button data-sf="top5">Top 5 journeys</button>
          <button data-sf="single">Single-touch only</button>
          <button data-sf="all">All journeys</button>
        </div>
        <div id="journeySankey">{sankey_inline}</div>
      </div>

      <div class="insight-card">
        <h3>Key insights from your customer journeys</h3>
        <ul id="journeyInsights" class="insight-list"></ul>
      </div>
    </div>'''


def build(inputs_dir: Path, config: dict) -> str:
    """Render the full attribution HTML page."""
    shell = _read(CHROME / "shell.html")
    theme = _read(CHROME / "theme.css")
    helpers = _read(CHROME / "format_helpers.js")
    js_render_sections = _read(CHROME / "render_sections.js")
    js_nc_roas = _read(HERE / "charts" / "nc_roas_line.js")
    js_window_filter = _read(CHROME / "window_filter.js")
    js_sankey_filter = _read(CHROME / "sankey_filter.js")
    js_tooltip = _read(CHROME / "tooltip.js")
    logos_mod = _load_module(CHROME / "logos.py")

    raws = _load_all_raws(inputs_dir)
    windows_cfg = config.get("windows") or {}

    # 28d series shared across windows.
    daily_28d = _build_daily_nc_roas_28d(raws, config)

    # Compute per-window payloads.
    payloads: dict = {}
    for key in ("3d", "7d", "28d"):
        win_in = _window_inputs(raws, key)
        cfg = windows_cfg.get(key) or {}
        blended  = _build_blended(win_in, config)
        platforms = _build_platforms(win_in, config)
        channels  = _build_channels(win_in, config)
        ch_insights = _build_channel_insights(channels)
        exec_takeaways = _build_exec_takeaways(blended, channels)
        payloads[key] = {
            "label":          {"3d": "Last 3 days", "7d": "Last 7 days", "28d": "Last 28 days"}[key],
            "start":          cfg.get("start", ""),
            "end":            cfg.get("end", ""),
            "blended":        blended,
            "platforms":      platforms,
            "channels":       channels,
            "ch_insights":    ch_insights,
            "exec_takeaways": exec_takeaways,
            "daily_nc_roas":  _slice_nc_roas(daily_28d, key),
        }

    # Journeys are not window-scoped (the channel-interactions payload
    # carries its own dates). Always run the journey build — when
    # touchpoints is absent the transforms return zeros / em-dashes,
    # which is the intended loading state for the skeleton phase. Real
    # numbers light up the same card without any structural change.
    orders_per_platform = _orders_per_platform_28d(raws)
    journeys_payload = _build_journeys(raws, config, orders_per_platform)
    sankey_views = (journeys_payload.get("sankey") or {}).get("views") or {}
    heatmap_html = (journeys_payload.get("heatmap") or {}).get("html") or ""

    # Strip the pre-rendered chunks from the JSON envelope to keep the
    # browser-side payload small — the SVG / heatmap HTML is spliced into
    # the Customer Journeys card directly by _journeys_section_html().
    journeys_clean = {
        "kpis": journeys_payload.get("kpis") or {},
        "cooccur_insights": journeys_payload.get("cooccur_insights") or [],
        "journey_insights": journeys_payload.get("journey_insights") or [],
    }

    # Assemble PAGE_DATA — the JSON the client-side renderer consumes.
    page_data = {
        "store": {
            "name": config.get("store_name", ""),
            "currency": config.get("store_currency", "EUR"),
            "fx": config.get("fx_to_eur", {}),
        },
        "windows": payloads,
        "journeys": journeys_clean,
        "logos": logos_mod.LOGOS,
    }

    low_sample_caveat = _low_sample_caveat(orders_per_platform)
    generated_date = dt.date.today().isoformat()

    # Detect which windows have real data so we only emit filter buttons
    # for windows whose data has been fetched. Step 1 of the build flow
    # only loads 28d data; the 3d/7d buttons would otherwise render but
    # show em-dashes when clicked.
    available_windows = ["28d"]
    if raws.get("overview_7d"):
        available_windows.append("7d")
    if raws.get("overview_3d"):
        available_windows.append("3d")
    available_windows = [w for w in ("3d", "7d", "28d") if w in available_windows]

    html = (
        shell
        .replace("{STORE_NAME}", page_data["store"]["name"])
        .replace("{INLINE_THEME_CSS}", theme)
        .replace("{INLINE_FORMAT_HELPERS_JS}", helpers)
        .replace("{INLINE_RENDER_SECTIONS_JS}", js_render_sections)
        .replace("{INLINE_NC_ROAS_JS}", js_nc_roas)
        .replace("{INLINE_WINDOW_FILTER_JS}", js_window_filter)
        .replace("{INLINE_SANKEY_FILTER_JS}", js_sankey_filter)
        .replace("{INLINE_TOOLTIP_JS}", js_tooltip)
        .replace("{INLINE_TB_DATA_JSON}", json.dumps(page_data))
        .replace("{BRAND_WORDMARK}", logos_mod.WORDMARK)
        .replace("{LOGO_TRACKBEE}", logos_mod.TRACKBEE)
        .replace("{WINDOW_FILTER}", _window_filter_html(available_windows))
        .replace("{JOURNEYS_SECTION}",
                 _journeys_section_html(raws.get("touchpoints") or {},
                                         heatmap_html,
                                         _sankey_inline_html(sankey_views)))
        .replace("{LOW_SAMPLE_CAVEAT}", low_sample_caveat)
        .replace("{GENERATED_DATE}", generated_date)
    )
    return html


def _load_config(inputs_dir: Path, override: Path | None) -> dict:
    """Read the dashboard config from inputs/config.json, or from the
    --config override path when that flag is set."""
    if override is not None:
        return _read_json(override)
    bundled = inputs_dir / "config.json"
    if not bundled.is_file():
        raise FileNotFoundError(
            f"Missing {bundled}. Stage store / window / FX metadata as "
            f"config.json inside the inputs directory."
        )
    return _read_json(bundled)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out",    required=True)
    # --config is optional. Default: inputs/config.json. Pass --config to
    # point at an out-of-band file.
    ap.add_argument("--config", required=False, default=None)
    args = ap.parse_args(argv)

    inputs_dir = Path(args.inputs)
    cfg = _load_config(inputs_dir, Path(args.config) if args.config else None)
    html = build(inputs_dir=inputs_dir, config=cfg)
    Path(args.out).write_text(html, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
