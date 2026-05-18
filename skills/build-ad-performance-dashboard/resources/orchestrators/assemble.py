#!/usr/bin/env python3
"""TrackBee Ad Performance Dashboard — full-section assembler.

Reads raw MCP JSON dumps for each store, runs the named transforms +
insights, fills the view templates, and writes one self-contained HTML
file to disk.

Sections are loaded in dependency order:
  1. chrome       — theme.css, format_helpers.js, app.js, shell.html
  2. transforms   — window, store_kpis, meta_rows, google_rows
  3. insights     — meta_insights, google_insights, next_questions
  4. views        — kpi_bar, table_controls, perf_table, insights_section,
                    questions_section, placeholder_card, footer

Each component file is self-contained (no inter-component imports). The
orchestrator plus its section helper (_sections.py) are the only
multi-file pieces.

Usage:
    python3 assemble.py --inputs <inputs_dir> --out <output.html>

The inputs directory must contain `config.json` with `stores` and
`window` keys, plus per-store JSON dumps from the TrackBee MCP. See the
skill's `SKILL.md` two levels up for the exact file list.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHROME = ROOT / "chrome"
TRANSFORMS = ROOT / "transforms"
INSIGHTS = ROOT / "insights"
VIEWS = ROOT / "views"


def _load_module(path: Path):
    """Import a sibling component module by absolute path.

    Transforms / insights live next to this file but aren't on sys.path,
    so we load them via importlib.util. Each module is fully standalone
    (no inter-component imports) so this just works.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_raw(inputs_dir: Path, filename: str, issues: list[dict]) -> dict:
    """Read `<filename>` from inputs and unwrap a JSON-RPC envelope if any.

    Missing or malformed files yield {} plus a structured issue describing
    what failed in plain language; the orchestrator surfaces issues to the
    viewer via a red-bordered card.
    """
    p = inputs_dir / filename
    if not p.is_file():
        issues.append({
            "title": f"Input file not found: {filename}",
            "body": (f"The build step expected `{filename}` in the inputs folder but "
                     f"the file isn't there. This usually means the MCP tool that "
                     f"produces it wasn't called, or its response wasn't saved."),
            "fix": ("Re-run the Phase 1 / Phase 2 MCP calls listed in the skill body "
                    "for this store. If a single platform returned no data, that's "
                    "expected — write `{\"result\": {}}` to the file to silence "
                    "this notice."),
        })
        return {}
    try:
        raw = _read_json(p)
    except json.JSONDecodeError as e:
        issues.append({
            "title": f"Couldn't read {filename}",
            "body": f"The file exists but isn't valid JSON: {e}.",
            "fix": ("Delete the file and re-run the MCP tool that produces it, "
                    "or edit the file to fix the parse error."),
        })
        return {}
    if isinstance(raw, dict) and "result" in raw and isinstance(raw["result"], dict):
        return raw["result"]
    return raw if isinstance(raw, dict) else {}


def _load_thresholds() -> dict:
    p = CHROME / "thresholds.json"
    if not p.is_file():
        return {}
    try:
        raw = _read_json(p)
    except json.JSONDecodeError:
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def build(inputs_dir: Path, out_path: Path) -> None:
    thresholds = _load_thresholds()
    if not thresholds:
        raise SystemExit(
            "FATAL: chrome/thresholds.json couldn't be loaded. The dashboard "
            "won't run without the threshold table — restore the file."
        )

    cfg_path = inputs_dir / "config.json"
    if not cfg_path.is_file():
        raise SystemExit(
            f"FATAL: {cfg_path} not found. The skill body writes this file as "
            f"step 5 of the workflow — re-run the data-collection step."
        )
    config = _read_json(cfg_path)

    window_mod = _load_module(TRANSFORMS / "window.py")
    try:
        window = window_mod.transform(inputs={}, config=config)
    except ValueError as e:
        raise SystemExit(f"FATAL: {e}")

    sections = _load_module(HERE / "_sections.py")
    rendered = []
    global_issues: list[dict] = []
    for store_cfg in (config.get("stores") or []):
        rs, store_issues = sections.render_store(
            store_cfg=store_cfg, window=window, inputs_dir=inputs_dir,
            transforms_dir=TRANSFORMS, insights_dir=INSIGHTS,
            views_dir=VIEWS, thresholds=thresholds, load_raw=_load_raw,
            load_module=_load_module, read_file=_read,
        )
        rendered.append(rs)
        global_issues.extend(store_issues)

    if not rendered:
        raise SystemExit(
            "FATAL: config.json has no `stores`. The dashboard needs at "
            "least one store to render. Add a store entry and re-run."
        )

    nav_tabs = "".join(
        f'<button class="store-tab" data-sid="{rs["id"]}" '
        f'onclick="switchStore({rs["id"]})">{rs["name_html"]}</button>'
        for rs in rendered
    )
    store_sections = "\n".join(rs["html"] for rs in rendered)
    generated_at = dt.datetime.now().strftime("%b %d, %Y %H:%M")
    footer = (_read(VIEWS / "footer.html")
              .replace("{DATE_LABEL}", window["label"])
              .replace("{GENERATED_AT}", generated_at))

    tb_data = {"thresholds": thresholds, "window": window}
    global_alerts = sections.render_global_alerts(global_issues, VIEWS, _read)

    shell = _read(CHROME / "shell.html")
    html = (shell
            .replace("{INLINE_THEME_CSS}", _read(CHROME / "theme.css"))
            .replace("{INLINE_FORMAT_HELPERS_JS}", _read(CHROME / "format_helpers.js"))
            .replace("{INLINE_APP_JS}", _read(CHROME / "app.js"))
            .replace("{INLINE_TB_DATA_JSON}", json.dumps(tb_data))
            .replace("{LOGO_HTML}", '<span class="wordmark">TrackBee</span>')
            .replace("{DATE_PILL}", window["pill"])
            .replace("{GENERATED_AT}", generated_at)
            .replace("{GLOBAL_ALERTS}", global_alerts)
            .replace("{NAV_TABS}", nav_tabs)
            .replace("{STORE_SECTIONS}", store_sections)
            .replace("{SLOT_FOOTER}", footer))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Written {len(html):,} bytes -> {out_path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    build(Path(args.inputs), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
