"""Meta key observations.

Returns a list of HTML-formatted factual observations the view stamps
into the Performance Analysis card. Each line states measured figures
(new-customer share, ROAS, frequency, spend) for the window — no scoring,
no recommendations. Thresholds in `thresholds.py` are used only to decide
which observations are material enough to surface, never to label a verdict.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fh = _load("format_helpers", _CHROME / "format_helpers.py")
_t = _load("thresholds", _HERE / "thresholds.py")


def build(campaigns: list[dict], sym: str) -> list[str]:
    active = [c for c in campaigns if _fh.safe_float(c.get("spend")) > 0]
    if not active:
        return ["No spending Meta campaigns in this window."]

    insights: list[str] = []

    total_purch = sum(int(c.get("purchases") or 0) for c in active)
    total_nc = sum(
        int(c.get("new_customer_purchases") or 0)
        for c in active
        if c.get("new_customer_purchases") is not None
    )

    # New-customer share of purchases.
    if total_purch > 0 and total_nc > 0:
        nc_pct = total_nc / total_purch * 100
        insights.append(
            f"<strong>{nc_pct:.0f}%</strong> of purchases are new customers "
            f"({total_nc:,} of {total_purch:,} total)."
        )

    # Best / worst ROAS.
    roas_list = [
        (c, _fh.safe_float(c.get("purchase_roas")))
        for c in active
        if c.get("purchase_roas")
    ]
    if roas_list:
        best_c, best_r = max(roas_list, key=lambda x: x[1])
        insights.append(
            f"Top performer: <strong>{_fh.text(_fh.short(best_c['campaign_name'], 44))}</strong> "
            f"at <strong>{best_r:.2f}× ROAS</strong>."
        )
        worst_c, worst_r = min(roas_list, key=lambda x: x[1])
        if worst_r < 1.0:
            insights.append(
                f"Lowest ROAS: <strong>{_fh.text(_fh.short(worst_c['campaign_name'], 44))}</strong> "
                f"at {worst_r:.2f}× on "
                f"{_fh.money(_fh.safe_float(worst_c.get('spend')), sym)} spend."
            )

    # Highest-frequency campaigns this window (impressions ÷ reach per person).
    freq_warn = [
        (c, _fh.safe_float(c.get("frequency")))
        for c in active
        if _fh.safe_float(c.get("frequency")) >= _t.FREQ_WARNING
    ]
    for c, f in sorted(freq_warn, key=lambda x: -x[1])[:2]:
        insights.append(
            f"Frequency {f:.1f}× on <strong>{_fh.text(_fh.short(c['campaign_name'], 44))}</strong> "
            f"this window ({_fh.money(_fh.safe_float(c.get('spend')), sym)} spend, "
            f"{_fh.safe_float(c.get('purchase_roas')):.2f}× ROAS)."
        )

    return insights
