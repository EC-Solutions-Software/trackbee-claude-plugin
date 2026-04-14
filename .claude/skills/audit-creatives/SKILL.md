---
name: audit-creatives
description: >-
  Audit creative performance — detect fatigue, measure creative lifetime,
  compare content types per product, and suggest what to create next. Use this
  skill when someone asks about creative fatigue, ad lifetime, which content
  types work best, what content to produce, or wants suggestions for new
  creatives.
---

# Audit Creatives

Understand which creatives are working, which are dying, and what to make next. This skill covers fatigue detection, lifetime analysis, content type performance, and production recommendations.

## Workflow

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to analyze. They can provide the store name or store ID.

### 2. Understand what the user needs

Common starting points:

- **Fatigue check**: "Are any of my creatives showing fatigue?"
- **Lifetime analysis**: "How long do my video ads last before performance drops?"
- **Content comparison**: "What type of content works best for [product]?"
- **Production guidance**: "What should I create next?"

Clarify the **platform** and whether they want to look at all creatives or a specific product/campaign.

Also ask: **Are any of your campaigns test campaigns?** If so, which ones — and do you want to include them in the results? Exclude test campaigns by default unless the user explicitly asks to include them.

### 3. Pull creative data

Campaign level gives you context; ad level gives you the answer:

**Meta:**
1. `get_meta_campaign_insights` — Identify active campaigns to drill into
2. `get_meta_ad_insights` — **The primary data source.** Returns per-ad performance (CTR, ROAS, CPA, frequency, net new reach) plus full creative content (format, copy, image/video URLs). This is where fatigue detection and content-type analysis happen
3. `get_meta_recommendations` — Platform-specific improvement suggestions

**Google Ads:**
1. `get_google_campaign_insights` — Campaign overview with new vs returning customer breakdown
2. `get_google_ad_insights` — Ad-level performance with new vs returning customer conversions per ad

**Both platforms:**
- `detect_anomalies` — Spot sudden performance drops

Request a long enough time range to see creative lifecycle trends — at least 30 days, ideally 60-90 days.

### 4. Detect creative fatigue

A creative is fatigued when its performance degrades over time despite stable or increasing spend. Check for:

| Indicator | What to look for |
| --- | --- |
| **CTR decline** | Steady drop over 2+ weeks — people stop clicking |
| **CPA increase** | Rising cost per acquisition — conversions get more expensive |
| **Frequency spike** | Same audience seeing the ad too often |
| **ROAS decline** | Diminishing returns on spend |
| **Net new reach drop** | Ad is no longer finding fresh audience (Meta only — check `net_new_reach` from `get_meta_ad_insights`) |

Compare current performance (last 7 days) against the creative's peak performance period. A creative that once had 2% CTR and now has 0.8% is fatigued.

Use attribution windows to avoid premature kills: if purchases_1d_click drops but purchases_28d_click holds steady, the creative still has residual impact — it's shifted to upper-funnel behavior rather than being fully fatigued.

For Google Ads and Meta, also check the new customer trend: `new_customer_conversions` (Google) or `new_customer_purchases` (Meta, when available). A creative where total conversions hold but new customer counts drop is fatiguing specifically on acquisition — it's only re-engaging existing customers.

### 5. Measure creative lifetime

For each content type (video, static image, carousel, etc.):

1. Identify when the creative launched (first day with impressions)
2. Find the peak performance period (highest CTR or ROAS window)
3. Find when performance dropped below a useful threshold
4. Calculate the active lifetime: launch to performance drop

Report average lifetime by content type:

- "Your video ads typically peak in week 2 and fatigue by week 5"
- "Static images have a shorter lifecycle — about 2-3 weeks before fatigue sets in"

### 6. Compare content types per product

If the user has multiple products or product categories:

1. Group creatives by product and content type
2. Compare key metrics: CTR, ROAS, CPA, lifetime, and attribution window patterns
3. Identify which content types win for each product

Example findings:
- "For [Product A], video ads outperform static images on ROAS (3.2x vs 1.8x) and last twice as long before fatigue."
- "Video ads show significantly more view-through conversions (1d_view) than static images — they build brand recall even without clicks."
- "Carousel ads drive mostly 1d_click conversions — they work as direct-response, not awareness."

### 7. Suggest what to create next

Based on the analysis, recommend:

- **Replace fatigued creatives**: "These 3 ads are past their prime — prioritize replacements"
- **Double down on what works**: "Video content for [Product A] consistently outperforms — create more variations"
- **Fill gaps**: "You have no carousel ads for [Product B] — worth testing since carousels perform well for similar products"
- **Content themes**: If certain angles or messages perform better, call them out

### 8. Present findings

Structure the response as:

1. **Fatigue report**: Which creatives are fatigued, with evidence
2. **Lifetime summary**: Average lifetime by content type
3. **Top performers**: What's working and why
4. **Production recommendations**: What to create next, in priority order

---

## Guidelines

- Always use TrackBee MCP tools for data — never guess at numbers
- Use consistent date ranges when comparing performance
- Surface actionable recommendations, not just data dumps
- Flag when data is insufficient to draw conclusions (short date ranges, low spend, etc.)

## Glossary

- Creative fatigue: when an audience has seen an ad too many times and engagement drops
- CTR: click-through rate
- ROAS: return on ad spend (revenue / spend)
- CPA: cost per acquisition (spend / purchases)
- Frequency: average number of times a person has seen your ad
- Creative lifetime: the period from launch to when performance drops below a useful threshold
- Net new reach: users reached during a period who were NOT reached in the prior 90 days — confirms fatigue when it drops alongside CTR
- Attribution window: time after an ad interaction during which a conversion is credited. Click windows are cumulative (1d_click ⊂ 7d_click ⊂ 28d_click — never sum them). 1d_view is separate (view-only, no click). Default purchases = 7d_click + 1d_view.
- View-through conversion (1d_view): purchase after seeing an ad without clicking — separate from click windows. Video ads typically show more of these than static.
- New customer conversions (Google Ads): orders from first-time buyers. A creative losing new customer conversions while keeping total conversions is fatiguing on acquisition specifically.
- New customer purchases (Meta): orders from first-time buyers, from TrackBee's custom conversion event. Null if not configured. Use the same way as Google's new customer conversions.
