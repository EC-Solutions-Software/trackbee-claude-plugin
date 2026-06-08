---
name: attribution
description: >-
  Generate a TrackBee-branded Attribution Overview — one self-contained HTML
  page combining an Executive Summary, Blended Overview with Acquisition MER
  over time, Platform Overview, Channel Attribution, Customer Journeys
  (touch-points heatmap + sankey, auto-hidden when the store has no shopper
  profiles), a Store Funnel Analysis with stage-specific fix-it insights,
  and a clickable "Where to go next" dock of follow-up prompts. Use this
  skill whenever someone asks for an attribution overview, a marketing
  scorecard, a channel-contribution view, where platforms overlap, a
  journey/path visualisation, a multi-touch overview, a funnel drop-off
  review, or any persistent multi-report attribution view that also covers
  the store funnel — even if they don't use the word "dashboard". Trigger
  also for "show me how each channel contributes", "where do my platforms
  overlap", "where is my funnel leaking", "what should I look at next",
  "rebuild this in our brand", or any request that includes blended /
  per-platform KPIs, a channel breakdown, and a funnel review together.
---

# Attribution Overview

Render a TrackBee-branded HTML report from the TrackBee MCP. The build is
driven by a thin entry script (`scripts/build_dashboard.py`) that hands off
to an orchestrator (`components/orchestrators/assemble.py`), which loads
small, focused components from `components/` in sequence — one file per
responsibility (transforms, insights, charts, chrome). No part of the build
is duplicated across files; HTML, CSS, and JS each live in their own files
under `components/chrome/`, never inside Python string literals. **Do NOT
regenerate the artifact code from scratch on each run** — always use the
bundled build.

This report covers six sections: Executive Summary, Blended Overview (with
the Acquisition MER / NC-ROAS line over time), Platform Overview, Channel
Attribution, Customer Journeys (touch-points heatmap + sankey, auto-hidden
when the store has no shopper profiles), Store Funnel Analysis (page view →
order, with stage-specific fix-it insights), and a "Where to go next" dock of
clickable follow-up prompts.

## Workflow (the happy path — keep tokens low)

1. **Pick store + windows.** Call `tool__list_my_stores`, ask the user which
   store and which time window (default **28 days** ending yesterday). The
   page always covers three windows together (28d / 7d / 3d) so the in-page
   filter works; you only need one set of dates.
2. **Make the MCP calls listed in §MCP calls below.** Use exactly that set —
   no extras. Save each `result` payload as a JSON file in
   `/tmp/attribution_overview_inputs/` with the filename listed in §MCP calls
   (e.g. `daily.json`, `meta_7d.json`).
3. **Write `/tmp/attribution_overview_config.json`** with store name,
   currency, FX rates, and the three windows' start/end dates (template in
   §Config).
4. **Run the build script:**
   ```bash
   python3 <SKILL_DIR>/scripts/build_dashboard.py \
     --inputs  /tmp/attribution_overview_inputs/ \
     --config  /tmp/attribution_overview_config.json \
     --assets  <SKILL_DIR>/assets/ \
     --out     "<workspace>/<store-slug>-attribution-overview-<YYYY-MM-DD>.html"
   ```
   `<SKILL_DIR>` is this skill's path (the script, components, and assets are
   bundled with the plugin; `--assets` defaults to the bundled `assets/` dir
   if omitted). Replace `<workspace>` with the user's selected workspace
   folder and `<store-slug>` with a kebab-case version of the store name.
5. **Create or update the live artifact.** Call
   `mcp__cowork__create_artifact` with:
   - `id`: `<store-slug>-attribution-overview-report` — **always use the same
     id for a given store**, so subsequent runs overwrite in place instead of
     stacking duplicates in the sidebar.
   - `html_path`: the absolute path of the HTML file written in step 4.
   - `description`: `"TrackBee Attribution Overview for <Store Name> —
     28d/7d/3d windows ending <end-date>. Refreshed daily at 08:00 by the
     scheduled task."`
   - `mcp_tools`: `[]` (data is baked in at build time; the artifact does not
     call MCP at runtime — the scheduled task in step 6 keeps it fresh).
