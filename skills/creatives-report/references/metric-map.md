# Creatives Report — Metric Map

Maps user-facing metric names to TrackBee MCP field names at the
**ad level**. Every figure in the report comes from the **last 7
days** — there is no longer-window or comparison slice.

## Meta (`tool__get_meta_ad_insights`)

| Dashboard Column   | MCP Field                    | Notes |
|--------------------|------------------------------|-------|
| Ad name            | `ad_name`                    | |
| Ad set             | `adset_name`                 | |
| Campaign           | `campaign_name`              | |
| Status             | `effective_status`           | |
| Format             | `creative.format` (nested)   | The MCP attaches creative as a nested `creative` object; format enum is `SINGLE_IMAGE` / `DYNAMIC_CREATIVE` / `VIDEO` / `CAROUSEL` (there is **no** flat `creative_format`). Map: VIDEO→Video, CAROUSEL→Carousel, SINGLE_IMAGE→Static, DYNAMIC_CREATIVE→Video if `creative.video_id` else Static. Fallback: `creative.video_id`→Video, `creative.image_url`/`thumbnail_url`→Static. |
| Spend              | `spend`                      | In `ad_account_currency`. Convert with `fx_to_store`. |
| Reach              | `reach`                      | Unique people |
| Impressions        | `impressions`                | |
| Frequency          | `frequency`                  | Threshold: >= 3.5 → REFRESH |
| CPM                | `cpm`                        | |
| CTR                | `ctr`                        | Already in % |
| CPC                | `cpc`                        | |
| Clicks             | `clicks`                     | |
| ATC                | `add_to_carts`               | |
| Purchases          | `purchases`                  | Default 7d_click + 1d_view |
| Revenue            | `revenue_1d_click`           | 1-day click attribution |
| ROAS               | `purchase_roas`              | Platform-reported |
| CPA                | `spend / purchases`          | Computed |
| Cost / ATC         | `spend / add_to_carts`       | Computed |
| Net new reach      | `net_new_reach`              | ⚠ **Not currently returned by `tool__get_meta_ad_insights`,** so the NNR-based REFRESH signal is dormant (renders "—"). |
| NNR share          | `net_new_reach / reach`      | Computed. Threshold: 0 ≤ share < 0.10 with reach > 1000 → REFRESH. ⚠ **Dormant** while `net_new_reach` is absent (renders "—", never fires REFRESH). |
| New customers      | `new_customer_purchases`     | TrackBee custom event |
| NC revenue         | `new_customer_revenue`       | |
| Purchases 1d click | `purchases_1d_click`         | Used for "upper-funnel shift" tag |
| Purchases 7d click | `purchases_7d_click`         | Cumulative with 1d |
| Purchases 28d click| `purchases_28d_click`        | Cumulative with 1d, 7d |
| Purchases 1d view  | `purchases_1d_view`          | View-through, separate from click |
| First active       | `first_active_date` / `created_time` | Drives Age (d) column. ⚠ **Neither field is returned by the MCP** — Age (d) currently always renders "—". |

## Google (`tool__get_google_ad_insights`)

| Dashboard Column   | MCP Field                            | Notes |
|--------------------|--------------------------------------|-------|
| Ad / Asset group   | `ad_name` / `asset_group_name`       | PMAX → asset group |
| Ad group           | `ad_group_name`                      | |
| Campaign           | `campaign_name`                      | |
| Campaign type      | `campaign_type`                      | `SEARCH` / `SHOPPING` / `PERFORMANCE_MAX` |
| Status             | `ad_status`                          | Google ad rows expose **`ad_status`** (with `ad_group_status` / `campaign_status` as fallbacks), **not** Meta's `effective_status`. The transform reads `ad_status` first. |
| Format             | derived from `campaign_type`         | Search → Search Text; Shopping → Shopping Feed; PMAX → PMAX |
| Headlines          | `headlines[]`                        | First 2 joined |
| Descriptions       | `descriptions[]`                     | First 1 in table |
| Spend              | `spend`                              | In `ad_account_currency`. Convert with `fx_to_store`. |
| Impressions        | `impressions`                        | |
| Clicks             | `clicks`                             | |
| CTR                | derived as `clicks / impressions × 100` | Computed in-transform for consistency across platforms |
| CPC                | `average_cpc`                        | |
| CPM                | `average_cpm`                        | |
| Conversions        | `conversions`                        | Google-tracked |
| Revenue            | `conversions_value`                  | |
| ROAS               | `conversions_value / spend`          | Computed |
| CPA                | `spend / conversions`                | Computed |
| New customers      | `new_customer_conversions`           | |
| NC revenue         | `new_customer_conversions_value`     | |
| First active       | `start_date`                         | Drives Age (d) column. ⚠ **Not returned** on Google ad rows (`start_date` is only a query parameter) — Age (d) always "—". |

