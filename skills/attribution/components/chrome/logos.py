"""Inline brand + platform marks for the Attribution Overview report.

Two TrackBee versions: the small icon mark for inline use and the wordmark
for the page header — both real brand assets, base64-encoded into data URLs
so the HTML stays self-contained. The platform marks (Meta, Google, Klaviyo,
TikTok, Pinterest, Microsoft Ads, Calendly) are small inline SVG letterforms
over coloured rounded squares; simple shapes render reliably everywhere.

``logos_by_key()`` returns the map that is JSON-embedded into the page as
``PAGE_DATA.logos`` and stamped into rows/tiles by the client-side JS.

This component is self-contained — it imports nothing from sibling
components. The orchestrator loads it by path and passes the assets dir.
"""

from pathlib import Path


def wordmark_img(assets_dir: Path) -> str:
    """The TrackBee wordmark for the hero header (base64 data URL).

    The hero is a navy panel, so this serves the dark-variant wordmark
    per the brand variant decision tree.
    """
    b64 = (Path(assets_dir) / "tb_wordmark_dark_b64.txt").read_text().strip()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="TrackBee" aria-label="TrackBee" '
        f'style="height:26px;width:auto;display:block">'
    )


def icon_img(assets_dir: Path) -> str:
    """The small TrackBee icon mark for inline use (base64 data URL)."""
    b64 = (Path(assets_dir) / "tb_icon_b64.txt").read_text().strip()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="TrackBee" aria-label="TrackBee" '
        f'style="width:14px;height:14px;vertical-align:-3px;display:inline-block">'
    )


LOGO_META = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Meta" style="vertical-align:-3px">
  <rect width="24" height="24" rx="5" fill="#1877F2"/>
  <path d="M5 17.5 V6.5 h2.4 L12 13.4 l4.6 -6.9 H19 v11 h-2.3 v-7 l-4.1 6.1 h-1.2 l-4.1 -6.1 v7 z" fill="#FFFFFF"/>
</svg>
""".strip()

LOGO_GOOGLE = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Google" style="vertical-align:-3px">
  <path d="M21.6 12.227c0-.709-.064-1.39-.182-2.045H12v3.868h5.382a4.6 4.6 0 0 1-1.996 3.018v2.51h3.232c1.891-1.742 2.982-4.305 2.982-7.351z" fill="#4285F4"/>
  <path d="M12 22c2.7 0 4.964-.895 6.618-2.422l-3.232-2.51c-.895.6-2.04.955-3.386.955-2.605 0-4.81-1.76-5.596-4.123H3.064v2.59A9.996 9.996 0 0 0 12 22z" fill="#34A853"/>
  <path d="M6.404 13.9A6.005 6.005 0 0 1 6.09 12c0-.66.114-1.3.314-1.9V7.51H3.064A9.996 9.996 0 0 0 2 12c0 1.614.386 3.14 1.064 4.49l3.34-2.59z" fill="#FBBC05"/>
  <path d="M12 5.977c1.468 0 2.786.504 3.823 1.495l2.868-2.868C16.96 2.99 14.696 2 12 2 8.09 2 4.71 4.245 3.064 7.51l3.34 2.59C7.19 7.736 9.395 5.977 12 5.977z" fill="#EA4335"/>
</svg>
""".strip()

# Klaviyo — dark navy tile with white "K".
LOGO_KLAVIYO = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Klaviyo" style="vertical-align:-3px">
  <rect width="24" height="24" rx="5" fill="#232323"/>
  <path d="M7 5 V19 H9.6 V13.5 L14.2 19 H17.6 L11.6 12 L17.4 5 H14.2 L9.6 10.5 V5 z" fill="#FFFFFF"/>
