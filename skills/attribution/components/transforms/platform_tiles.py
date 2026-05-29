"""Platform Overview tiles — Python data transform.

Reads raw inputs (get_dashboard_overview, get_meta_campaign_insights,
get_google_campaign_insights) and returns the payload that the view layer
reads via window.TB_DATA.windows.<key>.platforms.

Conventions:
  - Monetary values in overview's platform_statistics are store-currency CENTS.
    This transform converts to store-currency UNITS (cents / 100).
  - Impressions and clicks come from the platform's campaign-insights payload,
    NOT from overview (overview doesn't expose impressions).
  - Output is an insertion-ordered dict: Meta first, Google second, then any
    other platforms found in overview.platform_statistics. Downstream views
    iterate in this insertion order so the dashboard always shows Meta /
    Google first.
  - CTR is stored as a RATIO (clicks / impressions), not a percent — so the
    front-end fmt.pct helper (which multiplies by 100) produces the right
    string.
"""

from __future__ import annotations


# Visual identity per platform: stable label + brand color + logo key.
# The logo key is consumed by the front-end (chrome/brand or per-tile
# rendering) to pick an inline SVG; unknown platforms get a neutral
# fallback so the tile still renders.
_PLATFORM_VISUALS: dict[str, dict[str, str]] = {
    "meta":      {"label": "Meta",      "color": "#1877F2", "logo": "meta"},
    "google":    {"label": "Google",    "color": "#4285F4", "logo": "google"},
    "klaviyo":   {"label": "Klaviyo",   "color": "#000000", "logo": "klaviyo"},
    "tiktok":    {"label": "TikTok",    "color": "#000000", "logo": "tiktok"},
    "pinterest": {"label": "Pinterest", "color": "#E60023", "logo": "pinterest"},
}

# Conversion-provider strings as they appear in overview.platform_statistics,
# mapped to canonical lowercase platform keys.
_PROVIDER_TO_KEY: dict[str, str] = {
    "FACEBOOK":  "meta",
    "META":      "meta",
    "GOOGLE":    "google",
    "KLAVIYO":   "klaviyo",
    "TIKTOK":    "tiktok",
    "PINTEREST": "pinterest",
}


def _visuals_for(key: str) -> dict[str, str]:
    """Return label/color/logo for a platform key. Falls back to a neutral
    presentation when we haven't hard-coded the platform — the tile still
    renders, just without a brand colour.
    """
    if key in _PLATFORM_VISUALS:
        return _PLATFORM_VISUALS[key]
    # Title-case the key so an unknown provider like "snap" still shows
    # readably as "Snap" instead of "snap".
    return {"label": key.title(), "color": "#666666", "logo": key}


def _sum_int(rows: list[dict], field: str) -> int:
    """Sum an integer-like field across campaign rows. Missing/None → 0."""
    total = 0
    for row in rows:
        value = row.get(field)
        if value is not None:
            total += int(value)
    return total


def _sum_float(rows: list[dict], field: str) -> float:
    """Sum a float-like field across campaign rows. Missing/None → 0."""
    total = 0.0
    for row in rows:
        value = row.get(field)
        if value is not None:
            total += float(value)
    return total


def _platform_stat(overview: dict, provider_key: str) -> dict:
    """Return per-platform spend / revenue / clicks from overview.

    Overview values are in store-currency CENTS — we divide by 100 to convert
    to UNITS so downstream math matches the rest of the dashboard (which is
    unit-based).
    """
    provider_key = (provider_key or "").upper()
    for stat in (overview or {}).get("platform_statistics", []) or []:
        if (stat.get("conversion_provider") or "").upper() == provider_key:
            spend_units   = (stat.get("spend")   or 0) / 100
            revenue_units = (stat.get("revenue") or 0) / 100
            clicks        = int(stat.get("clicks") or 0)
            return {"spend": spend_units, "revenue": revenue_units, "clicks": clicks}
    return {"spend": 0.0, "revenue": 0.0, "clicks": 0}


