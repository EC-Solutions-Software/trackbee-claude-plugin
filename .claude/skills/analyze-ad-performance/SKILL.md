---
name: analyze-ad-performance
description: >-
  Analyze ad performance across the funnel — find ads that get great reach but
  poor ROAS, decide whether to scale or kill campaigns, and track what happens
  when budgets change. Use this skill when someone asks about ad performance,
  scaling decisions, budget changes, ROAS problems, or top-of-funnel vs
  bottom-of-funnel mismatches.
---

# Analyze Ad Performance

Find the disconnect between top-of-funnel wins and bottom-of-funnel losses. Help the user decide what to scale, what to adjust, and what to kill.

## Workflow

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to analyze. They can provide the store name or store ID.

### 2. Understand the question

Ask the user what they want to analyze. Common starting points:

- **Funnel mismatch**: "Which ads look good on reach but have bad ROAS?"
- **Scaling decision**: "This ad moved to scaling — can we push more budget?"
- **Budget tracking**: "Which ads were increased recently and what happened?"

Clarify the **platform** (Meta, Google, or both) and **time period**. Default to the last 30 days if they don't specify.

Also ask: **Are any of your campaigns test campaigns?** If so, which ones — and do you want to include them in the results? Exclude test campaigns by default unless the user explicitly asks to include them.

### 3. Pull the data

Start at campaign level to get the lay of the land, then drill into ad level for the actual analysis:

**Meta:**
1. `get_meta_campaign_insights` — Campaign overview to identify active campaigns and their spend
2. `get_meta_ad_insights` — **This is where the real analysis happens.** Pull ad-level data for each significant campaign. This gives you per-ad spend, ROAS, CTR, CPM, frequency, net new reach, and creative content

**Google Ads:**
1. `get_google_campaign_insights` — Campaign overview with spend, conversions, and new vs returning customer breakdown
2. `get_google_ad_insights` — Ad-level data within a specific campaign, including new vs returning customer conversions per ad

**Both platforms:**
- `detect_anomalies` — Spot sudden changes in performance

Campaign-level data is a starting point to find which campaigns to drill into. Always go to ad level for conclusions — campaign averages hide the winners and losers.

### 4. Analyze across the funnel

For each ad, compare:

| Metric | Top-of-funnel signal | Bottom-of-funnel signal |
| --- | --- | --- |
| Reach | High impressions, low CPM | — |
| Engagement | High CTR | — |
| Conversion (immediate) | — | High purchases_1d_click — impulse buys |
| Conversion (delayed) | — | High purchases_28d_click but low 1d — considered purchases |
| View-through | High purchases_1d_view — awareness impact | — |
| New customers | — | High new_customer_conversions — acquiring new buyers |
| Returning customers | — | High returning_customer_conversions — re-engaging existing buyers |
| Revenue | — | Revenue relative to spend |

Flag ads where top-of-funnel looks strong but bottom-of-funnel is weak. These are the most actionable — the creative works for attention but doesn't convert.

