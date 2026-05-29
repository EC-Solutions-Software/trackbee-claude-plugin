"""Data-driven follow-up questions.

Surfaces up to three short prompts the user can copy-paste back to the
assistant for a deeper dive. Each item is a {q, why} dict where `q` is
the question (rendered prominently) and `why` is the supporting context
(rendered as fine print).

Rules are conservative: a question only fires when the underlying signal
is meaningful (e.g. frequency ≥ 2.5 AND spend > 500 for the fatigue
question). The list returns at most `MAX_NEXT_QUESTIONS` items.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fh = _load("format_helpers", _CHROME / "format_helpers.py")
_t = _load("thresholds", _HERE / "thresholds.py")


def _is_meta(campaign: dict) -> bool:
    """Heuristic: only Meta campaigns carry a `purchase_roas` field."""
    return "purchase_roas" in campaign


def _campaign_roas(campaign: dict) -> float:
    if _is_meta(campaign):
        return _fh.safe_float(campaign.get("purchase_roas"))
    return _fh.google_roas(campaign) or 0


def build(meta_campaigns: list[dict], goog_campaigns: list[dict],
          sym: str, m_fx: float, g_fx: float) -> list[dict]:
    questions: list[dict] = []

    meta_active = [c for c in meta_campaigns if _fh.safe_float(c.get("spend")) > 0]
    goog_active = [c for c in goog_campaigns if _fh.safe_float(c.get("spend")) > 0]

    # Q1 — frequency vs ROAS conflict on a heavy spender.
    high_freq = [
        c for c in meta_active
        if _fh.safe_float(c.get("frequency")) >= _t.FREQ_HEALTHY_SCALE
        and _fh.safe_float(c.get("spend")) > _t.SPEND_FLOOR_HEAVY
    ]
    if high_freq:
        c = sorted(high_freq, key=lambda x: -_fh.safe_float(x.get("spend")))[0]
        cname = _fh.text(_fh.short(c.get("campaign_name", ""), 44))
        freq = _fh.safe_float(c.get("frequency"))
        spend = _fh.safe_float(c.get("spend")) * m_fx
        roas = _fh.safe_float(c.get("purchase_roas"))
        questions.append({
            "q": (
                f"Which ad inside {cname} is driving frequency to {freq:.1f}× — "
                "and is it still carrying ROAS, or coasting on past performance?"
            ),
            "why": (
                f"Frequency {freq:.1f} on {_fh.money(spend, sym)} of spend at "
                f"{roas:.2f}× ROAS. Ad-level fatigue typically surfaces several days "
                "before campaign ROAS drops. Review retention and CTR at the ad level "
                "to identify which creative to refresh."
            ),
        })

    # Q2 — underperforming spender across either platform.
    def _underp(c: dict) -> bool:
        return (
            _fh.safe_float(c.get("spend")) > _t.QUESTION_UNDERP_SPEND
            and 0 < _campaign_roas(c) < _t.QUESTION_UNDERP_ROAS
        )

    underp = [c for c in meta_active + goog_active if _underp(c)]
    if underp:
        c = sorted(underp, key=lambda x: -_fh.safe_float(x.get("spend")))[0]
        cname = _fh.text(_fh.short(c.get("campaign_name", ""), 44))
        roas = _campaign_roas(c)
        fx = m_fx if _is_meta(c) else g_fx
        spend = _fh.safe_float(c.get("spend")) * fx
        plat = "Meta" if _is_meta(c) else "Google"
        questions.append({
            "q": (
                f"Is the {roas:.2f}× ROAS on {cname} a creative, audience, "
                "or landing-page issue?"
            ),
            "why": (
                f"{plat} delivered {_fh.money(spend, sym)} below break-even. "
                "Before pausing, isolate the cause: CTR signals creative, frequency "
                "signals audience, and ATC-to-purchase rate signals landing page or "
                "checkout."
            ),
        })

    # Q3 — scaling lane.
    scaling: list[tuple[dict, float, float, str]] = []
    for c in meta_active:
        r = _fh.safe_float(c.get("purchase_roas"))
        f = _fh.safe_float(c.get("frequency"))
        s = _fh.safe_float(c.get("spend"))
        if r >= _t.QUESTION_SCALE_ROAS_META and (f == 0 or f < _t.FREQ_FRESH) and s > _t.QUESTION_SCALE_SPEND:
            scaling.append((c, r, s, "Meta"))
    for c in goog_active:
        r = _fh.google_roas(c) or 0
        s = _fh.safe_float(c.get("spend"))
        if r >= _t.QUESTION_SCALE_ROAS_GOOGLE and s > _t.QUESTION_SCALE_SPEND:
            scaling.append((c, r, s, "Google"))
    if scaling:
        c, r, s, plat = sorted(scaling, key=lambda x: -x[1])[0]
        fx = m_fx if plat == "Meta" else g_fx
        cname = _fh.text(_fh.short(c.get("campaign_name", ""), 44))
        questions.append({
            "q": f"How far can {cname} scale before efficiency degrades?",
            "why": (
                f"This {plat} campaign holds {r:.2f}× ROAS on "
                f"{_fh.money(s * fx, sym)} of spend. Increase daily budget 20–30%, "
                "then monitor CPM, frequency, and new-customer share over 48 hours "
                "before scaling further."
            ),
        })

    # Q4 fallback — new-customer share when nothing else fired.
    if len(questions) < 2:
        nc_total = sum(
            int(c.get("new_customer_purchases") or 0)
            for c in meta_active
            if c.get("new_customer_purchases")
        )
        purch_total = sum(int(c.get("purchases") or 0) for c in meta_active)
        if purch_total > 0:
            ratio = nc_total / purch_total
            questions.append({
                "q": (
                    "What share of revenue this week came from new customers, "
                    "and which campaigns drove the acquisition?"
                ),
                "why": (
                    f"{nc_total:,} of {purch_total:,} Meta purchases "
                    f"({ratio * 100:.0f}%) flagged as new-customer this window. "
                    "Separating new-customer ROAS from blended ROAS clarifies whether "
                    "growth is coming from acquisition or from retargeting existing "
                    "buyers."
                ),
            })

    return questions[: _t.MAX_NEXT_QUESTIONS]


_TAG_RE = re.compile(r"<[^>]+>")
_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&",
    "&lt;": "<", "&gt;": ">",
    "&quot;": '"',
}


def to_plain_text(s: str) -> str:
    """Strip HTML tags and decode common entities — used for clipboard copy."""
    t = _TAG_RE.sub("", s)
    for entity, char in _ENTITIES.items():
        t = t.replace(entity, char)
    return t.strip()


_VIEWS = Path(__file__).resolve().parent.parent / "views"


def render_questions_html(qs: list[dict]) -> str:
    """Render the Q-card section. Returns empty string when qs is empty.

    Loads the section and per-card templates from `components/views/`. The
    Python here only fills placeholders — the markup lives in HTML.
    """
    if not qs:
        return ""

    card_tpl = (_VIEWS / "question_card.html").read_text(encoding="utf-8")
    section_tpl = (_VIEWS / "questions_section.html").read_text(encoding="utf-8")

    cards = "".join(
        card_tpl
        .replace("{Q_NUM}",   f"Q{i+1}")
        .replace("{Q_TEXT}",  q["q"])
        .replace("{Q_WHY}",   q["why"])
        .replace("{Q_PLAIN}", _fh.attr(to_plain_text(q["q"])))
        for i, q in enumerate(qs)
    )

    return section_tpl.replace("{CARDS}", cards)
