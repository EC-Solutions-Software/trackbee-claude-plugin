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

### 1. Understand the question

Ask the user what they want to analyze. Common starting points:

- **Funnel mismatch**: "Which ads look good on reach but have bad ROAS?"
- **Scaling decision**: "This ad moved to scaling — can we push more budget?"
- **Budget tracking**: "Which ads were increased recently and what happened?"

Clarify the **store**, **platform** (Meta, Google, or both), and **time period** if not obvious. Default to the last 30 days if they don't specify.

### 2. Pull the data

Use the TrackBee MCP tools to get the relevant data:

- `get_campaign_performance` — Campaign-level spend, revenue, ROAS, CPA
- `get_meta_ad_insights` / `get_google_ad_insights` — Ad-level metrics including CTR, CPM, impressions, conversions
- `get_meta_campaign_insights` / `get_google_campaign_insights` — Campaign-level breakdown
- `detect_anomalies` — Spot sudden changes in performance

For funnel mismatch analysis, pull both reach metrics (impressions, CPM, CTR) and conversion metrics (purchases, ROAS, CPA) for the same ads.

### 3. Analyze across the funnel

For each ad or campaign, compare:

| Metric | Top-of-funnel signal | Bottom-of-funnel signal |
| --- | --- | --- |
| Reach | High impressions, low CPM | — |
| Engagement | High CTR | — |
| Conversion | — | High ROAS, low CPA |
| Revenue | — | Revenue relative to spend |

Flag ads where top-of-funnel looks strong but bottom-of-funnel is weak. These are the most actionable — the creative works for attention but doesn't convert.

### 4. Scaling assessment

For ads the user wants to scale, evaluate:

- **Current spend vs results**: Is ROAS stable or declining as spend increases?
- **Frequency**: Is the audience getting saturated? (frequency > 3 is a warning)
- **CPM trend**: Rising CPM with flat results means diminishing returns
- **Audience size**: Can the target audience sustain more spend?

Give a clear recommendation:
- **Scale**: ROAS is stable, frequency is low, CPM is flat — push more budget
- **Hold**: Results are okay but showing early signs of fatigue — monitor closely
- **Kill**: ROAS is declining, frequency is high, CPM is rising — stop spending

### 5. Budget change tracking

When the user asks what happened after budget changes:

1. Identify campaigns where spend increased or decreased significantly
2. Compare performance metrics before vs after the change
3. Show whether the increased spend maintained efficiency or diluted results

### 6. Present findings

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
