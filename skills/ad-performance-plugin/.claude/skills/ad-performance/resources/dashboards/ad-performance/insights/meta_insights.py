"""Meta ad performance insights + recommendations.

Pure-Python — no MCP calls, no HTML aside from the inline <strong> tags the
front-end already styles. Returns two lists of strings; the views/ layer
slots them into the meta insights card.

All comparison thresholds come from `thresholds` (loaded from
chrome/thresholds.json). The list contents are HTML fragments because the
front-end view embeds them with innerHTML — keep them well-escaped.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing transforms/_fmt when this module is loaded by the
# orchestrator via importlib (it loads each component as a top-level module).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from transforms import _fmt as f  # noqa: E402


def insights(campaigns: list[dict], symbol: str, thresholds: dict) -> tuple[list[str], list[str]]:
    """Return ``(observations, recommendations)`` for the Meta side."""
    active = [c for c in campaigns if f.safe_float(c.get("spend")) > 0]
    if not active:
        return (["No spending Meta campaigns in this window."], [])

    obs: list[str] = []
    recs: list[str] = []

    total_spend = sum(f.safe_float(c.get("spend")) for c in active)
    total_purch = sum(int(c.get("purchases") or 0) for c in active)
    total_nc = sum(int(c.get("new_customer_purchases") or 0)
                   for c in active if c.get("new_customer_purchases") is not None)

    if total_purch > 0 and total_nc > 0:
        nc_pct = total_nc / total_purch * 100
        obs.append(
            f"<strong>{nc_pct:.0f}%</strong> of purchases are new customers "
            f"({total_nc:,} of {total_purch:,} total)."
        )

    roas_list = [(c, f.safe_float(c.get("purchase_roas")))
                 for c in active if c.get("purchase_roas")]
    if roas_list:
        best_c, best_r = max(roas_list, key=lambda x: x[1])
        obs.append(
            f"Top performer: <strong>{f.short(best_c['campaign_name'], 44)}</strong> "
            f"at <strong>{best_r:.2f}× ROAS</strong>."
        )
        worst_c, worst_r = min(roas_list, key=lambda x: x[1])
        if worst_r < 1.0:
            obs.append(
                f"Below break-even: <strong>{f.short(worst_c['campaign_name'], 44)}</strong> "
                f"at {worst_r:.2f}× ROAS on "
                f"{symbol}{f.safe_float(worst_c.get('spend')):,.0f} spend."
            )

    freq_thr = thresholds["insights_high_freq_threshold"]
    freq_list = [(c, f.safe_float(c.get("frequency"))) for c in active
                 if f.safe_float(c.get("frequency")) >= freq_thr]
    for c, fq in sorted(freq_list, key=lambda x: -x[1])[:2]:
        obs.append(
            f"Frequency {fq:.1f} on <strong>{f.short(c['campaign_name'], 44)}</strong> "
            f"— creative fatigue risk."
        )

    scale = [(c, f.safe_float(c.get("purchase_roas"))) for c in active
             if f.safe_float(c.get("purchase_roas")) >= thresholds["scale_roas"]
             and f.safe_float(c.get("frequency")) < thresholds["scale_max_freq"]]
    for c, r in sorted(scale, key=lambda x: -x[1])[:3]:
        recs.append(
            f"<strong>Scale:</strong> {f.short(c['campaign_name'], 44)} — "
            f"{r:.2f}× ROAS at frequency {f.safe_float(c.get('frequency')):.1f}. "
            f"Test a 20–30% budget increase."
        )

    pause_min_spend = thresholds["insights_pause_min_spend"]
    pause = [c for c in active
             if 0 < f.safe_float(c.get("purchase_roas")) < thresholds["pause_roas"]
             and f.safe_float(c.get("spend")) > pause_min_spend]
    for c in sorted(pause, key=lambda x: f.safe_float(x.get("spend")), reverse=True)[:2]:
        recs.append(
            f"<strong>Review or pause:</strong> {f.short(c['campaign_name'], 44)} — "
            f"{f.safe_float(c.get('purchase_roas')):.2f}× ROAS on "
            f"{symbol}{f.safe_float(c.get('spend')):,.0f} spend. "
            f"Refresh creative or reallocate budget."
        )

    refresh = [c for c in active
               if f.safe_float(c.get("frequency")) >= thresholds["insights_creative_refresh_min_freq"]
               and f.safe_float(c.get("purchase_roas")) >= thresholds["insights_creative_refresh_min_roas"]]
    for c in sorted(refresh, key=lambda x: -f.safe_float(x.get("frequency")))[:2]:
        recs.append(
            f"<strong>Refresh creative:</strong> {f.short(c['campaign_name'], 44)} — "
            f"frequency {f.safe_float(c.get('frequency')):.1f} with ROAS still healthy. "
            f"Queue new variants before performance erodes."
        )

    if not recs:
        recs.append("All spending campaigns are within healthy ranges. "
                    "Continue monitoring frequency daily.")
    return obs, recs
