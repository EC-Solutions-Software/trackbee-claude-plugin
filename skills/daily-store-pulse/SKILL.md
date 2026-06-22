---
name: daily-store-pulse
description: >-
  Build the TrackBee Daily Store Pulse — a fast, self-contained HTML artifact
  surfacing yesterday's figures for every store the user can access. The
  morning check-in, NOT a deep analysis: a portfolio summary of which stores
  have a flagged anomaly today, then one card per store with KPI tiles
  (revenue, orders, MER, ROAS, PoAS, CAC — each vs a trailing-7-day baseline
  with the delta), month-to-date pacing, a ranked "needs attention" list of
  anomalies and Meta flags, top campaign movers, and a go-deeper dock. Runs
  for ALL stores by default with a store filter, creates a live Cowork
  artifact, schedules a daily 08:00 refresh. Trigger for "daily vitals",
  "store pulse", "store health check", "how's the store today", "morning
  briefing", "did anything spike or drop today", "MTD pacing", "daily
  baseline", "anything I need to act on today", or any recurring intra-day
  status pull across stores. NOT for deep dives — diagnostics route to
  performance, budget to scale-ads-profitably, channel/journey/funnel to
  attribution.
---

# Daily Store Pulse

A fast daily read of yesterday's figures. Optimised for speed and skimmability,
not exhaustiveness — the user should get the numbers in one glance per store.
The build is driven by a thin entry script (`scripts/build_pulse.py`) that
loads small, focused components from `components/` and renders one pulse card
per store plus a portfolio header.

When a store's payload is missing or empty the card still renders: the KPI
tiles and each section degrade to a plain "no data for yesterday yet" notice
instead of failing the whole build.

## Workflow (the happy path)

1. **Run for ALL stores. Do not ask which store.** Call `tool__list_my_stores`
   and build the pulse for **every** store it returns. The artifact renders a
   client-side store filter so the user narrows to one store or a subset after
   the fact — never gate the build on a store choice. Use the user's current
   Cowork workspace folder as `<workspace>` for the output path unless they
   name another.

2. **Compute the windows once** (local time):
   - `yesterday`  = today − 1 day (the report's reference day).
   - `baseline`   = the 7 days **before** yesterday (today−8 … today−2),
     inclusive. This is the "normal day" the pulse compares against.
   - `mtd`        = first of the current month … yesterday.
   - `prev_month_mtd` = the **same span last month**: first of last month …
     the day of last month matching yesterday's day-of-month (clamped to last
     month's final day if yesterday's day-of-month is larger). E.g. pulled on
     Jun 6 → `2026-05-01 … 2026-05-05` (the same 5 elapsed days).
   - `prev_month_full` = all of last month (first … last day).
   - `trend`      = ~14 days back … yesterday, for the daily-revenue sparkline.
   - Clamp every window's start to the store's onboarding date — **never pull
     a window that begins before the store joined TrackBee.** Record
     `mtd.days_elapsed` (days from month-start through yesterday, inclusive),
     `mtd.days_total` (days in the current month), and the month names
     `mtd.this_month_label` / `mtd.prev_month_label` (e.g. "June" / "May") for
     the pacing copy.

3. **Probe before you parse.** The first time you hit each tool in a session,
   make one call and glance at the response shape so your staged JSON matches
   what the parser expects (field names are documented in §MCP calls). Then
   make the full set below **for each store, fetching in parallel** to keep the
   build fast. Save each tool's `result` payload to
   `/tmp/daily_store_pulse_inputs/` using the exact `<store_id>__<role>.json`
   filename in §MCP calls. Keep the per-store call set minimal — this is a
   daily job and speed matters.

4. **Write `/tmp/daily_store_pulse_config.json`** (template in §Config) with the
   window dates, MTD meta, the stable `artifact_id`, and one entry per store
   (id, name, currency, onboarding date, the ad platforms it runs, and any
   per-platform `fx_to_store` multipliers). Required fields are validated up
   front — missing or malformed and the build stops with a one-line reason.

5. **Run the entry script:**

   ```bash
   python3 <SKILL_DIR>/scripts/build_pulse.py \
     --inputs  /tmp/daily_store_pulse_inputs/ \
     --config  /tmp/daily_store_pulse_config.json \
     --out     "<workspace>/trackbee-daily-store-pulse-<YYYY-MM-DD>.html"
   ```

   `<SKILL_DIR>` is this skill's directory; `<YYYY-MM-DD>` is **yesterday's**
   date (the reference day). The entry script imports the orchestrator at
   `components/orchestrators/assemble.py`, which loads each transform / insight
   on demand and renders the page.