6. **Schedule the daily 8am refresh.** Before handing off, call
   `mcp__scheduled-tasks__list_scheduled_tasks` to check whether a task for
   this store already exists. If `<store-slug>-attribution-overview-daily-refresh`
   is already listed, do nothing. Otherwise call
   `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `<store-slug>-attribution-overview-daily-refresh`
   - `cronExpression`: `"0 8 * * *"` (every day at 8am local time)
   - `description`: `"Refresh the <Store Name> TrackBee Attribution Overview
     every day at 8am."`
   - `notifyOnCompletion`: `false`
   - `prompt`: a self-contained instruction that captures everything the task
     needs to do without access to this conversation. Use this template
     (substitute the placeholders):
     ```
     Refresh the TrackBee Attribution Overview for <Store Name>
     (store id <STORE_ID>) by running the /attribution skill end-to-end.

     CONTEXT
     - Store: <Store Name>, store_id = <STORE_ID>, store_currency = <CCY>.
     - Ad-account FX: <FX_DICT> (e.g. {"GBP": 1.0, "EUR": 0.85}). Use a
       fresher rate if you have one.
     - Workspace folder: <WORKSPACE_PATH>
     - Entry script: $CLAUDE_PLUGIN_ROOT/.claude/skills/attribution/scripts/build_dashboard.py

     WINDOWS — compute every run, do NOT hard-code
     - 28d ends YESTERDAY (today − 1 day local). 7d ends yesterday. 3d ends
       yesterday. Each starts (N−1) days before its end.

     PLAN
     1. Invoke the /attribution skill against store <STORE_ID> using
        the windows above.
     2. Build the report HTML at
        <WORKSPACE_PATH>/<store-slug>-attribution-overview-<YYYY-MM-DD>.html
        (yesterday's date).
     3. Update the existing artifact in place: call
        mcp__cowork__create_artifact with the SAME id
        "<store-slug>-attribution-overview-report" and the new html_path.
        Same id = update, not duplicate.
     4. Print one line to chat: revenue, ROAS, biggest funnel leak, and the
        artifact link as computer://<absolute-path>. Keep the chat clean —
        this runs every morning.
     ```
   Tell the user one line: "Live artifact created and a daily 8am refresh is
   scheduled." First run pre-approves the MCP tools the task needs, so
   subsequent runs go through without prompts.
7. **Hand off.** Print a `computer://` link to the HTML and a one-paragraph
   headline (top KPI + most striking attribution finding + biggest funnel
   leak). Full template in `references/handoff-template.md`.

If anything in the spec needs clarifying — what each section should look
like, how insights are computed, brand tokens, copy tone — read
`references/dashboard-spec.md`. **Don't read it for normal runs.** It's only
needed when modifying a component or designing a new variant.

## MCP calls (exact set)

Make exactly these calls. **Do not call `tool__get_campaign_performance`** —
its data overlaps with `tool__get_*_campaign_insights` and it returns large
duplicated rows that bloat context for no benefit.

| Filename | Tool | Notes |
| --- | --- | --- |
| `overview.json` / `overview_7d.json` / `overview_3d.json` | `tool__get_dashboard_overview` | One per window. **Primary source for all spend, revenue, and ROAS numbers.** Drives Blended Overview KPI tiles, Platform Overview tiles, and Channel Attribution spend + ROAS columns. All monetary values are already converted to `store_currency` — do not use campaign-level spend/ROAS from `meta.json` or `google.json` for these tiles. |
| `daily.json` | `tool__get_daily_store_statistics` | 28-day window. **Pass `column_groups=["core","funnel","customer_segments","platform_totals"]`** to keep the response tight. Drives the daily NC-ROAS (Acquisition MER) line. |
| `funnel.json` / `funnel_7d.json` / `funnel_3d.json` | `tool__get_funnel_overview` | One per window. **Pass `compare_previous_period=true`** so deltas are baked in. Drives the Store Funnel Analysis section and the blended funnel rates. |
| `platform_funnel.json` / `platform_funnel_7d.json` / `platform_funnel_3d.json` | `tool__get_platform_funnel_breakdown` | One per window. Drives Channel Attribution sessions / TrackBee orders / revenue. |
| `meta.json` / `meta_7d.json` / `meta_3d.json` | `tool__get_meta_campaign_insights` | One per window. Used for impressions, CTR, CPM, and in-platform purchase counts only. |
| `google.json` / `google_7d.json` / `google_3d.json` | `tool__get_google_campaign_insights` | One per window. Used for impressions, CTR, CPM, and in-platform conversion counts only. |
| `touchpoints.json` | `tool__get_platform_footprints` + per-platform `tool__get_platform_breakdown` | Customer-journey scaffolding — see §Customer Journeys adapter. |
| `j_meta.json`, `j_google.json`, `j_klaviyo.json`, `j_tiktok.json`, `j_pinterest.json`, `j_email.json` | `tool__get_platform_journeys` | One per top channel — see §Customer Journeys adapter. |

