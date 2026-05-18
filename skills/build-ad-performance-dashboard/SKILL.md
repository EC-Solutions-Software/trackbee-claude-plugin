---
name: build-ad-performance-dashboard
description: >-
  Produce the TrackBee Ad Performance Dashboard — a self-contained Live Artifact
  HTML report covering every active and paused Meta + Google campaign across the
  user's stores, with KPI bar, sortable per-campaign/per-ad table, Scale/Hold/
  Refresh/Pause recommendations, and follow-up question prompts. Use this skill
  whenever someone asks to "build the ad performance dashboard", wants a
  cross-platform campaign breakdown, asks about ROAS / spend / scaling, or says
  "show me my ads", "how are my campaigns doing", "which ads should I scale".
---

# Build the Ad Performance Dashboard

Produces the TrackBee Ad Performance Report for one or more stores as one Live Artifact in a single pass. Every component file — layout, transforms, insights, threshold table, assembler — ships with this skill under `resources/`. The skill dispatches the data calls in one parallel batch, fans out per-campaign ad-level drill-downs as a dependent second batch, runs the assembler, and hands off.

The final report contains:

1. **Header strip** — store tabs, date pill, generated-at stamp.
2. **KPI bar** (per store) — Total Ad Spend, Blended ROAS, MER, Conversions, Avg Daily Spend.
3. **Sortable performance table** — every active and paused Meta + Google campaign in the window, with expandable rows that reveal the ads inside each campaign.
4. **Performance Analysis** — two cards of insights + recommendations (Meta and Google), driven by the threshold table.
5. **Questions to ask next** — up to three data-driven follow-up prompts with copy-to-clipboard buttons.
6. **Footer** — caveats on currency, attribution windows, and Avg-Daily-Spend as a daily-budget proxy.

All values are in store currency. The window applies to every section.

## Skill base directory

Every path below is relative to this skill's directory. Set `SKILL_DIR` to its absolute path before assembling:

- **Installed as a plugin** — `SKILL_DIR` is the plugin's skill install path; Claude announces it at skill load.
- **Driven via the TrackBee MCP** after the build kit has been cloned — `SKILL_DIR=/tmp/trackbee-claude-plugin/skills/build-ad-performance-dashboard`.

Components live at `$SKILL_DIR/resources/{chrome,transforms,insights,views,orchestrators}/`. No staging copy is needed — the assembler reads its siblings by relative path.

## What to say to the user

- **Opening line, after store selection and before the expectation gate:** "Pulling the ad performance dashboard for `<Store Name(s)>`. One quick confirmation, then the build runs."
- **Expectation gate (via `AskUserQuestion`):** "Builds in parallel; usually two to five minutes, longer for high-spend accounts with many active campaigns. Continue?" Options: `Yes, build it` / `No, stop here`.
- **During the build:** silent. No status narration, no "still working", no progress estimates.
- **Hand-off (after the artifact is ready):** open with the headline described in "Hand off" below. The headline is two or three sentences of data — the top-spend campaign by ROAS, the worst-performing campaign by ROAS, and one cross-platform observation. No preamble, no recap of what the dashboard contains (the user has the artifact in front of them).

## Workflow

### Pick the store(s) and confirm the build

Call `tool__list_my_stores`. Ask the user which store(s) via `AskUserQuestion`.

Then — **before fetching anything else** — use `AskUserQuestion` to set time expectations and get an explicit yes:

> "Building the ad performance dashboard for <store name(s)>. Pulls everything in parallel so it usually takes two to five minutes; longer for high-spend accounts with many active campaigns. Want to continue?"

Options: `Yes, build it` / `No, stop here`.

If **No**, stop. If **Yes**, proceed.

Default window: **7 days ending yesterday**. Compute start/end as ISO strings (`end = yesterday`, `start = end - 6 days`).

Stage the inputs directory:

- `/tmp/adperf_inputs/` — MCP responses + `config.json`.

Write `/tmp/adperf_inputs/config.json`:

```json
{
  "stores": [
    {
      "id": <store_id from tool__list_my_stores>,
      "name": "<Store Name>",
      "currency": "<GBP|EUR|USD|...>",
      "currency_symbol": "<£|€|$|...>",
      "meta_account_currency": "<EUR|...>",
      "google_account_currency": "<EUR|...>",
      "meta_fx_to_store": 1.0,
      "google_fx_to_store": 1.0
    }
  ],
  "window": { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>", "label": "7d (<short range>)" }
}
```

Currency rules — `currency` / `currency_symbol` is the store's native currency from `tool__list_my_stores`. `meta_account_currency` / `google_account_currency` land from `ad_accounts[0].ad_account_currency` in the platform responses once they return. `meta_fx_to_store` / `google_fx_to_store` multiply platform spend / revenue into store currency — **always provide both** even when they're 1.0; the assembler does not silently fall back. If a conversion rate isn't known at build time, fetch a current FX rate rather than hardcoding an approximation.

### Fetch all per-store data in one parallel batch

