# Daily Store Pulse — spec

A reference for editing or extending the pulse. **Don't read this on every
run** — only when modifying a component or adding a section.

## Page structure (top to bottom)

The shipped layout is `components/chrome/shell.html`.

1. **Portfolio header** (dark navy panel). Brand wordmark, "yesterday" date
   pill, eyebrow, an H1 headline summarising how many stores need attention,
   the portfolio verdict sentence, and a row of chips naming the flagged
   stores (pink dot = Act now, yellow dot = Watch). Built in
   `insights/verdict.py:build_portfolio`.
2. **Store filter** (sticky light bar). An "All stores" chip plus one chip per
   store, each with a verdict-coloured dot. Clicking shows/hides cards
   client-side via `components/chrome/store_filter.js`; the choice persists to
   `localStorage` under a key scoped to the artifact id. "All stores" is the
   default. The filter never re-fetches — all data is baked in.
3. **One pulse card per store** (`components/views/pulse_card.html`,
   `data-store="<id>"`). Each card, top to bottom:
   - **Head** — store name + meta line; verdict pill (On track / Watch / Act
     now) and a one-sentence why. Verdict logic: `insights/verdict.py:build_store`.
   - **KPI tiles** — revenue, orders, MER, ROAS, PoAS, CAC. Each shows
     yesterday's value, the trailing-7-day baseline, and a delta painted by
     whether the move is *good* (CAC inverts — a drop is good). `transforms/kpis.py`.
   - **Month-to-date pacing** — an interactive daily-revenue sparkline (hover a
     day for its date + revenue) plus revenue and ad-spend rows that compare
     **this month against last month**: MTD-so-far vs the same elapsed days last
     month, and the on-pace full-month projection vs last month's actual total
     (the bar's tick marks last month). `transforms/mtd.py` + `charts/sparkline.py`
     + `chrome/spark.js`.
   - **Needs attention** — ranked anomalies + Meta warnings, each with a
     plain-English so-what; empty state is "Nothing flagged today."
     `insights/attention.py`.
   - **Top movers** — up to five campaigns ranked by day-over-day spend swing,
     each surfacing its current ROAS and the ROAS swing. Meta data from
     `get_meta_campaign_insights` (`purchase_roas`), Google from
     `get_google_campaign_insights` (ROAS = `conversions_value` ÷ `spend`); spend
     in ad-account-currency units, FX-adjusted. `transforms/movers.py`.
   - **Go deeper** — a dock of store-aware prompts routing to follow-up skills.
     `insights/dock.py` + `components/chrome/dock.js`.
4. **Footer** (light). Store count, the reference day, the baseline window, and
   methodology caveats (`checkout_started` is client-side only; profit uses
   COGS settings with a store-level fallback).

## Windows

- `yesterday` — the reference day (today − 1).
- `baseline` — the 7 days before yesterday; the "normal day" comparison.
  Level metrics compare yesterday vs `baseline total ÷ baseline_days`; ratio
  metrics compare yesterday vs the baseline window ratio directly.
- `mtd` — month-start … yesterday; with `days_elapsed` / `days_total` and the
  `this_month_label` / `prev_month_label` names for the pacing copy.
- `prev_month_mtd` — last month, same elapsed days (the MTD comparison).
- `prev_month_full` — all of last month (the projection benchmark).
- `trend` — ~14 days back … yesterday; the sparkline series.

Every window start is clamped to the store's onboarding date upstream (in the
skill workflow), never in the renderer.

## Verdict thresholds

In `insights/verdict.py`. Deliberately conservative about red — daily numbers
are noisy:

- **Act now** — a high-severity anomaly, or revenue ≤ −35% vs a normal day, or
  MER/ROAS ≤ −30%.
- **Watch** — a medium anomaly, or revenue/MER/ROAS ≤ −12%, or CAC ≥ +20%, or
  any open recommendation, or no data yet for the day.
- **On track** — everything else.

The portfolio header rolls these up: Act now stores lead, then Watch, then the
"on track" remainder.

## Brand tokens

All v3 tokens in `components/chrome/theme.css`. The important ones:

- `--navy #0D1245` — header panel, body text on light, KPI values.
- `--lavender #F0F2FF` — hover/secondary accents.
- `--pink #FF1F6B` — Act-now dot, sparkline end point (display only; ink
  `#C8124B` for any pink text).
- `--yellow #FFCC00` — accent on dark only (date pill, "Act now:" emphasis).
- `--sky #3D9EFF` — the ad-spend pacing bar.
- Verdict tints: `--ok-bg / --watch-bg / --act-bg` and matching borders.
- Semantic: `--success` (good deltas), `--error` (bad deltas), `--warning`.

Deltas use `.delta-good` / `.delta-bad` / `.delta-flat` — the *class* carries
the meaning, not the sign, so CAC up renders red even though the number is
positive. Moves inside ±2% read as flat.

## Adding or changing a KPI tile

Tiles are built in `transforms/kpis.py:build`. Each is one `_tile(...)` call
with a label, a formatted value, a baseline string, the delta percent, and an
optional `lower_is_better=True` for cost metrics. Level metrics divide the
baseline window by `baseline_days`; ratio metrics compare windows directly. Add
or reorder tiles there — the orchestrator renders whatever list it returns.

## Defensive parsing

`get_profit_on_ad_spend`, `detect_anomalies`, and the campaign-insights tools
(`get_meta_campaign_insights` / `get_google_campaign_insights`) payload shapes
are read across candidate key names (see the `_*_KEYS` tuples in
`transforms/loader.py`, `transforms/movers.py`, and `insights/attention.py`).
If a live response uses a field name not yet in those tuples, add it there — the
parser degrades to "—" rather than crashing, so a missing field shows as no data
rather than a broken build.

## Voice

Every user-facing string follows the project voice contract in `VOICE.md`
(repo root). Reconcile copy there.

## Output + artifact convention

- Output filename: `trackbee-daily-store-pulse-<YYYY-MM-DD>.html`, where the
  date is **yesterday's** (the reference day).
- Artifact id: `trackbee-daily-store-pulse` — one portfolio artifact for every
  store, always reused so refreshes overwrite in place.
- Scheduled task id: `trackbee-daily-store-pulse-refresh`, cron `0 8 * * *`.
