# Growth Report — spec

A deeper reference for editing or extending the report. **Don't read this
on every run** — only when modifying a component or adding a new metric.

## Page structure (top to bottom)

The shipped layout is `components/chrome/shell.html`. Four blocks:

1. **Header + answer** (one merged dark navy panel — the first thing the
   user sees). Brand wordmark, current window pill, eyebrow tag, big H1
   headline, then the answer body. The H1 is dynamically chosen based on
   revenue Δ — see `insights/answer.py:build` for the rules. The answer
   body (`{ANSWER_BLOCK}`) carries the short answer (concrete numbers,
   what moved) and the "why this is happening" structural read of the
   growth engines — all built from this window's measured figures in
   `insights/answer.py`. It states figures, never recommended actions.
   The headline KPIs computed in
   `transforms/headline_kpis.py` feed this block, the drivers, and the
   metric table; they are not rendered as a separate tile grid.
2. **What's working / What's breaking** (side-by-side cards). Working =
   lavender background, breaking = soft pink. Each card lists up to 6
   items, each a `<strong>title</strong>` + one-line `<div class="why">`.
   Rules for inclusion live in `transforms/drivers.py` — see §Driver
   signal gates below for the thresholds.
3. **Metric framework table** (white card). Every row of the TrackBee
   Growth checklist. Filter pills above the table: All / Positive signals /
   Negative signals (filter on each row's `data-signal`, which records only
   the direction of the week-over-week move). Columns: Metric, What it
   indicates (a neutral definition — no "good/bad looks like" guidance),
   Imp.(ortance), Value · current, Value · prior, What this means for the
   analysis (states the figures + the WoW delta). The iROAS and incremental
   revenue rows describe themselves as modelled estimates; true lift needs a
   holdout test.
4. **Footer** (light card). Store id + window dates + caveats about
   `checkout_started` and COGS.

## Driver signal gates

The working / breaking panels fire on the gates below. The canonical
values are the constants block at the top of `transforms/drivers.py` —
keep this table in sync when changing one.

| Signal | Gate | Spend gate (store ccy) |
| --- | --- | --- |
| New-customer orders / MER / LTV improving | > +5% WoW | — |
| Per-platform ROAS improvement | > +10% WoW | ≥ 100 |
| Klaviyo email-assist | > 10% of order journeys | — |
| Revenue down | < −5% WoW | — |
| Returning-customer revenue down | < −10% WoW | — |
| AOV down (both segments) | < −5% WoW each | — |
| Per-platform CPC inflation (Meta/Google only) | > +20% WoW | ≥ 500 |
| Per-platform ROAS collapse | < −15% WoW | > 500 |
| LTV:CAC warning | < 2.0× | — |

Per-platform signals iterate the shared `AD_PLATFORMS` list in
`chrome/format_helpers.py`; the CPC signal intentionally covers Meta and
Google only (minor channels lack the click volume for a stable read).

## Brand tokens

All v3 tokens in `components/chrome/theme.css`. The important ones:

- `--navy #0D1245` — body text on light, primary fill on dark.
- `--lavender #F0F2FF` — "working" panel background, secondary accents.
- `--pink #FF1F6B` — display-only. Pink-deep `#C8124B` for body text.
- `--yellow #FFCC00` — accent on dark only (decorative on light).
- `--sky #3D9EFF` — reserved for partner contexts; not used in this
  report.
- `--pink-ink #C8124B`, `--honey-ink #7A5C00`, `--blue-ink #0066CC` — for
  brand-hue text on light surfaces.
- Semantic: `--success`, `--warning`, `--error`, `--info`.

## Adding or editing a metric

Each metric is defined in two places:

1. `transforms/metrics_table.py:METRICS_STATIC` — the static fields, a 7-tuple
   `(id, name, indicates, bad, normal, good, importance)`.
2. `transforms/metrics_table.py:_compute_values` — the per-run logic that
   produces `(current_str, prior_str, interpretation)` for that metric.

Add the metric to the `METRICS_STATIC` list AND add a `values["<id>"] = …`
assignment in `_compute_values`. If the new metric depends on a payload
that isn't currently fetched, add it to the MCP calls list in
`SKILL.md:§MCP calls` AND to `_load_raw` in the orchestrator AND to the
inputs dict passed into `metrics_mod.transform` in
`orchestrators/assemble.py:build`.

## Voice

Every user-facing string follows the TrackBee Insights voice contract.
The core rules:

- **Numbers carry the meaning, not adjectives.** A campaign isn't
  "fading" — it has a 22% WoW CTR drop. Replace commentary words with
  the metric that produced the impression.
- **No sales energy.** No hype phrases, emojis, or exclamation marks.
  Product gaps (EMQ, in-platform vs server-side) are reported as data
  findings, not pitches.
- **No self-reference or preamble.** Lead with the data; stay in the
  second person (the user's stores, the user's campaigns).
- **Scope every claim to the windows shown.** Interpretation columns
  state what the number means for this 7d-vs-7d comparison — never
  fabricate longer trends.

## Output filename convention

`<store-slug>-growth-report-<YYYY-MM-DD>.html`. The date is
**yesterday's** date (the end of the current window). Same store always
overwrites the same artifact id — never stack duplicates in the sidebar.
