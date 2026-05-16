#!/usr/bin/env python3
"""Thin entry-point wrapper that delegates to the component orchestrator.

This file exists so existing skill invocations of the form

    python3 <SKILL_DIR>/scripts/build_ad_performance.py \
        --inputs /tmp/adperf_inputs/ \
        --out    /path/to/output.html

keep working without changes. All real logic lives in the component
library under
`<SKILL_DIR>/resources/dashboards/ad-performance/orchestrators/assemble.py`.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSEMBLE = (HERE.parent
            / "resources" / "dashboards" / "ad-performance"
            / "orchestrators" / "assemble.py")

if not ASSEMBLE.is_file():
    sys.exit(
        f"FATAL: orchestrator not found at {ASSEMBLE}. The plugin install is "
        "broken — reinstall the ad-performance plugin from the marketplace."
    )

# Run as a script so its argparse / __main__ branch fires normally.
sys.argv[0] = str(ASSEMBLE)
runpy.run_path(str(ASSEMBLE), run_name="__main__")
