---
name: build-attribution-dashboard
description: >-
  Produce the TrackBee Attribution Dashboard — a self-contained Live Artifact
  HTML report that shows cross-channel attribution: blended KPIs, daily NC-ROAS
  trend, platform tiles, channel attribution table, journey Sankey + heatmap,
  and executive-summary insights. Use this skill whenever someone asks to
  "build the attribution dashboard", wants to see customer journeys across
  Meta / Google / organic / email, asks about NC-ROAS, MER, channel mix, or
  says "how do my channels stack up", "show the customer journey", "build an
  attribution report".
---

# Build the Attribution Dashboard

Produces the TrackBee Attribution Report as one Live Artifact in a single pass. Pulls every component file and every MCP data call in one parallel batch, assembles, hands off.

The final report contains:

1. **Executive Summary** — headline takeaways combining blended KPIs and channel attribution.
2. **Blended Overview** — 14 KPI tiles plus the daily NC ROAS line chart.
3. **Platform Overview** — one tile group per ad platform with nine in-platform KPIs each.
4. **Channel Attribution** — TrackBee first-party vs. in-platform table with insight card.
5. **Customer Journeys** — journey KPIs, channel touch-points heatmap, sankey path visualisation. Aligned with the 28-day window. Off-diagonal cells in the heatmap show the share of orders where both channels appeared in the path; diagonal cells show the share where the same channel touched the shopper more than once.
6. **Footer notes** — caveats on currency, attribution differences, and the journeys window.

All values are in store currency. The 3-day / 7-day / 28-day filter buttons in the header are client-side; the dashboard ships with all three windows populated.

## What to say to the user

- **Opening line (after the user picks the store, before the upfront expectation gate):** _"Setting up the attribution dashboard for <Store Name>. Going to ask one quick question first, then I'll start the build."_
- **While the build is running:** _"Pulling everything now — about two to five minutes."_
- **At hand-off:** the two-sentence headline described in "Hand off" below. Nothing before it.

Words to never say to the user (use the alternatives in parentheses): "phase" / "step" / "Step 1" / "Step 2" (just describe the work), "playbook" (use "build"), "MCP calls" (use "data" or just describe what's loading), "scorecard" (a retired model used this word — it doesn't exist here), "load the tools" (say "set up the dashboard"), "skeleton" (this build has no skeleton — don't reference the concept), "components" / "templates" (the user doesn't care; say "layout" or just describe the work). If you need a TodoWrite list, mirror the same vocabulary — "set up the dashboard", "pull the data", "hand off". Never "Step 1", never "MCP data", never "headline scorecard".

## Workflow

### Pick the store and confirm the build

Call `list_my_stores`. Ask the user which store via `AskUserQuestion` (one option per accessible store; skip the popup if they only have one store and confirm in a single sentence).

Then — **before fetching anything else** — use `AskUserQuestion` to set time expectations and get an explicit yes:

> "Building the attribution dashboard for <store name>. Pulls everything in parallel so it usually takes two to five minutes; longer for high-spend accounts. Want to continue?"

Options: `Yes, build it` / `No, stop here`.

If **No**, stop. If **Yes**, proceed.

Default window: **28 days ending yesterday**. Compute start/end as ISO strings for the 3d, 7d, and 28d windows.

Stage the shared input + component directories:

- `/tmp/full_inputs/` — MCP responses **and** `config.json`.
- `/tmp/dashboard_components/` — fetched components.

Write `/tmp/full_inputs/config.json`:

```json
{
  "store_name": "<Store name from list_my_stores>",
  "store_currency": "<EUR|USD|GBP|...>",
  "fx_to_eur": {},
  "windows": {
    "3d":  { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" },
    "7d":  { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" },
    "28d": { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" }
  }
}
```

### Fetch everything in one parallel batch

**Dispatch every call below in a single assistant message.** Component file reads and MCP data calls are independent — fan them out together. Sequential dispatch turns a few-minute build into a half-hour one; do not do it.

**Component file reads (`resource__get_component`)** — save each to `/tmp/dashboard_components/<same-relative-path>`. The assembler reads its siblings by relative path, so keep the `chrome/`, `charts/`, `transforms/`, `insights/`, `orchestrators/` directory structure intact when staging:

- `dashboards/attribution/chrome/shell.html`
- `dashboards/attribution/chrome/theme.css`
- `dashboards/attribution/chrome/format_helpers.js`
- `dashboards/attribution/chrome/render_sections.js`
- `dashboards/attribution/chrome/window_filter.js`
- `dashboards/attribution/chrome/sankey_filter.js`
- `dashboards/attribution/chrome/tooltip.js`
- `dashboards/attribution/chrome/logos.py`
- `dashboards/attribution/charts/nc_roas_line.js`
- `dashboards/attribution/orchestrators/assemble.py`
- `dashboards/attribution/transforms/blended_kpis.py`
- `dashboards/attribution/transforms/platform_tiles.py`
- `dashboards/attribution/transforms/channel_attribution.py`
- `dashboards/attribution/transforms/daily_nc_roas.py`
- `dashboards/attribution/transforms/journey_kpis.py`
- `dashboards/attribution/transforms/journey_heatmap.py`
- `dashboards/attribution/transforms/journey_sankey.py`
- `dashboards/attribution/insights/channel_attribution.py`
- `dashboards/attribution/insights/executive_summary.py`
- `dashboards/attribution/insights/cooccurrence.py`
- `dashboards/attribution/insights/journey.py`

**MCP data calls** — save each response to `/tmp/full_inputs/`.

