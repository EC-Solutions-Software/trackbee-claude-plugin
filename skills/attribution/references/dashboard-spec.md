# Attribution Report — per-section design spec

This is the design reference for the **attribution** skill. The runtime
contract lives in `SKILL.md`; this file describes what each section of the
HTML page looks like, how the copy reads, and which brand tokens it uses.
Open it when you're modifying a component or designing a new variant.

For metric → TrackBee-field mappings, see `metric-map.md`.
For the chat hand-off after a render, see `handoff-template.md`.

## Sections, top to bottom

The page has six sections, rendered in one scrollable column. No tabs.

1. **Header strip** — brand wordmark + "Attribution Report" + store name.
2. **Executive Summary** — 3–5 plain-English takeaways for the active window.
3. **Blended Overview** — KPI tiles + Blended NC ROAS daily line chart.
4. **Platform Overview** — per-platform tiles (Meta, Google, …) for the active window.
5. **Channel Attribution** — per-channel table with TrackBee + in-platform sides and {observation, action} insight cards.
6. **Customer Journeys** — three KPI tiles, touch-points heatmap with insights, sankey with view filter, and journey insights.
7. **Footer** — generated date, caveats list, brand wordmark low contrast.

A 3d / 7d / 28d filter at the top swaps the Executive Summary, Blended
Overview (KPI tiles + line chart), Platform Overview, and Channel
Attribution against the chosen window. Customer Journeys is not
window-scoped — its input window is the 28d range chosen at build time.

## 1. Header strip

- **Wordmark** (icon + "TrackBee" lockup) on the left, then a thin vertical divider, then **"Attribution Report"** as the `h1` with the store name in `--ink-muted` underneath. The wordmark is reserved for the header; small icon marks go in column headers and row icons.
- **Date filter** as a segmented control with three buttons — 3 days, 7 days, 28 days. Defaults to 28d. Clicking re-renders the window-scoped sections by reading the pre-baked payload for that window.
- **Do not surface the dates under the `h1`.** They go in the footer's caveats list (window range, store currency, ad-account FX) so the top of the page stays clean.

## 2. Executive Summary

Above the Blended Overview tiles, render an Executive Summary block with
3–5 numbered takeaways for the active window. This is the first thing
the user reads — make it useful on its own.

Style: dark surface (`--ink` gradient), `--yellow` numbered counter on
each takeaway, white prose. Each takeaway is one sentence containing a
number. Computed per window — they update on filter toggle.

The takeaways are produced by `components/insights/executive_summary.py`
from the blended KPI payload + channel rows. The rules are:

1. **Headline performance** — total revenue + orders + ad spend + Blended ROAS, with a delta vs the previous equal-length period.
2. **Top contributing channel** — which channel drives the largest share of TrackBee-attributed revenue. End with "Protect its budget."
3. **Scale or cut** — if any paid channel clears ROAS ≥ 2, name it as a scale candidate; otherwise surface the highest-CPA channel.
4. **Over-credit risk** — the biggest in-platform > TrackBee gap. If none, surface the largest earned-channel contribution as an incrementality test candidate.

The Executive Summary is wrapped in `<div class="exec-summary">` with an
`<ol id="execTakeaways">`. JS swaps the contents on every filter change.

## 3. Blended Overview

### 3.1 KPI tiles

A responsive grid of KPI tiles for the active window: Ad spend, Revenue,
New Customers, Orders, AOV, Blended ROAS, Blended CPA, Blended NC-CPA,
Blended NC-ROAS, Sessions, Added-to-cart rate, Started-checkout rate,
Conversion rate, Revenue / session.

Each tile shows: label, big value, and a delta vs the previous
equal-length period. `tool__get_funnel_overview` accepts
`compare_previous_period=true` and supplies the funnel-rate deltas
directly; the other deltas come from a second `tool__get_dashboard_overview`
call for the previous window (the orchestrator stages this as the
`_previous` slice on each `overview*.json`).

Tile chrome:

- Label in `--font-mono`, uppercase, `--ink-muted`.
- Big value in `--font-display`, `--ink`.
- Tile background `--surface-1`, 1px border `--line`, 12px radius.
- Delta arrow ▲/▼ in `--success` / `--error` plus the % delta.

### 3.2 Blended NC ROAS (Acquisition MER) over time

Below the KPI grid, render a daily line chart of Blended NC-ROAS for the
active window. This is the single most important retention-led growth
metric — surface it visually, not just as a tile.

