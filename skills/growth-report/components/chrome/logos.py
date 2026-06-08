"""Brand assets — inline base64 wordmark for the page header.

Two variants ship next door in ../../assets/:
  - tb_wordmark_b64.txt        — light variant (navy text + yellow bee), for white surfaces
  - tb_wordmark_dark_b64.txt   — dark variant (white text + yellow bee), for navy surfaces

The Growth report only ever places the wordmark on the navy hero,
so the default `wordmark_img_tag()` returns the dark variant.
"""

from __future__ import annotations
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"


def _read_b64(name: str) -> str:
    path = _ASSETS / name
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def wordmark_img_tag() -> str:
    """Return an <img> tag with the dark TrackBee wordmark as a data URI.

    The Growth report only ever places the wordmark on its navy hero, so
    the dark variant (white text + yellow bee) is the only one used.
    """
    b64 = _read_b64("tb_wordmark_dark_b64.txt")
    if not b64:
        # Plain-text fallback so the layout doesn't collapse.
        return (
            '<span style="font-family:Lexend,sans-serif;font-weight:700;'
            'font-size:22px;color:#FFFFFF">'
            "TrackBee</span>"
        )
    return (
        f'<img alt="TrackBee" src="data:image/png;base64,{b64}" '
        'style="display:block;height:28px;width:auto" />'
    )


# Default for this report's hero panel (which is always dark navy).
WORDMARK = wordmark_img_tag()
