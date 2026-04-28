---
name: scale-ads-profitably
description: >-
  Decide whether to push more ad spend without breaking profitability — adjust
  ROAS targets for new-vs-returning customer mix, cross-ad and cross-platform
  influence, true unit economics (discounts, shipping, fees, COGS), leading
  indicators that predict tomorrow's ROAS, and Google Ads brand cannibalization.
  Use this skill when someone asks how to scale profitably, whether their ROAS
  target is reliable, whether to increase budgets, or whether their reported
  ROAS reflects real incremental profit.
---

# Scale Ads Profitably

A ROAS target is a proxy for profitability, not profitability itself. This skill walks through the six things that make a ROAS target lie — new-vs-returning mix, cross-ad influence, cross-platform influence, true unit economics, leading-indicator drift, and Google brand cannibalization — and turns them into a per-channel scaling verdict the merchant can act on.

## Workflow

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to analyze. They can provide the store name or store ID.

### 2. Establish the ROAS target

Before pulling any data, anchor the conversation:

- **What is your current ROAS target per platform?**
- **How was it derived?** Three common answers:
  - **Margin-based**: `1 / contribution_margin` (e.g., 35% contribution margin → 2.86× breakeven). Most defensible.
  - **Payback-based**: a multiple that covers CAC over an expected customer lifetime (LTV/CAC).
  - **Rule-of-thumb**: an inherited number ("we run at 3×"). Treat with caution — step 7 will recompute it.

Record the targets. Every later step adjusts them.

### 3. Measure blended ROAS by platform & campaign

Default to the **last 30 days** unless the user specifies. Pull at the campaign level first:

- **Meta**: `get_meta_campaign_insights` — `spend`, `purchase_roas`, `purchases`, `cost_per_purchase`, `new_customer_purchases`, `new_customer_revenue`, `returning_customer_purchases`, `returning_customer_revenue`
- **Google**: `get_google_campaign_insights` — `spend`, `conversions`, `conversions_value`, `new_customer_conversions`, `new_customer_conversions_value`, `returning_customer_conversions`, `returning_customer_conversions_value`, plus `branded_search_analysis` for Search campaigns
- **TikTok / Pinterest**: `get_campaign_performance` with `platform="tiktok"` or `platform="pinterest"` — only `spend`, `impressions`, `clicks` are available; ROAS must be approximated using attributed orders elsewhere

IMPORTANT — currency: campaign spend is reported in **ad-account currency**, not store currency. Both `ad_account_currency` and `store_currency` are returned. Convert before comparing platforms.

### 4. Adjust for new-vs-returning customer mix

A high blended ROAS is misleading if most of the revenue is repeat customers you would have kept anyway. Compute, per channel:

| Metric | Formula |
| --- | --- |
| New-customer ROAS | `new_customer_revenue / spend` |
| New-customer CAC | `spend / new_customer_purchases` |
| New-customer ratio | `new_customer_purchases / total_purchases` |

Cross-reference store-level totals from `get_daily_store_statistics` with column group `customer_segments` (`total_new_customer_orders`, `total_new_customer_revenue`, `total_returning_customer_orders`, `total_returning_customer_revenue`) to sanity-check the platform splits.

Make the explicit point to the user:

- A campaign at **2× new-customer ROAS** can be worth more than a campaign at **4× returning-customer ROAS** — the second campaign is largely re-converting buyers you already had.
- A campaign with strong total ROAS but a low new-customer ratio is harvesting, not growing.
- A campaign with modest total ROAS and a high new-customer ratio is a growth lever — even if its headline ROAS sits below target.

For a per-ad breakdown of new-vs-returning, defer to the `analyze-ad-performance` skill and don't re-derive scale/hold/kill verdicts here.

Note: Meta's new/returning fields can be null when the ad account doesn't have TrackBee's `NewCustomerPurchase` / `ReturningCustomerPurchase` custom conversions configured. Flag this and continue with what you have.

### 5. Adjust for cross-ad influence

A single ad's reported ROAS depends on other ads in the same journey. Pull:

- `get_store_ad_touchpoint_dynamics` — per-ad `journeys`, `touches`, `opener`, `closer`, `solo`, `avg_position` (week-old snapshot, 365-day lookback)
- `get_store_ad_influence` with `granularity="ad"` — daily snapshot, 60-day lookback per journey, with tier distribution and top patterns
- `get_ad_journey_breakdown` for any specific `ad_id` the user wants to drill into (ad must appear in ≥3 journeys)

Read out:

