"""Config loader for the Ad Performance build.

Reads `config.json` from the inputs directory and parses the window block
into a `(stores, window, n_days)` triple. The fields are validated up
front so any missing key crashes with a plain-language explanation
instead of a deep TypeError later in the pipeline.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


_REQUIRED_TOP = ("stores", "window")
_REQUIRED_WINDOW = ("start", "end")
_REQUIRED_STORE = ("id", "name", "currency", "currency_symbol")


def load_config(inputs_dir: Path) -> tuple[list[dict], dict, int]:
    """Load and validate `config.json`. Returns (stores, window, n_days)."""
    path = inputs_dir / "config.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Stage the dashboard config as `config.json` "
            "inside the inputs directory before running the build."
        )

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} is not valid JSON: {exc}. Re-stage it and try again."
        ) from exc

    missing = [k for k in _REQUIRED_TOP if not cfg.get(k)]
    if missing:
        raise ValueError(
            f"{path} is missing required field(s): {', '.join(missing)}. "
            "Need `stores` (list) and `window` (start + end ISO dates)."
        )

    window = cfg["window"]
    win_missing = [k for k in _REQUIRED_WINDOW if not window.get(k)]
    if win_missing:
        raise ValueError(
            f"config.window is incomplete: missing {', '.join(win_missing)}. "
            "Both `start` and `end` must be ISO YYYY-MM-DD strings, inclusive."
        )

    try:
        w_start = dt.date.fromisoformat(window["start"])
        w_end = dt.date.fromisoformat(window["end"])
    except ValueError as exc:
        raise ValueError(
            f"config.window dates are not ISO YYYY-MM-DD: {exc}."
        ) from exc

    stores = cfg["stores"]
    if not isinstance(stores, list) or not stores:
        raise ValueError(
            "config.stores must be a non-empty list of store config dicts."
        )

    for i, sc in enumerate(stores):
        store_missing = [k for k in _REQUIRED_STORE if not sc.get(k)]
        if store_missing:
            raise ValueError(
                f"config.stores[{i}] is missing required field(s): "
                f"{', '.join(store_missing)}. Each store needs id, name, "
                "currency (ISO code), and currency_symbol."
            )

    n_days = (w_end - w_start).days + 1
    return stores, window, n_days


def load_json(inputs_dir: Path, name: str) -> dict:
    """Read `<name>` from the inputs directory and unwrap `{result: ...}`.

    Missing or malformed files return an empty dict so downstream
    transforms degrade to em-dashes instead of crashing.
    """
    p = inputs_dir / name
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, dict):
        inner = data.get("result")
        if isinstance(inner, dict):
            return inner
        return data
    return {}
