"""Creatives Report — next-question generator.

After surfacing the data, what should the user ask the assistant
next? Returns up to 3 question cards, each with the question text plus
a "why this matters" rationale built from the actual numbers."""

from __future__ import annotations

import importlib.util
from collections import Counter
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
short = _H.short
fmt_money = _H.fmt_money
fmt_float = _H.fmt_float
fmt_pct = _H.fmt_pct


def questions(store: dict) -> list[dict]:
    ads = [a for a in (store.get("ads") or []) if a["spend"] > 0]
    sym = store.get("sym") or ""
    out: list[dict] = []

    kills = [a for a in ads if a["status_tag"] == "KILL"]
    if kills:
        a = max(kills, key=lambda x: x["spend"])
        out.append({
            "q":  (f"Why is {short(a['ad_name'], 44)} under-performing — "
                   f"is it the creative, the audience, or the offer?"),
            "why": (f"{a['format']} ad spent {fmt_money(a['spend'], sym)} "
                    f"this week at {fmt_float(a['roas'], 2)}× ROAS. "
                    f"Compare CTR ({fmt_pct(a['ctr'])}) to your other "
                    f"{a['format']} ads, check audience overlap, and "
                    f"test a fresh angle before pausing."),
        })

    scales = [a for a in ads if a["status_tag"] == "SCALE"]
    if scales:
        by_fmt: Counter = Counter(a["format"] for a in scales)
        top_fmt, _n = by_fmt.most_common(1)[0]
        top_scale = max([a for a in scales if a["format"] == top_fmt],
                        key=lambda a: a["spend"])
        out.append({
            "q":  (f"How much budget can {top_fmt} carry across your "
                   f"account before frequency saturates?"),
            "why": (f"{len(scales)} SCALE-tagged ad"
                    f"{'s' if len(scales) != 1 else ''} this week — top: "
                    f"{short(top_scale['ad_name'], 38)} at "
                    f"{fmt_float(top_scale['roas'], 2)}× ROAS. Increase "
                    f"{top_fmt} budget 20–30% across the SCALE set and "
                    f"monitor frequency, CPM, and new-customer share "
                    f"over 48 hours."),
        })

    refresh = [a for a in ads if a["status_tag"] == "REFRESH"]
    if len(refresh) >= 2:
        out.append({
            "q":  ("Which creative angle should the next production "
                   "batch focus on?"),
            "why": (f"{len(refresh)} ads tagged REFRESH this week — "
                    f"frequency or net-new-reach signals are firing. "
                    f"Review the SCALE-tagged ads above to seed angles "
                    f"for the next round, then schedule launches in "
                    f"waves rather than all at once."),
        })

    rt_only = [a for a in ads if "retargeting only" in a["tags"]]
    if rt_only:
        a = max(rt_only, key=lambda x: x["spend"])
        out.append({
            "q":  (f"Is {short(a['ad_name'], 44)} still useful as a "
                   f"retargeting ad, or should we cap its budget?"),
            "why": (f"New-customer share is below 10% — this ad is "
                    f"running mostly on existing customers this week. "
                    f"Capping budget and shifting it to "
                    f"acquisition-focused creatives may improve blended "
                    f"new-customer ROAS."),
        })

    return out[:3]
