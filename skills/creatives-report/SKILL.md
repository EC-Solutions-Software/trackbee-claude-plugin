---
name: creatives-report
description: >-
  Generate a TrackBee-branded Creatives Report Dashboard — a self-contained
  HTML report covering the **last 7 days only**. Presents each spending ad's
  measured statistics (spend, ROAS, frequency, reach, net-new-reach share,
  purchases, new-customer share, 1d/28d), grouped by product and format with
  per-format median ROAS / CTR / CPA. Always installs as a live Cowork
  artifact and schedules a daily 8am refresh. Use whenever someone asks about
  creative performance, ad frequency and reach, which content types or formats
  perform for a product, video vs static or carousel performance, a
  cross-platform creative breakdown, "audit my creatives", "open the creatives
  report", or any request to review the figures for individual ads, not
  campaigns. Distinct from analyze-ad-performance (campaign-level metrics) —
  use creatives-report for per-ad creative statistics and format mix. For
  audience-level metrics (account-wide CPM / frequency, reach saturation), use
  diagnose-audience-health.
---

# Creatives Report Dashboard

Render a TrackBee-branded HTML report from the TrackBee MCP, covering
the **last 7 days** of ad performance. The build is driven by a thin
entry script (``scripts/build_dashboard.py``) that loads small,
focused components from ``components/`` in sequence — one file per
major piece of the report.

The skill **always** creates a live artifact and schedules a daily 8am
refresh — skip those steps only if the user explicitly says "one-off
snapshot, don't schedule."

When a section's required input is missing, the orchestrator stamps a
plain-language "Data unavailable" notice inside that section's card
instead of failing the whole build. The other sections still render so
the user gets every piece of data we actually have.

## Workflow (the happy path)

1. **Pick store, scope, and workspace.** Call `tool__list_my_stores`, ask the
   user which store. Use the user's current Cowork workspace folder as
   `<workspace>` for the output path unless they name another — ask only
   if no workspace is available. Then ask in one round:
   - Platform — `meta`, `google`, or `both` (default `both`).
   - Optional product focus — a single product name to weight grouping
     by (default: none — let the script infer products from ad-set /
     campaign names).
2. **Compute the window once.** The audit window is **the last 7
   days** ending yesterday. Compute: `end = yesterday`, `start = end -
   6 days`. Never ask the user a second time.
3. **Phase 1 — fetch the campaign-level files.** Make the Phase-1 MCP
   calls listed in §MCP calls (`{store_id}_meta.json`,
   `{store_id}_google.json`) and save each `result` payload as JSON in
   `/tmp/audit_inputs/`. Do this **before** any ad-level fetch.
4. **Choose exclusions from the real campaign list.** From the Phase-1
   files, present the spending campaigns as a neutral, **numbered** list —
   one row per campaign, numbered `1, 2, 3, …`, each showing
   `campaign_name · campaign_id · spend · ROAS · status` — so the user can
   pick by number. Present them **factually only**: do not label, group, or
   infer which are "test" campaigns, and do not recommend exclusions from
   the names — a campaign name is the merchant's and is not a reliable
   signal of intent, so the choice is the user's. (A plain fact like "paused
   campaigns that still spent will be scored unless dropped" is fine.) Ask
   which to exclude (default: none → empty list); accept row numbers or ids
   and resolve them to `campaign_id`s. On a scheduled refresh, reuse the
   saved list unchanged rather than re-asking.
5. **Confirm the exclusions, then fetch Phase 2.** If the exclude list
   is non-empty, echo it back and require an explicit yes before
   building: "Excluding N campaign(s) (≈M ads): name1, name2 —
   proceed?" If the list is empty, no confirmation is needed. Once
   confirmed, make the Phase-2 ad-level calls (§MCP calls) **only for
   the kept (non-excluded) spending campaigns**, saving each `result`
   under the filenames listed there.
6. **Write `/tmp/audit_config.json`** with store name, currency, FX
   rates, the 7-day window, plus scope including the resolved
   `exclude_campaign_ids` (template in §Config). Required fields are
   validated up front — if any are missing or malformed the build
   stops with a one-line message.
7. **Run the entry script:**

   ```bash
   python3 <SKILL_DIR>/scripts/build_dashboard.py \
     --inputs  /tmp/audit_inputs/ \
     --config  /tmp/audit_config.json \
     --out     "<workspace>/<store-slug>-creatives-report-<YYYY-MM-DD>.html"
   ```

   `<SKILL_DIR>` is this skill's directory. `<workspace>` is the folder
   chosen in step 1. `<store-slug>` is a kebab-case version of the store
   name.

