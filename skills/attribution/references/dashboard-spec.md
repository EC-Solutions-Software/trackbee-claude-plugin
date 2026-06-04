# Attribution Overview — per-section design spec

Design reference for the **attribution** skill. The runtime contract
lives in `SKILL.md`; this file describes what each section of the HTML page
looks like, how the copy reads, and which brand tokens it uses. Open it only
when modifying a component or designing a new variant.

For metric → TrackBee-field mappings, see `metric-map.md`.
For the chat hand-off after a render, see `handoff-template.md`.

## Sections, top to bottom

The page is one scrollable column. No tabs.

1. **Header strip** — brand wordmark + "Attribution Report" + store name + window filter.
2. **Executive Summary** — 3–4 plain-English takeaways for the active window.
3. **Blended Overview** — KPI tiles + Blended NC-ROAS daily line chart.
4. **Platform Overview** — per-platform tiles (Meta, Google, …) for the active window.
5. **Channel Attribution** — per-channel table (TrackBee + in-platform sides) + {observation, action} insight cards.
6. **Customer Journeys** — three KPI tiles, touch-points heatmap + insights, sankey with view filter + insights. *Removed entirely when the store has no shopper profiles.*
7. **Store Funnel Analysis** — page view → order, with the biggest leak flagged and stage-specific fix-it insights.
8. **Where to go next** — a grid of clickable follow-up prompts.
9. **Footer** — generated date, caveats list, low-contrast wordmark.

A 3d / 7d / 28d filter at the top swaps the Executive Summary, Blended
Overview, Platform Overview, Channel Attribution, and Store Funnel Analysis
against the chosen window. Customer Journeys is **not** window-scoped — it
uses a fixed 90-day server-side lookback (its input is the 28d range chosen
at build time).

All windowed sections are baked into `PAGE_DATA` for all three windows and
rehydrated client-side by `components/chrome/app.js`. The two SVG charts and
the heatmap are pre-rendered server-side and toggled with `display`.

## 1. Header strip

- Wordmark (icon + "TrackBee" lockup) on the left, a thin vertical divider,
  then **"Attribution Report"** as the `h1` with the store name in
  `--ink-muted` underneath.
- **Date filter** as a segmented pill — 3 days / 7 days / 28 days, default 28d.
- The window range, store currency, and ad-account FX live in the footer
  caveats, not under the `h1`.

## 2. Executive Summary

Dark surface (`--ink` gradient), `--yellow` numbered counters, white prose.
Each takeaway is one sentence with a number, computed per window (updates on
filter toggle). Produced by `components/insights/executive_summary.py`:

1. **Headline performance** — revenue + orders + ad spend + Blended ROAS, with a delta vs the previous equal-length period.
2. **Top contributing channel** — largest share of attributed revenue (skipped when the "Overall" row is the max). Ends "Protect its budget."
3. **Scale or cut** — names the highest-ROAS paid channel when it clears ROAS ≥ 2.
4. **Earned-revenue / over-credit risk** — the largest zero-spend channel's assisted revenue as an incrementality-test candidate.

Monetary values format through the store-currency formatter
(`components/chrome/format_helpers.py`) — the prose never hardcodes a symbol.

## 3. Blended Overview

### 3.1 KPI tiles

Responsive grid for the active window: Ad spend, Revenue, New customers,
Orders, AOV, Blended ROAS, Blended CPA, Blended NC-CPA, Blended NC-ROAS,
Sessions, Added-to-cart rate, Started checkout rate, Conversion rate, Revenue
/ session. Each tile: label, big value, ▲/▼ delta vs the previous period.
Tiles render client-side in `app.js`; values format via `Intl.NumberFormat`
driven by the store currency.

### 3.2 Blended NC-ROAS (Acquisition MER) over time

Daily line chart under the tiles. Heading "Blended NC ROAS (Acquisition MER)
over time", subtitle "Daily new-customer revenue ÷ daily ad spend." Period
avg shown in the header and as a dashed `--gold` line. Pre-rendered inline
SVG by `components/charts/nc_roas.py` (area fill, data points with hover
tooltips, thinned MM-DD x labels) — no chart library. The active window's SVG
is shown; the others are hidden `<div data-w="…">` blocks toggled by the
filter.

## 4. Platform Overview

Each platform with ad insights gets a row of tiles: ROAS (in-platform),
Revenue (in-platform), Ad spend, CTR, CPC, CPM, Impressions, Clicks,
Purchases. Meta and Google render whenever data is fetched. Refer to Facebook
as **"Meta"** in copy (the MCP key is `facebook`). Each platform header shows
its 14×14 inline SVG mark.

## 5. Channel Attribution

A single table: Channel · Sessions · Purchases · Revenue · Spend · CPA · ROAS.
Built dynamically from `tool__get_platform_funnel_breakdown.platforms.keys()`,
with a final "Overall" row. Rules:

- Em-dash (`—`) for missing values, never zero.
- The Purchases / Revenue cells prefer in-platform figures, falling back to
  TrackBee figures for zero-spend channels.
- **Spend, CPA, ROAS are pure in-platform** so they reconcile with Platform
  Overview to the cent (see metric-map.md).

Below the table, a **"Key insights from your channel attribution"** card list
(`--blue-tint`, observation + `Recommended action:`), computed by
`components/insights/channel_attribution.py`: ROAS spread across paid
channels, the CPA gap (cheapest vs priciest), an underinvested high-ROAS
channel, a zero-spend earned channel, and any paid channel below 2× ROAS that
still holds >10% of spend.

