"""Brand assets — inline base64 wordmark for the page header.

Two variants ship next door in ../../assets/:
  - tb_wordmark_b64.txt        — light variant (navy text + yellow bee), for white surfaces
  - tb_wordmark_dark_b64.txt   — dark variant (white text + yellow bee), for navy surfaces

The Daily Store Pulse only ever places the wordmark on its navy portfolio
header, so the default ``WORDMARK`` returns the dark variant.
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

    The pulse only ever places the wordmark on its navy header, so the dark
    variant (white text + yellow bee) is the only one used."""
    b64 = _read_b64("tb_wordmark_dark_b64.txt")
    if not b64:
        # Plain-text fallback so the layout doesn't collapse.
        return (
            '<span style="font-family:Lexend,sans-serif;font-weight:700;'
            'font-size:22px;color:#FFFFFF">TrackBee</span>'
        )
    return (
        f'<img alt="TrackBee" src="data:image/png;base64,{b64}" '
        'style="display:block;height:26px;width:auto" />'
    )


# Default for the pulse header panel (which is always dark navy).
WORDMARK = wordmark_img_tag()
