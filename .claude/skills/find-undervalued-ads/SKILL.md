---
name: find-undervalued-ads
description: >-
  Find Meta ads that look bad on the default 7-day-click + 1-day-view ROAS in
  Ads Manager but actually drive sales — either over a longer click window
  (top-of-funnel, delayed conversion) or by influencing other ads in the
  journey. For high-probability candidates, pull journey data to see which
  other ads they appear with and how often. Use this skill when someone asks
  why their ROAS looks bad, whether to kill an underperforming ad, which ads
  are being unfairly judged by default attribution, or which top-of-funnel
  ads are quietly carrying the portfolio.
---

# Find Undervalued Meta Ads

Meta's Ads Manager defaults to a 7-day-click + 1-day-view ROAS. That window misses two things: ads that drive purchases between day 8 and day 28 after the click (delayed top-of-funnel) and ads that open journeys other ads close (cross-ad influence). This skill finds those undervalued ads, recomputes their ROAS under longer and incremental lenses, and — for the strongest candidates — pulls their journey breakdown to show which other ads they actually feed.

## Workflow

### 1. Select the store

Run `list_my_stores` to load the user's available stores. Ask the user which store they want to analyze. They can provide the store name or store ID.

### 2. Set scope and pull ad-level data

Ask the user:

- **Time window** — default to `last_30d`. Avoid `last_7d` and shorter — a 7-day window cannot reveal delayed click conversions, which is the whole point.
- **Status filter** — default `active`. Use `paused` or `all` only when auditing a recent kill decision.
- **Spend floor** — minimum spend per ad to consider (default €100 in `ad_account_currency`). Below that the attribution-window patterns are noise.
- **Default-ROAS ceiling for candidates** — what counts as "looks bad". Default 1.5× if the user has no opinion; otherwise their target ROAS.

Then pull data:

1. `get_meta_campaign_insights` — get the active campaigns and their IDs in scope.
2. For each campaign with non-trivial spend, `get_meta_ad_insights` with the same `date_range` and `status_filter`. This is where every signal below comes from — it returns per-ad `purchase_roas`, `purchases`, the four attribution-window pairs (`purchases_1d_click` / `7d_click` / `28d_click` / `1d_view` and the matching `revenue_*` fields), `purchases_incrementality`, `revenue_incrementality`, `funnel_position`, `click_urgency`, `view_share`, plus `frequency`, `ctr`, `cpm`, `spend`, and the ad's `ad_id`.

IMPORTANT — currencies: spend and revenue from these tools are in `ad_account_currency` (units, not cents). Don't mix with TrackBee revenue figures without converting.

### 3. Filter to "looks bad on default" ads

Keep an ad as a candidate only if **both**:

- `purchase_roas` ≤ the user's bad-default ceiling (default 1.5×). Remember: `purchase_roas` is computed by Meta as `(revenue_7d_click + revenue_1d_view) / spend` — the same number Ads Manager shows by default.
- `spend` ≥ the user's spend floor.

Drop ads with `funnel_position == "UNKNOWN"` from the high-probability tier (they have <10 combined 28d_click + 1d_view purchases — too little signal). Keep them in a "not enough data" bucket and report them separately.

### 4. Score each candidate on hidden-contribution probability

For each kept ad, evaluate three independent signals from `get_meta_ad_insights`:

| Signal | Meaning | Triggered when |
| --- | --- | --- |
| **Delayed-click signal** | The ad drives purchases that land outside the 7-day window | `funnel_position == "TOP_OF_FUNNEL"` OR `click_urgency < 0.55` OR `(revenue_28d_click − revenue_7d_click) / max(revenue_28d_click, 1) > 0.30` |
| **View-through signal** | Conversions come from people who saw, didn't click, then bought | `view_share > 0.30` |
| **Incrementality signal** | Meta's own ML estimates the ad is genuinely causing conversions | `purchases_incrementality / max(purchases, 1) > 0.85` |

Rate each ad:

- **High** — two or more signals trigger. The default ROAS is meaningfully understating the ad's contribution. These flow into step 6.
- **Medium** — exactly one signal triggers. Worth surfacing; not worth journey-drill-down unless the user asks.
- **Low** — no signals trigger. The default ROAS is a fair judgement; the ad probably is just underperforming.

Note: `funnel_position`, `click_urgency`, and `view_share` are TrackBee-computed heuristics from Meta's attribution metrics — Meta does not return a TOF/MOF/BOF label itself. Frame them to the user as "TrackBee's behavioural classification", never as "Meta labelled this TOF".

### 5. Recompute ROAS under three lenses

For every candidate, show three ROAS numbers side by side so the gap between Ads-Manager reality and full attribution is concrete:

| Lens | Formula | What it captures |
| --- | --- | --- |
| **Default (Ads Manager)** | `purchase_roas` | 7d_click + 1d_view — the number that triggered the "bad ROAS" worry |
| **28-day click** | `revenue_28d_click / spend` | Adds the delayed click conversions Ads Manager hides |
| **Incremental** | `revenue_incrementality / spend` | Meta's ML estimate of revenue that wouldn't exist without the ad |

Highlight ads where the 28-day or incremental ROAS clears the user's target while the default does not — those are the clearest "do not kill" cases.

IMPORTANT — attribution-window math:

- Click windows are **cumulative** (nested): `1d_click ⊂ 7d_click ⊂ 28d_click`. Never sum them.
- Delayed click revenue between day 8 and day 28 = `revenue_28d_click − revenue_7d_click`.
- `1d_view` is **separate** from click windows — purchases from people who saw but didn't click.
- `purchases` / `purchase_roas` = 7d_click + 1d_view (Meta's default attribution).
- 7d_view and 28d_view were discontinued by Meta in January 2026; only 1d_view is available.

### 6. For High-probability candidates, pull the journey data

For each ad rated **High** in step 4, call `get_ad_journey_breakdown(store, ad_id)` using the platform-native ad ID. This returns `paths` — a list of `{count, sequence}` where `sequence` is an ordered list of ad_ids the buyer touched.

Also pull `get_store_ad_touchpoint_dynamics(store)` once and look up the same `ad_id` in the returned ad list to get aggregate `journeys`, `touches`, `opener`, `closer`, `solo`, `avg_position`.

Read out per ad:

- **Total journey participation** — sum of `count` across paths the ad appears in. Compare to its standalone `purchases` to show how often it shows up across multi-touch journeys without getting credit on default attribution.
- **Position pattern** — from touchpoint dynamics, the `opener` / `closer` / `solo` split. High `opener` count + low `closer` count = the ad mostly starts journeys other ads finish (classic "undervalued upper-funnel" pattern). High `solo` count = it stands on its own — its low default ROAS is probably real.
- **Co-occurring ads** — extract every other `ad_id` that appears in the candidate's `sequence` arrays, count co-occurrences, surface the top 3–5. These are the ads the candidate likely feeds.
- **Average position** — `avg_position` from touchpoint dynamics tells you where in the average journey the ad sits.

If `get_ad_journey_breakdown` returns an empty `paths` list, the ad has fewer than 3 journeys in the data — say so explicitly. Do not invent journey data.

Cross-link: if the user wants to walk through the journey from the perspective of the closer ads instead of the opener, point them at the `analyze-ad-performance` skill for per-ad scale/hold/kill verdicts.

### 7. Present findings

Structure the response as:

1. **Summary** — one-sentence verdict (e.g., "4 of your 18 active ads with default ROAS below 1.5× are likely undervalued — collectively they touched 312 journeys in the last 30 days").
2. **Likely undervalued ads (High)** — table per ad: name / id, default ROAS, 28d-click ROAS, incremental ROAS, signals triggered, opener/closer/solo split, total journey participation, top co-occurring ads. Recommendation: **do not kill**, and which ads to evaluate jointly with it.
3. **Possibly undervalued ads (Medium)** — same fields, lighter recommendation: **monitor on 28d, don't judge on 7d**.
4. **Default ROAS judgement stands (Low)** — ads where no hidden-contribution signal fires. The "bad ROAS" is real.
5. **Insufficient data (UNKNOWN)** — ads with too few combined 28d_click + 1d_view purchases to classify; surface them but don't draw conclusions.

End with one concrete next action — e.g., "before pausing the four High-rated ads, freeze them at current spend for 14 more days and re-run this skill on a `last_30d` window so the delayed click conversions land in the data."

---

## Guidelines

- Always use TrackBee MCP tools — never guess at numbers
- Never run this skill on a window shorter than 14 days; delayed click conversions cannot land inside a 7-day window, which defeats the entire analysis
- Frame `funnel_position`, `click_urgency`, and `view_share` as TrackBee's behavioural classification, never as "Meta labelled this ad TOF/MOF/BOF"
- Defer per-ad scale/hold/kill verdicts to `analyze-ad-performance`; this skill's only job is to surface ads where the default attribution is misleading
- Defer creative-fatigue analysis to `audit-creatives` and audience-saturation analysis to `diagnose-audience-health`
- Defer portfolio-level "should I scale this whole channel" decisions to `scale-ads-profitably`
- Flag UNKNOWN-funnel-position ads, empty journey-breakdown returns, and null incrementality fields rather than guessing
- This skill is Meta-only. Google Ads has different attribution semantics (`new_customer_conversions` vs Meta's custom-conversion approach) — do not mix the two in one analysis

## Glossary

- Default ROAS: Meta Ads Manager's headline ROAS — `(revenue_7d_click + revenue_1d_view) / spend`. Returned as `purchase_roas` from `get_meta_ad_insights`. The number that triggers most "this ad isn't working" judgements.
- 28-day click ROAS: `revenue_28d_click / spend`. Includes click conversions that landed between days 8–28 — the delayed sales that 7-day attribution hides. Higher than default ROAS for top-of-funnel ads.
- Delayed click revenue: `revenue_28d_click − revenue_7d_click`. The revenue Meta credits to clicks that converted in the second through fourth week. A large share is the clearest single sign of a delayed-conversion ad.
- Incremental ROAS: `revenue_incrementality / spend`. Meta's ML estimate of revenue that would not have happened without the ad. Treated as the truest measure of the ad's contribution.
- Incremental ratio: `purchases_incrementality / purchases`. Above ~0.85 means the ad is genuinely causing purchases; below ~0.70 means it's mostly claiming credit for sales that would have happened anyway.
- Funnel position (TrackBee-computed): TOP_OF_FUNNEL, MIDDLE_OF_FUNNEL, BOTTOM_OF_FUNNEL, or UNKNOWN. Heuristic from `click_urgency` and `view_share` — not a Meta-provided label. UNKNOWN means combined 28d_click + 1d_view purchases < 10.
- Click urgency: `purchases_1d_click / purchases_28d_click`. High (>0.85) = same-day conversions, BOF signal. Low (<0.55) = long click-to-purchase delay, TOF signal.
- View share: `purchases_1d_view / (purchases_7d_click + purchases_1d_view)`. High (>0.30) means a large share of attributed conversions came from people who saw but did not click — classic upper-funnel value.
- Opener / closer / solo (touchpoint dynamics): how often an ad starts a journey other ads finish (opener), finishes a journey other ads started (closer), or carries a journey on its own (solo). Returned from `get_store_ad_touchpoint_dynamics`. An undervalued upper-funnel ad is typically opener-heavy and closer-light.
- Journey participation: total count of multi-touch buyer journeys an ad appears in, summed across `paths` returned by `get_ad_journey_breakdown`. An ad can have low default ROAS while participating in many journeys — that gap is what this skill exists to surface.
- Co-occurring ads: other ads that appear in the same `sequence` arrays as the candidate. The ads it most likely feeds; consider their performance jointly with the candidate's before pausing either.
