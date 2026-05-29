---
name: attribution
description: >-
  Generate a TrackBee-branded Attribution Report — one self-contained
  HTML page combining an Executive Summary, Blended Overview with
  Acquisition MER over time, Platform Overview, Channel Attribution,
  and Customer Journeys (touch-points heatmap + sankey, auto-hidden
  when the store has no shopper profiles). Use this skill whenever
  someone asks for an attribution dashboard, a marketing scorecard,
  an Attribution Report, a channel-contribution view, where platforms
  overlap, a journey/path visualisation, a multi-touch overview, or
  any persistent multi-report attribution view — even if they don't
  use the word "dashboard". Trigger also for "show me how each channel
  contributes", "where do my platforms overlap", "rebuild this in our
  brand", "TrackBee-branded attribution view", or any request that
  includes both blended/per-platform KPIs and a channel breakdown.
---

# Attribution Report

Render a TrackBee-branded HTML report from the TrackBee MCP. The build
is driven by a thin entry script (`scripts/build_dashboard.py`) that
loads small, focused components from `components/` in sequence — one
file per major section of the report. No part of the build is
duplicated across files; every shared helper has a single home.

When a *secondary* section's input is missing, the orchestrator stamps
a plain-language "Data unavailable" notice inside that section's card
instead of failing the whole build. The other sections still render so
the user gets every piece of data we actually have. **The primary
overview file is different** — without it every KPI on the page is
blank, so the build script refuses to run when it's missing (see
step 2 below).

## Workflow (the happy path)

**You must fetch the data before you build.** The build script is not
a renderer of placeholders — it will hard-fail if you point it at an
empty inputs directory or one that's missing `overview.json`. Don't
skip ahead. Don't run the build, see "Data unavailable" notices, and
then create the artifact anyway — that's the exact failure mode this
skill was hardened to prevent.

1. **Pick store + windows.** Call `tool__list_my_stores`, ask the user which
   store and which time window (default **28 days** ending yesterday).
   The dashboard always covers three windows together (28d / 7d / 3d)
   so the in-page filter works; you only need one set of dates.
2. **Fetch the data — make every MCP call listed in §MCP calls below.**
   Use exactly that set — no extras, no skips. Save each tool response
   (the full payload, keeping the `{"result": ...}` envelope) as a
   JSON file in `/tmp/attribution_inputs/` with the filename listed in
   §MCP calls (e.g. `overview.json`, `daily.json`, `meta_7d.json`).

   **Before moving on, sanity-check the directory:** run
   `ls -la /tmp/attribution_inputs/` and confirm `overview.json` is
   there and is more than a few bytes. If an *ancillary* tool errored
   (one ad account isn't connected, the store has no shopper profiles,
   etc.), you can skip that one file — the orchestrator will stamp a
   "Data unavailable" notice into the affected section and the rest of
   the report still renders. But you can never skip `overview.json`,
   the daily/funnel/platform_funnel files, or the meta/google files
   for the 28d window. They drive every number on the page.
3. **Write `/tmp/attribution_config.json`** with store name, currency,
   FX rates, and the three windows' start/end dates (template in
   §Config). Required fields are validated up front — if any are
   missing or malformed the build stops with a one-line explanation.
4. **Run the entry script:**

   ```bash
   python3 <SKILL_DIR>/scripts/build_dashboard.py \
     --inputs  /tmp/attribution_inputs/ \
     --config  /tmp/attribution_config.json \
     --out     "<workspace>/<store-slug>-attribution-report-<YYYY-MM-DD>.html"
   ```

   `<SKILL_DIR>` is this skill's path. The entry script imports the
   orchestrator at `components/orchestrators/assemble.py`, which loads
   transforms, insights, charts, and chrome on demand. Each component
   lives in its own file (see §Component layout). Replace `<workspace>`
   with the user's selected workspace folder and `<store-slug>` with a
   kebab-case version of the store name.

5. **Create or update the live artifact.** Call
   `mcp__cowork__create_artifact` with:
   - `id`: `<store-slug>-attribution-report` — **always use the same
     id for a given store**, so subsequent runs overwrite in place
     instead of stacking duplicates in the sidebar.
   - `html_path`: the absolute path of the HTML file written in step 4.
   - `description`: `"TrackBee Attribution Report for <Store Name> —
     28d/7d/3d windows ending <end-date>. Refreshed daily at 08:00 by
     the scheduled task."`
   - `mcp_tools`: `[]` (data is baked in at build time; the artifact
     does not call MCP at runtime — the scheduled task in step 6 keeps
     it fresh).

