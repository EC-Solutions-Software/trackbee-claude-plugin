"""Channel Attribution rows — Python data transform.

Builds the table that compares TrackBee's first-party attribution against
in-platform reported numbers for every channel the store has data for, plus
an "Overall" summary row.

Inputs (already-unwrapped payloads):
    overview         — get_dashboard_overview (authoritative spend/revenue;
                       per-platform tile data in platform_statistics[]).
    platform_funnel  — get_platform_funnel_breakdown (TrackBee first-party
                       sessions, orders, revenue per channel).
    meta             — get_meta_campaign_insights (in-platform purchase counts).
    google           — get_google_campaign_insights (in-platform conversion counts).

Output: {"rows": [...]} where rows ends with the Overall row. Each row:
    channel, logo, sessions, purch_tb, purch_in, rev_tb, rev_in,
    spend, cpa, roas.
"""

from __future__ import annotations


# Maps platform_funnel keys -> (label, logo, has_in_platform_data)
# If has_in_platform_data is False the channel is treated as "earned" — no
# spend, no in-platform purchase / revenue numbers, just first-party totals.
CHANNEL_DEFS: dict[str, tuple[str, str, bool]] = {
    "facebook":  ("Meta",          "meta",      True),
    "google":    ("Google",        "google",    True),
    "klaviyo":   ("Klaviyo",       "klaviyo",   False),
    "tiktok":    ("TikTok",        "tiktok",    False),
    "pinterest": ("Pinterest",     "pinterest", False),
    "microsoft": ("Microsoft Ads", "microsoft", False),
    "calendly":  ("Calendly",      "calendly",  False),
    "email":     ("Email",         "klaviyo",   False),
}


def _step_count(funnel_obj: dict, step: str) -> int:
    """Pull a step count out of a funnel array, treating missing as zero."""
    for entry in funnel_obj.get("funnel", []) or []:
        if entry.get("step") == step:
            value = entry.get("count")
            return int(value) if value is not None else 0
    return 0


def _platform_stat(overview: dict, provider_key: str) -> dict:
    """Find a row in overview.platform_statistics by conversion_provider.

    Returns spend / revenue in store-currency units (overview reports cents).
    """
    provider_key = (provider_key or "").upper()
    for stat in (overview or {}).get("platform_statistics", []) or []:
        if (stat.get("conversion_provider") or "").upper() == provider_key:
            return {
                "spend": (stat.get("spend") or 0) / 100,
                "revenue": (stat.get("revenue") or 0) / 100,
            }
    return {"spend": 0, "revenue": 0}


def _sum_field(rows: list[dict], field: str) -> float:
    total = 0.0
    for row in rows or []:
        value = row.get(field)
        if value is not None:
            total += float(value)
    return total


def transform(inputs: dict, config: dict) -> dict:
    del config  # not used; signature kept for assembler symmetry

    overview        = inputs.get("overview") or {}
    platform_funnel = inputs.get("platform_funnel") or {}
    meta            = inputs.get("meta") or {"campaigns": []}
    google          = inputs.get("google") or {"campaigns": []}

    pf = (platform_funnel.get("platforms") or {})

    # In-platform spend / revenue come from overview.platform_statistics (the
    # FX-converted source the rest of the dashboard already uses).
    meta_ov   = _platform_stat(overview, "FACEBOOK")
    google_ov = _platform_stat(overview, "GOOGLE")

    # In-platform purchase counts and impressions/clicks come from the
    # campaign-insights payloads — those are the only place those numbers
    # exist per channel.
    meta_purchases   = int(_sum_field(meta.get("campaigns") or [],   "purchases"))
    google_conv      = _sum_field(google.get("campaigns") or [], "conversions")

    # Per-row builder. CPA / ROAS use in-platform numbers so the values match
    # the Platform Overview tiles (e.g. Meta ROAS reads the same on both).
    def ch_row(label: str, key: str, logo: str | None,
               plat_purchases, plat_revenue, spend: float) -> dict:
        funnel = pf.get(key, {})
        sessions = _step_count(funnel, "page_view_events")
        purch_tb = _step_count(funnel, "orders")
        rev_tb = (funnel.get("revenue") or 0) / 100
        cpa  = (spend / plat_purchases) if (spend and plat_purchases) else None
        roas = (plat_revenue / spend)   if (spend and plat_revenue)   else None
        return {
            "channel": label,
            "logo": logo,
            "sessions": sessions,
            "purch_tb": purch_tb,
            "purch_in": plat_purchases,
            "rev_tb": rev_tb,
            "rev_in": plat_revenue,
            "spend": spend,
            "cpa": cpa,
            "roas": roas,
        }

    rows: list[dict] = []
    for plat_key in pf.keys():
        if plat_key in CHANNEL_DEFS:
            label, logo, has_data = CHANNEL_DEFS[plat_key]
            if plat_key == "facebook":
                rows.append(ch_row(label, plat_key, logo,
                                   meta_purchases, meta_ov["revenue"], meta_ov["spend"]))
            elif plat_key == "google":
                rows.append(ch_row(label, plat_key, logo,
                                   round(google_conv), google_ov["revenue"], google_ov["spend"]))
            elif has_data:
                # No campaign-insights wired for this platform yet.
                rows.append(ch_row(label, plat_key, logo, None, None, 0))
            else:
                rows.append(ch_row(label, plat_key, logo, None, None, 0))
        else:
            # Unknown platform — render with title-case label, no logo.
            rows.append(ch_row(plat_key.replace("_", " ").title(), plat_key,
                               None, None, None, 0))

    overall = {
        "channel": "Overall",
        "logo": None,
        "sessions": sum(r["sessions"] for r in rows),
        "purch_tb": sum(r["purch_tb"] for r in rows),
        "purch_in": meta_purchases + round(google_conv),
        "rev_tb":   sum(r["rev_tb"] for r in rows),
        "rev_in":   meta_ov["revenue"] + google_ov["revenue"],
        "spend":    sum(r["spend"] for r in rows),
    }
    overall["cpa"]  = (overall["spend"] / overall["purch_in"]) if (overall["spend"] and overall["purch_in"]) else None
    overall["roas"] = (overall["rev_in"]  / overall["spend"])  if (overall["spend"] and overall["rev_in"])   else None
    rows.append(overall)

    return {"rows": rows}
