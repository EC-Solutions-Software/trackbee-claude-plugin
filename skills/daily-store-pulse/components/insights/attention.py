"""Needs-attention list for a store's pulse card.

Merges yesterday's anomalies (detect_anomalies) and Meta's recommendations
(get_meta_recommendations) into a single ranked list, each with a plain-English
"so what". Anomalies outrank recommendations — a revenue drop is more urgent
than a creative-consolidation suggestion. Empty list → the card shows
"Nothing flagged today."

Both source shapes are read defensively across documented candidate key names,
so a minor shape difference yields fewer items rather than a crash.
"""

from __future__ import annotations

# ---- anomalies --------------------------------------------------------------

_ANOM_LIST_KEYS = ("anomalies", "rows", "data", "results", "items")
_CATEGORY_KEYS = ("category", "metric", "type", "kind")
_DATE_KEYS = ("date", "day", "statistic_date", "ds")
_SEVERITY_KEYS = ("severity", "z_score", "zscore", "sigma", "deviation", "score")
_DIRECTION_KEYS = ("direction", "change", "trend")
_DESC_KEYS = ("description", "message", "summary", "explanation", "note")

_CATEGORY_LABEL = {
    "revenue": "Revenue anomaly",
    "orders": "Orders anomaly",
    "funnel": "Funnel anomaly",
    "tracking_health": "Tracking health",
    "tracking": "Tracking health",
}

_CATEGORY_SOWHAT = {
    "revenue": "Yesterday's revenue broke from its 14-day baseline. Confirm it's real before acting — check the day's orders and whether any campaigns changed.",
    "orders": "Order volume moved sharply against its 14-day baseline. Cross-check the funnel and any campaign or site changes from yesterday.",
    "funnel": "A step-to-step conversion rate shifted unusually. A drop points at a site or tracking issue between add-to-cart and checkout.",
    "tracking_health": "A platform's event-delivery failure rate spiked. TrackBee handles server-side tracking independently — if it persists, contact TrackBee support.",
}


