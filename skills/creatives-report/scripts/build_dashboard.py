#!/usr/bin/env python3
"""TrackBee Creatives Report — entry script.

This is intentionally a thin script. Every renderable piece of the
report lives under ``../components/`` and is loaded by the orchestrator
one module at a time. The job of this script is the boring outer loop:

1. Parse arguments.
2. Validate the config file (store name, store currency, and a single
   7-day window) — fail loudly with a plain-language message when
   something is missing rather than silently substituting a default.
3. Check that the staged inputs directory actually exists.
4. Hand off to ``components/orchestrators/assemble.py`` to load the
   components in sequence and stamp the HTML.
5. Surface any unexpected error in human-readable form on stderr.

Run as::

    python3 .../scripts/build_dashboard.py \\
        --inputs  /tmp/audit_inputs/ \\
        --config  /tmp/audit_config.json \\
        --out     /path/to/output.html

The default audit window is the last 7 days ending yesterday — this is
a pure snapshot, not a 7d-vs-prior-period comparison. Fatigue scoring
uses absolute thresholds (frequency >= 3.5, ROAS floor, NNR share)
rather than week-over-week decay.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import NoReturn


HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
ORCHESTRATOR = SKILL_DIR / "components" / "orchestrators" / "assemble.py"


# --- plain-language exit -----------------------------------------------------
def _die(msg: str, *, code: int = 1) -> NoReturn:
    sys.stderr.write("\nCreatives Report build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


# --- argument parsing --------------------------------------------------------
def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description=("Build the TrackBee Creatives Report Dashboard from "
                     "staged JSON inputs."),
    )
    ap.add_argument("--inputs", required=True,
                    help="Directory with the staged JSON tool dumps.")
    ap.add_argument("--config", required=True,
                    help=("Path to config.json (store name, currency, "
                          "FX rates, audit window, scope)."))
    ap.add_argument("--out", required=True,
                    help="Path to write the assembled HTML file.")
    return ap.parse_args(argv)


# --- config validation -------------------------------------------------------
REQUIRED_TOP_LEVEL = ("store_name", "store_currency", "window")


def _validate_config(path: Path) -> dict:
    if not path.is_file():
        _die(f"can't find the config file at {path}. "
             "Stage it with store_name, store_currency, and a 7-day "
             "window block before re-running.")

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
             + ". Set store_name (human-readable store name), "
               "store_currency (3-letter ISO code like EUR / USD / GBP), "
               "and a window block with start + end dates "
               "(ISO YYYY-MM-DD) covering the last 7 days.")

    window = cfg.get("window")
    if not isinstance(window, dict) or not window.get("start") or not window.get("end"):
        _die("config.window must be an object with start and end dates "
             "(ISO YYYY-MM-DD), inclusive of both endpoints. The audit "
             "is a 7-day snapshot — set start = end - 6 days.")

    # Warn (not fail) if the window isn't 7 days. We accept other
    # window sizes for one-off custom runs but log it on stderr.
    import datetime as dt
    try:
        s = dt.date.fromisoformat(window["start"])
        e = dt.date.fromisoformat(window["end"])
        n = (e - s).days + 1
        if n != 7:
            sys.stderr.write(
                f"\nNote: config.window covers {n} days instead of the "
                f"default 7. Absolute-threshold scoring still applies; "
                f"the in-page label will reflect the actual window.\n"
            )
    except Exception:
        _die("config.window.start / end are not valid ISO YYYY-MM-DD "
             "dates.")

    if cfg.get("fx_to_store") is None:
        cfg["fx_to_store"] = {}
    if not isinstance(cfg["fx_to_store"], dict):
        _die("config.fx_to_store must be an object mapping currency codes "
             "to numeric conversion rates, e.g. {\"EUR\": 0.85}.")

    if cfg.get("scope") is None:
        cfg["scope"] = {}
    if not isinstance(cfg["scope"], dict):
        _die("config.scope, when set, must be an object with optional "
             "platforms / exclude_campaign_ids / product_focus fields.")

    return cfg


# --- orchestrator loading ----------------------------------------------------
def _load_orchestrator():
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
def main(argv=None) -> int:
    args = _parse_args(argv)

    inputs_dir = Path(args.inputs)
    config_path = Path(args.config)
    out_path = Path(args.out)

    if not inputs_dir.is_dir():
        _die(f"can't find the inputs directory at {inputs_dir}. "
             "Stage the JSON tool dumps there before running the build.")

    cfg = _validate_config(config_path)
    orchestrator = _load_orchestrator()

    try:
        html = orchestrator.build(inputs_dir=inputs_dir, config=cfg)
    except (FileNotFoundError, ValueError) as exc:
        _die(f"the report failed to assemble: {exc}. "
             "Re-check the staged JSON files in --inputs and the window "
             "block in --config, then try again.")
    except Exception as exc:  # noqa: BLE001 — surface anything unexpected plainly
        _die(f"the report failed to assemble unexpectedly: {exc}.")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        _die(f"couldn't write the HTML to {out_path}: {exc}. "
             "Check the directory exists and is writable.")

    print(f"Creatives Report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
