---
name: growth-report
description: >-
  Build the TrackBee Growth Report — a self-contained HTML artifact
  answering "What is actually driving profitable growth, and why?" for
  any TrackBee-connected store. Compares the last 7 days against the
  prior 7 days, renders a narrative answer (short answer + why,
  grounded in this window's measured figures), a what's-working /
  what's-breaking split, and the full TrackBee Growth metric framework
  with each row's current/prior values and week-over-week change. Always creates
  a live Cowork artifact and schedules a daily 08:00 refresh. Trigger when
  asked "what's driving profitable growth", "what's working / breaking on this
  store", "is MER improving", "build the growth report", "open the growth
  scorecard", or any request to score a store against the TrackBee growth
  checklist. Distinct from attribution (multi-touch channel journeys, NC-ROAS,
  channel mix) and performance (ad-account diagnostics) — use growth-report
  for the profitable-growth KPI + structural-driver narrative.
---

# Growth Report

Render a TrackBee-branded HTML report from the TrackBee Insights. The build is
driven by a thin entry script (`scripts/build_report.py`) that loads small,
focused components from `components/` in sequence — one file per major
section of the report.

When a section's required input is missing, the orchestrator stamps a
plain-language "Data unavailable" notice inside that section's card
instead of failing the whole build. The other sections still render so the
user gets every piece of data we actually have.

## Workflow (the happy path)

1. **Pick store and workspace.** Call `tool__list_my_stores`. If
   the user didn't name a store, ask which. Use the user's current Cowork
   workspace folder as `<workspace>` for the output path unless they name
   another — ask only if no workspace is available. Window dates
   are computed for you in step 2 — don't ask the user about windows.
   Campaign exclusions are chosen in step 2b, from the real campaign list.

2. **Compute the windows, then make the MCP calls.** First run
   `python3 <SKILL_DIR>/scripts/build_report.py --print-windows` — it prints the
   `anchor_date` (yesterday) and the exact current + prior 7-day ranges.
   **Never compute these dates by hand.** Then make the MCP calls listed in
   §MCP calls below using those dates (current = current window, prior = prior
   window). Save each `result` payload as a JSON file in
   `/tmp/growth_report_inputs/` with the filename listed in §MCP calls.

2b. **Choose exclusions from the real campaign list, then confirm.** The
   `meta_campaigns.json` / `google_campaigns.json` payloads fetched in step 2
   carry the spending campaigns. Present them as a neutral, **numbered**
   list — one row per campaign, numbered `1, 2, 3, …`, each showing
   `campaign_name · campaign_id · spend · ROAS · status` — so the user can
   pick by number. Present them **factually only**: do not label, group, or
   infer which are "test" campaigns, and do not recommend exclusions from
   the names — a campaign name is not a reliable signal of intent, so the
   choice is the user's. Ask which to exclude from the report
   (default: none → empty list); accept row numbers or ids and resolve them
   to `campaign_id`s. If the resulting list is non-empty, echo it
   back and require an explicit yes before building: "Excluding N campaign(s):
   name1, name2 — proceed?" If the list is empty, no
   confirmation is needed. On a scheduled refresh, reuse the saved list
   unchanged rather than re-asking.

3. **Write `/tmp/growth_report_config.json`** with the store id, name,
   currency, the `anchor_date` from step 2, and the resolved
   `scope.exclude_campaign_ids` from step 2b (template in §Config). The script
   derives the window ranges from `anchor_date` — don't write them yourself.
   Required fields are validated up front — missing or malformed and the build
   stops with a one-line explanation.

4. **Run the entry script:**

   ```bash
   python3 <SKILL_DIR>/scripts/build_report.py \
     --inputs  /tmp/growth_report_inputs/ \
     --config  /tmp/growth_report_config.json \
     --out     "<workspace>/<store-slug>-growth-report-<YYYY-MM-DD>.html"
   ```

   `<SKILL_DIR>` is this skill's directory. The entry script imports the
   orchestrator at `components/orchestrators/assemble.py`, which loads each
   transform / insight on demand. Replace `<workspace>` with the workspace
   folder chosen in step 1 and `<store-slug>` with a kebab-case version of
   the store name.

5. **Create or update the live artifact.** Call
   `mcp__cowork__create_artifact` with:
   - `id`: `<store-slug>-growth-report` — **always use the
     same id for a given store**, so subsequent runs overwrite in place
     instead of stacking duplicates in the sidebar.
   - `html_path`: the absolute path of the HTML file written in step 4.
   - `description`: `"TrackBee Growth Report for <Store
     Name> — last 7d vs prior 7d, ending <end-date>. Refreshed daily at
     08:00 by the scheduled task."`
   - `mcp_tools`: `[]` (data is baked in at build time; the artifact does
     not call MCP at runtime — the scheduled task in step 6 keeps it
     fresh).

6. **Schedule the daily 08:00 refresh.** Before handing off, call
   `mcp__scheduled-tasks__list_scheduled_tasks` to check whether a task
   for this store already exists. If
   `<store-slug>-growth-report-daily-refresh` is already listed, do
   nothing. Otherwise call `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `<store-slug>-growth-report-daily-refresh`
   - `cronExpression`: `"0 8 * * *"` (every day at 08:00 local time)
   - `description`: `"Refresh the <Store Name> TrackBee Growth
     Report every day at 08:00."`
   - `notifyOnCompletion`: `false`
   - `prompt`: a self-contained instruction that captures everything the
     task needs to do without access to this conversation. Use this
     template (substitute the placeholders) — and include the
     `impersonate=<USER_ID>` lines only if this run impersonated a user
     (internal/admin runs); for a normal customer authed to their own
     store, omit both impersonate lines so the daily refresh runs under
     the user's own access:

     ```
     Refresh the TrackBee Growth Report for <Store Name>
     (store id <STORE_ID>) by running the /growth-report skill
     end-to-end.

     CONTEXT
     - Store: <Store Name>, store_id = <STORE_ID>,
       store_currency = <CCY>.
     - Pass impersonate=<USER_ID> on every TrackBee Insights call (this is
       the user the original run used).
     - Workspace folder: <WORKSPACE_PATH>
     - Entry script:
       $CLAUDE_PLUGIN_ROOT/.claude/skills/growth-report/scripts/build_report.py

     WINDOWS — let the script compute them, do NOT hard-code
     - Run build_report.py --print-windows to get anchor_date (yesterday)
       and the current + prior 7-day ranges. Use those exact dates for the
       MCP calls and write anchor_date into the config.

     SCOPE
     - exclude_campaign_ids = <EXCLUDED_OR_EMPTY> (reuse the original run's
       list; the scheduled refresh does not re-ask).

     PLAN
     1. Invoke the /growth-report skill against store <STORE_ID>
        using those windows. Use impersonate=<USER_ID>.
     2. Build the report HTML at
        <WORKSPACE_PATH>/<store-slug>-growth-report-<YYYY-MM-DD>.html
        (yesterday's date).
     3. Update the existing artifact in place: call
        mcp__cowork__create_artifact with the SAME id
        "<store-slug>-growth-report" and the new html_path.
        Same id = update, not duplicate.
     4. Print one line to chat: revenue, MER, the biggest "breaking"
        driver, and the artifact link as computer://<absolute-path>.
     ```

   Tell the user one line: "Live artifact created and a daily 08:00
   refresh is scheduled."

7. **Hand off.** Print a `computer://` link to the HTML and a
   two-sentence headline: top KPI delta + the most material driver.

## MCP calls (exact set)

Make exactly these calls, both windows. Names are the filenames to write
under `/tmp/growth_report_inputs/`.

| Filename | Tool | Notes |
| --- | --- | --- |
| `overview_current.json` | `tool__get_dashboard_overview` | Current 7-day window. **Primary source for revenue / MER / ROAS / CAC / LTV / new-vs-returning splits.** All values converted to `store_currency`. |
| `overview_prior.json` | `tool__get_dashboard_overview` | Prior 7-day window. Same store + currency. |
| `funnel_current.json` | `tool__get_funnel_overview` | Current window. Pass `compare_previous_period=true` so the prior-window funnel ships in the same payload. |
| `funnel_prior.json` | `tool__get_funnel_overview` | Optional. Used as a fallback if `funnel_current.json` somehow doesn't include the comparison block. |
| `platform_footprints_current.json` | `tool__get_platform_footprints` | Channel share-of-orders, top/mid/bottom shares — drives first-touch + last-touch + assist rows. |
| `meta_recommendations.json` | `tool__get_meta_recommendations` | Meta's own creative-fatigue + fragmentation flags — drives the creative-fatigue row. |
| `meta_campaigns.json` | `tool__get_meta_campaign_insights` | Current window only, `status_filter="all"`. Used to resolve excluded `campaign_id`s back to campaign names for the exclusion note. |
| `google_campaigns.json` | `tool__get_google_campaign_insights` | Current window only, `status_filter="all"`. Same — name resolution for the exclusion note. |
| `anomalies.json` | `tool__detect_anomalies` | Cover both windows. Drives the confidence row. |

**`tool__get_meta_campaign_insights` and `tool__get_google_campaign_insights` return large
payloads (~90KB each).** Slim them at fetch time to keep only `campaign_id`, `campaign_name`, `campaign_type` (Google only), `spend`, `purchase_roas` / `conversions_value`, and a couple of related fields — the exclusion note only needs `campaign_id` + `campaign_name`.

**Missing inputs:** if a tool errors (store not connected, ad account
missing, etc.), skip the file. The orchestrator tolerates absent files —
affected metric rows render "—" / "N/A" with a plain reason in the
interpretation column rather than crashing.

## Config

Write to `/tmp/growth_report_config.json`:

```json
{
  "store_id":       "<store id as string or number>",
  "store_name":     "<human-readable store name from list_my_stores>",
  "store_currency": "<EUR | USD | GBP | ...>",
  "currency_symbol": "<optional — overrides the derived symbol, e.g. \"€\">",
  "anchor_date":    "<YYYY-MM-DD — the current-window end from --print-windows (yesterday)>",
  "meta_fx_to_store":   1.0,
  "google_fx_to_store": 1.0,
  "scope": {
    "exclude_campaign_ids": []
  }
}
```

`store_id`, `store_name`, and `store_currency` are required — the entry
script validates them before any rendering begins.

`currency_symbol` is optional — when present it overrides the symbol derived
from `store_currency` (useful when the MCP/config supplies one directly).
Omit it to fall back to the built-in ISO-code table.

`meta_fx_to_store` / `google_fx_to_store` are optional multipliers that
convert campaign **spend** from the ad-account currency into the store
currency (the campaign-insights payloads report spend in ad-account
currency; everything else is already store currency). Pass them whenever a
store's ad account runs in a different currency than `store_currency`, so
the Next-steps `min_spend` gates compare like-for-like. Omit them (or pass
`1.0`) for same-currency stores. ROAS is a ratio and is unaffected.

Window dates are **derived by the script**, never written by hand.
`anchor_date` is the current-window end (yesterday by default);
`build_report.py` computes current = the 7 days ending on it and prior = the 7
days immediately before that, inclusive — each window exactly 7 days. Get the
exact dates with `--print-windows` (step 2) and use them for the MCP calls.
Omit `anchor_date` to default to yesterday.

`scope.exclude_campaign_ids` is an optional list of campaign **ids** to drop
from the report (e.g. test campaigns). The excluded names are listed in a
plain-language note so nothing is hidden silently. Resolve any user-named
campaigns to their ids from the fetched campaign payloads. Empty list =
exclude nothing.

## Component layout

```
components/
  chrome/                       page shell, theme, helpers
    shell.html                  outer HTML scaffold with placeholders
    theme.css                   v3 brand tokens + per-section CSS
    format_helpers.py           build-time currency-symbol + number helpers
    logos.py                    inline brand wordmark (base64)
  transforms/                   raw JSON -> render-ready dicts
    headline_kpis.py            per-window KPI summary (current / prior)
    drivers.py                  what's-working / what's-breaking lists
    metrics_table.py            the metric framework table
  insights/                     payload -> narrative strings
    answer.py                   hero headline + answer card (lead answer + why)
  orchestrators/
    assemble.py                 loads each transform/insight + stamps HTML
```

Each file owns one responsibility. The orchestrator loads each component
by relative path the moment it's needed; shared build-time helpers live in
`chrome/format_helpers.py` and are loaded via the same path-based shim. The
metrics framework definition lives inside `transforms/metrics_table.py` as a
static list so every row is versioned alongside the code.

## What's bundled

```
scripts/build_report.py         entry script (thin wrapper)
components/                     modular build kit (see §Component layout)
assets/tb_wordmark_dark_b64.txt TrackBee wordmark (dark variant), base64 — the one the navy hero renders
assets/tb_wordmark_b64.txt      TrackBee wordmark (light variant), base64
assets/tb_icon_b64.txt          TrackBee icon, base64
references/dashboard-spec.md    full per-section spec
references/metric-map.md        metric -> MCP-field mapping
references/handoff-template.md  what to print to chat after the build
```

## Guidelines

- **Always use the entry script.** Re-implementing the renderer from
  scratch wastes tokens and drifts from the visual spec.
- **`tool__get_dashboard_overview` is the authoritative source for all spend,
  revenue, and ROAS.** Never substitute campaign-level numbers for the
  headline KPIs.
- **One config, two windows.** Compute window dates once; don't ask the
  user twice.
- **Hand off short.** A `computer://` link plus a two-sentence headline.
- **Always create the live artifact AND schedule the daily refresh.**
  Skip only if the user explicitly says "one-off snapshot, don't
  schedule."
- **Brand styling is fixed.** All v3 tokens live in
  `components/chrome/theme.css`. Don't inline brand colors elsewhere —
  edit the tokens.
