"""Numeric thresholds that drive Ad Performance insights + recommendations.

Centralised here so a marketing / strategy edit happens in one place — no
hunting through multiple modules. Every constant is referenced by at least
one insight rule or the action-badge renderer.
"""

from __future__ import annotations


# ── ROAS bands ────────────────────────────────────────────────────────────────
# Used by status badges (chrome/format_helpers.roas_class) and the
# SCALE / HOLD / REFRESH / PAUSE action pill (transforms/table_meta.action_badge).
ROAS_GOOD = 2.5             # ≥ this = "good" colour band
ROAS_OK = 1.5               # ≥ this = "ok" colour band
ROAS_SCALE_CANDIDATE = 1.8  # Meta scale-budget threshold
ROAS_PAUSE = 1.2            # below this on meaningful spend = pause/review
ROAS_GOOGLE_SCALE = 4.0     # Google's higher bar for aggressive scaling

# ── Frequency bands (Meta only — Google has no frequency) ────────────────────
FREQ_WARNING = 3.0          # surface as creative-fatigue risk
FREQ_FATIGUE = 3.5          # refresh creative; performance erodes soon
FREQ_FRESH = 2.0            # below this = audience still has headroom
FREQ_HEALTHY_SCALE = 2.5    # scale candidates must be below this

# ── Spend floors (in store-currency units) ───────────────────────────────────
# Below these floors the insight signal is noise, not a finding. They
# scale with the dashboard's window (defaults to 7d) — review them when
# changing the default window.
SPEND_FLOOR_BADGE = 50.0    # action-badge minimum spend
SPEND_FLOOR_PAUSE = 100.0   # need this much spend for "pause" insight
SPEND_FLOOR_INSIGHT = 200.0 # general insights minimum
SPEND_FLOOR_HEAVY = 500.0   # used for the heavy-spender Q1 question

# ── Q-card thresholds (insights/next_questions.py) ───────────────────────────
QUESTION_UNDERP_ROAS = 1.5
QUESTION_UNDERP_SPEND = 300.0
QUESTION_SCALE_ROAS_META = 1.7
QUESTION_SCALE_ROAS_GOOGLE = 2.0
QUESTION_SCALE_SPEND = 200.0
MAX_NEXT_QUESTIONS = 3
