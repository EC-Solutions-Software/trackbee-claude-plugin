"""Creatives Report — production recommendations.

Take a store's processed ads (plus the product × format grid) and
return prioritised recommendation cards:

  P1 — Replace fatigued KILL-tagged ads
  P2 — Double down on winning product × format combos
  P3 — Fill gaps where formats win for other products but are missing
       here
  P4 — Theme insights from keywords in SCALE-tagged ad names
  P5 — Stop the bleed (single ad eating ≥ 15% of spend with KILL tag)

Each item is a dict ``{priority, kind, headline, body}`` ready for the
orchestrator to render."""

from __future__ import annotations

import importlib.util
import re
from collections import Counter
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"
_TRANSFORMS = _HERE.parent / "transforms"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_H = _load("format_helpers", _CHROME / "format_helpers.py")
_PFG = _load("product_format_grid", _TRANSFORMS / "product_format_grid.py")

html_escape = _H.html_escape
short = _H.short
fmt_money = _H.fmt_money
fmt_float = _H.fmt_float


STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "with", "of", "to", "in",
    "is", "on", "v1", "v2", "v3", "v4", "v5", "ad", "ads", "copy",
    "test", "new", "main", "fb", "ig", "reels", "story", "stories",
    "feed", "facebook", "instagram", "google", "broad", "cold",
    "retarget", "lookalike",
}


def recommendations(store: dict, n_days: int) -> list[dict]:
    ads = store.get("ads") or []
    sym = store.get("sym") or ""
    spending = [a for a in ads if a["spend"] > 0]
    if not spending:
        return [{
            "priority": 1, "kind": "info",
            "headline": "No spending ads in this window",
            "body": ("<p>Either no ads have run in the audit window "
                     "or all spending campaigns were explicitly "
                     "excluded from scope.</p>"),
        }]

    recs: list[dict] = []
    kill = [a for a in spending if a["status_tag"] == "KILL"]
    kill.sort(key=lambda a: -a["spend"])

    # P1 — Replace fatigued
    if kill:
        items = []
        for a in kill[:3]:
            items.append(
                f'<strong>{html_escape(short(a["ad_name"], 44))}</strong> '
                f'({html_escape(a["format"])}, {html_escape(a["product"])}) — '
                f'{fmt_money(a["spend"], sym)} at {fmt_float(a["roas"], 2)}× ROAS. '
                f'{html_escape(a["reason"])}'
            )
        recs.append({
            "priority": 1, "kind": "replace",
            "headline": (
                f"Replace these {min(len(kill), 3)} fatigued "
                f"ad{'s' if len(kill) != 1 else ''} first"
            ),
            "body": "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>",
        })

    # P2 — Double down — product × format combos with ROAS ≥ 2 and N ≥ 3
    grid = _PFG.grid(spending)
    double_down: list[tuple[str, dict]] = []
    for product, rows in grid.items():
        if product == "Uncategorised":
            continue
        for r in rows:
            if r["insufficient"]:
                continue
            roas = r.get("median_roas") or 0
            if roas >= 2.0 and r["total_spend"] >= 200 and r["n"] >= 3:
                double_down.append((product, r))
    double_down.sort(key=lambda x: -(x[1].get("median_roas") or 0))
    if double_down:
        items = []
        for product, r in double_down[:3]:
            items.append(
                f'<strong>{html_escape(r["format"])} for {html_escape(product)}</strong> — '
                f'{fmt_float(r["median_roas"], 2)}× median ROAS across {r["n"]} '
                f'ad{"s" if r["n"] != 1 else ""} on '
                f'{fmt_money(r["total_spend"], sym)} spend. Produce more '
                f'variants in this lane.'
            )
        recs.append({
            "priority": 2, "kind": "double",
            "headline": "Double down on what's winning",
            "body": "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>",
        })

    # P3 — Fill gaps
    strong_formats: Counter = Counter()
    formats_per_product: dict[str, dict] = {}
    for product, rows in grid.items():
        if product == "Uncategorised":
            continue
        present = {r["format"]: r for r in rows if not r["insufficient"]}
        formats_per_product[product] = present
        for fmt, r in present.items():
            if r.get("median_roas") and r["median_roas"] >= 2.0:
                strong_formats[fmt] += 1
    winning_formats = [f for f, c in strong_formats.items() if c >= 2]
    gaps: list[tuple[str, str]] = []
    for product, present in formats_per_product.items():
        for fmt in winning_formats:
            if fmt not in present:
                gaps.append((product, fmt))
    if gaps:
        items = []
        for product, fmt in gaps[:3]:
            items.append(
                f'No <strong>{html_escape(fmt)}</strong> ads for '
                f'<strong>{html_escape(product)}</strong>. This format '
                f'delivers ≥ 2× ROAS for other products in this account '
                f'— worth testing.'
            )
        recs.append({
            "priority": 3, "kind": "gap",
            "headline": "Test missing winning formats",
            "body": "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>",
        })

    # P4 — Theme insights from SCALE-tagged ad names
    scale_ads = [a for a in spending if a["status_tag"] == "SCALE"]
    if len(scale_ads) >= 3:
        words: Counter = Counter()
        for a in scale_ads:
            toks = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", (a["ad_name"] or "").lower())
            for t in toks:
                if t in STOP_WORDS:
                    continue
                words[t] += 1
        top = [(w, c) for w, c in words.most_common(6) if c >= 2]
        if top:
            kws = ", ".join(f'"{html_escape(w)}" ({c})' for w, c in top[:4])
            recs.append({
                "priority": 4, "kind": "theme",
                "headline": "Recurring themes in your top performers",
                "body": (f"<p>Common tokens across SCALE-tagged ads: {kws}. "
                         f"Consider doubling down on these creative angles "
                         f"in new variants.</p>"),
            })

    # P5 — Stop the bleed
    total_spend = sum(a["spend"] for a in spending) or 1.0
    bleed = []
    for a in kill:
        share = a["spend"] / total_spend
        if share >= 0.15:
            daily = a["spend"] / max(n_days, 1)
            bleed.append((a, share, daily))
    if bleed:
        items = []
        for a, share, daily in bleed:
            items.append(
                f'<strong>{html_escape(short(a["ad_name"], 44))}</strong> consumes '
                f'{share*100:.0f}% of account spend ({fmt_money(a["spend"], sym)}, '
                f'~{fmt_money(daily, sym)}/day) at {fmt_float(a["roas"], 2)}× ROAS — '
                f'pausing today saves ~{fmt_money(daily, sym)} per day.'
            )
        recs.append({
            "priority": 5, "kind": "bleed",
            "headline": "Stop the bleed",
            "body": "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>",
        })

    if not recs:
        recs.append({
            "priority": 1, "kind": "info",
            "headline": "All creatives are performing within healthy ranges",
            "body": ("<p>No fatigue triggers fired in this window. Keep "
                     "monitoring frequency and CTR weekly, and prepare "
                     "next-generation variants of your current "
                     "winners.</p>"),
        })

    recs.sort(key=lambda r: r["priority"])
    return recs