If the store has additional platforms (Microsoft Ads, Calendly, future
channels) tracked by `tool__get_platform_funnel_breakdown`, those rows render
automatically without code changes. The journey and heatmap sections
auto-discover whichever platforms appear in `touchpoints.json`'s
`available_platforms` and `co_occurrence`.

**Missing inputs:** if an *ancillary* tool errors (store not connected, an ad
account missing, no shopper profiles, etc.), either skip the file entirely or
write `{"result": {}}`. The build tolerates both — missing inputs collapse to
em-dashes in tiles and skipped rows in tables. When the store has no
shopper-profile data (`total_journeys == 0` and no `co_occurrence`), the
Customer Journeys section is removed from the page entirely rather than
showing an empty card.

## Customer Journeys adapter

The build expects `touchpoints.json` and `j_<platform>.json` files in the
shape below. Build them from the current TrackBee MCP tools:

- **`tool__get_platform_footprints`** (max 31-day window — pass the 28d
  range): returns an `items` array. Each entry has `id`, `share_of_orders`,
  and `solo_share`. Pick the top 3 by `share_of_orders` (typically meta,
  google, klaviyo). If none exceed 1% of orders, the store has no shopper
  profiles yet — skip the touchpoints/journey files and let the orchestrator
  hide the Customer Journeys section.
- **`tool__get_platform_breakdown(platform=<plat>)`** per top platform:
  returns a `cooccurrence` array where `share_of_target_journeys` is the
  fraction of that platform's journeys that also touched another channel.
  Multiply by 100 for the matrix.
- **`tool__get_platform_journeys(platform=<plat>)`** per top platform:
  returns `patterns` like
  `{pattern: ["meta","klaviyo","order"], share_of_orders: 0.0056}`. Drop the
  trailing `"order"` to get the `sequence`. Multiply `share_of_orders` by
  `total_orders` (from `overview.json`) for the `count`.

Assemble the files:

```python
# touchpoints.json result payload
{
  "total_journeys":       int(total_orders * (1 - share_no_tracked_platform)),
  "multi_touch_journeys": int(total_orders * (1 - single_touch_share)),
  "single_touch_share":   sum(p.share_of_orders * p.solo_share for p in top_3),
  "available_platforms":  ["meta", "google", "klaviyo"],
  "co_occurrence": {
    "meta":    {"meta": 100, "google": <pct>, "klaviyo": <pct>,
                "no_other_platform": <solo_share*100>},
    "google":  {"meta": <pct>, "google": 100, "klaviyo": <pct>,
                "no_other_platform": <solo_share*100>},
    "klaviyo": {"meta": <pct>, "google": <pct>, "klaviyo": 100,
                "no_other_platform": <solo_share*100>},
  },
  "transitions": {},
}

# j_<plat>.json result payload
{"paths":
  [{"sequence": p.pattern[:-1],
    "count": int(p.share_of_orders * total_orders)}
   for p in patterns],
 "available_platforms": ["meta", "google", "klaviyo"]}
```

Write empty stubs (`{"paths": [], "available_platforms": [...]}`) for the
filenames you didn't fetch (`j_tiktok.json`, `j_pinterest.json`,
`j_email.json` if those weren't in the top 3). The build tolerates empty
`paths`.

## Config

Write to `/tmp/attribution_overview_config.json`:

```json
{
  "store_name": "<Store name from list_my_stores>",
  "store_currency": "<EUR|USD|GBP|SEK|...>",
  "fx_to_eur": {"USD": 0.92, "SEK": 0.087},
  "windows": {
    "28d": {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
    "7d":  {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
    "3d":  {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"}
  }
}
```