6. **Create or update the live artifact.** Call
   `mcp__cowork__create_artifact` with:
   - `id`: `trackbee-daily-store-pulse` — **always the same id**, so each run
     overwrites in place instead of stacking duplicates in the sidebar. The
     pulse is one portfolio artifact covering every store, not one per store.
   - `html_path`: the absolute path of the HTML written in step 5.
   - `description`: `"TrackBee Daily Store Pulse — <N> stores, yesterday vs
     trailing 7-day baseline (<yesterday-date>). Refreshed daily at 08:00 by
     the scheduled task."`
   - `mcp_tools`: `[]` (data is baked in at build time; the artifact does not
     call MCP at runtime — the scheduled task in step 7 keeps it fresh).

7. **Schedule the daily 08:00 refresh.** First call
   `mcp__scheduled-tasks__list_scheduled_tasks`. If
   `trackbee-daily-store-pulse-refresh` already exists, do nothing. Otherwise
   call `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `trackbee-daily-store-pulse-refresh`
   - `cronExpression`: `"0 8 * * *"` (every day at 08:00 local time)
   - `description`: `"Refresh the TrackBee Daily Store Pulse every day at 08:00."`
   - `notifyOnCompletion`: `false`
   - `prompt`: a self-contained instruction that captures everything the task
     needs without this conversation. Use the template in §Scheduled refresh
     prompt — note it **always pulls ALL stores**, regardless of whatever
     filter the user last left the artifact on.

   Then tell the user one line: "Live artifact created and a daily 08:00
   refresh is scheduled."

8. **Hand off short.** Print a `computer://` link to the HTML and the portfolio
   summary in one sentence (how many stores have a flagged anomaly today and
   which). See `references/handoff-template.md`.

## MCP calls (exact set, per store)

Probe each tool once first to confirm its shape, then make these calls for
**every** store. `<id>` is the numeric store id; `<platform>` is each ad
platform the store runs (`facebook`, `google`, …). Filenames are what to write
under `/tmp/daily_store_pulse_inputs/`.

| Filename | Tool | Args / window | Used for |
| --- | --- | --- | --- |
| `<id>__store_info.json` | `tool__get_store_information` | store | Store name, URL, onboarding date (clamps every window). |
| `<id>__overview_yday.json` | `tool__get_dashboard_overview` | `yesterday` (1 day) | Yesterday's revenue, orders, spend, MER, ROAS, CAC, new/returning, per-platform stats. **Authoritative for all spend/revenue/ROAS.** Cents of store currency. |
| `<id>__overview_base.json` | `tool__get_dashboard_overview` | `baseline` (7 days) | The "normal day" baseline. Levels (revenue, orders) compare yesterday vs window-total ÷ 7; ratios (MER, ROAS, CAC) compare yesterday vs the window ratio. |
| `<id>__overview_mtd.json` | `tool__get_dashboard_overview` | `mtd` | Month-to-date revenue + spend (this month so far). |
| `<id>__overview_prev_month_mtd.json` | `tool__get_dashboard_overview` | `prev_month_mtd` | Last month's revenue + spend over the same elapsed days — the "where am I vs last month" comparison. |
| `<id>__overview_prev_month_full.json` | `tool__get_dashboard_overview` | `prev_month_full` | Last month's full-month revenue + spend — the projection benchmark. |
| `<id>__daily.json` | `tool__get_daily_store_statistics` | `trend` | Daily revenue series for the sparkline. `{store_currency, rows:[{date, total_revenue, total_orders, …}]}`, cents. |
| `<id>__poas_yday.json` | `tool__get_profit_on_ad_spend` | `grain="platform"`, `yesterday`, `cost_overrides={}` | Profit/revenue ratio yesterday. PoAS = that ratio × ROAS; est. profit = ratio × revenue. Falls back to the store-level COGS % when per-variant cost is missing. |
| `<id>__poas_base.json` | `tool__get_profit_on_ad_spend` | `grain="platform"`, `baseline` | Baseline profit/revenue ratio for the PoAS delta. |
| `<id>__anomalies.json` | `tool__detect_anomalies` | `yesterday`, `sensitivity="medium"` | Yesterday's anomalies (revenue / orders / funnel / tracking_health). Drives the needs-attention list and the portfolio flag count. `{anomalies:[…]}`. |
| `<id>__meta_recs.json` | `tool__get_meta_recommendations` | store | Meta's own warnings (creative-limited, fragmentation, …). `{recommendations:[{type, description, opportunity_score_lift, trackbee_note}]}`. Tracking-flavoured recs (with `trackbee_note`) are defused, never shown as "your tracking is broken". |
| `<id>__cmp_facebook_yday.json` | `tool__get_meta_campaign_insights` | `start_date=end_date=yesterday`, `status_filter="all"` | Per-campaign `spend` + `purchase_roas` (Meta). Spend in **units** of the ad-account currency. |
| `<id>__cmp_facebook_prev.json` | `tool__get_meta_campaign_insights` | day **before** yesterday, `status_filter="all"` | Same shape — top movers rank by day-over-day spend swing and surface the ROAS swing. |
| `<id>__cmp_google_yday.json` | `tool__get_google_campaign_insights` | `start_date=end_date=yesterday`, `status_filter="all"` | Per-campaign `spend` + `conversions_value` (Google; ROAS = value ÷ spend). Spend in **units** of the ad-account currency. |
| `<id>__cmp_google_prev.json` | `tool__get_google_campaign_insights` | day **before** yesterday, `status_filter="all"` | Same shape, prior day. |