PMAX asset groups have no per-asset spend / impressions — listed for
inventory only, excluded from fatigue scoring.

## Anomalies (`tool__detect_anomalies`)

⚠ **Contract mismatch — this tool returns store-level daily-statistic
anomalies (z-scores on `total_revenue`, `total_orders`, funnel rates,
etc.), not ad/creative-level signals.** Each anomaly object has:
`date`, `metric`, `value`, `baseline_mean`, `baseline_std`, `z_score`,
`direction`. There is **no `severity` and no `entity_name`/per-entity
dimension**, and `direction` is **`"above"` / `"below"`**. The banner derives
what it can from this shape: it title-cases the metric name, maps `direction`
to an ↑/↓ arrow, and synthesizes a severity label from `abs(z_score)`
(e.g. `2.3σ above`). It does not invent a per-ad entity — anomalies are
store-wide, so the banner surfaces store-level signals (e.g. `Total Revenue`),
not per-creative ones.

| Dashboard Use            | Field | Status |
|--------------------------|-------|--------|
| Banner: "X anomalies"    | length of `anomalies[]` | OK |
| Anomaly card title       | `anomalies[].metric` | Title-cased; is a store-level stat name (e.g. `Total Revenue`), not an ad |
| Anomaly direction        | `anomalies[].direction` | `above`/`below` mapped to an ↑/↓ arrow |
| Severity                 | derived from `anomalies[].z_score` | No `severity` field exists; the banner renders `abs(z_score)` as a `Nσ` label |
| Affected entity          | `anomalies[].entity_name` | **Absent** — anomalies are store-wide, no entity dimension |

## Format detection rules

```python
def meta_format(ad):
    # Creative is nested under ad["creative"]; format enum is
    # SINGLE_IMAGE / DYNAMIC_CREATIVE / VIDEO / CAROUSEL.
    creative = ad.get("creative") or {}
    fmt = (creative.get("format") or "").upper()
    if fmt == "VIDEO":            return "Video"
    if fmt == "CAROUSEL":         return "Carousel"
    if fmt == "SINGLE_IMAGE":     return "Static"
    if fmt == "DYNAMIC_CREATIVE":
        return "Video" if creative.get("video_id") else "Static"
    if creative.get("video_id"):  return "Video"
    if creative.get("image_url") or creative.get("thumbnail_url"):
        return "Static"
    return "Other"

def google_format(ad_or_group, campaign_type):
    if campaign_type == "PERFORMANCE_MAX":  return "PMAX"
    if campaign_type == "SHOPPING":         return "Shopping Feed"
    if campaign_type == "SEARCH":           return "Search Text"
    return (campaign_type or "Other").title()
```

## Status decision badges

See `dashboard-spec.md §1` for the full decision tree. Quick
reference:

| Tag      | Color (CSS class)  |
|----------|---------------------|
| SCALE    | `act-scale`  — green / success |
| HOLD     | `act-hold`   — muted grey |
| REFRESH  | `act-refresh` — amber / warning |
| KILL     | `act-kill`   — red / error |
| retargeting only     | `tag-chip` — lavender / blue ink |
| upper-funnel shift   | `tag-chip` — lavender / blue ink |
