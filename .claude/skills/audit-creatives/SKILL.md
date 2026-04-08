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

### 1. Understand what the user needs

Common starting points:

- **Fatigue check**: "Are any of my creatives showing fatigue?"
- **Lifetime analysis**: "How long do my video ads last before performance drops?"
- **Content comparison**: "What type of content works best for [product]?"
- **Production guidance**: "What should I create next?"

Clarify the **store**, **platform**, and whether they want to look at all creatives or a specific product/campaign.

### 2. Pull creative data

Use the TrackBee MCP tools:

- `get_meta_ad_insights` / `get_google_ad_insights` — Ad-level performance over time
- `get_meta_campaign_insights` / `get_google_campaign_insights` — Campaign context for the ads
- `detect_anomalies` — Spot sudden performance drops
- `get_meta_recommendations` — Platform-specific improvement suggestions

Request a long enough time range to see creative lifecycle trends — at least 30 days, ideally 60-90 days.

### 3. Detect creative fatigue

A creative is fatigued when its performance degrades over time despite stable or increasing spend. Check for:

| Indicator | What to look for |
| --- | --- |
| **CTR decline** | Steady drop over 2+ weeks — people stop clicking |
| **CPA increase** | Rising cost per acquisition — conversions get more expensive |
| **Frequency spike** | Same audience seeing the ad too often |
| **ROAS decline** | Diminishing returns on spend |

Compare current performance (last 7 days) against the creative's peak performance period. A creative that once had 2% CTR and now has 0.8% is fatigued.

### 4. Measure creative lifetime

For each content type (video, static image, carousel, etc.):

1. Identify when the creative launched (first day with impressions)
2. Find the peak performance period (highest CTR or ROAS window)
3. Find when performance dropped below a useful threshold
4. Calculate the active lifetime: launch to performance drop

Report average lifetime by content type:

- "Your video ads typically peak in week 2 and fatigue by week 5"
- "Static images have a shorter lifecycle — about 2-3 weeks before fatigue sets in"

### 5. Compare content types per product

If the user has multiple products or product categories:

1. Group creatives by product and content type
2. Compare key metrics: CTR, ROAS, CPA, and lifetime
3. Identify which content types win for each product

Example finding: "For [Product A], video ads outperform static images on ROAS (3.2x vs 1.8x) and last twice as long before fatigue."

### 6. Suggest what to create next

Based on the analysis, recommend:

- **Replace fatigued creatives**: "These 3 ads are past their prime — prioritize replacements"
- **Double down on what works**: "Video content for [Product A] consistently outperforms — create more variations"
- **Fill gaps**: "You have no carousel ads for [Product B] — worth testing since carousels perform well for similar products"
- **Content themes**: If certain angles or messages perform better, call them out

### 7. Present findings

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
