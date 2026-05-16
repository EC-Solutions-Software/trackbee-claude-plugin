"""TrackBee Ad Performance — input loading + missing-data discovery.

Every transform calls one of these helpers to read its raw JSON. Shared
behaviour:

* Missing files → empty dict + a structured "issue" the orchestrator can
  surface to the viewer via the global error banner.
* Malformed files → empty dict + an issue with the parse error message.
* `_unwrap` handles both `{"result": {...}}` envelopes (what the skill
  writes) and bare payloads.

The whole module is intentionally tiny so it can be loaded as one
component file by the MCP without pulling extra dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _unwrap(data: Any) -> dict:
    """Accept `{"result": <payload>}` or `<payload>`; return the dict payload."""
    if not isinstance(data, dict):
        return {}
    if "result" in data and isinstance(data["result"], dict):
        return data["result"]
    return data


def load_json(inputs_dir: Path, filename: str, issues: list[dict]) -> dict:
    """Return the unwrapped payload from `<inputs_dir>/<filename>`.

    Issues are *appended* to the shared list — the caller decides whether
    a missing file is fatal or merely cosmetic for the section it owns.
    """
    p = inputs_dir / filename
    if not p.is_file():
        issues.append({
            "kind": "missing_file",
            "file": filename,
            "title": f"Input file not found: {filename}",
            "body": (f"The build step expected `{filename}` in the inputs folder but "
                     f"the file isn't there. This usually means the MCP tool that "
                     f"produces it wasn't called, or its response wasn't saved."),
            "fix": ("Re-run the Phase 1 / Phase 2 MCP calls listed in SKILL.md for "
                    "this store. If a single platform returned no data, that's "
                    "expected — write `{\"result\": {}}` to the file to silence "
                    "this notice."),
        })
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        issues.append({
            "kind": "parse_error",
            "file": filename,
            "title": f"Couldn't read {filename}",
            "body": f"The file exists but isn't valid JSON: {e}.",
            "fix": ("Delete the file and re-run the MCP tool that produces it, "
                    "or edit the file to fix the parse error."),
        })
        return {}
    return _unwrap(raw)


def load_thresholds(repo_root: Path) -> dict:
    """Read chrome/thresholds.json. Falls back to {} on failure — callers
    must validate the keys they need."""
    p = repo_root / "chrome" / "thresholds.json"
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    # Strip the description key so consumers iterate cleanly over numbers.
    return {k: v for k, v in raw.items() if not k.startswith("_")}
