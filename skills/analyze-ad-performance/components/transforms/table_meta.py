"""Performance-table column contract.

The header list is the canonical source — both meta_rows and google_rows
emit cells in this order. If you add or reorder a column, update this
file; nothing else needs to know.
"""

from __future__ import annotations

# Import the format helper used to escape attribute values.
import importlib.util
from pathlib import Path

_CHROME = Path(__file__).resolve().parent.parent / "chrome"
_spec = importlib.util.spec_from_file_location(
    "format_helpers", _CHROME / "format_helpers.py"
)
assert _spec is not None and _spec.loader is not None
_fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fh)


CAMPAIGN_HEADERS = [
    # (label,         sort key,   tooltip)
    ("Name",          "name",     ""),
    ("Status",        "status",   ""),
    ("Platform",      "platform", ""),
    ("Spend",         "spend",    "Total spend in the window"),
    ("Revenue",       "revenue",  "1d-click revenue (Meta) / Conversion value (Google)"),
    ("ROAS",          "roas",     "Return on ad spend (platform-reported)"),
    ("Results",       "results",  "Purchases (Meta) / Conversions (Google)"),
    ("Reach",         "reach",    "Unique people reached"),
    ("Impressions",   "impr",     "Total impressions"),
    ("Freq",          "freq",     "Average frequency (impressions ÷ reach)"),
    ("CPM",           "cpm",      "Cost per 1,000 impressions"),
    ("CTR",           "ctr",      "Click-through rate"),
    ("CPC",           "cpc",      "Cost per click"),
    ("Clicks",        "clicks",   "Total link clicks"),
    ("ATC",           "atc",      "Add-to-cart events"),
    ("Cost/ATC",      "cost_atc", "Spend ÷ add-to-cart"),
    ("New Cust.",     "nc",       "New customer purchases"),
    ("NC Revenue",    "nc_rev",   "New customer revenue"),
    ("Avg Daily",     "daily",    "Average daily spend (total ÷ days)"),
]


def cell(content: str, cls: str = "") -> str:
    """Emit a `<td>` with an optional class attribute."""
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def header(label: str, sort_key: str = "", tooltip: str = "") -> str:
    """Emit a `<th>` with optional sort + tooltip metadata.

    Sortable headers carry a `data-sort` attribute and a dual-arrow
    indicator. `tooltip` is escaped into the `title` attribute.
    """
    tip = f' title="{_fh.attr(tooltip)}"' if tooltip else ""
    sk = f' data-sort="{sort_key}"' if sort_key else ""
    ind = (
        '<span class="sort-ind" aria-hidden="true">'
        '<span class="ar ar-up">▲</span>'
        '<span class="ar ar-down">▼</span>'
        "</span>"
    ) if sort_key else ""
    return f"<th{sk}{tip}>{label}{ind}</th>"


def thead_html() -> str:
    """Render the table's <thead><tr>...</tr></thead> as one string."""
    cells = "".join(header(label, sk, tip) for label, sk, tip in CAMPAIGN_HEADERS)
    return f"<tr>{cells}</tr>"