**Dispatch every call below in a single assistant message.** Sequential dispatch turns a few-minute build into a half-hour one; do not do it.

**Per-store data (3 calls per store)** — save each response to `/tmp/adperf_inputs/`:

| Filename                      | Tool                                                  | Notes                                                |
| ----------------------------- | ----------------------------------------------------- | ---------------------------------------------------- |
| `<store_id>_overview.json`    | `tool__get_dashboard_overview`                              | Store-level KPIs (MER, total revenue, blended ROAS). |
| `<store_id>_meta.json`        | `tool__get_meta_campaign_insights` `status_filter="all"`    | All Meta campaigns regardless of status.             |
| `<store_id>_google.json`      | `tool__get_google_campaign_insights` `status_filter="all"`  | All Google campaigns regardless of status.           |

### Ad-level drill-down (one dependent second batch)

Campaign IDs aren't known until the campaign-insights calls return, so per-campaign ad-level calls must dispatch as one parallel batch **the moment the per-store calls land** — not call-by-call.

| Filename                                          | Tool                       | Notes                                                                                            |
| ------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| `<store_id>_meta_ads_<campaign_id>.json`          | `tool__get_meta_ad_insights`     | One per spending Meta campaign. Cap at the top 8 by spend if a store has more than 10 campaigns. |
| `<store_id>_google_ads_<campaign_id>.json`        | `tool__get_google_ad_insights`   | One per spending Google campaign. PMAX returns `asset_groups`; Search/Shopping return `ads`.     |

So the dispatch pattern is: one parallel batch of `(overview + meta + google) × stores`, then immediately a second parallel batch of every per-campaign drill-down across every store. The top-8-by-spend cap protects you when an account has many small campaigns. On any tool error, write `{"result": {}}` to the file — the assembler renders a "Data unavailable" card.

### Assemble

```bash
python3 "$SKILL_DIR/resources/orchestrators/assemble.py" \
  --inputs /tmp/adperf_inputs/ \
  --out    "<workspace>/<store-slug>-ad-performance-<YYYY-MM-DD>.html"
```

Use kebab-case for the store slug (e.g. `acme-store`). For multi-store builds, use `all-stores`. The orchestrator degrades gracefully on missing inputs: KPI cells show em-dashes, the campaign table shows a "Data unavailable" placeholder card, the insights and "Questions to ask next" sections render empty.

### Create the Live Artifact

- `id`: `<store-slug>-ad-performance`
- `html_path`: absolute path from above.
- `description`: `"Ad Performance Dashboard — <Store Name>."`
- `mcp_tools`: `[]`

### Hand off

`computer://` link + a 2–3 sentence headline: total spend, blended ROAS, top scaling opportunity (with the specific ad name when possible), biggest risk. Don't paraphrase the table — the dashboard is the deliverable.

---

## Stopping early

If the user picks "No" at the upfront expectation gate, do not start the build. Once data calls are in flight the user can still send "stop" at any time — handle that gracefully by handing off whatever the latest assemble produced.

## Tuning thresholds

Every numeric threshold the dashboard uses — ROAS colour bands, frequency warnings, SCALE / HOLD / REFRESH / PAUSE rules, follow-up question triggers — lives in `resources/chrome/thresholds.json`. Edit a number there and both the Python rule packs (server-side) and the front-end formatter (client-side) pick it up on the next build. There are no numeric constants inside any rule module.

## Plain-language error cards

When the assembler can't read an input file or a whole store has no data, the dashboard renders a red-bordered "Data unavailable" card instead of silently showing blank cells. Each card has a one-line title, a body paragraph explaining the likely cause, and an italic "fix" sentence with the next action.

## Key design decisions

- **Platform-reported metrics** (spend, impressions, clicks, ROAS, purchases) come from the campaign-insights calls — not from `tool__get_dashboard_overview`. Overview is used only for store-level KPIs (MER, total revenue, total orders) in the top tiles.
- **`daily_budget`** is not exposed by the TrackBee MCP. The dashboard shows average daily spend (total spend ÷ window days) as a proxy column.
- **Checkout Initiated** is not available via campaign insights. Cells render "—".
- **Revenue** = `revenue_1d_click` for Meta (1-day-click attribution); `conversions_value` for Google.
- **ROAS** = `purchase_roas` for Meta; `conversions_value / spend` for Google.
- **Results** = `purchases` for Meta; `conversions` for Google.

## Guidelines

- **Always use the assembler.** Don't re-implement the HTML inline.
- **Edit thresholds in `resources/chrome/thresholds.json`, never in code.**
- **One parallel batch.** The store-level + campaign-level MCP data calls go out in a single assistant message. The only acceptable split is the per-campaign ad-level drill-down, which depends on campaign IDs returned by the first batch — and that second batch still goes out as one parallel block, not call-by-call.
- **One config, one window.** Don't prompt the user multiple times.
- **Hand off short.** `computer://` link + 2–3 sentence headline.
- **Always create the Live Artifact after building.**
