"""Brand mark loaders for the Ad Performance dashboard.

Loads the TrackBee icon from `assets/ICON-PNG.png` and returns it as a
base64 string ready to drop into `<img src="data:image/png;base64,...">`.
Crashes loud if the asset is missing — a missing brand mark is a build
bug, not a runtime fallback.
"""

from __future__ import annotations

import base64
from pathlib import Path


def load_icon_b64(skill_dir: Path) -> str:
    """Return the base64-encoded TrackBee icon. Raises if missing."""
    p = skill_dir / "assets" / "ICON-PNG.png"
    if not p.is_file():
        raise FileNotFoundError(
            f"Brand asset missing at {p}. The build cannot ship a dashboard "
            "without the TrackBee mark — reinstall the plugin to restore the "
            "bundled assets."
        )
    return base64.b64encode(p.read_bytes()).decode("ascii")


def render_logo_block(icon_b64: str) -> str:
    """The header logo block (icon + TrackBee wordmark text).

    Emits the icon and wordmark as direct flex children of `.page-header`
    using the class names the theme styles (`.tb-icon`, `.wordmark`).
    """
    return (
        f'<img src="data:image/png;base64,{icon_b64}" alt="TrackBee" class="tb-icon">'
        '<span class="wordmark">TrackBee</span>'
    )
