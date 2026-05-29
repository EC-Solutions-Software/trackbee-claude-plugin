"""Daily NC ROAS series — Acquisition MER over time.

Builds a per-day series of NC ROAS = (daily new-customer revenue) /
(daily ad spend) for the selected window (default: 28d). The view layer
renders this as a line chart with the period average as the headline.

Daily spend approximation
-------------------------
The upstream data source doesn't return per-day ad spend, only per-window
totals. We approximate using three tiers derived from the 3d/7d/28d
overview totals:

    - Days inside the 3d window:    total_3d / n_3d
    - Days inside 7d but not 3d:    (total_7d  - total_3d) / (n_7d - n_3d)
    - Days inside 28d but not 7d:   (total_28d - total_7d) / (n_28d - n_7d)

A calendar day always falls into exactly one tier and gets the same
daily spend regardless of which window the viewer selects.

All monetary inputs are store-currency cents → output is in units.
"""

from __future__ import annotations

import datetime as dt


def _ov_spend_units(ov: dict | None) -> float:
    """Overview ad_account_spend in store-currency units (cents / 100)."""
    if not ov:
        return 0.0
    return float(ov.get("ad_account_spend") or 0) / 100


def _build_tiers(window_dates: dict, inputs: dict) -> list[tuple[dt.date, dt.date, float]]:
    """Return [(tier_start, tier_end, per_day_spend), ...].

    Tiers cover the full 28d window without gaps. Each tier's per-day spend
    is the slice total ÷ slice length.
    """
    d3 = window_dates["3d"]
    d7 = window_dates["7d"]
    d28 = window_dates["28d"]

    total_3d = _ov_spend_units(inputs.get("overview_3d"))
    total_7d = _ov_spend_units(inputs.get("overview_7d"))
    total_28d = _ov_spend_units(inputs.get("overview_28d"))

    gap_3_to_7 = max(1, d7["n_days"] - d3["n_days"])
    gap_7_to_28 = max(1, d28["n_days"] - d7["n_days"])

    return [
        # 3d slice (newest)
        (d3["start"], d3["end"], (total_3d / d3["n_days"]) if d3["n_days"] else 0.0),
        # 7d-but-not-3d slice
        (d7["start"], d3["start"] - dt.timedelta(days=1),
         (total_7d - total_3d) / gap_3_to_7),
        # 28d-but-not-7d slice (oldest)
        (d28["start"], d7["start"] - dt.timedelta(days=1),
         (total_28d - total_7d) / gap_7_to_28),
    ]


def _daily_spend_for(date: dt.date, tiers: list[tuple[dt.date, dt.date, float]],
                    fallback: float) -> float:
    for start, end, avg in tiers:
        if start <= date <= end:
            return avg
    return fallback


def transform(inputs: dict, config: dict) -> list[dict]:
    """Return a list of {date, value, nc_revenue, daily_spend} for the 28d window.

    The returned list is ordered oldest → newest, aligned to the tail of the
    daily-rows payload. Each `value` is NC ROAS for that day (units / units).
    """
    # Inline parse — the assembler runs transforms independently, so we can't
    # rely on having called window_dates first.
    windows_cfg = (config or {}).get("windows") or {}
    window_dates: dict[str, dict] = {}
    for key, spec in windows_cfg.items():
        start = dt.date.fromisoformat(spec["start"])
        end = dt.date.fromisoformat(spec["end"])
        window_dates[key] = {
            "start": start,
            "end": end,
            "n_days": (end - start).days + 1,
        }

    d28 = window_dates.get("28d")
    if not d28:
        return []

    # Need 3d + 7d to build tiers; if they're missing, fall back to a flat
    # per-day spend across the 28d window.
    has_tiers = "3d" in window_dates and "7d" in window_dates
    total_28d = _ov_spend_units(inputs.get("overview_28d"))
    flat_per_day = (total_28d / d28["n_days"]) if d28["n_days"] else 0.0

    tiers = _build_tiers(window_dates, inputs) if has_tiers else []

    daily_payload = inputs.get("daily") or {}
    all_rows = daily_payload.get("rows") or []
    # Take the tail matching the 28d window length so we align to end_date.
    rows = all_rows[-d28["n_days"]:] if d28["n_days"] else all_rows
    n_rows = len(rows)

    end_date = d28["end"]
    series: list[dict] = []
    for i, row in enumerate(rows):
        offset_from_end = (n_rows - 1) - i
        day = end_date - dt.timedelta(days=offset_from_end)
        nc_rev_day = float(row.get("total_new_customer_revenue") or 0) / 100
        spend_day = _daily_spend_for(day, tiers, flat_per_day) if tiers else flat_per_day
        nc_roas_day = (nc_rev_day / spend_day) if spend_day else 0.0
        series.append({
            "date": day.isoformat(),
            "value": round(nc_roas_day, 3),
            "nc_revenue": round(nc_rev_day, 2),
            "daily_spend": round(spend_day, 2),
        })
    return series
