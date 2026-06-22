"""Numeric thresholds that decide which follow-up questions and key
observations are material enough to surface in Ad Performance.

Centralised here so a marketing / strategy edit happens in one place — no
hunting through multiple modules. These thresholds gate *which figures get
shown*; they never label a verdict or recommend an action on the user's data.
"""

from __future__ import annotations


# ── Frequency bands (Meta only — Google has no frequency) ────────────────────
FREQ_WARNING = 3.0          # surface the campaign's frequency as a key observation
FREQ_FRESH = 2.0            # scaling-lane question gate (frequency headroom)
FREQ_HEALTHY_SCALE = 2.5    # frequency-vs-ROAS question gate

# ── Spend floor (in store-currency units) ─────────────────────────────────────
# Below this floor a campaign is too small to anchor a follow-up question.
SPEND_FLOOR_HEAVY = 500.0   # heavy-spender gate for the frequency question

# ── Q-card thresholds (insights/next_questions.py) ───────────────────────────
QUESTION_UNDERP_ROAS = 1.5
QUESTION_UNDERP_SPEND = 300.0
QUESTION_SCALE_ROAS_META = 1.7
QUESTION_SCALE_ROAS_GOOGLE = 2.0
QUESTION_SCALE_SPEND = 200.0
MAX_NEXT_QUESTIONS = 3
