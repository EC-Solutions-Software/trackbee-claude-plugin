---
name: ad-performance
description: >-
  Generate a TrackBee-branded Ad Performance Dashboard — a self-contained HTML
  report showing all active campaigns, ad sets, and ads across Meta and Google
  for every store the user has access to. Answers "how is my ad account
  performing this week and how do I scale profitably?" Shows spend, ROAS,
  impressions, reach, frequency, CPM, CTR, CPC, clicks, ATC, purchases, revenue,
  new-customer metrics, and AI-generated scaling recommendations per platform.
  Filterable by store, platform, campaign, ad set, and individual ad.
  Use this skill whenever someone asks about ad performance, wants to see their
  campaigns across platforms, asks how to scale profitably, mentions ROAS,
  Meta Ads, Google Ads, campaign data, ad spend, or wants a cross-platform
  campaign breakdown. Also trigger for "show me my ads", "how are my campaigns
  doing", "which ads should I scale", "what's my ROAS this week", "pull up the
  ad report", or any request to review, audit, or act on paid advertising results.
---

# Ad Performance Dashboard

Generates a TrackBee-branded interactive HTML report from TrackBee MCP data.
Use the bundled `scripts/build_ad_performance.py` entry-point — do NOT
reconstruct the dashboard code from scratch. The script is a 30-line shim
that delegates to the component library under
`resources/dashboards/ad-performance/`.

## Component layout

This skill follows the trackbee-mcp-context dashboard convention. Every
section of the report is one file under
`resources/dashboards/ad-performance/`:

```
chrome/             page shell, theme, format helpers, app JS, thresholds
transforms/         raw MCP JSON → row HTML / KPI dicts (one responsibility per file)
insights/           pure-Python rule packs (meta_insights, google_insights, next_questions)
views/              HTML templates with {PLACEHOLDER}s
orchestrators/      assemble.py + _sections.py — wire components together
```

When the MCP serves this plugin, each file is its own loadable resource
(≤150 lines for components, ≤250 for orchestrator helpers). That keeps
the surface small enough to stream individually instead of as one 1.4k-line
monolith.

## Workflow

1. **Identify stores.** Call `list_my_stores`. If multiple stores, ask the
   user which they want (default: all). Note each store's `id`, `name`,
   `currency`.

2. **Determine the date window.** Default: last 7 days ending yesterday.
   Always compute exactly: `end = yesterday`, `start = end - 6 days`.
   Ask the user only if they specify a different window.

3. **Fetch Phase 1 — store + campaign level** (run all in parallel):
   For each store:
   - `get_dashboard_overview` → store-level KPIs (MER, total revenue, blended ROAS)
   - `get_meta_campaign_insights` with `status_filter="all"` → all Meta campaigns
   - `get_google_campaign_insights` with `status_filter="all"` → all Google campaigns

4. **Fetch Phase 2 — ad level** (run all in parallel):
   For each store:
   - For every Meta campaign where `spend > 0`: call `get_meta_ad_insights`
     (same date range, `status_filter="all"`). Skip zero-spend campaigns.
   - For every Google campaign where `spend > 0.01`: call `get_google_ad_insights`
     (PMAX campaigns return asset groups; Search/Shopping return individual ads).
   - Limit: if a store has more than 10 spending Meta campaigns, fetch ad-level
     only for the top 8 by spend to keep call count manageable.

5. **Write JSON files** to `/tmp/adperf_inputs/`:

   | Filename | Source |
   |---|---|
   | `config.json` | Store list + window dates (template below) |
   | `{store_id}_overview.json` | `get_dashboard_overview` result |
   | `{store_id}_meta.json` | `get_meta_campaign_insights` result |
   | `{store_id}_google.json` | `get_google_campaign_insights` result |
   | `{store_id}_meta_ads_{campaign_id}.json` | `get_meta_ad_insights` result |
   | `{store_id}_google_ads_{campaign_id}.json` | `get_google_ad_insights` result |

   Write each response as `{"result": <tool_result_payload>}`.
   On tool error: write `{"result": {}}`. The dashboard surfaces a plain-language
   error card for each missing or unreadable file instead of silently rendering
   empty cells.

6. **Run the build script:**
   ```bash
   python3 <SKILL_DIR>/scripts/build_ad_performance.py \
     --inputs  /tmp/adperf_inputs/ \
     --out     "<workspace>/<store-slug>-ad-performance-<YYYY-MM-DD>.html"
   ```
   `<SKILL_DIR>` = this skill's directory. `<workspace>` = the user's selected
   workspace folder. Use kebab-case store slug (e.g. `sassy-saints`).
   For multi-store, use `all-stores` as the slug.

