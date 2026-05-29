#!/usr/bin/env python3
"""TrackBee Ad Performance Dashboard — entry script.

Thin wrapper: parse args, hand off to `components/orchestrators/assemble.py`,
write the HTML, surface failures in plain language. Every renderable piece
of the report lives under `../components/`.

Run as::

    python3 .../scripts/build_ad_performance.py \\
        --inputs /tmp/adperf_inputs/ \\
        --out    /path/to/output.html

The orchestrator validates `config.json` up front and crashes with a clear
message if a required field is missing — see
`components/transforms/config.py`.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
ORCHESTRATOR = SKILL_DIR / "components" / "orchestrators" / "assemble.py"


def _die(msg: str, *, code: int = 1) -> NoReturn:
    sys.stderr.write("\nAd Performance build failed: " + msg.rstrip() + "\n\n")
    sys.exit(code)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build the TrackBee Ad Performance Dashboard from staged JSON inputs.",
    )
    ap.add_argument("--inputs", required=True,
                    help="Directory containing the staged JSON tool dumps + config.json.")
    ap.add_argument("--out", required=True,
                    help="Path to write the assembled HTML file.")
    return ap.parse_args(argv)


def _load_orchestrator():
    if not ORCHESTRATOR.is_file():
        _die(
            f"the orchestrator is missing at {ORCHESTRATOR}. "
            "Reinstall the plugin to restore the bundled components."
        )
    spec = importlib.util.spec_from_file_location("assemble", ORCHESTRATOR)
    if spec is None or spec.loader is None:
        _die(f"couldn't load the orchestrator from {ORCHESTRATOR}.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    inputs_dir = Path(args.inputs)
    out_path = Path(args.out)

    if not inputs_dir.is_dir():
        _die(
            f"can't find the inputs directory at {inputs_dir}. "
            "Stage the JSON tool dumps + config.json there before running."
        )

    orchestrator = _load_orchestrator()

    try:
        html = orchestrator.build(inputs_dir=inputs_dir, skill_dir=SKILL_DIR)
    except (FileNotFoundError, ValueError) as exc:
        _die(str(exc))
    except Exception as exc:  # noqa: BLE001 — surface anything unexpected plainly
        _die(f"the report failed to assemble: {exc}")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        _die(
            f"couldn't write the HTML to {out_path}: {exc}. "
            "Check the directory exists and is writable."
        )

    print(f"Ad Performance report written to {out_path} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