`fx_to_eur` is a per-ad-account-currency dict whose values are the multiplier
to convert FROM that currency TO the store currency. Despite the historical
name it does NOT have to end in EUR — for a GBP store you might pass
`{"GBP": 1.0, "EUR": 1.17}`. Only needs entries for currencies present on the
store's ad accounts; if they all match `store_currency`, pass `{}`. Required
fields (`store_name`, `store_currency`, the three windows' `start`/`end`) are
validated up front — if any are missing the build stops with a one-line
explanation.

Window dates: `28d` ends yesterday and starts 27 days before that. `7d` ends
yesterday and starts 6 days before. `3d` ends yesterday and starts 2 days
before. Inclusive on both ends.

## Output

The build writes one self-contained HTML file. It bakes all three windows of
data into the page, so toggling 3d/7d/28d is instant and client-side. Every
monetary value is formatted from `store_currency` (the page uses
`Intl.NumberFormat` client-side and the store currency symbol server-side) —
nothing hardcodes a currency symbol.

The NC ROAS line chart and customer-journey sankey are pre-rendered as inline
SVG in the Python build step (no Chart.js / Plotly / CDN dependency).
TrackBee logos are inlined as data URLs from the bundled assets. The page
renders identically whether opened from a local file, an air-gapped viewer,
or behind a strict CSP.

## Live artifact + daily refresh (always on)

Every run of this skill MUST do two things after the build writes the HTML:

1. **Create or update the live artifact** with `id =
   "<store-slug>-attribution-overview-report"` and `mcp_tools: []`. Using the
   same id on subsequent runs replaces the artifact in place — no duplicates.
2. **Schedule the daily 8am refresh.** List first to check for an existing
   `<store-slug>-attribution-overview-daily-refresh` task; if one exists, do
   nothing. Otherwise create it with `cronExpression = "0 8 * * *"` and the
   prompt template in step 6. The task re-runs this skill end-to-end each
   morning and updates the same artifact in place.

If the user explicitly says "don't schedule anything" or "just give me a
one-off snapshot," skip step 2 and tell them the report is static. Default is
always to schedule.

## Component layout

```
SKILL.md                              this file — build instructions
scripts/build_dashboard.py            thin entry: parse args, validate config, hand off
components/
  chrome/
    shell.html                        page shell with {TOKEN} placeholders
    theme.css                         brand tokens, layout, all CSS
    app.js                            filter wiring + client-side section renderers
    tooltip.js                        shared hover-tooltip behaviour
    format_helpers.py                 currency / number / delta formatters (factory)
    logos.py                          inline brand + platform marks
  transforms/
    loader.py                         tolerant JSON input loader
    window_metrics.py                 per-window blended / platform / channel / funnel data
    journeys.py                       path union + sankey views + journey-shape stats
    heatmap.py                        co-occurrence heatmap + low-sample caveat
  insights/
    channel_attribution.py           channel ROAS / CPA / underinvested / underperformer
    executive_summary.py             headline takeaways
    funnel.py                         stage-specific funnel fix-it insights
    journey.py                       customer-journey insights
    cooccurrence.py                  touch-point overlap insights
    questions.py                     "Where to go next" suggested prompts
  charts/
    nc_roas.py                        inline SVG NC-ROAS line
    sankey_svg.py                     inline SVG journey sankey
  orchestrators/
    assemble.py                      loads components, computes, stamps shell.html
references/                           design spec, metric map, hand-off template
assets/                              TrackBee icon + wordmark (base64 + source PNG)
```

## Guidelines

- **Always use the build.** Re-implementing the artifact code wastes tokens
  with no upside, and the components keep HTML/CSS/JS out of Python.
- **`tool__get_dashboard_overview` is the authoritative source for all spend,
  revenue, and ROAS.** Use its `platform_statistics` for Platform Overview
  tiles and Channel Attribution. Never substitute campaign-level spend or
  ROAS from `tool__get_meta_campaign_insights` /
  `tool__get_google_campaign_insights` — those are FX-unconverted and
  unblended.
- **Use `column_groups` on `tool__get_daily_store_statistics`.** Without it,
  the response is ~2.5× larger.
- **One config, three windows.** Compute window dates once; don't ask the
  user three times.
- **Currency handling lives in the build.** Pass FX rates in `config.json`
  and let the build convert. Don't convert in chat.
- **Hand off short.** A `computer://` link plus a three-sentence headline.
  The page is the deliverable; don't paste tables into chat.
- **Always create the live artifact AND schedule the daily refresh.** Same
  artifact id across runs; same task id per store. Skip the schedule only if
  the user explicitly asks for a one-off snapshot.