- **Heading**: "Blended NC ROAS (Acquisition MER) over time"
- **Subtitle**: "Daily new-customer revenue ÷ daily ad spend"
- X axis: each day in the active window (3 / 7 / 28 ticks).
- Y axis: `total_new_customer_revenue` (daily) ÷ `daily_spend` (per-day, tier-derived — see metric-map.md).
- **Period avg** in the chart header = `sum(daily_nc_revenue) ÷ sum(daily_spend)` across displayed days. Matches the Blended NC-ROAS tile exactly.
- **Period-average dashed line** in `--gold` so anomalies are obvious.

The chart renderer lives in `components/charts/nc_roas_line.js` and
draws an inline SVG — no chart library. Re-renders on filter toggle.

## 4. Platform Overview

Each platform that has ad insights connected gets a row of
platform-coloured tiles: ROAS, Revenue (in-platform), Ad spend, CTR,
CPC, CPM, Impressions, Clicks, Purchases. The Meta and Google rows are
always present when data is fetched; additional platforms appear
automatically.

Refer to Facebook/Meta as **"Meta"** in all user-facing copy. The MCP
returns the key as `facebook` — translate to "Meta" for the UI.

Each platform's section header shows the platform's small inline SVG
mark (14×14) next to the platform name.

## 5. Channel Attribution

A single table titled **"Channel Attribution"** with these columns:

| Channel | Sessions | [TB] TrackBee Purchases | Purchases (in-platform) | [TB] TrackBee Revenue | Revenue (in-platform) | Spend | CPA | ROAS |

`[TB]` is the small inline TrackBee icon (14×14, the icon mark — never
the wordmark). Spell "TrackBee" out in the column header so the source
is unambiguous even without the icon. Columns sourced from the ad
platform's own reporting get a small `(in-platform)` subtitle.

Each tracked channel's row shows its brand mark next to the name. The
table is built dynamically from
`tool__get_platform_funnel_breakdown.platforms.keys()` so new tracked
channels render automatically; only the brand-mark map needs an entry
when TrackBee adds a channel.

Rules:

- Rows = channels in `tool__get_platform_funnel_breakdown`. A final "Overall" row sums totals (no logo on Overall).
- Em-dash (`—`) for missing values, never zero. Em-dash = "not applicable / no data"; zero = "we measured zero".
- Surface platform revenue alongside TrackBee revenue. The two columns side-by-side is the whole point — the gap is what the user is here to see.
- **Spend, CPA, ROAS are pure in-platform.** All three use ad-platform numbers exclusively. This guarantees Meta's ROAS in Channel Attribution matches Meta's ROAS in Platform Overview to the cent.
  - `Spend` = in-platform spend (sum of campaign spend from `tool__get_meta_campaign_insights` / `tool__get_google_campaign_insights`).
  - `CPA` = in-platform spend ÷ in-platform purchases.
  - `ROAS` = in-platform revenue ÷ in-platform spend.
- The TrackBee-attributed columns sit alongside for reconciliation; they do not feed into CPA or ROAS.
- The Overall row uses summed in-platform purchases and in-platform revenue across paid channels, so its CPA and ROAS are also pure in-platform.
- No legend below the table. The "TrackBee" prefix on the columns plus the icon and the `(in-platform)` subtitles make every source clear.

### Insight cards

Below the table, render a **"Key insights from your channel attribution"**
callout — `--blue-tint` background, same chrome as the other insight
sections. Each insight is structured as `{observation, action}` and
rendered as a card with:

- A vertical accent bar in `--accent` on the left.
- The observation in body text.
- A `Recommended action:` line below, separated by a dashed border, with the label in small uppercase `--accent` text.

The four strategic questions the insights answer:

1. **Which channel contributes most to orders and revenue?** → Top revenue channel + its share + "Treat it as a core channel; protect its budget."
2. **Where to spend more or less based on actual sales contribution?** → Highest-ROAS paid channel + scale recommendation. Plus the highest-CPA channel + investigate recommendation.
3. **Channels getting credit for sales they likely didn't drive?** → Biggest over-reporter (platform > TrackBee) + "Discount this channel's in-platform ROAS by ~X% when comparing across channels."
4. **What's contributing without spend?** → Earned channels with revenue and zero spend + "Audit upstream paid channels; run a list-only segmentation test to measure incremental lift."

Computed by `components/insights/channel_attribution.py`. Keep to 4–5
cards. Cards update on filter toggle.