8. **Create or update the live artifact.** Call
   `mcp__cowork__create_artifact` with:
   - `id`: `<store-slug>-creatives-report` — **always use the same id
     for a given store**, so subsequent runs overwrite in place
     instead of stacking duplicates in the sidebar.
   - `html_path`: the absolute path of the HTML file from step 7.
   - `description`: `"TrackBee Creatives Report for <Store Name> —
     last 7 days ending <end-date>. Refreshed daily at 08:00 by the
     scheduled task."`
   - `mcp_tools`: `[]` (data is baked in at build time; the artifact
     does not call MCP at runtime — the scheduled task in step 9
     keeps it fresh).

9. **Schedule the daily 8am refresh.** Before handing off, call
   `mcp__scheduled-tasks__list_scheduled_tasks` to check whether a
   task for this store already exists. If
   `<store-slug>-creatives-report-daily-refresh` is already listed, do
   nothing. Otherwise call
   `mcp__scheduled-tasks__create_scheduled_task`:
   - `taskId`: `<store-slug>-creatives-report-daily-refresh`
   - `cronExpression`: `"0 8 * * *"` (every day at 8am local time)
   - `description`: `"Refresh the <Store Name> TrackBee Creative
     Audit every day at 8am."`
   - `notifyOnCompletion`: `false`
   - `prompt`: a self-contained instruction that captures everything
     the task needs to do without access to this conversation. Use
     this template (substitute the placeholders). The scheduled task runs
     under the user's own authenticated access, so it already scopes to
     their store — no extra parameters are needed:

     ```
     Refresh the TrackBee Creatives Report for <Store Name>
     (store id <STORE_ID>) by running the /creatives-report skill
     end-to-end.

     CONTEXT
     - Store: <Store Name>, store_id = <STORE_ID>,
       store_currency = <CCY>.
     - Ad-account FX: <FX_DICT> (e.g. {"GBP": 1.0, "EUR": 1.17}).
     - Workspace folder: <WORKSPACE_PATH>
     - Entry script: $CLAUDE_PLUGIN_ROOT/.claude/skills/creatives-report/scripts/build_dashboard.py
     - Scope: platforms=<PLATFORMS>,
       exclude_campaign_ids=<EXCLUDED>,
       product_focus=<PRODUCT_OR_NULL>.

     WINDOW — compute every run, do NOT hard-code
     - 7 days ending YESTERDAY (today − 1 day local). Start is 6
       days before that end.

     PLAN
     1. Invoke the /creatives-report skill against store <STORE_ID>
        using the window above.
     2. Build the report HTML at
        <WORKSPACE_PATH>/<store-slug>-creatives-report-<YYYY-MM-DD>.html
        (yesterday's date).
     3. Update the existing artifact in place: call
        mcp__cowork__create_artifact with the SAME id
        "<store-slug>-creatives-report" and the new html_path.
        Same id = update, not duplicate.
     4. Print one line to chat: the active-ad count this week, total
        spend and blended ROAS, and the artifact link as
        computer://<absolute-path>.
     ```

   Tell the user one line: "Live artifact created and a daily 8am
   refresh is scheduled."

10. **Hand off.** Print a `computer://` link to the HTML and a 2-3
    sentence headline (active-ad count this week, total spend and blended
    ROAS, median frequency). Full template in
    `references/handoff-template.md`.

If anything in the spec needs clarifying — what each section should
look like, how the figures are computed, brand tokens, copy tone — read
`references/dashboard-spec.md`. **Don't read it for normal runs.**
It's only needed when modifying a component or designing a new
variant.

## MCP calls (exact set)

For each store in scope, make exactly these calls **over the last 7
days only**. The orchestrator tolerates missing files — affected
sections render a "Data unavailable" card with the reason rather than
failing the build.

> **Save each MCP response verbatim** — don't unwrap, flatten, or
> hand-edit the payload before writing it to disk. The loaders accept
> both `{"result": {...}}`-wrapped and already-unwrapped payloads, so
> the verbatim response always works; hand-reshaped ones may not.

| Filename | Tool | Notes |
| --- | --- | --- |
| `{store_id}_meta.json` | `tool__get_meta_campaign_insights`, `status_filter="all"` | Last 7 days. Scaffolding to identify spending campaigns to drill into. |
| `{store_id}_google.json` | `tool__get_google_campaign_insights`, `status_filter="all"` | Last 7 days. Same. |
| `{store_id}_meta_ads_{campaign_id}.json` | `tool__get_meta_ad_insights` | One per spending Meta campaign over the last 7 days. **Primary ad-level data.** Includes a nested `creative` object (carries the format enum + image/video refs), `purchases_1d_click`, `purchases_28d_click`, `new_customer_purchases`. Note: `net_new_reach` is **not** currently returned by this tool, so the net-new-reach-share column reads "—" for those ads (see `references/metric-map.md`). Cap: if a store has > 12 spending campaigns this week, fetch the top 10 by spend. |
| `{store_id}_google_ads_{campaign_id}.json` | `tool__get_google_ad_insights` | One per spending Google campaign. PMAX returns asset groups (no per-asset spend); Search / Shopping return ads. |
| `{store_id}_anomalies.json` | `tool__detect_anomalies` | Sudden drops / spikes in the window. Rendered as a banner above the table. |