- **Opener-heavy ads**: most touches start the journey. Their reported ROAS is understated — they create demand a closer captures.
- **Closer-heavy ads**: most touches finish the journey. Their reported ROAS is overstated — they harvest demand an opener created.
- **Solo ads**: single-touch conversions. Their reported ROAS is the truest reflection of incremental impact.

The point: **cutting an opener can collapse a closer's ROAS.** If the user is about to pause a "low-ROAS" upper-funnel ad to reallocate budget to a "high-ROAS" closer, walk them through the dependency before they do.

### 6. Adjust for cross-platform influence

Same logic, one level up. Pull:

- `get_store_platform_touchpoint_dynamics` — co-occurrence matrix, transition matrix, single-touch share across Meta, Google, TikTok, Pinterest, Klaviyo, Bing
- `get_platform_journey_breakdown` with the platform in scope — collapsed sequences of platform names
- `get_store_ad_influence` with `granularity="platform"` — tier distribution (`0_no_ad`, `1`, `2_to_3`, `4_plus`) and top platform patterns

Read out:

- **Single-touch share**: high single-touch on a platform means it converts on its own. Low single-touch means it depends on assists.
- **Transition matrix**: which platforms feed which. A common pattern is Meta → Google Search; Meta opens, Google brand search closes.
- **Tier distribution**: if a large share of orders sit in `4_plus`, the journey is paid-touch-heavy; cutting any platform risks downstream fallout.

The point: **scaling a closer platform without scaling its opener will not produce incremental orders** — you will simply pay more per existing journey. Pair scaling decisions across platforms.

### 7. Adjust for true unit economics

**Gap to flag explicitly to the user**: TrackBee MCP does not currently surface order-level discounts, shipping revenue/cost, payment-processor fees, refunds, or COGS. There is no tool that returns these. Ask the user to provide blended values:

- Gross margin % (after COGS)
- Average discount % off list
- Shipping margin (revenue minus carrier cost, as % of order)
- Payment-processor fee % (Shopify Payments / Stripe / etc.)
- Refund / chargeback rate %

Then compute:

```
contribution_margin% = gross_margin%
                       − discount%
                       − shipping_loss%
                       − payment_fee%
                       − refund_rate%
breakeven_ROAS       = 1 / contribution_margin%
true_profit_ROAS     = (revenue × contribution_margin%) / spend
```

Compare each channel's blended ROAS to **`breakeven_ROAS`**, not to the user's rule-of-thumb target. A channel at 3× headline ROAS with 25% contribution margin is at break-even (1 / 0.25 = 4×) and is not actually profitable to scale. Conversely, a channel at 2× headline ROAS with 60% contribution margin is comfortably above break-even (1.67×) and can take more spend.

If the user can't supply the inputs, give them a working default range (gross margin 40–60%, discount 10–20%, shipping loss 0–5%, payment fee 2–3%, refund rate 2–5%) and label every output as an estimate.

### 8. Check forward-looking sustainability

Today's profitable ROAS doesn't guarantee tomorrow's. Pull leading indicators per scalable channel:

- **Meta**: `get_meta_ad_insights` — `ctr`, `cpm`, `frequency`, `net_new_reach`, `cost_per_net_new_reach`
- **Google**: `get_google_ad_insights` — `ctr`, `average_cpc`, video-retention quartiles
- **Both**: `detect_anomalies` over the same window to catch funnel-rate or revenue anomalies

Flag any of:

- Rising **CPM** with flat or falling **CTR** → auction is getting more expensive without the creative compensating
- Rising **`cost_per_net_new_reach`** or falling **`net_new_reach`** → the audience is saturating; more budget will mostly increase frequency
- **Frequency > 3** → wear-out risk
- **CPC drift up** with conversions flat → Google auction pressure
- Anomalies in store-level funnel rates from `detect_anomalies` → upstream issue (site speed, checkout, supply)

Don't re-derive creative-fatigue analysis here — defer to `audit-creatives`. Don't re-derive audience-saturation diagnosis — defer to `diagnose-audience-health`.

### 9. Check Google Ads brand cannibalization

For every Google **Search** campaign in `get_google_campaign_insights`, read the `branded_search_analysis` object:

- `branded_click_share` — % of clicks driven by branded queries (your store name, product brand)
- `cannibalization_risk` — `high` / `medium` / `low`
- `top_branded_terms` and `top_non_branded_terms`

`branded_search_analysis` is only populated for Search campaigns; Display, Shopping, and Performance Max won't have it.