## 6. Customer Journeys

The Customer Journeys section uses the 28-day input window staged at
build time. Its data comes from
`tool__get_platform_footprints` (cross-channel shares),
`tool__get_platform_breakdown(platform=…)` (cooccurrence + transitions
per top channel), and `tool__get_platform_journeys(platform=…)`
(sequences). The agent assembles `touchpoints.json` and per-channel
`j_<platform>.json` files as described in SKILL.md §Customer Journeys
adapter.

Section heading: **"Customer Journeys"** — no pill, no badge, no
confidence tag in the heading itself.

### 6.1 Three KPI tiles

Directly under the heading:

- **Total customer journeys** — `total_journeys` from `touchpoints.json`.
- **Single-touch share** — `single_touch_share` as a percentage. Sub-text: count of journeys with one tracked touchpoint.
- **Multi-touch share** — `1 - single_touch_share` as a percentage. Sub-text: count of journeys with 2+ tracked touchpoints.

### 6.2 Touch-points heatmap

A square grid showing how often a customer who touched platform A also
touched platform B.

- Subtitle: **"When a customer interacts with platform A, how often do they interact with platform B?"** — customer-centric phrasing, not analyst jargon.
- Rows = platform A, columns = platform B.
- Off-diagonal cells: `share_of_target_journeys` from the per-platform breakdown, expressed as a percentage.
- Diagonal: rendered as an em-dash. Per-channel single-touch share is not in the interactions payload, so we don't fabricate it — the diagonal is a visual structural marker only.
- Cell colour: brand-v3 gradient from `--lavender` (low) to `--navy` (high). Built as a plain HTML `<table>` with inline `background-color` — no chart library needed.

Below the heatmap, render a **"Key insights from your channel touch points"**
observation/action card list. Each insight reads off the matrix:

- **Strongest pairing** — the top off-diagonal cell after the sample-size guard (skip platforms with fewer than 50 attributed orders in `tool__get_platform_funnel_breakdown`).
- **Channels that rarely converge** — low overlap in any pairing involving the channel.
- **Channels that depend on others** — the channel with the highest total cross-channel overlap.
- **Asymmetric dependencies** — pairs where A → B share is at least 20pp above B → A.
- **One reading-the-matrix line** — "Off-diagonal values quantify how often two channels appear in the same customer journey."

Computed by `components/insights/cooccurrence.py`. Keep to 4–5 bullets.

### 6.3 Sankey

A single sankey diagram across all platforms. The renderer is the
inline SVG produced by `components/transforms/journey_sankey.py` — no
external chart library, so the artifact works in any environment.

**View filter** as a segmented control above the diagram:

- **Multi-touch only** (default) — paths with `len(sequence) ≥ 2`. The point of the sankey is multi-channel handoffs.
- **Top 5 journeys** — the 5 highest-count paths regardless of length.
- **Single-touch only** — paths with `len(sequence) == 1`. Reveals which channels close on the first touch.
- **All journeys** — every path.

All four views are pre-rendered server-side; the JS toggle swaps the
visible `<div data-sv="…">`. When a filter view is empty, the
orchestrator stamps an empty-state message in its place instead of
rendering an empty SVG.

Below the sankey, render a **"Key insights from your customer journeys"**
observation/action card list:

- **Top opener** — the platform that starts the most multi-touch journeys (counted on `sequence[0]`, weighted by `share_of_orders`).
- **Top closer** — the platform that closes the most multi-touch journeys (last touch before ORDER).
- **Most frequent journey** — the highest-share `sequence` overall.
- **Cross-platform handoff rate** — share of multi-touch journeys whose sequence contains two or more distinct platforms.
- **Median journey depth** — weighted median of `len(sequence)`.
- **Single-touch share** — already on the tile, repeated as a reading-the-sankey note.

Computed by `components/insights/journey.py`. Keep to 5–7 bullets.

## 7. Footer

- **Caveats list** — generated date, the 28d window range with start/end, the store currency, ad-account FX rates, plus any low-sample-platform note from the orchestrator.
- **Methodology notes**: TrackBee tracks `page_view` events, not session boundaries; `checkout_started` is a client-side proxy; in-platform vs TrackBee numbers will not match by design.
- **Brand wordmark** at low contrast.

The orchestrator stamps the low-sample caveat (`<50 attributed orders in
28 days`) automatically when a platform falls below the threshold.

## Brand tokens — TrackBee v3

