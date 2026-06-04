#!/usr/bin/env python3
"""TrackBee Attribution Overview — entry script.

Intentionally thin. Every renderable piece of the report lives under
``../components/`` and is loaded by the orchestrator one module at a time.
This script does the boring outer loop:

1. Parse arguments.
2. Validate the config file (store name, store currency, three window ranges)
   — fail loudly with a plain-language message rather than silently
   substituting a default.
3. Check that the staged inputs directory exists.
4. Hand off to ``components/orchestrators/assemble.py`` to load the components
   in sequence and stamp the HTML.
5. Surface any unexpected error in human-readable form on stderr.

Run as::

    python3 .../scripts/build_dashboard.py \\
        --inputs  /tmp/attribution_overview_inputs/ \\
        --config  /tmp/attribution_overview_config.json \\
        --assets  .../skills/attribution/assets/ \\
        --out     /path/to/output.html

If an *ancillary* section's input file is missing or empty, the loader
degrades that section to em-dash / empty output and the rest of the report
still renders. This script only crashes when the config itself is incomplete
(so the user knows what to fix).
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
ASSETS = HERE.parent / "assets"


def _die(msg: str, *, code: int = 1) -> "None":
    sys.stderr.write("\nAttribution Overview build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Build the TrackBee Attribution Overview report from staged JSON inputs.")
    ap.add_argument("--inputs", required=True, help="Directory containing the staged JSON tool dumps.")
    ap.add_argument("--config", required=True, help="Path to config.json (store, currency, FX, windows).")
    ap.add_argument("--assets", default=str(ASSETS), help="Skill's assets/ directory (logos).")
    ap.add_argument("--out", required=True, help="Path to write the HTML file.")
    return ap.parse_args(argv)


def _load_config(path: Path) -> dict:
    if not path.is_file():
        _die(f"config file not found at {path}.")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _die(f"config file {path} is not valid JSON ({exc}).")
    for key in ("store_name", "store_currency", "windows"):
        if not cfg.get(key):
            _die(f"config is missing required field '{key}'.")
    for wk in ("3d", "7d", "28d"):
        w = cfg["windows"].get(wk)
        if not w or not w.get("start") or not w.get("end"):
            _die(f"config window '{wk}' must have both 'start' and 'end' dates.")
    return cfg


def _load_orchestrator():
    spec = importlib.util.spec_from_file_location("assemble", ORCHESTRATOR)
    if spec is None or spec.loader is None:
        _die(f"cannot load orchestrator at {ORCHESTRATOR}.")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv=None) -> int:
    args = _parse_args(argv)
    inputs = Path(args.inputs)
    if not inputs.is_dir():
        _die(f"inputs directory not found at {inputs}.")
    cfg = _load_config(Path(args.config))

    try:
        assemble = _load_orchestrator()
        result = assemble.build(inputs, cfg, args.assets, args.out)
    except Exception as exc:  # noqa: BLE001
        _die(f"unexpected error during assembly: {exc}")

    fmt = result["fmt"]
    print(f"Wrote {result['out_path']}")
    print(f"Size: {result['bytes']:,} bytes")
    print()
    for k in ("3d", "7d", "28d"):
        w = result["window_data"][k]
        b = w["blended"]
        print(f"=== {w['label']} ({w['start']} → {w['end']}) ===")
        print(f"  Revenue: {fmt.fmt_eur(b['revenue'])}   Orders: {fmt.fmt_int(b['orders'])}   "
              f"Spend: {fmt.fmt_eur(b['ad_spend'])}   ROAS: {b['roas']:.2f}")
    print()
    print(f"Customer-journey insights: {len(result['journey_insights'])}")
    print(f"Co-occurrence insights:    {len(result['cooccur_insights'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