def _build_tile(
    key: str,
    overview: dict,
    provider_string: str,
    campaign_rows: list[dict],
    purchases_field: str,
) -> dict:
    """Compose one platform tile from overview totals + campaign insights.

    - Spend / revenue come from overview.platform_statistics (server-side
      FX-converted into store currency).
    - Impressions / clicks come from the campaign-insights payload, because
      overview doesn't expose those.
    - Purchases come from the platform-specific field name (Meta uses
      `purchases`, Google uses `conversions`).
    """
    visuals = _visuals_for(key)
    ov_stat = _platform_stat(overview, provider_string)

    impressions = _sum_int(campaign_rows, "impressions")
    clicks_from_campaigns = _sum_int(campaign_rows, "clicks")
    # Clicks: prefer the campaign-insights total (matches what users see in
    # the platform UI). Fall back to overview only when campaign data is
    # missing entirely.
    clicks = clicks_from_campaigns or ov_stat["clicks"]

    purchases_raw = _sum_float(campaign_rows, purchases_field)
    purchases = round(purchases_raw)

    spend = ov_stat["spend"]
    revenue = ov_stat["revenue"]

    return {
        "label":       visuals["label"],
        "color":       visuals["color"],
        "logo":        visuals["logo"],
        "spend":       spend,
        "revenue":     revenue,
        "roas":        (revenue / spend)             if spend       else 0.0,
        "ctr":         (clicks / impressions)        if impressions else 0.0,
        "cpc":         (spend / clicks)              if clicks      else 0.0,
        "cpm":         (spend / impressions * 1000)  if impressions else 0.0,
        "impressions": impressions,
        "clicks":      clicks,
        "purchases":   purchases,
    }


def _build_other_tile(key: str, overview: dict, provider_string: str) -> dict:
    """Compose a tile for a platform that has no campaign-insights input.

    Without campaign insights, impressions and clicks aren't available. We
    show spend / revenue / ROAS from overview and leave the other fields
    at zero — the view renders them as zeros (or `—` for blanks) without
    crashing.
    """
    visuals = _visuals_for(key)
    ov_stat = _platform_stat(overview, provider_string)
    spend = ov_stat["spend"]
    revenue = ov_stat["revenue"]
    clicks = ov_stat["clicks"]
    return {
        "label":       visuals["label"],
        "color":       visuals["color"],
        "logo":        visuals["logo"],
        "spend":       spend,
        "revenue":     revenue,
        "roas":        (revenue / spend) if spend else 0.0,
        "ctr":         0.0,
        "cpc":         (spend / clicks) if clicks else 0.0,
        "cpm":         0.0,
        "impressions": 0,
        "clicks":      clicks,
        "purchases":   0,
    }


def transform(inputs: dict, config: dict) -> dict:
    """Return an insertion-ordered dict of platform-key → tile dict.

    Args:
        inputs: ``{"overview": <ov>, "meta": <m>, "google": <g>}``.
                Each value may be the unwrapped input payload or missing
                entirely (we treat missing as empty).
        config: dashboard config (currently unused by this transform but
                kept in the signature so all transforms share one shape).
    """
    del config  # not used yet — kept for transform-signature parity

    overview: dict = inputs.get("overview") or {}
    meta:     dict = inputs.get("meta")     or {}
    google:   dict = inputs.get("google")   or {}

    meta_rows:   list[dict] = meta.get("campaigns")   or []
    google_rows: list[dict] = google.get("campaigns") or []

    tiles: dict[str, dict] = {}

    # Meta first, then Google — these are the platforms with full campaign
    # insights, so they always render even when overview's platform_statistics
    # is empty.
    tiles["meta"] = _build_tile(
        key="meta",
        overview=overview,
        provider_string="FACEBOOK",
        campaign_rows=meta_rows,
        purchases_field="purchases",
    )
    tiles["google"] = _build_tile(
        key="google",
        overview=overview,
        provider_string="GOOGLE",
        campaign_rows=google_rows,
        purchases_field="conversions",
    )

    # Any extra platforms in overview's platform_statistics get appended in
    # the order overview lists them. This keeps Klaviyo / TikTok / Pinterest
    # discoverable without hard-coding them as required inputs.
    for stat in overview.get("platform_statistics", []) or []:
        provider = (stat.get("conversion_provider") or "").upper()
        key = _PROVIDER_TO_KEY.get(provider, provider.lower())
        if not key or key in tiles:
            continue
        tiles[key] = _build_other_tile(key=key, overview=overview, provider_string=provider)

    return tiles
