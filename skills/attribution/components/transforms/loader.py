"""Tolerant input loader for the Attribution Overview build.

``load_json(inputs_dir, name)`` returns the inner ``result`` payload for a
staged tool dump, merged onto a sensible default skeleton so downstream
transforms can rely on standard keys existing. Tolerates three real-world
failure modes: file missing, result empty ``{}``, or file malformed — each
falls back to the default skeleton so the rest of the build still runs.

Self-contained — stdlib only.
"""

import json
from pathlib import Path

_DEFAULTS = {
    "daily": {"rows": []},
    "touchpoints": {"co_occurrence": {}, "transitions": {}, "total_journeys": 0,
                    "multi_touch_journeys": 0, "single_touch_share": 0,
                    "available_platforms": []},
    "funnel": {"current": {"funnel": []}, "previous": {"funnel": []}},
    "platform_funnel": {"platforms": {}},
    "meta": {"campaigns": [], "ad_accounts": []},
    "google": {"campaigns": [], "ad_accounts": []},
    "journey": {"paths": [], "available_platforms": []},
    "overview": {"platform_statistics": [], "ad_account_spend": 0},
}


def default_for(name):
    base = Path(name).stem
    if base.startswith("j_"):
        return dict(_DEFAULTS["journey"])
    if base.startswith("funnel"):
        return dict(_DEFAULTS["funnel"])
    if base.startswith("platform_funnel"):
        return dict(_DEFAULTS["platform_funnel"])
    if base.startswith("meta"):
        return dict(_DEFAULTS["meta"])
    if base.startswith("google"):
        return dict(_DEFAULTS["google"])
    if base.startswith(("pinterest_perf", "tiktok_perf")):
        return {"campaigns": []}
    if base.startswith("touchpoints"):
        return dict(_DEFAULTS["touchpoints"])
    if base.startswith("daily"):
        return dict(_DEFAULTS["daily"])
    if base.startswith("overview"):
        return dict(_DEFAULTS["overview"])
    return {}


def load_json(inputs_dir, name):
    path = Path(inputs_dir) / name
    if not path.exists():
        return default_for(name)
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return default_for(name)
    result = payload.get("result") if isinstance(payload, dict) else None
    if not result:
        return default_for(name)
    default = default_for(name)
    if isinstance(default, dict) and isinstance(result, dict):
        merged = dict(default)
        merged.update(result)
        # Recurse one level for funnel current/previous structure.
        if name.startswith("funnel") or "funnel" in (default.keys() & {"current", "previous"}):
            for k in ("current", "previous"):
                if k in default and isinstance(default[k], dict):
                    merged[k] = {**default[k], **(result.get(k) or {})}
        # Overview nests platform_statistics under result.overview — flatten
        # it up so the per-platform stat lookup always finds it.
        if name.startswith("overview"):
            nested_ov = result.get("overview")
            if isinstance(nested_ov, dict):
                for k, v in nested_ov.items():
                    if not merged.get(k):
                        merged[k] = v
        return merged
    return result