IMPORTANT — how attribution windows work:
- Click windows are **cumulative** (nested, not additive): 1d_click ⊂ 7d_click ⊂ 28d_click. Every 1d_click purchase is also counted in 7d_click and 28d_click. Never sum them.
- 1d_view is **separate**: view-only conversions from people who saw the ad but did NOT click. Does not overlap with click windows.
- The default `purchases` field = 7d_click + 1d_view (Meta's standard attribution).
- To find delayed click conversions: 28d_click - 7d_click = purchases that happened between day 8 and day 28 after clicking.

Use attribution windows to avoid false negatives: an ad with low purchases_1d_click but strong purchases_28d_click is working as upper funnel — Meta's algorithm is placing it for users who need time to decide. Don't kill it for low immediate ROAS.

### 5. New vs returning customer analysis

Both platforms can report new vs returning customer breakdowns, but via different mechanisms:

- **Google Ads**: `new_customer_conversions` and `returning_customer_conversions` per campaign and ad (from Google's own segmentation using the server-side new_customer tag)
- **Meta**: `new_customer_purchases` and `returning_customer_purchases` per campaign and ad (from TrackBee's custom conversion events — NewCustomerPurchase and ReturningCustomerPurchase). Meta fields may be null if the ad account doesn't have these custom conversions configured.

Use these to assess acquisition efficiency:

- **New customer ratio**: new / total — high ratio means the campaign is acquiring, not just re-engaging
- **New customer CAC**: spend / new_customer_purchases (or new_customer_conversions) — the real cost of acquiring a new buyer. Compare across campaigns to find the cheapest acquisition channels
- **New customer ROAS**: new_customer_revenue / spend — revenue efficiency for new customers specifically
- A campaign with strong total ROAS but low new customer ratio may just be re-converting existing customers. That's valuable but not growth.
- A campaign with modest total ROAS but high new customer ratio is driving growth — it may deserve more budget even if headline ROAS is lower

Note: new + returning may not exactly equal total conversions. For Google, some have UNKNOWN customer status. For Meta, the custom events may differ slightly from the standard purchase event due to attribution.

### 6. Scaling assessment

For ads the user wants to scale, evaluate:

- **Current spend vs results**: Is ROAS stable or declining as spend increases?
- **Frequency**: Is the audience getting saturated? (frequency > 3 is a warning)
- **CPM trend**: Rising CPM with flat results means diminishing returns
- **Net new reach** (Meta): Is the ad still finding fresh audience? Check `net_new_reach` from `get_meta_ad_insights` — this counts users reached who were NOT reached in the prior 90 days, which is different from the standard reach in Ads Manager. A low net-new-reach-to-reach ratio means the ad is mostly re-showing to the same people. If net new reach is drying up, scaling more budget will just increase frequency without expanding your audience
- **New customer trend** (Google Ads): Is the campaign still acquiring new customers? Declining `new_customer_conversions` while total conversions hold steady means you're scaling into existing customers, not new ones
- **Audience size**: Can the target audience sustain more spend?

Give a clear recommendation:
- **Scale**: ROAS is stable, frequency is low, CPM is flat, net new reach is healthy, new customer ratio is strong — push more budget
- **Hold**: Results are okay but showing early signs of fatigue (net new reach declining, frequency creeping up, new customer ratio dropping) — monitor closely
- **Kill**: ROAS is declining across all attribution windows, frequency is high, CPM is rising, net new reach is near zero — stop spending
- **Reclassify as upper funnel**: Low 1d_click ROAS but strong 28d_click or 1d_view conversions — the ad drives delayed or view-through conversions. Don't kill it; evaluate it on its upper-funnel contribution

### 7. Budget change tracking

When the user asks what happened after budget changes:

1. Identify campaigns where spend increased or decreased significantly
2. Compare performance metrics before vs after the change
3. Show whether the increased spend maintained efficiency or diluted results

### 8. Present findings

Structure the response as:

1. **Summary**: One-sentence verdict (e.g., "3 of your 12 active ads have strong reach but poor conversion")
2. **Top performers**: Ads worth scaling, with supporting numbers
3. **Problem ads**: Ads with funnel mismatches, with specific metrics
4. **Recommendations**: Clear next steps — scale, adjust targeting, refresh creative, or kill

---

## Guidelines

- Always use TrackBee MCP tools for data — never guess at numbers
- Use consistent date ranges when comparing performance
- Surface actionable recommendations, not just data dumps
- Consider the full funnel — an ad can look great on reach but terrible on conversions
- Flag when data is insufficient to draw conclusions (short date ranges, low spend, etc.)

## Glossary

- TOF (top-of-funnel): awareness and reach — impressions, CPM, CTR, video views
- BOF (bottom-of-funnel): conversions — purchases, ROAS, CPA, revenue
- CPM: cost per 1,000 impressions
- CTR: click-through rate
- ROAS: return on ad spend (revenue / spend)
- CPA: cost per acquisition (spend / purchases)
- Frequency: average number of times a person has seen your ad
- Creative fatigue: when an audience has seen an ad too many times and engagement drops
- Net new reach: users reached during a period who were NOT reached in the prior 90 days — different from standard reach in Ads Manager
- Cost per net new reach: spend / net new reach — lower means more efficient at finding fresh audiences
- Attribution window: the time period after an ad interaction during which a conversion is credited. Click windows are cumulative (1d_click ⊂ 7d_click ⊂ 28d_click — never sum them). 1d_view is separate (view-only, no click). Default purchases = 7d_click + 1d_view.
- View-through conversion (1d_view): a purchase after someone saw an ad but didn't click — separate from click windows
- New customer conversions (Google Ads): orders from first-time buyers, as determined by Google using TrackBee's server-side new_customer tag. Use to calculate new customer CAC and acquisition ROAS.
- Returning customer conversions (Google Ads): orders from repeat customers. High returning ratio means the campaign re-engages existing buyers rather than acquiring new ones.
- New customer purchases (Meta): orders from first-time buyers, from TrackBee's NewCustomerPurchase custom conversion event. Null if the ad account doesn't have this configured.
- Returning customer purchases (Meta): orders from repeat customers, from TrackBee's ReturningCustomerPurchase custom conversion event. Null if not configured.
