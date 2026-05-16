#!/usr/bin/env python3
"""TrackBee Ad Performance Dashboard — full-section assembler.

Reads raw MCP JSON dumps for each store, runs the named transforms +
insights, fills the view templates, and writes one self-contained HTML
file to disk.

Sections are loaded in dependency order:
  1. chrome        — theme.css, format_helpers.js, app.js, shell.html
  2. transforms    — window, store_kpis, meta_rows, google_rows, action_rules
  3. insights      — meta_insights, google_insights, next_questions
  4. views         — kpi_bar, table_controls, perf_table, insights_section,
                     questions_section, placeholder_card, footer
Each component file lives in its own ≤150-line module so an MCP serving
this plugin can stream individual files instead of one 1.4k-line monolith.

The ~250-line limit for orchestrators (per CLAUDE.md) is enforced by
splitting the per-section helpers into `_sections.py`. Read that file
together with this one for the full picture.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                          # .../ad-performance/
CHROME = ROOT / "chrome"
TRANSFORMS = ROOT / "transforms"
INSIGHTS = ROOT / "insights"
VIEWS = ROOT / "views"


# ── Component loading (importlib so sibling dirs aren't on sys.path) ──
def _load_module(path: Path, package_name: str):
    """Load a sibling component module under a synthetic package name so
    that relative imports inside the module (e.g. `from . import _fmt`)
    work without needing to add ROOT to sys.path globally."""
    spec = importlib.util.spec_from_file_location(package_name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = m
    spec.loader.exec_module(m)
    return m


def _bootstrap_packages():
    """Register `transforms` and `insights` as importable packages so
    individual modules can do `from transforms import _fmt as f`."""
    for pkg_dir, pkg_name in ((TRANSFORMS, "transforms"), (INSIGHTS, "insights")):
        init = pkg_dir / "__init__.py"
        if init.is_file():
            spec = importlib.util.spec_from_file_location(
                pkg_name, init, submodule_search_locations=[str(pkg_dir)]
            )
            m = importlib.util.module_from_spec(spec)
            sys.modules[pkg_name] = m
            spec.loader.exec_module(m)


# ── Tiny IO ─────────────────────────────────────────────────────────
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Brand asset ──────────────────────────────────────────────────────
def _load_icon_b64() -> str:
    """Inline the bundled TrackBee icon. Stored next to this skill's
    `assets/` folder. Returns '' if the icon isn't present so the build
    still succeeds in environments where assets were stripped."""
    candidates = [
        ROOT.parent.parent.parent / "assets" / "ICON-PNG.png",  # SKILL_DIR/assets
        ROOT.parent.parent / "assets" / "ICON-PNG.png",
    ]
    for p in candidates:
        if p.is_file():
            try:
                return base64.b64encode(p.read_bytes()).decode("ascii")
            except OSError:
                return ""
    return ""


def _logo_html(b64: str) -> str:
    if b64:
        return (f'<img src="data:image/png;base64,{b64}" alt="TrackBee" '
                f'class="tb-icon"><span class="wordmark">TrackBee</span>')
    return '<span class="wordmark">TrackBee</span>'


# ── Main build ───────────────────────────────────────────────────────
def build(inputs_dir: Path, out_path: Path) -> None:
    _bootstrap_packages()

    # Chrome (assets that always load first).
    theme = _read(CHROME / "theme.css")
    helpers = _read(CHROME / "format_helpers.js")
    app_js = _read(CHROME / "app.js")
    shell = _read(CHROME / "shell.html")

    io = _load_module(TRANSFORMS / "_io.py", "transforms._io")
    thresholds = io.load_thresholds(ROOT)
    if not thresholds:
        raise SystemExit(
            "FATAL: chrome/thresholds.json couldn't be loaded. The dashboard "
            "won't run without the threshold table — restore the file."
        )

    # Load config + window.
    cfg_issues: list[dict] = []
    cfg_path = inputs_dir / "config.json"
    if not cfg_path.is_file():
        raise SystemExit(
            f"FATAL: {cfg_path} not found. The skill writes this file as "
            f"step 5 of the workflow — re-run the data-collection step."
        )
    config = _read_json(cfg_path)

    window_mod = _load_module(TRANSFORMS / "window.py", "transforms.window")
    try:
        window = window_mod.transform(inputs={}, config=config)
    except ValueError as e:
        raise SystemExit(f"FATAL: {e}")

    # Pre-render the per-store sections.
    sections_mod = _load_module(HERE / "_sections.py", "orchestrators._sections")
    rendered = []
    global_issues: list[dict] = list(cfg_issues)
    for store_cfg in (config.get("stores") or []):
        rs, store_issues = sections_mod.render_store(
            store_cfg=store_cfg,
            window=window,
            inputs_dir=inputs_dir,
            views_dir=VIEWS,
            thresholds=thresholds,
        )
        rendered.append(rs)
        global_issues.extend(store_issues)

    if not rendered:
        raise SystemExit(
            "FATAL: config.json has no `stores`. The dashboard needs at "
            "least one store to render. Add a store entry and re-run."
        )

    # Stitch into the shell.
    nav_tabs = "".join(
        f'<button class="store-tab" data-sid="{rs["id"]}" '
        f'onclick="switchStore({rs["id"]})">{rs["name_html"]}</button>'
        for rs in rendered
    )
    store_sections = "\n".join(rs["html"] for rs in rendered)
    footer = _read(VIEWS / "footer.html").replace(
        "{DATE_LABEL}", window["label"]
    ).replace(
        "{GENERATED_AT}", dt.datetime.now().strftime("%b %d, %Y %H:%M")
    )

    tb_data = {"thresholds": thresholds, "window": window}
    global_alerts = sections_mod.render_global_alerts(global_issues, VIEWS)

    html = (shell
            .replace("{INLINE_THEME_CSS}", theme)
            .replace("{INLINE_FORMAT_HELPERS_JS}", helpers)
            .replace("{INLINE_APP_JS}", app_js)
            .replace("{INLINE_TB_DATA_JSON}", json.dumps(tb_data))
            .replace("{LOGO_HTML}", _logo_html(_load_icon_b64()))
            .replace("{DATE_PILL}", window["pill"])
            .replace("{GENERATED_AT}", dt.datetime.now().strftime("%b %d, %Y %H:%M"))
            .replace("{GLOBAL_ALERTS}", global_alerts)
            .replace("{NAV_TABS}", nav_tabs)
            .replace("{STORE_SECTIONS}", store_sections)
            .replace("{SLOT_FOOTER}", footer))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Written {len(html):,} bytes -> {out_path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    build(Path(args.inputs), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
