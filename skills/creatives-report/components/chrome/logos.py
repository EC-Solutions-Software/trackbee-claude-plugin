"""Inline brand marks used by the creatives-report dashboard.

Per the TrackBee brand guidelines v3 the report header uses the
**horizontal lockup, dark variant** on the navy surface (yellow bee
mark + white wordmark — the bundled wordmark is the navy-text source PNG
that ``theme.css`` inverts to white). The marks ship as pre-encoded
base64 text (``*_b64.txt``) next to their source PNGs under ``assets/``,
following the repo-wide asset convention; either form is read at module
import so the report is fully self-contained — no external requests.

Sizing follows the brand spec minimums: bee mark 16-32px tall, wordmark
height proportionally matched. On a 28-32px tall header the bee mark
+ wordmark together comfortably exceed the 110px horizontal lockup
minimum.

Two callers consume this module:
  * ``orchestrators.assemble`` splices ``header_logo_html()`` into the
    shell's header block.
  * Transforms read ``LOGOS["meta"]`` / ``LOGOS["google"]`` when
    rendering platform badges inside the ad table.
"""

from __future__ import annotations

import base64
from pathlib import Path


# chrome -> components -> creatives-report (skill root, where assets/ lives).
HERE = Path(__file__).resolve().parent.parent.parent
ASSETS = HERE / "assets"


def _load_b64(txt_name: str, png_name: str) -> str:
    """Return base64 for a brand mark.

    Prefer the pre-encoded ``*_b64.txt`` (the documented asset convention);
    fall back to encoding the source PNG at import. Returns '' when neither
    is present (the header then falls back to a CSS text wordmark)."""
    txt = ASSETS / txt_name
    if txt.is_file():
        return txt.read_text(encoding="utf-8").strip()
    png = ASSETS / png_name
    if png.is_file():
        try:
            return base64.b64encode(png.read_bytes()).decode("ascii")
        except Exception:
            return ""
    return ""


# Bee mark + wordmark, base64 at import so the report is self-contained.
TB_ICON_B64     = _load_b64("tb_icon_b64.txt", "trackbee-icon.png")
TB_WORDMARK_B64 = _load_b64("tb_wordmark_b64.txt", "trackbee-wordmark.png")


def header_logo_html() -> str:
    """Render the brand lockup for the report header.

    Renders the horizontal lockup in dark variant (bee mark + wordmark
    on a navy surface). Falls back gracefully to whatever asset is
    available — never throws.
    """
    icon_html = (
        f'<img src="data:image/png;base64,{TB_ICON_B64}" '
        f'alt="" class="tb-icon" aria-hidden="true">'
        if TB_ICON_B64 else ""
    )
    if TB_WORDMARK_B64:
        wordmark_html = (
            f'<img src="data:image/png;base64,{TB_WORDMARK_B64}" '
            f'alt="TrackBee" class="tb-wordmark">'
        )
    else:
        # Fallback — typeset the wordmark in the loaded body font so
        # the brand block still reads as "TrackBee" if the PNG didn't
        # ship with the plugin.
        wordmark_html = '<span class="tb-wordmark-text">TrackBee</span>'
    return (
        f'<a class="brand-lockup" href="#" aria-label="TrackBee">'
        f'  {icon_html}{wordmark_html}'
        f'</a>'
    )


# ── Platform marks (used in plat-badge cells) ────────────────────────
META = (
    '<svg viewBox="0 0 24 24" width="14" height="14" '
    'xmlns="http://www.w3.org/2000/svg" aria-label="Meta" '
    'style="vertical-align:-3px">'
    '<rect width="24" height="24" rx="5" fill="#1877F2"/>'
    '<path d="M5 17.5 V6.5 h2.4 L12 13.4 l4.6 -6.9 H19 v11 '
    'h-2.3 v-7 l-4.1 6.1 h-1.2 l-4.1 -6.1 v7 z" fill="#FFFFFF"/>'
    '</svg>'
)

GOOGLE = (
    '<svg viewBox="0 0 24 24" width="14" height="14" '
    'xmlns="http://www.w3.org/2000/svg" aria-label="Google" '
    'style="vertical-align:-3px">'
    '<path d="M21.6 12.227c0-.709-.064-1.39-.182-2.045H12v3.868h5.382'
    'a4.6 4.6 0 0 1-1.996 3.018v2.51h3.232c1.891-1.742 2.982-4.305 '
    '2.982-7.351z" fill="#4285F4"/>'
    '<path d="M12 22c2.7 0 4.964-.895 6.618-2.422l-3.232-2.51c-.895.6'
    '-2.04.955-3.386.955-2.605 0-4.81-1.76-5.596-4.123H3.064v2.59A9.996 '
    '9.996 0 0 0 12 22z" fill="#34A853"/>'
    '<path d="M6.404 13.9A6.005 6.005 0 0 1 6.09 12c0-.66.114-1.3.314'
    '-1.9V7.51H3.064A9.996 9.996 0 0 0 2 12c0 1.614.386 3.14 1.064 '
    '4.49l3.34-2.59z" fill="#FBBC05"/>'
    '<path d="M12 5.977c1.468 0 2.786.504 3.823 1.495l2.868-2.868C16.96 '
    '2.99 14.696 2 12 2 8.09 2 4.71 4.245 3.064 7.51l3.34 2.59C7.19 '
    '7.736 9.395 5.977 12 5.977z" fill="#EA4335"/>'
    '</svg>'
)


LOGOS = {
    "meta":   META,
    "google": GOOGLE,
}
