---
name: analyze-ad-performance
description: >-
  Generate a TrackBee-branded Ad Performance Dashboard — a self-contained
  HTML report showing all active campaigns, ad sets, and ads across Meta and
  Google for every store the user has access to. Answers "how is my ad
  account performing this week?" Shows spend, ROAS, impressions, reach,
  frequency, CPM, CTR, CPC, clicks, ATC, purchases, revenue, and
  new-customer metrics, plus per-platform key observations stating the
  measured figures. Filterable by store, platform, campaign, ad set, and
  individual ad. Use this skill whenever someone asks about ad performance,
  wants to see their campaigns across platforms, asks how to scale
  profitably, mentions ROAS, Meta Ads, Google Ads, campaign data, ad spend,
  or wants a cross-platform campaign breakdown. Also trigger for "show me
  my ads", "how are my campaigns doing", "which ads should I scale", "what's
  my ROAS this week", "pull up the ad report", or any request to review,
  audit, or act on paid advertising results.
---

# Ad Performance Dashboard

Render a TrackBee-branded HTML report from the TrackBee MCP. The build is
driven by a thin entry script (`scripts/build_ad_performance.py`) that
loads small, focused components from `components/` in sequence — one file
per major responsibility. The script does not inline HTML, CSS, or JS —
those live in `.html`, `.css`, and `.js` files under `components/chrome/`.

## Workflow (the happy path)

1. **Identify stores.** Call `tool__list_my_stores`. If the user has more
   than one store, ask which they want via `AskUserQuestion` (default: all
   they have access to). Note each store's `id`, `name`, `currency`, and
   `currency_symbol`.

2. **Determine the date window.** Default: **7 days ending yesterday**.
   Compute exactly: `end = yesterday`, `start = end − 6 days`. Only ask
   the user when they explicitly want a different window.

3. **Fetch Phase 1 — store + campaign level** (run all in parallel).
   For each store:
   - `tool__get_dashboard_overview` → store-level KPIs (MER, total revenue, blended ROAS).
   - `tool__get_meta_campaign_insights` with `status_filter="all"` → every Meta campaign.
   - `tool__get_google_campaign_insights` with `status_filter="all"` → every Google campaign.

4. **Fetch Phase 2 — ad level** (run all in parallel).
   For each store:
   - For every Meta campaign where `spend > 0`: `tool__get_meta_ad_insights`
     (same date range, `status_filter="all"`). Skip zero-spend campaigns.
   - For every Google campaign where `spend > 0.01`: `tool__get_google_ad_insights`
     (PMAX returns `asset_groups`; Search / Shopping return `ads`).
   - Limit: if a store has more than 10 spending Meta campaigns, fetch
     ad-level only for the top 8 by spend.

5. **Stage JSON files** in `/tmp/adperf_inputs/`:

   | Filename | Source |
   |---|---|
   | `config.json` | Store list + window dates (template below) |
   | `<store_id>_overview.json` | `tool__get_dashboard_overview` result |
   | `<store_id>_meta.json` | `tool__get_meta_campaign_insights` result |
   | `<store_id>_google.json` | `tool__get_google_campaign_insights` result |
   | `<store_id>_meta_ads_<campaign_id>.json` | `tool__get_meta_ad_insights` result |
   | `<store_id>_google_ads_<campaign_id>.json` | `tool__get_google_ad_insights` result |

   Each file holds the full tool response, kept inside the `{"result": ...}`
   wrapper. On tool error, write `{"result": {}}` — the orchestrator tolerates
   absent / empty inputs.

6. **Run the build script:**

   ```bash
   python3 <SKILL_DIR>/scripts/build_ad_performance.py \
     --inputs /tmp/adperf_inputs/ \
     --out    "<workspace>/<store-slug>-ad-performance-<YYYY-MM-DD>.html"
   ```

   `<SKILL_DIR>` is this skill's directory. `<workspace>` is the user's
   workspace folder. `<store-slug>` is the kebab-case store name; for a
   multi-store run, use `all-stores`.

