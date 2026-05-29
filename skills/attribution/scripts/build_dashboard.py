#!/usr/bin/env python3
"""TrackBee Attribution Report — entry script.

This is intentionally a thin script. Every renderable piece of the report
lives under ``../components/`` and is loaded by the orchestrator one
module at a time. The job of this script is the boring outer loop:

1. Parse arguments.
2. Validate the config file (store name, store currency, three window
   ranges) — fail loudly with a plain-language message when something is
   missing rather than silently substituting a default.
3. Check that the staged inputs directory actually exists.
4. Hand off to ``components/orchestrators/assemble.py`` to load the
   components in sequence and stamp the HTML.
5. Surface any unexpected error in human-readable form on stderr.

Run as::

    python3 .../scripts/build_dashboard.py \\
        --inputs  /tmp/attribution_inputs/ \\
        --config  /tmp/attribution_config.json \\
        --out     /path/to/output.html

If a section's input file is missing or empty, the orchestrator stamps a
plain-language "Data unavailable" notice into that section's card and the
rest of the report still renders. This script never crashes the whole
build because one section is missing — it only crashes when the config
itself is incomplete (so the user knows what to fix).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parent / "components"
ORCHESTRATOR = COMPONENTS / "orchestrators" / "assemble.py"

# --- plain-language exit -----------------------------------------------------

def _die(msg: str, *, code: int = 1) -> "None":
    """Print a plain-language failure line and exit."""
    sys.stderr.write("\nAttribution build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


# --- argument parsing --------------------------------------------------------

def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build the TrackBee Attribution Report from staged JSON inputs.",
    )
    ap.add_argument("--inputs", required=True,
                    help="Directory containing the staged JSON tool dumps.")
    ap.add_argument("--config", required=True,
                    help="Path to config.json (store name, currency, "
                         "FX rates, three window ranges).")
    ap.add_argument("--out", required=True,
                    help="Path to write the assembled HTML file.")
    # --assets kept for backward-compat with older callers. The logos are
    # bundled inside the components/ tree now; this flag is silently
    # ignored. Newer callers can omit it.
    ap.add_argument("--assets", required=False, default=None,
                    help=argparse.SUPPRESS)
    return ap.parse_args(argv)


# --- config validation -------------------------------------------------------

REQUIRED_TOP_LEVEL = ("store_name", "store_currency", "windows")
REQUIRED_WINDOW_KEYS = ("3d", "7d", "28d")


def _validate_config(path: Path) -> dict:
    if not path.is_file():
        _die(f"can't find the config file at {path}. "
             "Stage it with store_name, store_currency, fx_to_eur, and a "
             "windows block before re-running.")

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _die(f"the config file at {path} isn't valid JSON: {exc}. "
             "Re-stage it and try again.")

    if not isinstance(cfg, dict):
        _die(f"the config file at {path} must be a JSON object, "
             f"got {type(cfg).__name__}.")

    missing = [k for k in REQUIRED_TOP_LEVEL if not cfg.get(k)]
    if missing:
        _die("the config file is missing required field(s): "
             + ", ".join(missing)
             + ". Set store_name (the human-readable store name), "
               "store_currency (a 3-letter ISO code like EUR / USD / GBP), "
               "and a windows block with start+end dates for 3d / 7d / 28d.")

    windows = cfg.get("windows")
    if not isinstance(windows, dict):
        _die("config.windows must be an object keyed by window slug "
             "(3d, 7d, 28d), each with start and end dates.")

    bad: list[str] = []
    for key in REQUIRED_WINDOW_KEYS:
        win = windows.get(key)
        if not isinstance(win, dict):
            bad.append(f"{key} (missing)")
            continue
        if not win.get("start") or not win.get("end"):
            bad.append(f"{key} (missing start or end)")
    if bad:
        _die("config.windows is incomplete: "
             + "; ".join(bad)
             + ". Each of 3d / 7d / 28d needs both start and end dates "
               "(ISO YYYY-MM-DD), inclusive of both endpoints.")

    # fx_to_eur is optional — when every ad-account currency matches the
    # store currency, an empty dict is fine. Normalise to {} so the
    # orchestrator never sees None.
    if cfg.get("fx_to_eur") is None:
        cfg["fx_to_eur"] = {}
    if not isinstance(cfg["fx_to_eur"], dict):
        _die("config.fx_to_eur must be an object mapping currency "
             "codes to numeric conversion rates, e.g. {\"USD\": 0.92}.")

    return cfg


# --- inputs validation -------------------------------------------------------

# overview.json is the central data source for every KPI in the report — the
# blended tiles, the per-platform tiles, the channel-attribution rows. Every
# other staged file builds on top of it. If overview.json is missing or holds
# an empty payload, the build can only produce a report full of "Data
# unavailable" notices — i.e. an artifact with no numbers. That's the failure
# mode this guard exists to prevent: instead of silently writing an empty
# dashboard, the script stops and tells the caller to fetch the data first.


def _payload_is_non_empty(path: Path) -> bool:
    """Return True if path holds a JSON object with real content.

    Accepts both ``{"result": {...}}`` wrappers (the shape every TrackBee MCP
    tool returns) and unwrapped dicts. An empty dict, an empty wrapped result,
    a non-object payload, or a file that can't be parsed all count as empty.
    """
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    if "result" in data and isinstance(data["result"], dict):
        return bool(data["result"])
    return bool(data)


def _validate_inputs(inputs_dir: Path) -> "None":
    """Refuse to build when the central data files weren't staged.

    The build script is the last line of defence against an empty artifact.
    If overview.json is missing entirely, the orchestrator would render a
    page with every section flagged "Data unavailable" — that's worse than
    failing, because the artifact still ships and the user thinks it worked.
    """
    overview = inputs_dir / "overview.json"
    if not _payload_is_non_empty(overview):
        _die(
            f"no usable data was staged in {inputs_dir}. The build needs "
            f"`overview.json` (from get_dashboard_overview) at a minimum — "
            f"that file drives every KPI on the page. Make the MCP calls "
            f"listed in the skill's §MCP calls section, save each result "
            f"as JSON into {inputs_dir}, then re-run this script. Building "
            f"now would only produce an empty dashboard."
        )


# --- orchestrator loading ----------------------------------------------------

def _load_orchestrator():
    """Import the orchestrator module from its absolute path.

    Loading it dynamically (rather than ``import assemble``) keeps the
    layout flat: this script lives in ``scripts/`` and the orchestrator
    lives in ``components/orchestrators/`` — no package init files
    needed.
    """
    if not ORCHESTRATOR.is_file():
        _die(f"the orchestrator is missing at {ORCHESTRATOR}. "
             "Reinstall the plugin from its zip to restore the bundled "
             "components.")
    spec = importlib.util.spec_from_file_location("assemble", ORCHESTRATOR)
    if spec is None or spec.loader is None:
        _die(f"couldn't load the orchestrator from {ORCHESTRATOR}.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- main --------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    inputs_dir = Path(args.inputs)
    config_path = Path(args.config)
    out_path = Path(args.out)

    if not inputs_dir.is_dir():
        _die(f"can't find the inputs directory at {inputs_dir}. "
             "Stage the JSON tool dumps there before running the build.")

    # Refuse to build a numberless artifact. If overview.json wasn't staged
    # (or came back empty) we abort here so the caller actually fetches the
    # data instead of shipping a "Data unavailable" page.
    _validate_inputs(inputs_dir)

    cfg = _validate_config(config_path)

    orchestrator = _load_orchestrator()

    try:
        html = orchestrator.build(inputs_dir=inputs_dir, config=cfg)
    except Exception as exc:  # noqa: BLE001 — surface any failure plainly
        _die(f"the report failed to assemble: {exc}. "
             "Re-check the staged JSON files in --inputs and the windows "
             "block in --config, then try again.")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        _die(f"couldn't write the HTML to {out_path}: {exc}. "
             "Check the directory exists and is writable.")

    print(f"Attribution report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
