# Creatives Report — Framework

This document captures the methodology behind the dashboard. The
user-facing SKILL.md gives the headline; this is the implementation
reference.

## 0. Scope

The audit covers the **last 7 days only**. This is a pure snapshot:
no week-over-week comparison, no longer-term baseline — a deliberate
design choice. If a longer historical view is needed later, that's a
separate report — not a knob to flip inside this one.

Because there's no baseline, fatigue scoring uses **absolute
thresholds** for everything (frequency, ROAS, NNR share). Decay-vs-
baseline signals (CTR dropped 30% in the last 7d vs the prior 7d,
etc.) are intentionally out of scope.

## 1. Fatigue scoring

Each ad gets one of four tags. See ``fatigue_scoring.py`` for the
canonical decision tree.

### Inputs per ad

| Signal              | Field (Meta)              | Field (Google)            |
|---------------------|---------------------------|---------------------------|
| Spend               | `spend`                   | `spend`                   |
| Revenue             | `revenue_1d_click`        | `conversions_value`       |
| ROAS                | `purchase_roas`           | `conversions_value/spend` |
| Frequency           | `frequency`               | — (no analogue)           |
| CTR                 | `ctr`                     | `ctr * 100`               |
| CPA                 | `spend / purchases`       | `spend / conversions`     |
| Net new reach       | `net_new_reach`           | —                         |
| NNR share           | `net_new_reach / reach`   | —                         |
| New-customer share  | `new_customer_purchases / purchases` | `new_customer_conversions / conversions` |
| First active        | `first_active_date` / `created_time` | `start_date` |

### Decision tree

```
if spend < MIN_SCORED_SPEND (50, store currency):
    HOLD, note = "insufficient spend to score in this 7-day window"

elif roas < 1.0 and spend > 150:
    KILL — below break-even at meaningful spend
    (no ROAS floor: a zero-ROAS ad that spent real money is the textbook
     KILL; the spend gate alone keeps under-tested ads out)

elif frequency >= 3.5:
    REFRESH — audience saturated

elif reach > 1000 and 0 <= nnr_share < 0.10:
    REFRESH — net new reach collapsed, audience exhausted

elif roas >= 1.8 and frequency < 2.5:        # frequency < 2.5 also covers Google's freq == 0
    SCALE — increase budget 20-30%

elif roas < 1.0:
    HOLD (losing) — below break-even but spend hasn't reached the kill
    threshold yet; let it run to a clearer read before cutting

else:
    HOLD — performing within normal range
```

### Secondary tags

After the primary status is assigned the scorer applies up to two
secondary chips:

- **"retargeting only"** — `new_customer_purchases / purchases < 0.10`
  while purchases is non-zero. The ad is converting almost entirely on
  existing customers this week.

- **"upper-funnel shift"** (Meta only) — when
  `purchases_1d_click < 0.5 × purchases` AND
  `purchases_28d_click >= 0.85 × purchases`. The ad still drives
  conversions but they're landing outside the 1-day click window —
  treat it more like a brand-builder than a direct response.

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
- Status mix (count of SCALE / HOLD / REFRESH / KILL)

Rows with N < 3 get a small ``low sample`` chip next to the ad count
— the figures are still shown but should be read as directional. The
``winner`` highlight has a stricter requirement: both the leading row
and the runner-up it is compared against must have N >= 3 (and the
leader must beat the next row by >= 20% on median ROAS at meaningful
spend) before the chip is applied. A win declared over a single-ad
runner-up isn't a win — there's nothing solid to compare against.

## 4. Production recommendations

The script generates up to 5 recommendations in this priority:

1. **Replace** — the top 3 KILL-tagged ads by spend, with their
   format, product, and current ROAS. "These have spent £X at Y×
   ROAS this week — queue replacements first."

2. **Double down** — the top 3 (product, format) combinations by
   median ROAS where total spend >= £200 and at least 3 ads exist.
   "Video for [Product A] is your strongest pairing this week — 3.2×
   median ROAS across 7 ads. Make more."

3. **Fill gaps** — for each product, list formats that perform well
   for *other* products in the same account but are missing or
   under-represented here. "You have no carousel ads for [Product B],
   yet carousels deliver 2.8× ROAS for similar products in this
   account. Test one."

4. **Theme insights** — if SCALE-tagged ad names share keyword tokens
   (e.g. "discount", "founder", "review"), surface that token: "Three
   of your top four winners include 'review' in the ad name —
   testimonials are over-indexing this week."

5. **Stop the bleed** — if any KILL-tagged ad represents >= 15% of
   account spend this week, surface it specifically with the absolute
   daily cost of continued under-performance.

## 5. Edge cases

- **Single-platform accounts.** If only Meta or only Google is in
  scope, hide the absent-platform tab and skip platform-specific
  sections rather than rendering "no data" placeholders.
- **PMAX asset groups.** Listed in the table with `format = "PMAX"`
  but excluded from fatigue scoring (no per-asset spend).
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
- Don't recommend killing an ad before it hits the spend threshold
  (default £150). Below that the noise dominates the signal.
- Don't fabricate trends. "This week" is the only frame of reference
  the audit has — every claim should be scoped to it.