Only call the campaign-insights tool for platforms a store actually runs (the
`platforms` list in its config entry). These two tools scope to one ad account
per store; a store with no Meta/Google ad account simply yields no movers.

**Missing inputs:** if a tool errors (store not connected, no ad account, a
window before onboarding, etc.), skip that file. The orchestrator tolerates
absent files — affected KPI tiles render "—" and the affected sections show a
plain notice. A store with no usable data renders a "no data for yesterday
yet" notice on its KPI tiles rather than fabricated figures.

**Currency:** every `get_dashboard_overview` / `get_daily_store_statistics` /
`detect_anomalies` figure is in **cents of the store currency** — the parser
divides by 100 once. Campaign-insights spend is in **units** (not cents) of the
**ad-account** currency; pass `fx_to_store` per platform in the config when a
store's ad account runs in a different currency than the store, so movers read
in one currency. ROAS / MER / PoAS are unitless ratios, unaffected by FX.

## Config

Write to `/tmp/daily_store_pulse_config.json`:

```json
{
  "generated_date": "<today, YYYY-MM-DD>",
  "baseline_days": 7,
  "artifact_id": "trackbee-daily-store-pulse",
  "windows": {
    "yesterday":        {"start": "<YYYY-MM-DD>", "end": "<same day>"},
    "baseline":         {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
    "mtd":              {"start": "<month-start>", "end": "<yesterday>"},
    "prev_month_mtd":   {"start": "<last-month-1st>", "end": "<last-month-same-day>"},
    "prev_month_full":  {"start": "<last-month-1st>", "end": "<last-month-last-day>"},
    "trend":            {"start": "<~14d back>",   "end": "<yesterday>"}
  },
  "mtd": {"days_elapsed": <int>, "days_total": <int>,
          "this_month_label": "<e.g. June>", "prev_month_label": "<e.g. May>"},
  "stores": [
    {
      "store_id": "<id>",
      "store_name": "<from list_my_stores>",
      "store_currency": "<EUR | USD | GBP | ...>",
      "store_url": "<myshopify url, optional>",
      "onboarding_date": "<YYYY-MM-DD from get_store_information>",
      "platforms": ["facebook", "google"],
      "fx_to_store": {"facebook": 1.0, "google": 1.0}
    }
  ]
}
```

`windows.yesterday`, `windows.baseline`, and `stores` (a list, possibly empty)
are required and validated before any rendering. `baseline_days` defaults to 7.
`fx_to_store` defaults to 1.0 per platform (same-currency stores omit it).

## Scheduled refresh prompt

The scheduled task re-runs the whole skill daily. Use this template (substitute
the placeholders):