The point: a high `branded_click_share` means the campaign's ROAS is propped up by demand created elsewhere — branded searchers were going to find you anyway. Scaling its budget will not produce incremental revenue, only shift attribution from organic to paid. The right action is usually to **cap budget at current branded query volume** and reallocate the rest to non-brand or to upper-funnel platforms that create the demand.

This signal is point-in-time per date range — TrackBee does not currently expose a brand-cannibalization trend. If the user wants a trend, run the same analysis across two consecutive windows manually.

### 10. Synthesize the scaling decision

Produce one verdict per channel — not per ad. Anchor each verdict to:

- **Step 7 breakeven ROAS** (am I above the line at all?)
- **Step 4 new-customer contribution** (is this growth or harvest?)
- **Steps 5–6 cross-influence** (does this channel pay for, or get paid by, another?)
- **Step 8 leading indicators** (will tomorrow's ROAS hold?)
- **Step 9 brand cannibalization** (is the ROAS even incremental?)

| Verdict | When |
| --- | --- |
| **Scale** | Above breakeven ROAS, healthy new-customer ratio, leading indicators stable or improving, no cannibalization concern, and the channel is a closer that has a paired opener still funded |
| **Hold** | Above breakeven but at least one warning sign (frequency creeping up, net-new-reach declining, branded share rising) |
| **Pull back** | Below breakeven on contribution-margin terms, or harvesting branded demand, or a closer whose opener has been cut |
| **Reallocate** | The channel is fine on its own but one of its dependencies (opener, creative, audience) is the actual constraint — fix that first |

End with one concrete next action for the merchant — e.g., "raise Meta prospecting budget 20% next week, freeze Google brand budget at current spend, pull TikTok back 30% pending creative refresh, revisit in 14 days."

---

## Guidelines

- Always pull data via TrackBee MCP tools — never guess at numbers
- Use the same date range for every step in a single analysis so the picture is consistent
- Defer per-ad scale/hold/kill verdicts to `analyze-ad-performance`; this skill is portfolio-level
- Defer creative-fatigue diagnosis to `audit-creatives`
- Defer audience-health diagnosis to `diagnose-audience-health`
- Flag insufficient data — short windows, low spend, or null new/returning fields — before drawing a verdict
- Never invent fields. TrackBee does not surface order-level discounts, shipping, fees, refunds, COGS, GA4 data, TikTok/Pinterest new-vs-returning splits, a unified cross-platform new-customer ROAS, or a brand-cannibalization trend. Ask the user for the missing inputs or label outputs as estimates

## Glossary

- Breakeven ROAS: `1 / contribution_margin%`. The ROAS at which the merchant earns zero profit on the marginal order. Scaling below this number loses money.
- Contribution-margin ROAS: blended ROAS adjusted for gross margin, discounts, shipping margin, payment fees, and refunds. The number to compare against breakeven.
- True profit: `revenue × contribution_margin% − spend`. The actual euros (or dollars) the channel adds to the bottom line, not its top-line ROAS.
- New-customer CAC: `spend / new_customer_purchases` (Meta) or `spend / new_customer_conversions` (Google). The real cost of acquiring a first-time buyer in a channel.
- Blended CAC: `total_spend / total_new_customers` across all channels. Useful as a portfolio-level guardrail.
- Opener: an ad or platform that frequently appears at the start of a conversion journey. Tends to have understated reported ROAS.
- Closer: an ad or platform that frequently appears at the end of a conversion journey. Tends to have overstated reported ROAS.
- Solo touch: a single-platform, single-ad journey. Reported ROAS reflects true incremental impact.
- Cross-platform tier: how many distinct platforms touched a journey, bucketed as `0_no_ad`, `1`, `2_to_3`, `4_plus`. High `4_plus` share means journeys are paid-touch-heavy and cross-influence matters more.
- Branded click share: % of a Google Search campaign's clicks coming from branded queries. High share signals harvested demand, not created demand.
- Cannibalization risk: TrackBee's `high` / `medium` / `low` summary of branded click share for a Search campaign. Treat `high` as a sign that scaling the campaign won't produce incremental revenue.
- Incremental ROAS: the ROAS attributable to spend that would not have happened without the ad. Branded harvesting and closer-only campaigns systematically overstate reported ROAS relative to incremental ROAS.
- Net-new-reach trend: how `cost_per_net_new_reach` and `net_new_reach` are moving over consecutive windows — distinct from the point-in-time net-new-reach metric used in `analyze-ad-performance`. A worsening trend is the earliest leading indicator that scaling will hit diminishing returns.
