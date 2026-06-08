"""Creatives Report — fatigue scoring decision tree (7-day snapshot).

Single responsibility: take a pre-extracted metrics dict for one ad
over the audit window (default: last 7 days) and return its status
tag plus a plain-language reason and any secondary tags.

The decision tree uses **absolute thresholds only** — no week-over-week
decay comparison. Seven days isn't enough history to compute meaningful
decay; the audit is by design a pure 7-day snapshot.

See ``references/dashboard-spec.md`` §1 for the rationale behind each
threshold.
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


_H = _load("format_helpers", _CHROME / "format_helpers.py")
safe_float = _H.safe_float

# Minimum spend (store currency) for an ad to be worth scoring in a 7-day
# window. Below this we HOLD with a "low spend" tag rather than judging it.
MIN_SCORED_SPEND = 50.0


def score_ad(metrics: dict, platform: str) -> dict:
    """Return ``{status, reason, tags}`` for a single ad.

    ``metrics`` is the unified pre-normalised (currency-converted) dict
    documented in ``ad_processing.py``. ``platform`` is "meta" or
    "google" — the Meta-only "upper-funnel shift" tag is gated on this.
    """
    spend     = safe_float(metrics.get("spend"))
    roas      = safe_float(metrics.get("roas"))
    freq      = safe_float(metrics.get("frequency"))
    purchases = safe_float(metrics.get("purchases"))
    # Keep nnr_share as None when net-new-reach data is absent — only a
    # present value (including a genuine 0) may trigger the REFRESH gate.
    nnr_share = metrics.get("nnr_share")
    reach     = safe_float(metrics.get("reach"))
    p1d       = safe_float(metrics.get("p_1d_click"))
    p28d      = safe_float(metrics.get("p_28d_click"))
    # Keep nc as None when new-customer data is absent (ad_processing
    # preserves the distinction) — only a present value, including a
    # genuine 0, may trigger the "retargeting only" tag.
    nc        = metrics.get("new_customers")

    tags: list[str] = []

    # Insufficient spend → HOLD with low-spend tag
    if spend < MIN_SCORED_SPEND:
        return {
            "status": "HOLD",
            "reason": (
                "Insufficient spend to score in this 7-day window "
                f"(< {int(MIN_SCORED_SPEND)} in store currency)."
            ),
            "tags": ["low spend"],
        }

    # KILL — below break-even at meaningful spend. No ROAS floor: a zero-ROAS
    # ad (spent real money, zero/low-value conversions) is the textbook KILL,
    # so it must not be excluded by a `roas > 0` guard. The spend gate alone
    # keeps under-tested ads out.
    if roas < 1.0 and spend > 150:
        status = "KILL"
        reason = (
            f"ROAS {roas:.2f}× on {spend:,.0f} spend this week — "
            "below break-even at meaningful spend."
        )
    # REFRESH — frequency saturated (Meta only signal; Google has freq == 0)
    elif freq >= 3.5:
        status = "REFRESH"
        reason = (
            f"Frequency {freq:.1f}× this week — audience saturated."
        )
    # REFRESH — net new reach has collapsed (Meta only signal). Fires on a
    # genuine 0% (zero net-new people reached = fully exhausted audience).
    # A missing net_new_reach arrives as None and is skipped here — we never
    # score "audience exhausted" off absent data.
    elif reach > 1000 and nnr_share is not None and 0 <= nnr_share < 0.10:
        status = "REFRESH"
        reason = (
            f"Net new reach is only {nnr_share * 100:.0f}% of total — "
            "audience exhausted."
        )
    # SCALE — strong ROAS, frequency healthy (freq < 2.5 already covers
    # Google's freq == 0)
    elif roas >= 1.8 and freq < 2.5:
        status = "SCALE"
        # Frequency is a Meta-only metric — citing "frequency 0.0×" on a
        # Google ad would reference data the platform doesn't report.
        freq_clause = f" at frequency {freq:.1f}×" if platform == "meta" else ""
        reason = f"ROAS {roas:.2f}×{freq_clause} — increase budget 20-30%."
    # HOLD (losing) — below break-even but spend hasn't reached the kill
    # threshold yet. Don't call it healthy; let it run to a clear read.
    elif roas < 1.0:
        status = "HOLD"
        reason = (
            f"ROAS {roas:.2f}× this week, but spend is still under the kill "
            "threshold — let it run to a clearer read before cutting."
        )
    else:
        status = "HOLD"
        reason = "Performing within normal range this week."

    # Secondary tag: low new-customer share (acquisition fade). A present
    # zero (pure retargeting — no new customers at all) is the strongest
    # case and must fire; absent data arrives as None and never tags.
    if nc is not None and purchases > 0:
        nc_share = safe_float(nc) / purchases
        if nc_share < 0.10:
            tags.append("retargeting only")

    # Secondary tag: shifted upper-funnel (Meta only — needs the
    # 1d/28d click-attribution breakdowns Google doesn't expose).
    if platform == "meta" and p1d > 0 and p28d > 0 and purchases > 0:
        if p1d < (purchases * 0.5) and p28d >= purchases * 0.85:
            tags.append("upper-funnel shift")

    return {"status": status, "reason": reason, "tags": tags}
