---
name: attribution
description: >-
  Produce the TrackBee Attribution Dashboard — a self-contained Live Artifact
  HTML report that shows cross-channel attribution: blended KPIs, daily NC-ROAS
  trend, platform tiles, channel attribution table, journey Sankey + heatmap,
  store funnel analysis with stage-specific fix-it insights, and
  executive-summary insights. Use this skill whenever someone asks to
  "build the attribution dashboard", wants to see customer journeys across
  Meta / Google / organic / email, asks about NC-ROAS, MER, channel mix,
  where the funnel is leaking, or says "how do my channels stack up",
  "show the customer journey", "where is my funnel leaking", "build an
  attribution report".
---

# Build the Attribution Dashboard

Produces the TrackBee Attribution Report as one Live Artifact in a single pass. Every component file — layout, transforms, insights, charts, assembler — ships with this skill under `resources/`. The skill dispatches the data calls in one parallel batch (plus one dependent batch for dynamic per-channel journey calls), runs the assembler, and hands off.

The final report contains:

1. **Executive Summary** — headline takeaways combining blended KPIs and channel attribution.
2. **Blended Overview** — 14 KPI tiles plus the daily NC ROAS line chart.
3. **Platform Overview** — one tile group per ad platform with nine in-platform KPIs each.
4. **Channel Attribution** — TrackBee first-party vs. in-platform table with insight card.
5. **Customer Journeys** — journey KPIs, channel touch-points heatmap, sankey path visualisation. Aligned with the 28-day window. Off-diagonal cells in the heatmap show the share of orders where both channels appeared in the path; diagonal cells show the share where the same channel touched the shopper more than once.
6. **Store Funnel Analysis** — page-view → product-view → add-to-cart → checkout-started → orders ladder with per-stage counts, drop-off rates, and the biggest leak called out with stage-specific fix-it insights. Responds to the 3d / 7d / 28d filter.
7. **Footer notes** — caveats on currency, attribution differences, and the journeys window.

All values are in store currency. The 3-day / 7-day / 28-day filter buttons in the header are client-side; the dashboard ships with all three windows populated.

## Skill base directory

Every path below is relative to this skill's directory. Set `SKILL_DIR` to its absolute path before assembling:

- **Installed as a plugin** — `SKILL_DIR` is the plugin's skill install path; Claude announces it at skill load.
- **Driven via the TrackBee MCP** after the build kit has been cloned — `SKILL_DIR=/tmp/trackbee-claude-plugin/skills/attribution`.

Components live at `$SKILL_DIR/resources/{chrome,charts,transforms,insights,orchestrators}/`. No staging copy is needed — the assembler reads its siblings by relative path.

## What to say to the user

- **Opening line, after store selection and before the expectation gate:** "Pulling the attribution dashboard for `<Store Name(s)>`. One quick confirmation, then the build runs."
- **Expectation gate (via `AskUserQuestion`):** "Builds in parallel; usually three to six minutes, longer for stores with many channels or high event volume. Continue?" Options: `Yes, build it` / `No, stop here`.
- **During the build:** silent. No status narration.
- **Hand-off (after the artifact is ready):** open with the headline described in "Hand off" below. Two or three sentences of data — blended ROAS for the window, the channel with the largest in-platform vs server-side gap, and one journey-pattern observation. No preamble.

## Workflow

### Pick the store and confirm the build

Call `tool__list_my_stores`. Ask the user which store via `AskUserQuestion` (one option per accessible store; skip the popup if they only have one store and confirm in a single sentence).

Then — **before fetching anything else** — use `AskUserQuestion` to set time expectations and get an explicit yes:

Use the exact gate wording from "What to say to the user" above.

Options: `Yes, build it` / `No, stop here`.

If **No**, stop. If **Yes**, proceed.

Default window: **28 days ending yesterday**. Compute start/end as ISO strings for the 3d, 7d, and 28d windows.

Stage the inputs directory:

- `/tmp/full_inputs/` — MCP responses **and** `config.json`.

