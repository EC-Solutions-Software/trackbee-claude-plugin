---
name: discover-insights
description: >-
  Suggest valuable questions to ask about ad performance, surface seasonal
  opportunities, and share what high-growth brands look at. Use this skill when
  someone wants to know what to ask, needs ideas for analysis, wants to review
  seasonal campaign investments, or asks what other brands or marketers are
  doing to grow.
---

# Discover Insights

Help the user figure out what to ask and where the opportunities are. Not everyone knows what questions lead to growth — this skill bridges that gap by suggesting analyses, reviewing seasonal investments, and sharing proven growth patterns.

## Workflow

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to explore. They can provide the store name or store ID.

Also ask: **Are any of your campaigns test campaigns?** If so, which ones — these will be excluded when routing to other skills unless the user says otherwise.

### 2. Understand the context

Ask the user:

- What's their current focus? (scaling, launching, optimizing, seasonal planning)
- Are they looking for quick wins or strategic direction?

### 3. Suggest valuable questions

Based on their context, present a curated list of high-value questions they can ask. Group them by theme:

**Performance health check:**
- "Which campaigns have the best and worst ROAS this month?"
- "Are any ads showing signs of creative fatigue?"
- "Is my CPM trending up — am I running out of fresh audience?"
- "What's my net new reach — are my ads still finding new people?"
- "Which ads got budget increases and did the results hold up?"

**Scaling opportunities:**
- "Which ads have strong engagement but haven't been scaled yet?"
- "What's my best-performing content type — should I make more of it?"
- "Are there products where I'm underspending relative to performance?"

**Creative intelligence:**
- "What content type works best for each of my products?"
- "How long do my creatives last before they fatigue?"
- "What should I create next based on what's working?"

**Competitive and market signals:**
- "What are competitors running in the Meta Ad Library for [product category]?"
- "Are there trending products in my niche I should be advertising?"
- "What does Google Trends say about demand for my products?"

**Seasonal and investment review:**
- "Were my Black Friday campaigns worth it? What was the ROAS vs regular periods?"
- "Should I reinvest in [holiday] campaigns based on last year's results?"
- "What's the best time to start ramping spend before a seasonal peak?"

Tailor the suggestions to what's relevant for the user's store and current situation. Don't dump all questions — pick the 5-8 most relevant ones.

### 4. Seasonal campaign review

When the user asks about past seasonal investments (Black Friday, Christmas, summer sales, etc.):

1. Pull performance data for the seasonal period and a comparison period (same duration before or after)
2. Compare key metrics: spend, revenue, ROAS, CPA, new customers
3. Calculate the incremental value — did the seasonal push generate results above baseline?
4. Assess whether the creative investment was worth repeating

Present as: "You spent X on Black Friday creatives and generated Y in revenue (Z ROAS). Your normal ROAS for that period would have been W. The seasonal push added [amount] in incremental revenue — [worth it / not worth repeating]."

### 5. Growth patterns from other brands

Share proven patterns that high-performing DTC brands and performance marketers use. These aren't from the user's data — they're general best practices:

**What top performers track weekly:**
- ROAS at ad level, not just campaign or account level — campaign averages hide the winners and losers
- Creative fatigue scores — replacing ads before they die
- New vs returning customer acquisition ratio
- Platform-level efficiency — shifting budget to what's working

**Common blind spots:**
- Only looking at last-click attribution — missing top-of-funnel value
- Not tracking creative lifetime — running fatigued ads too long
- Ignoring frequency and net new reach until CPM spikes
- Treating all products the same — different products need different content strategies

**Scaling playbook:**
- Test at low budget, identify winners, scale incrementally (20-30% budget increases)
- Monitor ROAS stability with each budget bump — flatten = stop scaling
- Diversify creatives before scaling — one winning ad will fatigue faster at high spend
- Use seasonal peaks to acquire customers at lower CPA, then retarget year-round

### 6. Offer next steps

After presenting suggestions, ask the user which direction interests them most. Route to the appropriate skill:

- Ad performance questions → `/analyze-ad-performance`
- Audience and reach concerns → `/diagnose-audience-health`
- Creative and content questions → `/audit-creatives`
- Specific data requests → Use the TrackBee MCP tools directly

---

## Guidelines

- Always use TrackBee MCP tools for data — never guess at numbers
- Use consistent date ranges when comparing performance
- Surface actionable recommendations, not just data dumps
- Flag when data is insufficient to draw conclusions (short date ranges, low spend, etc.)

## Glossary

- ROAS: return on ad spend (revenue / spend)
- CPA: cost per acquisition (spend / purchases)
- CPM: cost per 1,000 impressions
- CTR: click-through rate
- Frequency: average number of times a person has seen your ad
- Creative fatigue: when an audience has seen an ad too many times and engagement drops