```
Refresh the TrackBee Daily Store Pulse by running the /daily-store-pulse skill
end-to-end for EVERY store the user has access to.

CONTEXT
- Workspace folder: <WORKSPACE_PATH>
- Entry script:
  $CLAUDE_PLUGIN_ROOT/.claude/skills/daily-store-pulse/scripts/build_pulse.py

WINDOWS — compute every run, do NOT hard-code
- yesterday        = today − 1 day (local)
- baseline         = the 7 days before yesterday (today−8 … today−2), inclusive
- mtd              = first of the current month … yesterday
- prev_month_mtd   = first of last month … last month's day matching yesterday's
                     day-of-month (clamped to last month's final day)
- prev_month_full  = all of last month (first … last day)
- trend            = ~14 days back … yesterday
- Clamp every start to each store's onboarding date.

PLAN
1. Call list_my_stores and run the pulse for ALL stores it returns — ignore any
   store filter a human may have left the artifact on; the refresh is always
   the full portfolio.
2. For each store, make the per-store MCP calls from the skill's SKILL.md, stage
   them under /tmp/daily_store_pulse_inputs/, write the config, and build the
   HTML at <WORKSPACE_PATH>/trackbee-daily-store-pulse-<YYYY-MM-DD>.html
   (yesterday's date).
3. Update the existing artifact in place: call mcp__cowork__create_artifact with
   the SAME id "trackbee-daily-store-pulse" and the new html_path. Same id =
   update, not a duplicate.
4. Print one line to chat: how many stores need attention, which, and the
   artifact link as computer://<absolute-path>.
```

## Component layout

```
components/
  chrome/                       page shell, theme, helpers, page glue
    shell.html                  outer HTML scaffold with placeholders
    theme.css                   v3 brand tokens + per-section CSS
    format_helpers.py           build-time currency / number / delta helpers
    logos.py                    inline brand wordmark (base64)
    store_filter.js             client-side store filter (all / single / subset, localStorage)
    dock.js                     go-deeper dock glue (sendPrompt or clipboard)
  transforms/                   raw JSON -> render-ready dicts
    loader.py                   per-store payload normalizer (cents -> units)
    kpis.py                     the six KPI tiles (yesterday vs baseline)
    mtd.py                      month-to-date pacing vs implied pace
    movers.py                   top campaign movers by spend swing
  insights/                     payload -> attention list / dock copy
    attention.py                anomalies + Meta flags -> ranked list
    dock.py                     store-aware go-deeper prompts
  charts/
    sparkline.py                inline SVG daily-revenue sparkline
  views/
    pulse_card.html             one-per-store card template
  orchestrators/
    assemble.py                 loads each component + stamps the page
```

Each file owns one responsibility and is self-contained — no inter-component
imports; the orchestrator loads each by relative path. Shared build-time helpers
live in `chrome/format_helpers.py`.

## What's bundled

```
scripts/build_pulse.py          entry script (thin wrapper)
components/                     modular build kit (see §Component layout)
assets/tb_wordmark_dark_b64.txt TrackBee wordmark (dark variant), base64 — the navy header renders this
assets/tb_wordmark_b64.txt      TrackBee wordmark (light variant), base64
assets/tb_icon_b64.txt          TrackBee icon, base64
references/dashboard-spec.md    full per-section spec
references/handoff-template.md  what to print to chat after the build
```

## Guidelines

- **Always use the entry script.** Re-implementing the renderer wastes tokens
  and drifts from the visual spec.
- **All stores, every run. Never ask which store.** The filter does the
  narrowing client-side; the scheduled refresh always pulls the full portfolio.
- **Skimmable figures, no verdicts.** Every card must be skimmable in under ten
  seconds: the KPI tiles (yesterday vs baseline, with the delta) and the
  needs-attention list carry the card. The pulse presents measured figures and
  the anomaly monitor's own flags — it never labels a store with a TrackBee
  verdict. Keep added copy short and concrete.
- **`tool__get_dashboard_overview` is the authoritative source** for spend,
  revenue, MER, ROAS, and CAC. Never substitute campaign-level numbers for the
  headline KPIs.
- **Respect onboarding dates and empty returns.** Clamp windows to onboarding;
  let new stores and quiet days render a "no data for yesterday yet" notice
  gracefully.
- **Hand off short.** A `computer://` link plus the one-line portfolio summary.
- **Always create the live artifact AND schedule the daily refresh.** Skip only
  if the user explicitly says "one-off snapshot, don't schedule."
- **Brand styling is fixed.** All v3 tokens live in
  `components/chrome/theme.css`. Don't inline brand colors elsewhere — edit the
  tokens. Monetary strings always format from `store_currency`; never hardcode a
  currency symbol.
- **Don't swallow deep dives.** The pulse answers "is it healthy today?" and
  routes everything heavier through the go-deeper dock: `/performance` for
  ad-account diagnostics, `/scale-ads-profitably` for budget moves,
  `/attribution` for channel / journey / funnel work, `/creatives-report` for
  creative fatigue, `/growth-report` for the full profitable-growth picture.
```