Write `/tmp/full_inputs/config.json`:

```json
{
  "store_name": "<Store name from tool__list_my_stores>",
  "store_currency": "<EUR|USD|GBP|...>",
  "fx_to_eur": {},
  "windows": {
    "3d":  { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" },
    "7d":  { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" },
    "28d": { "start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>" }
  }
}
```

### Fetch all data in one parallel batch

**Dispatch every call below in a single assistant message.** Sequential dispatch turns a few-minute build into a half-hour one; do not do it.

**MCP data calls** — save each response to `/tmp/full_inputs/`.

> **Save the full MCP response verbatim.** Do not unwrap, flatten, or
> hand-edit the payload before writing it to disk. `tool__get_dashboard_overview`
> in particular returns `{"store_currency": ..., "overview": {...}}` —
> save *that* whole object. The assembler's `_load_raw` handles JSON-RPC
> envelopes (`{"result": {...}}`), the native `{"overview": {...}}`
> wrapper, and already-unwrapped payloads. Touching the shape by hand
> breaks the contract and tends to render zeros.

**Per-window data (14 calls)**

| Filename                  | Tool                            | Notes |
| ------------------------- | ------------------------------- | ----- |
| `overview.json`           | `tool__get_dashboard_overview`        | 28d window. Authoritative spend / revenue / platform_statistics. |
| `overview_7d.json`        | `tool__get_dashboard_overview`        | 7d. |
| `overview_3d.json`        | `tool__get_dashboard_overview`        | 3d. |
| `daily.json`              | `tool__get_daily_store_statistics`    | Pass `column_groups=["core","funnel","customer_segments","platform_totals"]`. 28d. |
| `funnel.json`             | `tool__get_funnel_overview`           | 28d, `compare_previous_period=true`. |
| `funnel_7d.json`          | `tool__get_funnel_overview`           | 7d, `compare_previous_period=true`. |
| `funnel_3d.json`          | `tool__get_funnel_overview`           | 3d, `compare_previous_period=true`. |
| `platform_funnel.json`    | `tool__get_platform_funnel_breakdown` | 28d. |
| `platform_funnel_7d.json` | `tool__get_platform_funnel_breakdown` | 7d. |
| `platform_funnel_3d.json` | `tool__get_platform_funnel_breakdown` | 3d. |
| `meta.json`               | `tool__get_meta_campaign_insights`    | 28d. |
| `meta_7d.json` / `meta_3d.json`     | `tool__get_meta_campaign_insights`    | 7d / 3d. |
| `google.json`             | `tool__get_google_campaign_insights`  | 28d. |
| `google_7d.json` / `google_3d.json` | `tool__get_google_campaign_insights`  | 7d / 3d. |

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
python3 "$SKILL_DIR/resources/orchestrators/assemble.py" \
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

Print the `computer://` link, then deliver the hand-off described in "What to say to the user": two or three sentences carrying the blended ROAS for the window, the channel with the largest in-platform vs server-side gap, and one journey-pattern observation (e.g. "62% of orders are still single-touch" or "Meta opens 71% of multi-touch journeys"). No preamble, no paraphrasing — the dashboard is the deliverable.

---

## Stopping early

If the user picks "No" at the upfront expectation gate, do not start the build. Once the parallel batch is in flight the user can still send "stop" at any time — handle that gracefully by handing off whatever the latest assemble produced.

## Guidelines

- **Bundle config.json inside `/tmp/full_inputs/`.** The assembler reads it from there. Do not pass `--config` separately unless overriding.
- **One parallel batch.** All MCP data calls go out in a single assistant message. The only acceptable split is the dynamic per-channel journey calls that depend on `touchpoints.json`.
- **Customer Journeys uses the same window as the 28-day section.** The journey tools take a max one-month window; the 3-day / 7-day filter does not apply to that section because the data isn't refetched per filter — call it out if the user asks.
- **Hand off short.** `computer://` link + two or three data-led sentences per "What to say to the user".