Aligned to TrackBee brand guidelines v3 (April 2026): display palette +
ink extensions + Honeycomb tokens. Every pairing used clears WCAG 2.1
AA. These tokens live in `components/chrome/theme.css`; do not
duplicate or fork them.

```css
:root {
  color-scheme: light;

  /* Brand display palette. */
  --navy:      #0D1245;
  --lavender:  #F0F2FF;
  --pink:      #FF1F6B;
  --yellow:    #FFCC00;
  --sky:       #3D9EFF;

  /* Accessible ink extensions for brand-hue text/icons on light. */
  --pink-ink:  #C8124B;
  --honey-ink: #7A5C00;
  --blue-ink:  #0066CC;

  /* Honeycomb base/* — what the brand library binds to. */
  --ink:        var(--navy);
  --ink-2:      #2A2F5C;
  --ink-muted:  #737373;
  --line:       #E5E5E5;
  --surface-0:  #FAFAFA;
  --surface-1:  #FFFFFF;

  /* Aliases — keep older component names pointed at the v3 hex set. */
  --accent:    var(--blue-ink);
  --accent-bg: var(--sky);
  --blue-tint: var(--lavender);
  --gold:      var(--honey-ink);

  /* Semantic colours (4.5:1 on white). */
  --success: #027A48;
  --warning: #B54708;
  --error:   #B42318;
  --info:    var(--blue-ink);

  /* Type stack — brand-site fonts. */
  --font-display: 'Lexend', 'Inter Tight', 'Inter', system-ui, sans-serif;
  --font-body:    'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'Bricolage Grotesque', ui-monospace, monospace;

  /* Honeycomb radius scale. */
  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 10px;
  --radius-xl: 12px; --radius-4xl: 32px; --radius-full: 9999px;

  /* Platform colours — used ONLY for per-platform tiles and table icons. */
  --plt-meta:      #1877F2;
  --plt-google:    #4285F4;
  --plt-tiktok:    #000000;
  --plt-pinterest: #E60023;
  --plt-klaviyo:   #232323;
}
```

The page loads its fonts via the system stack and falls back gracefully.

## Brand marks — inline SVG / base64 PNG

The TrackBee icon and wordmark are bundled with the skill as
`assets/tb_icon_b64.txt` and `assets/tb_wordmark_b64.txt`. The
orchestrator inlines them as `<img src="data:image/png;base64,…">`
into the HTML at build time — no external file references, no PNG
fetching.

Per-channel brand marks (14×14, `vertical-align:-3px`, inline SVG):

- **TrackBee** — `--ink` rounded square + `--yellow` stylised B with bee accent.
- **Meta** — `--plt-meta` rounded square + white "M".
- **Google** — standard four-colour "G" mark.
- **Klaviyo** — `--plt-klaviyo` rounded square + white "K".
- **TikTok** — `--plt-tiktok` rounded square + white stylised "d".
- **Pinterest** — `--plt-pinterest` circle + white "P".

All marks live in `components/chrome/logos.py`. They render in three
places: Platform Overview section headers, Channel Attribution column
headers (the TrackBee mark in front of the TrackBee Purchases /
TrackBee Revenue columns), and Channel Attribution rows.

## Copy tone

Every observation and recommended action reads like product copy, not
internal Slack. The voice is direct, declarative, and quantified.

Prefer:

- "Meta contributes 38% of attributed revenue. Protect its budget."
- "Klaviyo is the dominant top-of-funnel channel."
- "Treat Meta and Klaviyo as a joint investment."
- "Discount this channel's in-platform ROAS by ~30% when comparing across channels."

Each insight pairs an observation with a recommended action. The action
is the part that turns a dashboard into a decision.

## Glossary

- **Blended metric** — combines all platforms / sources, used for store-wide views (e.g. Blended ROAS).
- **In-platform metric** — reported directly by the ad platform (Meta, Google).
- **TrackBee-attributed metric** — first-party, from TrackBee's pixel and click-id matching.
- **Cooccurrence** — fraction of journeys that include both platform A and platform B.
- **Single-touch share** — fraction of converting journeys where the shopper had exactly one tracked touchpoint.
- **NC** — new customer (first-ever order, identified by email).
- **NC-ROAS / NC-CPA** — same as ROAS / CPA but using new-customer revenue / orders.
- **MER** — Marketing Efficiency Ratio. For web-only stores, identical to Blended ROAS.
- **Acquisition MER** — Blended NC-ROAS — the headline retention-led growth metric.
