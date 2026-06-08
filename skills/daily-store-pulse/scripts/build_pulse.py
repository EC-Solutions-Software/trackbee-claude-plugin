#!/usr/bin/env python3
"""TrackBee Daily Store Pulse — entry script.

Thin wrapper that validates the staged config + inputs directory, then hands off
to the orchestrator at ../components/orchestrators/assemble.py.

Usage:
    python3 .../scripts/build_pulse.py \
        --inputs  /tmp/daily_store_pulse_inputs/ \
        --config  /tmp/daily_store_pulse_config.json \
        --out     /path/to/output.html
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


def _die(msg: str, code: int = 1) -> NoReturn:
    sys.stderr.write("\nDaily pulse build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Build the TrackBee Daily Store Pulse from staged JSON inputs.",
    )
    ap.add_argument("--inputs", required=True,
                    help="Directory containing the staged per-store MCP JSON dumps.")
    ap.add_argument("--config", required=True,
                    help="Path to config.json (stores list + window dates + MTD meta).")
    ap.add_argument("--out", required=True,
                    help="Path to write the assembled HTML file.")
    return ap.parse_args(argv)


def _validate_config(path: Path) -> dict:
    if not path.is_file():
        _die(f"can't find the config file at {path}. Stage it before running.")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _die(f"config file at {path} isn't valid JSON: {exc}.")
    if not isinstance(cfg, dict):
        _die(f"config file at {path} must be a JSON object.")

    if "windows" not in cfg or not isinstance(cfg["windows"], dict):
        _die("config is missing the `windows` block (yesterday + baseline + mtd).")
    w = cfg["windows"]
    for k in ("yesterday", "baseline"):
        win = w.get(k)
        if not isinstance(win, dict) or not win.get("start") or not win.get("end"):
            _die(f"config.windows.{k} needs start + end (ISO YYYY-MM-DD), inclusive.")

    stores = cfg.get("stores")
    if not isinstance(stores, list):
        _die("config.stores must be a list (it may be empty — the page renders an "
             "empty-portfolio state — but the key must exist).")
    for i, s in enumerate(stores):
        if not isinstance(s, dict) or s.get("store_id") in (None, ""):
            _die(f"config.stores[{i}] is missing store_id.")
    return cfg


def _load_orchestrator():
    if not ORCHESTRATOR.is_file():
        _die(f"orchestrator missing at {ORCHESTRATOR}. Reinstall the plugin.")
    spec = importlib.util.spec_from_file_location("assemble", ORCHESTRATOR)
    if spec is None or spec.loader is None:
        _die(f"couldn't load orchestrator from {ORCHESTRATOR}.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    args = _parse_args(argv)
    inputs_dir = Path(args.inputs)
    config_path = Path(args.config)
    out_path = Path(args.out)

    if not inputs_dir.is_dir():
        _die(f"can't find the inputs directory at {inputs_dir}.")

    cfg = _validate_config(config_path)
    orch = _load_orchestrator()

    try:
        html = orch.build(inputs_dir=inputs_dir, config=cfg)
    except (FileNotFoundError, ValueError) as exc:
        _die(f"pulse failed to assemble: {exc}. Re-check staged JSON and config.")
    except Exception as exc:  # noqa: BLE001 — surface anything unexpected plainly
        _die(f"pulse failed to assemble unexpectedly: {exc}.")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        _die(f"couldn't write HTML to {out_path}: {exc}.")

    print(f"Daily store pulse written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