7. **Create the live artifact.** Call `mcp__cowork__create_artifact`:
   - `id`: `<store-slug>-ad-performance` (same id reused on every run so
     reruns overwrite in place instead of duplicating).
   - `html_path`: the absolute path of the HTML file from step 6.
   - `description`: `"Ad Performance Dashboard — <Store Name> — 7d ending <end-date>"`.
   - `mcp_tools`: `[]` (data is baked in at build time; a scheduled task
     keeps the artifact fresh).

8. **Schedule the daily refresh** (skip only if the user explicitly says
   "one-off snapshot"). Call
   `mcp__scheduled-tasks__list_scheduled_tasks` to check whether a task
   for this store already exists. If
   `<store-slug>-ad-performance-daily-refresh` is already listed, do
   nothing. Otherwise call `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `<store-slug>-ad-performance-daily-refresh`.
   - `cronExpression`: `"0 8 * * *"` (every day at 8am local time).
   - `description`: `"Refresh the <Store Name> Ad Performance Dashboard every day at 8am."`.
   - `notifyOnCompletion`: `false`.
   - `prompt`: a self-contained instruction that captures everything the
     task needs without access to this conversation. Use this template
     (substitute the placeholders):

     ```
     Refresh the TrackBee Ad Performance Dashboard for <Store Name>
     (store id <STORE_ID>) by running the /analyze-ad-performance skill end-to-end.

     CONTEXT
     - Store: <Store Name>, store_id = <STORE_ID>,
       currency = <CCY>, currency_symbol = <SYMBOL>.
     - Ad-account FX rates: meta_fx_to_store=<X>, google_fx_to_store=<Y>.
       Refetch live rates before staging the config — never reuse the
       previous run's hardcoded values.
     - Workspace folder: <WORKSPACE_PATH>.
     - Entry script: $CLAUDE_PLUGIN_ROOT/.claude/skills/analyze-ad-performance/scripts/build_ad_performance.py.

     WINDOW — compute every run, do NOT hard-code
     - end = yesterday (today − 1 day local).
     - start = end − 6 days. Both inclusive (7 days total).

     PLAN
     1. Invoke the /analyze-ad-performance skill against store <STORE_ID>
        using the window above.
     2. Build the report HTML at
        <WORKSPACE_PATH>/<store-slug>-ad-performance-<YYYY-MM-DD>.html
        (yesterday's date).
     3. Update the existing artifact in place: call
        mcp__cowork__create_artifact with the SAME id
        "<store-slug>-ad-performance" and the new html_path.
        Same id = update, not duplicate.
     4. Print one line to chat: blended ROAS, total spend, and the
        highest- and lowest-ROAS campaigns by name, and the artifact
        link as computer://<absolute-path>.
     ```
   Tell the user one line: "Live artifact created and a daily 8am
   refresh is scheduled." First run pre-approves the MCP tools the
   task needs, so subsequent runs go through without prompts.

9. **Hand off.** Print a `computer://` link to the HTML plus a 2–3 sentence
   summary stating the measured figures: blended ROAS, total spend, and the
   highest- and lowest-ROAS campaigns for the window.

## Config template

Write to `/tmp/adperf_inputs/config.json`:

```json
{
  "stores": [
    {
      "id": "<numeric store id from tool__list_my_stores>",
      "name": "<store name>",
      "currency": "<ISO code, e.g. GBP / EUR / USD>",
      "currency_symbol": "<£ | € | $ | ...>",
      "meta_account_currency": "<ISO code from the Meta ad account>",
      "google_account_currency": "<ISO code from the Google ad account>",
      "meta_fx_to_store": 1.0,
      "google_fx_to_store": 1.0
    }
  ],
  "window": {
    "start": "<YYYY-MM-DD>",
    "end": "<YYYY-MM-DD>",
    "label": "<e.g. 7d (May 4–10)>"
  }
}
```

**Currency rules:**

- `currency` / `currency_symbol` — the store's native currency (from `tool__list_my_stores`).
- `meta_account_currency` / `google_account_currency` — from `ad_accounts[0].ad_account_currency` in the respective platform response.
- `meta_fx_to_store` / `google_fx_to_store` — multiplier that converts spend / revenue from the ad-account currency INTO the store currency. **Always pass both even when they're 1.0** — the assembler does not silently fall back to a default symbol or rate.
- Dashboard overview values arrive in CENTS of `currency` — the orchestrator divides by 100 for display.
- If a conversion rate isn't known at build time, fetch a current FX rate rather than hardcoding an approximation. Stale FX silently mis-states revenue numbers in the dashboard.

## Component layout

```
components/
  chrome/                     page shell, theme, brand-neutral helpers
    shell.html                outer HTML scaffold with placeholders
    theme.css                 brand v3 tokens + per-section CSS
    format_helpers.py         money / number / pct / escape helpers
    logos.py                  brand mark loader + header logo block
    render_filters.js         store switch, platform tabs, search, zero-spend toggle
    render_table.js           sortable table click handler
    render_questions.js       copy-to-clipboard for Q-cards
  transforms/                 raw JSON → one named key on the payload
    config.py                 load + validate config.json
    store_data.py             load every store's overview / meta / google / ad files
    store_kpis.py             KPI tile math + tile-bar HTML
    meta_rows.py              Meta campaign + ad rows (HTML strings)
    google_rows.py            Google campaign + ad / asset-group rows
    table_meta.py             canonical column list + thead / cell helpers
    window.py                 date-pill formatter
  insights/                   payload → list of HTML observation strings
    meta_insights.py          per-platform key observations (measured figures)
    google_insights.py        same for Google
    next_questions.py         Q-card data + render
    thresholds.py             numeric thresholds gating which figures surface
  orchestrators/
    assemble.py               loads each transform / insight / chrome file in sequence
                              and stamps the final HTML
```

Each component owns one responsibility and is self-contained — no
inter-component imports beyond `chrome/format_helpers.py` for shared
formatting.

## Key design decisions

- **Platform-reported metrics** (spend, impressions, clicks, ROAS, purchases) come from `tool__get_meta_campaign_insights` / `tool__get_google_campaign_insights`, not from `tool__get_dashboard_overview`.
- **`tool__get_dashboard_overview`** is used only for store-level KPIs (MER, total revenue, total orders) in the header tiles — not for per-campaign numbers.
- **`daily_budget`** is not returned by the TrackBee MCP. The dashboard shows average daily spend (total spend ÷ window days) as a proxy column labelled "Avg Daily Spend".
- **Checkout Initiated** is not available in the campaign insights API. The column is rendered with an em-dash and a footer disclosure.
- **Revenue** = `revenue_1d_click` for Meta (standard 1-day-click attribution window); `conversions_value` for Google.
- **ROAS** = `purchase_roas` for Meta; `conversions_value / spend` for Google.
- **Results** = `purchases` for Meta; `conversions` for Google.
- **Numeric thresholds** (which follow-up questions and key observations are material enough to surface, frequency bands, etc.) live in `components/insights/thresholds.py`. Edit there; the observation rules and question rules read from it. They gate *which figures are shown* — they never label a verdict or recommend an action.

## What's bundled

```
scripts/build_ad_performance.py     thin entry script (parse args, hand off)
components/                         modular build kit (see Component layout)
references/metric-map.md            standard ad metrics → TrackBee fields
assets/ICON-PNG.png                 brand icon (embedded base64 at build time)
```

## Guidelines

- **Always use the entry script.** Re-implementing the renderer from scratch wastes tokens and drifts from the visual spec.
- **Run Phase 1 and Phase 2 in parallel batches.** No sequential calls.
- **One config, one date window.** Don't ask the user multiple times.
- **Provide every FX rate explicitly.** Never rely on a default symbol or rate — the build will not silently substitute. If a conversion rate is unknown, fetch a current one before staging the config.
- **Hand off short.** A `computer://` link plus a 2–3 sentence headline. The dashboard is the deliverable.
- **Always create the live artifact AND schedule the daily refresh.** Skip the scheduled task only when the user explicitly says "one-off snapshot, don't schedule."
