"""Verdicts — the one-glance answer the pulse exists to deliver.

Per store: On track / Watch / Act now, plus a one-sentence why. Portfolio: a
combined read across every store and the list of who needs attention.

The verdict is deliberately conservative about red: daily numbers are noisy, so
a single soft dip reads as "Watch", not "Act now". "Act now" is reserved for a
high-severity anomaly or a material collapse (revenue or efficiency falling hard
against a normal day).
"""

from __future__ import annotations

import html
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FH = _load("format_helpers", _CHROME / "format_helpers.py")
_pct = _FH.pct_change


def _deltas(summary, days):
    y = summary.get("yday") or {}
    b = summary.get("base") or {}
    b_rev_day = (b.get("revenue") / days) if b.get("revenue") is not None else None
    return {
        "rev":  _pct(y.get("revenue"), b_rev_day),
        "mer":  _pct(y.get("mer"), b.get("mer")),
        "roas": _pct(y.get("roas"), b.get("roas")),
        "cac":  _pct(y.get("cac"), b.get("cac")),
    }


def build_store(summary, attention, baseline_days):
    days = baseline_days or 7
    y = summary.get("yday") or {}
    d = _deltas(summary, days)

    # No usable data for yesterday — newly connected, or tracking not live yet.
    if not summary.get("has_overview") or (
        y.get("revenue") is None and y.get("orders") is None
    ):
        return {
            "class": "watch", "label": "Watch",
            "why": "No data for yesterday yet — newly connected, or a day with nothing recorded.",
        }

    rev = d["rev"]
    mer = d["mer"]
    roas = d["roas"]
    cac = d["cac"]
    high = attention.get("high", 0)
    medium = attention.get("medium", 0)

    # ---- Act now ----
    act_reasons = []
    if high:
        act_reasons.append("a high-severity anomaly is flagged")
    if rev is not None and rev <= -35:
        act_reasons.append(f"revenue fell {_FH.signed_pct(rev)} against a normal day")
    if mer is not None and mer <= -30:
        act_reasons.append(f"MER dropped {_FH.signed_pct(mer)}")
    elif roas is not None and roas <= -30:
        act_reasons.append(f"ROAS dropped {_FH.signed_pct(roas)}")
    if act_reasons:
        return {"class": "act", "label": "Act now", "why": _sentence(act_reasons)}

    # ---- Watch ----
    watch_reasons = []
    if medium:
        watch_reasons.append("an anomaly is flagged")
    if rev is not None and rev <= -12:
        watch_reasons.append(f"revenue is {_FH.signed_pct(rev)} vs a normal day")
    if mer is not None and mer <= -12:
        watch_reasons.append(f"MER is {_FH.signed_pct(mer)}")
    if roas is not None and roas <= -12:
        watch_reasons.append(f"ROAS is {_FH.signed_pct(roas)}")
    if cac is not None and cac >= 20:
        watch_reasons.append(f"CAC is up {_FH.signed_pct(cac)}")
    if watch_reasons:
        return {"class": "watch", "label": "Watch", "why": _sentence(watch_reasons)}
    # Low-severity items (cosmetic Meta nudges, auction-overlap tips) are
    # informational — they show in the needs-attention list but don't downgrade
    # an otherwise-healthy day to Watch.

    # ---- On track ----
    if (y.get("revenue") or 0) == 0 and (y.get("orders") or 0) == 0:
        return {"class": "ok", "label": "On track",
                "why": "A quiet day — no orders recorded and nothing flagged."}
    if rev is not None and rev >= 8:
        why = f"Revenue ran {_FH.signed_pct(rev)} above a normal day with nothing flagged."
    elif rev is not None and rev <= -8:
        why = f"Revenue dipped {_FH.signed_pct(rev)}, but within normal daily swing and nothing flagged."
    else:
        why = "Tracking close to a normal day with nothing flagged."
    return {"class": "ok", "label": "On track", "why": why}


def _sentence(reasons):
    """Join reason fragments into one capitalized sentence."""
    if not reasons:
        return ""
    if len(reasons) == 1:
        body = reasons[0]
    elif len(reasons) == 2:
        body = reasons[0] + " and " + reasons[1]
    else:
        body = ", ".join(reasons[:-1]) + ", and " + reasons[-1]
    return body[0].upper() + body[1:] + "."


# ---- portfolio --------------------------------------------------------------

def build_portfolio(store_verdicts):
    """store_verdicts: [{store_name, verdict:{class,label,why}}]."""
    n = len(store_verdicts)
    act = [s for s in store_verdicts if s["verdict"]["class"] == "act"]
    watch = [s for s in store_verdicts if s["verdict"]["class"] == "watch"]
    needs = act + watch

    if n == 0:
        return {
            "headline": "No stores connected yet",
            "verdict": "Connect a Shopify store in TrackBee and the daily pulse will fill in here.",
            "attention": [],
        }

    plural = "store" if n == 1 else "stores"
    if act:
        headline = (f"Action needed on {len(act)} {('store' if len(act) == 1 else 'stores')} today"
                    if not watch else
                    f"{len(needs)} of {n} {plural} need attention")
    elif watch:
        headline = (f"{len(watch)} {('store' if len(watch) == 1 else 'stores')} to watch, "
                    f"the rest on track")
    else:
        headline = (f"All {n} {plural} on track" if n > 1 else "Your store is on track")

    # Verdict sentence. Store names are escaped here because this string is
    # stamped into the page as raw HTML (it carries intentional <strong>/<span>).
    if not needs:
        verdict = "<strong>Every store is pacing normally.</strong> Nothing flagged across the portfolio this morning."
    else:
        names = ", ".join(_ename(s) for s in needs)
        if act and watch:
            verdict = (f"<strong>{len(needs)} of {n} {plural} need a look.</strong> "
                       f"<span class=\"yellow-accent\">Act now:</span> {', '.join(_ename(s) for s in act)}. "
                       f"Watch: {', '.join(_ename(s) for s in watch)}. The rest are pacing normally.")
        elif act:
            verdict = (f"<strong>{len(act)} {('store needs' if len(act) == 1 else 'stores need')} action.</strong> "
                       f"<span class=\"yellow-accent\">{names}.</span> The rest are pacing normally.")
        else:
            verdict = (f"<strong>{len(watch)} {('store' if len(watch) == 1 else 'stores')} to keep an eye on.</strong> "
                       f"{names}. Everything else is pacing normally.")

    attention = [{"name": _name(s), "level": s["verdict"]["class"]} for s in needs]
    return {"headline": headline, "verdict": verdict, "attention": attention}


def _name(s):
    return s.get("store_name") or "Store"


def _ename(s):
    """Store name escaped for embedding in the raw-HTML verdict string."""
    return html.escape(_name(s), quote=True)