</svg>
""".strip()

# TikTok — black tile with white "d" (stylised) + cyan/red glyph hint.
LOGO_TIKTOK = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="TikTok" style="vertical-align:-3px">
  <rect width="24" height="24" rx="5" fill="#000000"/>
  <path d="M14 4 h2.6 c.2 1.6 1.2 2.8 2.8 3.1 V9.6 c-1.1 0 -2 -.3 -2.8 -.8 V14.6 c0 3 -2.4 5.4 -5.4 5.4 c-3 0 -5.4 -2.4 -5.4 -5.4 c0 -2.9 2.3 -5.3 5.2 -5.4 V11.7 c-1.6 .1 -2.8 1.4 -2.8 3 c0 1.6 1.3 3 3 3 c1.6 0 3 -1.3 3 -3 V4 z" fill="#FFFFFF"/>
</svg>
""".strip()

# Pinterest — red tile with white "P".
LOGO_PINTEREST = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Pinterest" style="vertical-align:-3px">
  <rect width="24" height="24" rx="12" fill="#E60023"/>
  <path d="M12 5 c-3.9 0 -6 2.7 -6 5.6 c0 1.7 .9 3.6 2.4 4.2 c.2 .1 .4 0 .4 -.2 c0 -.1 .1 -.5 .2 -.9 c0 -.1 0 -.2 -.1 -.4 c-.4 -.5 -.7 -1.2 -.7 -2.1 c0 -2.7 2 -5.1 5.2 -5.1 c2.8 0 4.4 1.7 4.4 4 c0 3 -1.3 5.5 -3.3 5.5 c-1.1 0 -1.9 -.9 -1.6 -2 c.3 -1.3 .9 -2.7 .9 -3.7 c0 -.8 -.5 -1.5 -1.4 -1.5 c-1.1 0 -2 1.2 -2 2.7 c0 1 .3 1.7 .3 1.7 l -1.4 5.7 c-.4 1.7 -.1 3.7 -.1 3.9 c0 .1 .2 .2 .2 .1 c.1 -.1 1.3 -1.6 1.7 -3.2 c.1 -.5 .8 -2.9 .8 -2.9 c.4 .7 1.5 1.3 2.6 1.3 c3.5 0 5.8 -3.1 5.8 -7.3 c0 -3.2 -2.7 -6.1 -6.8 -6.1 z" fill="#FFFFFF"/>
</svg>
""".strip()

# Microsoft Ads — Microsoft 4-square logo.
LOGO_MICROSOFT = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Microsoft" style="vertical-align:-3px">
  <rect width="24" height="24" rx="3" fill="#FFFFFF" stroke="#E5E5E5" stroke-width="0.5"/>
  <rect x="3"  y="3"  width="8" height="8" fill="#F25022"/>
  <rect x="13" y="3"  width="8" height="8" fill="#7FBA00"/>
  <rect x="3"  y="13" width="8" height="8" fill="#00A4EF"/>
  <rect x="13" y="13" width="8" height="8" fill="#FFB900"/>
</svg>
""".strip()

# Calendly — blue tile with stylised calendar mark.
LOGO_CALENDLY = """
<svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg" aria-label="Calendly" style="vertical-align:-3px">
  <rect width="24" height="24" rx="5" fill="#006BFF"/>
  <rect x="6" y="7" width="12" height="11" rx="1.5" fill="#FFFFFF"/>
  <rect x="6" y="7" width="12" height="3" rx="1.5" fill="#0050C7"/>
  <rect x="8.5" y="4" width="1.5" height="4" rx="0.5" fill="#FFFFFF"/>
  <rect x="14" y="4" width="1.5" height="4" rx="0.5" fill="#FFFFFF"/>
  <circle cx="12" cy="14" r="1.6" fill="#006BFF"/>
</svg>
""".strip()


def logos_by_key(assets_dir: Path) -> dict:
    """Map of logo key → inline SVG/data-URL markup, embedded into PAGE_DATA
    so the client-side renderer can stamp the right mark per row/tile."""
    return {
        "meta": LOGO_META, "google": LOGO_GOOGLE, "trackbee": icon_img(assets_dir),
        "klaviyo": LOGO_KLAVIYO, "tiktok": LOGO_TIKTOK, "pinterest": LOGO_PINTEREST,
        "microsoft": LOGO_MICROSOFT, "calendly": LOGO_CALENDLY,
    }