6. **Schedule the daily 8am refresh.** Before handing off, call
   `mcp__scheduled-tasks__list_scheduled_tasks` to check whether a task
   for this store already exists. If `<store-slug>-attribution-daily-refresh`
   is already listed, do nothing. Otherwise call
   `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `<store-slug>-attribution-daily-refresh`
   - `cronExpression`: `"0 8 * * *"` (every day at 8am local time)
   - `description`: `"Refresh the <Store Name> TrackBee Attribution
     Report every day at 8am."`
   - `notifyOnCompletion`: `false`
   - `prompt`: a self-contained instruction that captures everything
     the task needs to do without access to this conversation. Use
     this template (substitute the placeholders):

     ```
     Refresh the TrackBee Attribution Report for <Store Name>
     (store id <STORE_ID>) by running the /attribution skill end-to-end.

     CONTEXT
     - Store: <Store Name>, store_id = <STORE_ID>,
       store_currency = <CCY>.
     - Pass impersonate=<USER_ID> on every TrackBee MCP call (this is
       the user the original run used).
     - Ad-account FX: <FX_DICT> (e.g. {"GBP": 1.0, "EUR": 0.85}). Use a
       fresher rate if you have one.
     - Workspace folder: <WORKSPACE_PATH>
     - Entry script: $CLAUDE_PLUGIN_ROOT/.claude/skills/attribution/scripts/build_dashboard.py

     WINDOWS — compute every run, do NOT hard-code
     - 28d ends YESTERDAY (today − 1 day local). 7d ends yesterday. 3d
       ends yesterday. Each starts (N−1) days before its end.

     PLAN
     1. Invoke the /attribution skill against store <STORE_ID> using
        the windows above. Use impersonate=<USER_ID>.
     2. Build the report HTML at
        <WORKSPACE_PATH>/<store-slug>-attribution-report-<YYYY-MM-DD>.html
        (yesterday's date).
     3. Update the existing artifact in place: call
        mcp__cowork__create_artifact with the SAME id
        "<store-slug>-attribution-report" and the new html_path.
        Same id = update, not duplicate.
     4. Print one line to chat: revenue, ROAS, biggest journey insight,
        and the artifact link as computer://<absolute-path>.
     ```
   Tell the user one line: "Live artifact created and a daily 8am
   refresh is scheduled." First run pre-approves the MCP tools the
   task needs, so subsequent runs go through without prompts.

7. **Hand off.** Print a `computer://` link to the HTML and a
   one-paragraph headline (top KPI + most striking attribution finding
   + most useful journey insight). Full template in
   `references/handoff-template.md`.

If anything in the spec needs clarifying — what each section should
look like, how insights are computed, brand tokens, copy tone — read
`references/dashboard-spec.md`. **Don't read it for normal runs.** It's
only needed when modifying a component or designing a new variant.

## MCP calls (exact set)

Make exactly these calls. **Do not call `tool__get_campaign_performance`** —
its data overlaps with `tool__get_*_campaign_insights` and it returns large
duplicated rows that bloat context for no benefit.

| Filename | Tool | Notes |
| --- | --- | --- |
| `overview.json` / `overview_7d.json` / `overview_3d.json` | `tool__get_dashboard_overview` | One per window. **Primary source for all spend, revenue, and ROAS numbers.** Drives Blended Overview KPI tiles, Platform Overview tiles, and Channel Attribution spend + ROAS columns. All monetary values are already converted to `store_currency` — do not use campaign-level spend/ROAS from `meta.json` or `google.json` for these tiles. |
| `daily.json` | `tool__get_daily_store_statistics` | 28-day window. **Pass `column_groups=["core","funnel","customer_segments","platform_totals"]`** to keep the response tight. |
| `funnel.json` / `funnel_7d.json` / `funnel_3d.json` | `tool__get_funnel_overview` | One per window. **Pass `compare_previous_period=true`** so deltas are baked in. |
| `platform_funnel.json` / `platform_funnel_7d.json` / `platform_funnel_3d.json` | `tool__get_platform_funnel_breakdown` | One per window. |
| `meta.json` / `meta_7d.json` / `meta_3d.json` | `tool__get_meta_campaign_insights` | One per window. Used for impressions, CTR, CPM, and in-platform purchase counts only. |
| `google.json` / `google_7d.json` / `google_3d.json` | `tool__get_google_campaign_insights` | One per window. Used for impressions, CTR, CPM, and in-platform conversion counts only. |
| `touchpoints.json` | `tool__get_platform_footprints` + per-platform `tool__get_platform_breakdown` | Customer-journey scaffolding — see §Customer Journeys adapter. |
| `j_meta.json`, `j_google.json`, `j_klaviyo.json`, `j_tiktok.json`, `j_pinterest.json`, `j_email.json` | `tool__get_platform_journeys` | One per top channel — see §Customer Journeys adapter. |

If the store has additional platforms tracked by
`tool__get_platform_funnel_breakdown`, those rows render automatically
without code changes.

**Missing inputs:** if a tool errors (store not connected, ad account
missing, etc.), skip the file. The build script tolerates absent
files — the affected section renders a plain-language "Data
unavailable" notice with the reason rather than zeros / em-dashes.

## Customer Journeys adapter

The build expects `touchpoints.json` and `j_<platform>.json` files in
the shape:

- **`tool__get_platform_footprints`** (max 31-day window — pass the 28d
  range): returns an `items` array. Each entry has `id`,
  `share_of_orders`, and `solo_share`. Pick the top 3 by
  `share_of_orders`. If none exceed 1% of orders, the store has no
  shopper profiles yet — skip the touchpoints/journey files and let
  the orchestrator render the Customer Journeys "Data unavailable"
  card.
- **`tool__get_platform_breakdown(platform=<plat>)`** per top platform:
  returns a `cooccurrence` array where `share_of_target_journeys` is
  the fraction of that platform's journeys that also touched another
  channel. Multiply by 100 for the matrix.
- **`tool__get_platform_journeys(platform=<plat>)`** per top platform:
  returns `patterns` like
  `{pattern: ["meta","klaviyo","order"], share_of_orders: 0.0056}`.
  Drop the trailing `"order"` to get the `sequence`. Multiply
  `share_of_orders` by `total_orders` (from `overview.json`) for the
  `count`.

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

Write empty stubs (`{"paths": [], "available_platforms": [...]}`) for
the filenames you didn't fetch.

## Config

Write to `/tmp/attribution_config.json`:

```json
{
  "store_name": "<Store name from tool__list_my_stores>",
  "store_currency": "<EUR|USD|GBP|SEK|...>",
  "fx_to_eur": {"USD": 0.92, "SEK": 0.087},
  "windows": {
    "28d": {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
    "7d":  {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
    "3d":  {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"}
  }
}
```

Every top-level field is required except `fx_to_eur` (default empty).
The entry script validates the config before any rendering begins; a
missing or malformed field fails the build with a one-line message
naming what's missing.

`fx_to_eur` is a per-ad-account-currency dict whose values are the
multiplier to convert FROM that currency TO the store currency.
Despite the historical name it does NOT have to end in EUR — for a GBP
store you might pass `{"GBP": 1.0, "EUR": 1.17}`. Only needs entries
for currencies present on the store's ad accounts; if they all match
`store_currency`, pass `{}`.

Window dates: `28d` ends yesterday and starts 27 days before that. `7d`
ends yesterday and starts 6 days before. `3d` ends yesterday and
starts 2 days before. Inclusive on both ends.

## Component layout

The build is split into focused modules under `components/`, loaded by
the orchestrator on demand:

```
components/
  chrome/                     page shell, theme, brand-neutral helpers
    shell.html                outer HTML scaffold with placeholders
    theme.css                 colour tokens + per-section CSS
    format_helpers.js         currency / number / pct formatters
    render_sections.js        per-section renderers + unavailable notices
    window_filter.js          3d / 7d / 28d filter glue
    sankey_filter.js          sankey view toggles
    tooltip.js                shared tooltip
    logos.py                  inline SVG marks for platforms + brand
  transforms/                 raw JSON → one named key in window.TB_DATA
    blended_kpis.py
    platform_tiles.py
    channel_attribution.py
    daily_nc_roas.py
    journey_kpis.py
    journey_heatmap.py
    journey_sankey.py
  insights/                   payload → array of {obs, act} observations
    executive_summary.py
    channel_attribution.py
    journey.py
    cooccurrence.py
  charts/
    nc_roas_line.js           inline SVG chart renderer
  orchestrators/
    assemble.py               loads each transform/insight in sequence
                              and stamps the final HTML
```

Each file owns one responsibility. The orchestrator imports each
component the moment it's needed and never bundles them up front —
this keeps individual files small (every file under ~250 lines) and
makes section-by-section edits possible without touching the rest.

## What's bundled

```
scripts/build_dashboard.py        entry script (thin wrapper)
components/                       modular build kit (see §Component layout)
assets/tb_icon_b64.txt            TrackBee icon, base64
assets/tb_wordmark_b64.txt        TrackBee wordmark, base64
assets/trackbee-icon.png          icon source — only if regenerating
assets/trackbee-wordmark.png      wordmark source
references/dashboard-spec.md      full per-section spec
references/metric-map.md          standard attribution metrics → TrackBee fields
references/handoff-template.md    what to print to chat after rendering
```

## Guidelines

- **Always use the entry script.** Re-implementing the renderer from
  scratch wastes tokens and drifts from the visual spec.
- **`tool__get_dashboard_overview` is the authoritative source for all
  spend, revenue, and ROAS.** Never substitute campaign-level numbers
  for tile values.
- **Use `column_groups` on `tool__get_daily_store_statistics`.** Without it,
  the response is ~2.5× larger.
- **One config, three windows.** Compute window dates once; don't ask
  the user three times.
- **Currency handling lives in the components.** Pass FX rates in
  `config.json` and let the transforms convert.
- **Hand off short.** A `computer://` link plus a three-sentence
  headline.
- **Always create the live artifact AND schedule the daily refresh.**
  Skip only if the user explicitly says "one-off snapshot, don't
  schedule."