Phases run **in order**: Phase 1 (campaign-level) first, then the user
picks exclusions from the real campaign list, then Phase 2 (ad-level)
fetches **only the kept, non-excluded** spending campaigns — batch the
Phase-2 calls in parallel within that phase. Phase 1 must complete
before Phase 2 so the exclusion choice is made against actual
campaigns. There is no "recent window" phase — the audit is a
pure 7-day snapshot.

## Config

Write to `/tmp/audit_config.json`:

```json
{
  "store_name": "<Store name from list_my_stores>",
  "store_currency": "<EUR|USD|GBP|SEK|...>",
  "fx_to_store": {"USD": 0.79, "EUR": 0.85},
  "window": {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"},
  "stores": [
    {"id": 1, "name": "<Store Name>",
     "currency_symbol": "£",
     "meta_account_currency": "GBP",
     "google_account_currency": "EUR"}
  ],
  "scope": {
    "platforms": ["meta", "google"],
    "exclude_campaign_ids": [],
    "product_focus": null
  }
}
```

Every top-level field is required except `fx_to_store` (default `{}`)
and `scope` (defaults applied if absent). The entry script validates
the config before any rendering begins; a missing or malformed field
fails the build with a one-line message naming what's missing.

The top-level `store_name` / `store_currency` set the report title and the
display currency. The `stores` array carries the per-store ad-account
currency mapping the FX step needs (a store can run Meta in one currency
and Google in another); `id` must match the `{id}_*` input filenames. If
`stores` is omitted, the orchestrator synthesises a single-store entry
from `store_name` / `store_currency`.

`fx_to_store` is keyed by ad-account-currency and values are the
multiplier to convert FROM that currency TO the store currency.
Despite its name it does NOT have to end in EUR. Only needs entries
for currencies present on the store's ad accounts; if they all match
`store_currency`, pass `{}`.

The window should cover exactly 7 days (`end - start = 6 days`). The
entry script warns on stderr if it doesn't but still builds — every
figure is computed over whatever window is supplied.

## Component layout

The build is split into focused modules under `components/`, loaded
by the orchestrator on demand:

```
components/
  chrome/                      page shell + theme + helpers
    shell.html                 outer HTML scaffold with placeholders
    theme.css                  TrackBee brand v3 tokens + section CSS
    format_helpers.py          build-time currency / number / pct formatters + currency-symbol table
    render_formatters.js       client-side formatters for table interactivity
    table_filters.js           client-side platform / format / search filters
    logos.py                   inline SVG marks for platforms + brand
  transforms/                  raw JSON → per-store payload dicts
    ad_processing.py           Meta + Google raw ads → unified per-ad records
    store_rollups.py           KPI tiles per store (ad count, spend, ROAS, frequency)
    product_format_grid.py     per-product × per-format metric grids
  insights/                    payload → factual follow-up question cards
    next_questions.py                Q1-Q3 neutral follow-up prompts
  views/                       per-section HTML templates stamped by the orchestrator
  orchestrators/
    assemble.py                loads each component + stamps the views into the page
```

Each file owns one responsibility. The orchestrator loads each component
by relative path the moment it's needed; shared build-time helpers live in
`chrome/format_helpers.py` and are loaded via the same path-based shim,
and section HTML lives in `views/*.html` rather than inside Python strings.

There is no `lifetime_by_format` component — a 7-day window
isn't long enough to compute meaningful lifetime stats. The file is
intentionally absent from the bundle.

## What's bundled

```
scripts/build_dashboard.py        entry script (thin wrapper)
components/                       modular build kit (see §Component layout)
assets/tb_icon_b64.txt            TrackBee icon, base64 (+ source trackbee-icon.png)
assets/tb_wordmark_b64.txt        TrackBee wordmark, base64 (+ source trackbee-wordmark.png)
references/dashboard-spec.md      per-section spec (metric columns + layout)
references/metric-map.md          MCP field mapping reference
references/handoff-template.md    what to print to chat after rendering
```

## Guidelines

- **Always use the entry script.** Don't reconstruct the HTML inline.
- **Phase 1 → choose exclusions → Phase 2.** Fetch campaign-level
  (Phase 1) first, present the real campaigns and let the user pick
  exclusions by id, confirm the list, then fetch ad-level (Phase 2)
  only for the kept campaigns — batch the Phase-2 calls in parallel.
- **One config, one 7-day window.** Compute the window once; don't
  prompt the user twice.
- **Currency handling lives in the components.** Pass FX rates in
  `config.json` and let the transforms convert. All monetary values
  reach the template in store currency.
- **Hand off short.** A `computer://` link plus a 2-3 sentence
  headline.
- **Always create the live artifact AND schedule the daily refresh.**
  Skip only if the user explicitly says "one-off snapshot, don't
  schedule."
