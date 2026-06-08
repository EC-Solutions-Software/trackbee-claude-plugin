#!/usr/bin/env python3
"""TrackBee Growth Report — entry script.

Thin wrapper that validates the staged config + inputs directory, then hands
off to the orchestrator at ../components/orchestrators/assemble.py.

Usage:
    python3 .../scripts/build_report.py \
        --inputs  /tmp/growth_report_inputs/ \
        --config  /tmp/growth_report_config.json \
        --out     /path/to/output.html
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
ORCHESTRATOR = SKILL_DIR / "components" / "orchestrators" / "assemble.py"


def _die(msg: str, code: int = 1) -> NoReturn:
    sys.stderr.write("\nGrowth build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Build the TrackBee Growth Report from staged JSON inputs.",
    )
    ap.add_argument("--inputs",
                    help="Directory containing the staged MCP JSON tool dumps.")
    ap.add_argument("--config",
                    help="Path to config.json (store id/name/currency; window dates are derived).")
    ap.add_argument("--out",
                    help="Path to write the assembled HTML file.")
    ap.add_argument("--print-windows", action="store_true",
                    help="Print the derived current + prior 7-day window dates as JSON, then exit. "
                         "Run this FIRST and use the dates for the MCP calls + config.")
    ap.add_argument("--anchor",
                    help="Anchor date (current-window end), ISO YYYY-MM-DD. Default: yesterday (local).")
    return ap.parse_args(argv)


REQUIRED_TOP = ("store_id", "store_name", "store_currency")


def _derive_windows(anchor: dt.date) -> dict:
    """Derive both 7-day windows from a single anchor (the current-window end).

    All four bounds are computed here so nothing upstream has to do the date
    math by hand: current = the 7 days ending on `anchor`; prior = the 7 days
    immediately before that. Inclusive on both endpoints.
    """
    current_end = anchor
    current_start = current_end - dt.timedelta(days=6)
    prior_end = current_start - dt.timedelta(days=1)
    prior_start = prior_end - dt.timedelta(days=6)
    return {
        "current": {"start": current_start.isoformat(), "end": current_end.isoformat()},
        "prior":   {"start": prior_start.isoformat(),   "end": prior_end.isoformat()},
    }


def _resolve_anchor(value) -> dt.date:
    """Anchor = explicit ISO date if given, else yesterday (local)."""
    if value:
        try:
            return dt.date.fromisoformat(str(value))
        except ValueError:
            _die(f"anchor date must be ISO YYYY-MM-DD, got {value!r}.")
    return dt.date.today() - dt.timedelta(days=1)


def _validate_config(path: Path) -> dict:
    if not path.is_file():
        _die(f"can't find the config file at {path}. Stage it before running.")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _die(f"config file at {path} isn't valid JSON: {exc}.")
    if not isinstance(cfg, dict):
        _die(f"config file at {path} must be a JSON object.")
    missing = [k for k in REQUIRED_TOP if cfg.get(k) in (None, "")]
    if missing:
        _die("config is missing required field(s): " + ", ".join(missing)
             + ". Set store_id, store_name, and store_currency. Window dates "
               "are derived by the script (optional anchor_date).")
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

    # --print-windows: emit the derived window dates and exit. Run this FIRST,
    # then feed the dates into the MCP calls + config so the fetched data and
    # the rendered labels always agree (and the model never hand-does the math).
    if args.print_windows:
        anchor = _resolve_anchor(args.anchor)
        out = {"anchor_date": anchor.isoformat(), "windows": _derive_windows(anchor)}
        print(json.dumps(out, indent=2))
        return 0

    missing_args = [name for name, val in (("--inputs", args.inputs),
                                           ("--config", args.config),
                                           ("--out", args.out)) if not val]
    if missing_args:
        _die("missing required argument(s): " + ", ".join(missing_args) + ".")

    inputs_dir = Path(args.inputs)
    config_path = Path(args.config)
    out_path = Path(args.out)

    if not inputs_dir.is_dir():
        _die(f"can't find the inputs directory at {inputs_dir}.")

    cfg = _validate_config(config_path)
    # Derive both windows from the anchor (config.anchor_date, else yesterday),
    # overriding anything in config. This is the single source of truth, so the
    # rendered window labels can never disagree with the data the model fetched.
    cfg["windows"] = _derive_windows(_resolve_anchor(cfg.get("anchor_date")))
    orch = _load_orchestrator()

    try:
        html = orch.build(inputs_dir=inputs_dir, config=cfg)
    except (FileNotFoundError, ValueError) as exc:
        _die(f"report failed to assemble: {exc}. Re-check staged JSON and config.")
    except Exception as exc:  # noqa: BLE001 — surface anything unexpected plainly
        _die(f"report failed to assemble unexpectedly: {exc}.")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        _die(f"couldn't write HTML to {out_path}: {exc}.")

    print(f"Growth report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