7. **Create the live artifact.** Call `mcp__cowork__create_artifact`:
   - `id`: `<store-slug>-ad-performance`
   - `html_path`: absolute path of the HTML file from step 6
   - `description`: `"Ad Performance Dashboard — <Store Name> — 7d ending <end-date>"`
   - `mcp_tools`: `[]`

8. **Hand off.** Print a `computer://` link to the HTML file plus a 2–3 sentence
   summary: total spend, blended ROAS, top scaling opportunity, biggest risk.

## Config template

Write to `/tmp/adperf_inputs/config.json`:

```json
{
  "stores": [
    {
      "id": 766,
      "name": "Sassy Saints",
      "currency": "GBP",
      "currency_symbol": "£",
      "meta_account_currency": "GBP",
      "google_account_currency": "EUR",
      "google_fx_to_store": 1.17,
      "meta_fx_to_store": 1.0
    }
  ],
  "window": {
    "start": "2026-05-04",
    "end":   "2026-05-10",
    "label": "7d (May 4–10)"
  }
}
```

**Currency rules:**
- `currency` / `currency_symbol` = store's native currency (from `list_my_stores`).
- `meta_account_currency` = from `ad_accounts[0].ad_account_currency` in the Meta response.
- `google_account_currency` = from `ad_accounts[0].ad_account_currency` in the Google response.
- `google_fx_to_store` / `meta_fx_to_store` = multiplier to convert platform spend
  / revenue INTO store currency. **Always provide both** even when the platform
  currency matches the store currency (set the multiplier to `1.0`). The build
  no longer falls back to 1.0 silently — missing values are flagged in the
  build log so currency mismatches don't go unnoticed.

**FX rates** — use reasonable current approximations if exact rate is not
known:
- EUR → GBP: 1.17  |  USD → GBP: 0.79  |  EUR → USD: 1.13

## Tuning thresholds

All numeric thresholds (ROAS colour bands, frequency warnings, SCALE / HOLD /
REFRESH / PAUSE rules, follow-up-question triggers) live in one place:
`resources/dashboards/ad-performance/chrome/thresholds.json`.

Change a number there and both the Python rule packs and the front-end
formatter pick it up on the next build. There are NO numeric constants
inside any rule module.

## Plain-language error cards

When the build can't read an input file or a whole store has no data, the
dashboard renders a red-bordered "Data unavailable" card instead of silently
showing blank cells. Each card includes:

- a one-line title describing what's missing
- a body paragraph explaining the likely cause (in non-technical language)
- a single italic "fix" sentence with the next action to take

Look for "Couldn't read", "Input file not found", or "No ad data found"
near the top of the report when a section looks empty.

## Key design decisions

- **Platform-reported metrics** (spend, impressions, clicks, ROAS, purchases) come from
  `get_meta_campaign_insights` / `get_google_campaign_insights`, not from `get_dashboard_overview`.
- **`get_dashboard_overview`** is used only for store-level KPIs (MER, total revenue, total orders)
  shown in the header tiles — not for per-campaign numbers.
- **`daily_budget`** is not returned by the TrackBee MCP. Display average daily spend
  (total spend ÷ window days) as a proxy column labelled "Avg Daily Spend".
- **Checkout Initiated** is not available in the campaign insights API. The column is shown
  but marked "—" with a tooltip explaining it requires native platform exports.
- **Revenue** = `revenue_1d_click` for Meta (standard 1-day-click attribution window).
  For Google = `conversions_value` (Google's tracked conversion value).
- **ROAS** = `purchase_roas` for Meta; `conversions_value / spend` for Google.
- **Results** = `purchases` for Meta; `conversions` for Google.

## What's bundled

```
scripts/build_ad_performance.py                       30-line entry-point shim
resources/dashboards/ad-performance/
  chrome/        theme.css, shell.html, format_helpers.js, app.js, thresholds.json
  transforms/    window.py, store_kpis.py, action_rules.py, meta_rows.py,
                 google_rows.py, _fmt.py, _io.py
  insights/      meta_insights.py, google_insights.py, next_questions.py
  views/         kpi_bar.html, table_controls.html, perf_table.html,
                 insights_section.html, questions_section.html,
                 placeholder_card.html, footer.html
  orchestrators/ assemble.py (entry), _sections.py (per-store rendering)
references/      metric-map.md (field reference)
assets/          ICON-PNG.png (TrackBee brand icon, embedded as base64)
```

## Guidelines

- **Always use the script.** Do not re-implement the HTML inline.
- **Edit thresholds in `chrome/thresholds.json`,** never in code.
- **Run Phase 1 and Phase 2 in parallel batches.** Don't call sequentially.
- **One config, one date window.** Don't prompt the user multiple times.
- **Hand off short.** `computer://` link + 2-3 sentence headline.
- **Always create the live artifact** after building.