## 6. Customer Journeys

Uses the 28d input window. Assembled from `tool__get_platform_footprints`,
`tool__get_platform_breakdown`, and `tool__get_platform_journeys` (see
SKILL.md §Customer Journeys adapter). Heading is plain **"Customer Journeys"**.

When the store has no shopper profiles (`total_journeys == 0` and no
`co_occurrence`), the orchestrator removes the entire section from the DOM
(no empty card) and strips the 90-day-lookback caveat from the footer.

### 6.1 Three KPI tiles

Total customer journeys, Single-touch share, Multi-touch share — formatted
via `format_helpers.py`.

### 6.2 Touch-points heatmap

Square grid: "When a customer interacts with platform A, how often do they
interact with platform B?" Rows/cols auto-derived from the co-occurrence
matrix, well-known platforms pinned first. The **diagonal is 100%**, rendered
on `--ink` with `--yellow` text as a structural marker; off-diagonal cells
use an `--accent` → `--blue-tint` intensity gradient. Plain HTML `<table>`
with inline `background-color` — built by `components/transforms/heatmap.py`.
Followed by a **"Key insights from your channel touch points"** card list
(`components/insights/cooccurrence.py`): most-coupled pair, channels that
rarely converge, channels that stand alone, asymmetric dependencies, and a
reading-the-matrix line. A per-platform 50-order sample guard applies.

### 6.3 Sankey

One sankey across all platforms, with a segmented view filter: Multi-touch
only (default), Top 5 journeys, Single-touch only, All journeys. All four
views are pre-rendered server-side by `components/charts/sankey_svg.py`
(column layout, cubic-bezier links coloured by source platform, hover
tooltips); the JS toggle swaps the visible `<div data-sv="…">`. Empty views
render a plain "No journeys match this filter" state. Path union + view
construction live in `components/transforms/journeys.py`. Followed by a
**"Key insights from your customer journeys"** card list
(`components/insights/journey.py`): top opener, top closer, most frequent
journey, cross-platform share, median depth, single-touch share.

## 7. Store Funnel Analysis

Window-scoped (responds to the top filter). Header shows the active window
pill. Two summary stats — "Top to order" (page view → order rate) and
"Biggest leak" (worst step-to-step stage + rate). Then a horizontal bar per
stage (count + step-to-step rate + "from X — N lost" + "% of page views
reach this step"). Below, a **"Key insights from your store funnel"** card
list from `components/insights/funnel.py` — one entry per leaking stage,
tuned to that stage's UX levers, worst-first. The page view → product view
drop is excluded from "worst" by default (browsing behaviour) and only
surfaced when below 25%.

## 8. Where to go next

A grid of clickable follow-up prompts computed from the 28d window
(`components/insights/questions.py`): diagnose the biggest funnel leak, break
down / scale the top paid channel, reconcile platform vs TrackBee numbers,
and a journey-incrementality question (or a top-channel creative question
when the store has no profiles). In a live artifact (`window.sendPrompt`
present) clicking sends the prompt; otherwise it copies to the clipboard.

## 9. Footer

Caveats list — generated date, the window range + store currency + ad-account
FX, the client-side `checkout_started` note, the in-platform-vs-TrackBee note,
and any low-sample-platform caveat the orchestrator stamps. Low-contrast
wordmark at the bottom.

## Brand tokens

The tokens live in `components/chrome/theme.css` — the single source of
truth; do not duplicate or fork them. Key values:

```css
--ink:#040F24; --ink-2:#21283B; --ink-muted:#696E7C;
--line:#CCD1DF; --surface-0:#FAFAFA; --surface-1:#FFFFFF;
--accent:#0072FF; --blue-tint:#DFEAFB; --gold:#E79810; --yellow:#FEC119;
--font-display:'PP Formula','Inter Tight','Inter',system-ui,sans-serif;
--font-body:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
```

Platform colours (per-platform tiles + table icons): Meta `#1877F2`, Google
`#4285F4`, Klaviyo `#7C3AED`, TikTok `#000000`, Pinterest `#E60023`, Email
`#696E7C`.

## Brand marks

The TrackBee icon and wordmark are bundled as `assets/tb_icon_b64.txt` and
`assets/tb_wordmark_b64.txt`; the orchestrator inlines them as
`<img src="data:image/png;base64,…">` at build time. Per-channel 14×14 inline
SVG marks (Meta, Google, Klaviyo, TikTok, Pinterest, Microsoft Ads, Calendly,
TrackBee) live in `components/chrome/logos.py` and are embedded into
`PAGE_DATA.logos` for the client-side renderer.

## Copy tone

Every observation and recommended action reads like product copy — direct,
declarative, quantified. Each insight pairs an observation with a recommended
action; the action is what turns a report into a decision.

## Glossary

- **Blended metric** — combines all platforms / sources (e.g. Blended ROAS).
- **In-platform metric** — reported directly by the ad platform.
- **TrackBee-attributed metric** — first-party, from TrackBee's pixel + click-id matching.
- **Co-occurrence** — fraction of journeys that include both platform A and B.
- **Single-touch share** — fraction of converting journeys with exactly one tracked touchpoint.
- **NC** — new customer (first-ever order).
- **NC-ROAS / NC-CPA** — ROAS / CPA using new-customer revenue / orders.
- **Acquisition MER** — Blended NC-ROAS, the headline retention-led growth metric.
