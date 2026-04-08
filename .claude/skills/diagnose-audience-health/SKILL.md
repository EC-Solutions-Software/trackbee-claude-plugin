---
name: diagnose-audience-health
description: >-
  Diagnose audience saturation and reach health — spot rising CPM, dropping CTR,
  and climbing frequency that signal you're running out of fresh audience. Use
  this skill when someone asks about CPM trends, frequency problems, whether
  they're reaching new customers, audience fatigue, or ad delivery issues.
---

# Diagnose Audience Health

Detect when ad campaigns are running out of fresh audience. Rising CPM + dropping CTR + climbing frequency is the classic signal that you're paying more to show ads to the same people.

## Workflow

### 1. Understand the concern

The user usually comes in with one of these:

- "My CPM keeps going up"
- "CTR is dropping across campaigns"
- "Am I still reaching new people?"
- "Frequency is getting high — is that a problem?"

Clarify the **store**, **platform**, and **time period**. For trend analysis, you need at least 14 days of data — suggest 30 days if they don't specify.

### 2. Pull trend data

Use the TrackBee MCP tools:

- `get_meta_campaign_insights` / `get_google_campaign_insights` — Campaign-level daily metrics
- `get_meta_ad_insights` / `get_google_ad_insights` — Ad-level for drilling into specific creatives
- `detect_anomalies` — Flag sudden changes in CPM, CTR, or frequency

Request data broken down by day so you can see trends over time.

### 3. Check the three warning signals

Analyze the data for the saturation pattern:

| Signal | Healthy | Warning | Critical |
| --- | --- | --- | --- |
| **CPM trend** | Flat or declining | Rising 10-20% week-over-week | Rising 20%+ week-over-week |
| **CTR trend** | Stable or improving | Declining 10-15% | Declining 15%+ |
| **Frequency** | Below 2.0 | 2.0 - 3.5 | Above 3.5 |

All three moving in the wrong direction together is a strong signal of audience saturation. One metric moving alone may have a different cause.

### 4. Identify the scope

Determine if the problem is:

- **Account-wide**: All campaigns showing the pattern — the overall audience pool may be tapped out
- **Campaign-specific**: Only certain campaigns — likely a targeting or creative issue
- **Platform-specific**: One platform saturated but not the other — reallocate budget

### 5. Assess new customer reach

Look at these indicators:

- **Frequency distribution**: What percentage of impressions go to people who've seen the ad 1x vs 5x+?
- **Reach vs impressions ratio**: A widening gap means the same people see more ads
- **New audience metrics**: If available from the platform, check new vs returning reach

### 6. Present the diagnosis

Structure the response as:

1. **Verdict**: Clear statement — "Your Meta campaigns are showing audience saturation" or "Audience health looks fine — the CPM increase has a different cause"
2. **Evidence**: The specific metrics and trends that support the verdict
3. **Scope**: Account-wide, campaign-specific, or platform-specific
4. **Recommendations**:
   - Broaden targeting to reach new audiences
   - Refresh creatives to re-engage existing audience
   - Shift budget to platforms or campaigns with healthier metrics
   - Reduce frequency caps if available
   - Test new audience segments (lookalikes, interest expansion)

---

## Guidelines

- Always use TrackBee MCP tools for data — never guess at numbers
- Use consistent date ranges when comparing performance
- Surface actionable recommendations, not just data dumps
- Flag when data is insufficient to draw conclusions (short date ranges, low spend, etc.)

## Glossary

- CPM: cost per 1,000 impressions
- CTR: click-through rate
- ROAS: return on ad spend (revenue / spend)
- CPA: cost per acquisition (spend / purchases)
- Frequency: average number of times a person has seen your ad
- Audience saturation: when you've shown ads to most of your target audience and start paying more to reach the same people