def _first(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def _anom_list(payload):
    if not isinstance(payload, dict):
        return []
    for k in _ANOM_LIST_KEYS:
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []


def _severity_bucket(item):
    """Map an anomaly to high / medium / low. The list arrives sorted by
    severity (most extreme first), so position is a fallback signal."""
    raw = _first(item, _SEVERITY_KEYS)
    try:
        mag = abs(float(raw))
        # z-score / sigma style: >=3 extreme, >=2 moderate.
        if mag >= 3:
            return "high"
        if mag >= 2:
            return "medium"
        return "low"
    except (TypeError, ValueError):
        sev = str(raw or "").lower()
        if sev in ("high", "critical", "severe"):
            return "high"
        if sev in ("medium", "moderate", "warning"):
            return "medium"
        if sev in ("low", "minor"):
            return "low"
    return None


def _from_anomalies(payload):
    items = []
    rows = _anom_list(payload)
    for idx, a in enumerate(rows):
        if not isinstance(a, dict):
            continue
        cat_raw = str(_first(a, _CATEGORY_KEYS, "")).lower()
        label = _CATEGORY_LABEL.get(cat_raw, "Anomaly")
        date = _first(a, _DATE_KEYS)
        direction = str(_first(a, _DIRECTION_KEYS, "")).lower()
        title = label
        if direction in ("drop", "down", "decrease", "negative"):
            title = label + " · drop"
        elif direction in ("spike", "up", "increase", "positive"):
            title = label + " · spike"
        if date:
            title += f" ({date})"
        sev = _severity_bucket(a)
        if sev is None:
            # No usable severity field — first few are most extreme.
            sev = "high" if idx == 0 else "medium" if idx < 3 else "low"
        sowhat = _first(a, _DESC_KEYS) or _CATEGORY_SOWHAT.get(cat_raw) or \
            "Flagged against the 14-day baseline. Verify the day before acting."
        items.append({
            "sev": sev, "title": title, "sowhat": sowhat,
            "rank": {"high": 0, "medium": 1, "low": 2}[sev],
        })
    return items


# ---- meta recommendations ---------------------------------------------------

_REC_LIST_KEYS = ("recommendations", "rows", "data", "results", "items")
_REC_TYPE_KEYS = ("type", "recommendation_type", "title", "name")
_REC_DESC_KEYS = ("body", "description", "message", "summary", "recommendation")
_REC_LIFT_KEYS = ("opportunity_score_lift", "score_lift", "lift", "opportunity_score")
_REC_LIFT_ESTIMATE_KEYS = ("lift_estimate", "estimated_lift", "expected_lift")
_REC_TRACKBEE_NOTE_KEYS = ("trackbee_note", "trackbeeNote")

# Meta surfaces a steady stream of cosmetic auto-enhancement nudges (add music,
# A+ visual touch-ups, flexible media). They're not "needs attention today", so
# they're dropped from the pulse entirely.
_REC_SKIP_TYPES = {
    "MUSIC", "APLUSC_STANDARD_ENHANCEMENTS_BUNDLE", "STANDARD_ENHANCEMENTS",
    "FLEXIBLE_MEDIA", "IMAGE_ANIMATION", "ADD_OVERLAYS", "PROFILE_TILE",
    "TEXT_IMPROVEMENTS", "STORE_VISITS",
}
# Recs that genuinely affect spend efficiency — surfaced at medium severity.
_REC_ELEVATE_TYPES = {
    "CREATIVE_LIMITED", "CREATIVE_FATIGUE", "LOW_OUTCOMES",
    "UNDERPERFORMING", "BUDGET", "BID",
}
# Human labels for the types we keep; anything else is title-cased generically.
_REC_TYPE_LABEL = {
    "CREATIVE_LIMITED": "Creative-limited ads",
    "CREATIVE_FATIGUE": "Creative fatigue",
    "FRAGMENTATION": "Ad-set auction overlap",
}


def _rec_list(payload):
    if not isinstance(payload, dict):
        return []
    for k in _REC_LIST_KEYS:
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []


def _humanize_type(t):
    return str(t or "").replace("_", " ").strip().capitalize() or "Meta recommendation"


def _lift(r):
    for k in _REC_LIFT_KEYS:
        if k in r and r[k] is not None:
            try:
                return float(r[k])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _from_meta(payload, cap=2):
    """Group Meta recs by type (collapsing the many per-ad-set duplicates), drop
    cosmetic nudges, and emit at most ``cap`` items. Only spend-efficiency recs
    (creative-limited, fatigue, …) carry medium severity; everything else is
    low-severity, informational."""
    recs = [r for r in _rec_list(payload) if isinstance(r, dict)]

    grouped = {}
    for r in recs:
        rtype = str(_first(r, _REC_TYPE_KEYS, "")).upper()
        if not rtype or rtype in _REC_SKIP_TYPES:
            continue
        g = grouped.setdefault(rtype, {"count": 0, "lift": 0.0, "sample": r})
        g["count"] += 1
        g["lift"] = max(g["lift"], _lift(r))

    ordered = sorted(grouped.items(), key=lambda kv: kv[1]["lift"], reverse=True)

    items = []
    for rtype, g in ordered[:cap]:
        sample = g["sample"]
        tb_note = _first(sample, _REC_TRACKBEE_NOTE_KEYS)
        label = _REC_TYPE_LABEL.get(rtype, _humanize_type(rtype))
        count = g["count"]
        title = "Meta: " + label + (f" ({count} ad sets)" if count > 1 else "")

        if tb_note:
            # Tracking-flavoured recs are usually false positives — defuse them,
            # never present them as "your tracking is broken".
            items.append({
                "sev": "low", "rank": 3,
                "title": title,
                "sowhat": ("Meta flags a tracking/pixel item here. TrackBee already "
                           "handles server-side tracking, so this is typically a false "
                           "positive — no action needed unless support says otherwise."),
            })
            continue

        sowhat = _first(sample, _REC_DESC_KEYS) or "Meta flagged an optimization opportunity."
        est = _first(sample, _REC_LIFT_ESTIMATE_KEYS)
        if est:
            sowhat = f"{sowhat} Meta estimates {est}."
        sev = "medium" if rtype in _REC_ELEVATE_TYPES else "low"
        items.append({"sev": sev, "rank": 1.5 if sev == "medium" else 2.5,
                       "title": title, "sowhat": sowhat})
    return items


def build(summary, limit=5):
    items = _from_anomalies(summary.get("anomalies"))
    items += _from_meta(summary.get("meta_recs"))
    items.sort(key=lambda i: i["rank"])
    items = items[:limit]
    high = sum(1 for i in items if i["sev"] == "high")
    medium = sum(1 for i in items if i["sev"] == "medium")
    return {"items": items, "high": high, "medium": medium, "total": len(items)}