> **Save the full MCP response verbatim.** Do not unwrap, flatten, or
> hand-edit the payload before writing it to disk. `get_dashboard_overview`
> in particular returns `{"store_currency": ..., "overview": {...}}` —
> save *that* whole object. The assembler's `_load_raw` handles JSON-RPC
> envelopes (`{"result": {...}}`), the native `{"overview": {...}}`
> wrapper, and already-unwrapped payloads. Touching the shape by hand
> breaks the contract and tends to render zeros.

**Per-window data (14 calls)**

| Filename                  | Tool                            | Notes |
| ------------------------- | ------------------------------- | ----- |
| `overview.json`           | `get_dashboard_overview`        | 28d window. Authoritative spend / revenue / platform_statistics. |
| `overview_7d.json`        | `get_dashboard_overview`        | 7d. |
| `overview_3d.json`        | `get_dashboard_overview`        | 3d. |
| `daily.json`              | `get_daily_store_statistics`    | Pass `column_groups=["core","funnel","customer_segments","platform_totals"]`. 28d. |
| `funnel.json`             | `get_funnel_overview`           | 28d, `compare_previous_period=true`. |
| `funnel_7d.json`          | `get_funnel_overview`           | 7d, `compare_previous_period=true`. |
| `funnel_3d.json`          | `get_funnel_overview`           | 3d, `compare_previous_period=true`. |
| `platform_funnel.json`    | `get_platform_funnel_breakdown` | 28d. |
| `platform_funnel_7d.json` | `get_platform_funnel_breakdown` | 7d. |
| `platform_funnel_3d.json` | `get_platform_funnel_breakdown` | 3d. |
| `meta.json`               | `get_meta_campaign_insights`    | 28d. |
| `meta_7d.json` / `meta_3d.json`     | `get_meta_campaign_insights`    | 7d / 3d. |
| `google.json`             | `get_google_campaign_insights`  | 28d. |
| `google_7d.json` / `google_3d.json` | `get_google_campaign_insights`  | 7d / 3d. |

**Customer-journey data (7 base calls)** — use the SAME `start` / `end` dates as the 28-day window above. The journey tools take a max one-month window, so they align naturally with the rest of the dashboard.

| Filename           | Tool                              | Notes                                                                              |
| ------------------ | --------------------------------- | ---------------------------------------------------------------------------------- |
| `touchpoints.json` | `tool__get_platform_interactions` | Drives the journey KPI tiles, the channel touch-points heatmap, and the insights.  |
| `j_meta.json`      | `tool__get_platform_journeys`     | `platform="meta"`.                                                                 |
| `j_google.json`    | `tool__get_platform_journeys`     | `platform="google"`.                                                               |
| `j_klaviyo.json`   | `tool__get_platform_journeys`     | `platform="klaviyo"`.                                                              |
| `j_tiktok.json`    | `tool__get_platform_journeys`     | `platform="tiktok"`.                                                               |
| `j_pinterest.json` | `tool__get_platform_journeys`     | `platform="pinterest"`.                                                            |
| `j_email.json`     | `tool__get_platform_journeys`     | `platform="email"`.                                                                |

**Dynamic per-channel journey calls (one acceptable second batch)** — after `touchpoints.json` lands, walk the `leading` and `related` fields across its `transitions[]` and `cooccurrence[]` lists. For every channel that appears there but isn't already in the fixed list above (e.g. `bing`), call `tool__get_platform_journeys` for that channel and save it as `j_<platform>.json`. Dispatch these extra calls as one parallel batch the moment `touchpoints.json` returns — never call-by-call. This is the only acceptable split.

On any tool error, write `{"result": {}}` to the file — the assembler renders a "Data unavailable" card.

### Assemble

```bash
python3 /tmp/dashboard_components/dashboards/attribution/orchestrators/assemble.py \
  --inputs /tmp/full_inputs/ \
  --out    "<workspace>/<store-slug>-attribution-<YYYY-MM-DD>.html"
```

The orchestrator degrades gracefully on missing inputs: sections whose data didn't land render "Data unavailable" cards instead of disappearing.

### Create the Live Artifact

- `id`: `<store-slug>-attribution`
- `html_path`: the absolute path of the HTML written above.
- `description`: `"TrackBee Attribution Report for <Store Name>."`
- `mcp_tools`: `[]`

### Hand off

Print the `computer://` link. Read out one or two of the strongest insights — the headline blended ROAS with its delta, plus the single most striking journey insight (e.g. "62% of orders are still single-touch" or "Meta opens 71% of multi-touch journeys"). Two sentences max — don't paraphrase the dashboard, it's the deliverable.

---

## Stopping early

If the user picks "No" at the upfront expectation gate, do not start the build. Once the parallel batch is in flight the user can still send "stop" at any time — handle that gracefully by handing off whatever the latest assemble produced.

## Guidelines

- **Skill is leading.** The component paths above are the ONLY paths to fetch. Do not invent variants.
- **Bundle config.json inside `/tmp/full_inputs/`.** The assembler reads it from there. Do not pass `--config` separately unless overriding.
- **One parallel batch.** Component reads and MCP data calls go out in a single assistant message. The only acceptable split is the dynamic per-channel journey calls that depend on `touchpoints.json`.
- **Customer Journeys uses the same window as the 28-day section.** The journey tools take a max one-month window; the 3-day / 7-day filter does not apply to that section because the data isn't refetched per filter — call it out if the user asks.
- **Hand off short.** `computer://` link + one or two sentences of the strongest insight.
