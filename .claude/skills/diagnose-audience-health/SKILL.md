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

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to analyze. They can provide the store name or store ID.

### 2. Understand the concern

The user usually comes in with one of these:

- "My CPM keeps going up"
- "CTR is dropping across campaigns"
- "Am I still reaching new people?"
- "Frequency is getting high — is that a problem?"

Clarify the **platform** and **time period**. For trend analysis, you need at least 14 days of data — suggest 30 days if they don't specify.

Also ask: **Are any of your campaigns test campaigns?** If so, which ones — and do you want to include them in the results? Exclude test campaigns by default unless the user explicitly asks to include them.

### 3. Pull trend data

Start at campaign level for orientation, then drill into ad level for the real diagnosis:

**Meta:**
1. `get_meta_campaign_insights` — Campaign overview to identify which campaigns to investigate
2. `get_meta_ad_insights` — **The core data source.** Ad-level metrics reveal which specific ads are saturating. Campaign averages can mask that one ad is healthy while another is exhausted. For Meta, this includes **net new reach** per ad

**Google Ads:**
1. `get_google_campaign_insights` — Campaign overview with new vs returning customer breakdown
2. `get_google_ad_insights` — Ad-level data with new vs returning customer conversions per ad

**Both platforms:**
- `detect_anomalies` — Flag sudden changes in CPM, CTR, or frequency

### 4. Check the three warning signals

Analyze the data for the saturation pattern:

| Signal | Healthy | Warning | Critical |
| --- | --- | --- | --- |
| **CPM trend** | Flat or declining | Rising 10-20% week-over-week | Rising 20%+ week-over-week |
| **CTR trend** | Stable or improving | Declining 10-15% | Declining 15%+ |
| **Frequency** | Below 2.0 | 2.0 - 3.5 | Above 3.5 |

All three moving in the wrong direction together is a strong signal of audience saturation. One metric moving alone may have a different cause.

### 5. Identify the scope

Determine if the problem is:

- **Account-wide**: All campaigns showing the pattern — the overall audience pool may be tapped out
- **Campaign-specific**: Only certain campaigns — drill into ad-level data to pinpoint which ads are the culprits
- **Platform-specific**: One platform saturated but not the other — reallocate budget

### 6. Assess new customer reach

Look at these indicators:

- **Net new reach** (Meta only): The most direct signal. `get_meta_ad_insights` returns `net_new_reach` per ad — users reached who were NOT reached in the prior 90 days. This is different from the standard "reach" in Ads Manager, which only deduplicates within the selected date range. Compare `net_new_reach` to total `reach`: if the ratio is low, the ad is mostly re-showing to existing audience. Also check `cost_per_net_new_reach` — rising cost means you're paying more for each new person
- **Frequency distribution**: What percentage of impressions go to people who've seen the ad 1x vs 5x+?
- **Reach vs impressions ratio**: A widening gap means the same people see more ads

When net new reach is low, diagnose the cause in priority order:
1. **Creative fatigue** — the audience has seen your ads too many times. Refresh creatives or test new angles. This is the most common cause.
2. **Lack of creative diversity** — too few variations. Broaden the creative mix to unlock new audience segments.
3. **Custom optimisation goals** — in rare cases, the campaign objective may be limiting audience expansion. Lower priority; check creatives first.

Also check **attribution windows** for brand awareness impact:
- High `purchases_1d_view` relative to click-based conversions suggests the ad drives brand recall — people see the ad, don't click, but buy later. This is a sign of healthy upper-funnel reach even if click metrics look weak.
- If `purchases_1d_view` is dropping alongside net new reach, the ad is losing both new and existing audience impact.

### 7. Check new vs returning customer balance

Both platforms can report new vs returning customer breakdowns:

- **Google Ads**: `new_customer_conversions` and `returning_customer_conversions` per campaign and ad
- **Meta**: `new_customer_purchases` and `returning_customer_purchases` per campaign and ad (from TrackBee's custom conversion events — null if not configured on the ad account)

Use this to validate whether the audience is truly fresh:

- **Declining new customer ratio**: If new / total drops over time, the campaign is increasingly re-converting existing customers — a sign of audience saturation even if overall conversion numbers look healthy.
- **New customer CAC rising**: If spend / new_customer_purchases (or conversions) is trending up, it's getting more expensive to find new buyers — the easy-to-reach audience is tapped out.
- **Cross-reference net new reach with new customer purchases**: For Meta ads specifically, low net new reach + low new_customer_purchases is a double confirmation of audience exhaustion. If net new reach is low but new_customer_purchases stays healthy, the ad is still converting the fresh reach efficiently.

### 8. Present the diagnosis

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
- Net new reach: users reached during a period who were NOT reached in the prior 90 days — different from standard reach in Ads Manager, which only deduplicates within the selected date range
- Cost per net new reach: spend / net new reach — lower means more efficient at finding fresh audiences
- Attribution window: the time period after an ad interaction during which a conversion is credited. Click windows are cumulative (1d_click ⊂ 7d_click ⊂ 28d_click — never sum them). 1d_view is separate (view-only, no click). Default purchases = 7d_click + 1d_view.
- View-through conversion (1d_view): a purchase after seeing an ad without clicking — separate from click windows, signals brand awareness impact
- New customer conversions (Google Ads): orders from first-time buyers. A declining new customer ratio is a strong signal of audience saturation.
- Returning customer conversions (Google Ads): orders from repeat customers. Rising share suggests the campaign is re-engaging rather than acquiring.
- New customer purchases (Meta): orders from first-time buyers, from TrackBee's custom conversion event. Null when not configured on the ad account.
- Returning customer purchases (Meta): orders from repeat customers, from TrackBee's custom conversion event. Null when not configured.
