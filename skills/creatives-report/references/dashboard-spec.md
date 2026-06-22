# Creatives Report — Framework

This document captures the methodology behind the dashboard. The
user-facing SKILL.md gives the headline; this is the implementation
reference.

## 0. Scope

The report covers the **last 7 days only**. This is a pure snapshot:
no week-over-week comparison, no longer-term baseline — a deliberate
design choice. If a longer historical view is needed later, that's a
separate report — not a knob to flip inside this one.

The report presents **measured statistics only**. It does not score,
rank, or label ads, and it never recommends an action — readers
interpret the figures themselves.

## 1. Per-ad metric columns

The per-ad table shows, for each spending ad over the window, the
figures below. No status tag or action column is rendered.

| Column              | Field (Meta)              | Field (Google)            |
|---------------------|---------------------------|---------------------------|
| Spend               | `spend`                   | `spend`                   |
| Revenue             | `revenue_1d_click`        | `conversions_value`       |
| ROAS                | `purchase_roas`           | `conversions_value/spend` |
| Frequency           | `frequency`               | — (no analogue)           |
| CTR                 | `ctr`                     | `ctr * 100`               |
| CPA                 | `spend / purchases`       | `spend / conversions`     |
| NNR share           | `net_new_reach / reach`   | —                         |
| New customers       | `new_customer_purchases`  | `new_customer_conversions`|
| Status              | platform `effective_status` (Active / Paused) — platform-native |
| First active        | `first_active_date` / `created_time` | `start_date` |

Each value renders as the measured figure; a missing value renders as
"—". The "Status" column is the platform's own delivery state, not a
TrackBee verdict.

## 2. Lifetime measurement

**Intentionally not included.** A 7-day window doesn't carry enough history for
median lifetime by format to be meaningful. The `lifetime_by_format`
component is intentionally absent from the bundle. The `age_days`
field on each ad is still computed (from `first_active_date` /
`start_date` / `created_time`) and shown in the table as context,
but no aggregate is reported.

If we ever want lifetime stats back, the right move is a sibling
report on a longer window — not bolting it back into the 7-day
snapshot.

## 3. Content-type per product

Product inference uses three signals in priority order:

1. **`product_focus` from config** — if the user named a product
   upfront, that label is applied to every ad whose ad-set or campaign
   name contains it (case-insensitive substring).
2. **Ad-set name tokens** — bracketed labels like `[Hoodie]`, prefixes
   like `PRO-Tee`, or pipe-separated segments like
   `BR | Hoodie | Cold-traffic`.
3. **Campaign name tokens** — same patterns applied at campaign
   level.

Ads that match none of these end up in `"Uncategorised"`.

The grid covers **ads with spend in the window only** — a zero-spend ad
has no performance to aggregate, so it appears in the ad table (the
inventory view) but not in the grid. The grid caption states this so the
two sections' differing populations aren't a silent mismatch.

Within each product, ads are bucketed by format (Video / Static /
Carousel / Collection / Search Text / Shopping Feed / PMAX). The
script reports every row, regardless of sample size:

- Median ROAS
- Median CTR
- Median CPA
- Total spend
- Total purchases / conversions

Rows with N < 3 get a small ``low sample`` chip next to the ad count
— the figures are still shown but should be read as directional. When
the leading format's median ROAS is >= 20% above the next-best (both
rows N >= 3, at meaningful spend), the row states the gap as numbers —
e.g. the leader's median ROAS next to the runner-up's. This is a
measured comparison only; no "winner" label or verdict is applied.

## 4. Follow-up question cards

Below the data the report shows up to three neutral follow-up question
cards (``next_questions.py``). Each states a measured figure for one ad
— e.g. its ROAS, its frequency, or its new-customer share — and poses an
open question the user can send back to the assistant. The cards do not
prescribe an action or score the ad; they only point at a number worth a
closer look.

## 5. Edge cases

- **Single-platform accounts.** If only Meta or only Google is in
  scope, hide the absent-platform tab and skip platform-specific
  sections rather than rendering "no data" placeholders.
- **PMAX asset groups.** Listed in the table with `format = "PMAX"`;
  they carry no per-asset spend, so spend-derived columns read "—".
- **Very low spend.** If total ad-level spend across all stores is
  < £100 in the week, render a top-of-page warning that conclusions
  are unreliable.
- **No first-active data.** Drop the age column for that row; the
  rest of the row still renders normally.
- **Multi-store.** Each store gets its own audit; cross-store
  comparisons are intentionally not surfaced (different currencies,
  different catalogues).

## 6. Don'ts

- Don't sum click-window purchases. `purchases_1d_click ⊂
  purchases_7d_click ⊂ purchases_28d_click` — they're cumulative.
- Don't try to back-fit week-over-week decay signals from a single
  7-day window. If the user wants decay analysis, that's a different
  report on a different window.
- Don't score, rank, or label ads, and don't recommend an action on
  them. The report presents the measured figures; interpretation is
  the reader's.
- Don't fabricate trends. "This week" is the only frame of reference
  the report has — every claim should be scoped to it.
