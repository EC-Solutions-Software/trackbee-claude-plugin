"""Creatives Report — next-question generator.

After surfacing the data, what could the user ask the assistant next?
Returns up to 3 neutral question cards, each with the question text plus
a "why this matters" note built from the actual numbers. The cards state
measured figures and pose open questions — they do not prescribe actions
or score the ads."""

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
short = _H.short
fmt_money = _H.fmt_money
fmt_float = _H.fmt_float
fmt_pct = _H.fmt_pct


def questions(store: dict) -> list[dict]:
    ads = [a for a in (store.get("ads") or []) if a["spend"] > 0]
    sym = store.get("sym") or ""
    out: list[dict] = []

    # Highest-spend ad with a defined ROAS below 1.0 (spent real money,
    # returned less than it cost this window). Stated as a figure, not a verdict.
    low_roas = [a for a in ads if a.get("roas") is not None and a["roas"] < 1.0]
    if low_roas:
        a = max(low_roas, key=lambda x: x["spend"])
        out.append({
            "q":  (f"What's behind {short(a['ad_name'], 44)}'s "
                   f"{fmt_float(a['roas'], 2)}× ROAS this week?"),
            "why": (f"This {a['format']} ad spent {fmt_money(a['spend'], sym)} "
                    f"at {fmt_float(a['roas'], 2)}× ROAS and "
                    f"{fmt_pct(a['ctr'])} CTR. You can compare its CTR and "
                    f"CPA against your other {a['format']} ads to see how it "
                    f"sits in the set."),
        })

    # Highest Meta frequency this window (impressions ÷ reach per person).
    freq_ads = [a for a in ads
                if a["platform"] == "meta" and a.get("frequency") is not None]
    if freq_ads:
        a = max(freq_ads, key=lambda x: x["frequency"])
        if a["frequency"] >= 2.5:
            out.append({
                "q":  (f"How is {short(a['ad_name'], 44)}'s performance "
                       f"changing as its frequency rises?"),
                "why": (f"Frequency is {fmt_float(a['frequency'], 1)}× on "
                        f"{fmt_money(a['spend'], sym)} of spend at "
                        f"{fmt_float(a['roas'], 2)}× ROAS this week. You can "
                        f"track CTR and CPA against frequency over the coming "
                        f"days to see how they move together."),
            })

    # Ad with the lowest new-customer share (mostly existing customers).
    nc_ads = [a for a in ads
              if a.get("nc") is not None and (a.get("purchases") or 0) > 0]
    if nc_ads:
        a = min(nc_ads, key=lambda x: x["nc"] / x["purchases"])
        nc_share = a["nc"] / a["purchases"]
        if nc_share < 0.10:
            out.append({
                "q":  (f"How much of {short(a['ad_name'], 44)}'s volume is "
                       f"new versus returning customers?"),
                "why": (f"New customers were {fmt_pct(nc_share * 100, 0)} of "
                        f"this ad's {int(a['purchases'])} purchases this week "
                        f"({int(a['nc'])} new). You can compare its "
                        f"new-customer share against your other ads."),
            })

    return out[:3]
