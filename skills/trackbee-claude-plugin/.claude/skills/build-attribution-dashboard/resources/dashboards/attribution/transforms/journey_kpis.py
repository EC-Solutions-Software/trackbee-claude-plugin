"""Customer Journeys KPI tiles.

Reads the channel-interactions payload (saved as ``touchpoints.json``) and
returns the three envelope shares used as KPI tiles in the Customer Journeys
section: how many orders had exactly one tracked touch, two or more, or none.
"""

from __future__ import annotations


def transform(inputs: dict, config: dict) -> dict:
    del config
    touchpoints: dict = inputs.get("touchpoints") or {}

    single = float(touchpoints.get("single_touch_share") or 0.0)
    multi = float(touchpoints.get("multi_touch_share") or 0.0)
    organic = float(touchpoints.get("organic_share") or 0.0)

    return {
        "single_touch_share": single,
        "multi_touch_share": multi,
        "organic_share": organic,
    }
