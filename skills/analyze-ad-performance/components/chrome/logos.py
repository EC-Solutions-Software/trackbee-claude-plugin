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
    """Return the base64-encoded TrackBee mark for the header.

    Prefers the dark-variant wordmark (the header is a navy surface, per
    the brand variant decision tree); falls back to the bee icon. Raises
    only when no brand asset shipped at all.
    """
    wm = skill_dir / "assets" / "tb_wordmark_dark_b64.txt"
    if wm.is_file():
        return wm.read_text(encoding="utf-8").strip()
    wm_png = skill_dir / "assets" / "trackbee-wordmark-dark.png"
    if wm_png.is_file():
        return base64.b64encode(wm_png.read_bytes()).decode("ascii")
    p = skill_dir / "assets" / "ICON-PNG.png"
    if not p.is_file():
        raise FileNotFoundError(
            f"Brand asset missing at {p}. The build cannot ship a dashboard "
            "without the TrackBee mark — reinstall the plugin to restore the "
            "bundled assets."
        )
    return base64.b64encode(p.read_bytes()).decode("ascii")


def render_logo_block(icon_b64: str) -> str:
    """The header brand lockup (dark-variant wordmark image).

    The wordmark lockup already contains the bee mark, so it renders
    alone — no second standalone bee, no typeset duplicate.
    """
    return (
        f'<img src="data:image/png;base64,{icon_b64}" alt="TrackBee" class="tb-wordmark-dark">'
    )
