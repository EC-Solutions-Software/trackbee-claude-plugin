# Growth Report — Metric Map

Maps the TrackBee Growth framework metrics to the MCP fields they are
computed from. The full framework (names, bad/normal/good bands,
importance) lives as a static list in
`components/transforms/metrics_table.py` — this file documents only where
each row's numbers come from. Every framework row ships; the rows whose data
the MCP doesn't expose yet (true incrementality, per-product cuts,
product-cost sync) render as a prose placeholder in the interpretation column
rather than a measured value — none are dropped, and they're noted inline below.

All monetary fields from `tool__get_dashboard_overview` arrive in **cents** of
`store_currency` — divide by 100 once (`_cents` helper) before use.

## Store-level KPIs (`tool__get_dashboard_overview`)

| Framework row | MCP field | Notes |
|---|---|---|
| Revenue | `total_revenue` | Top-line, store currency. |
| New customer revenue | `total_new_customer_revenue` | |
| Returning customer revenue | `total_returning_customer_revenue` | |
| New customers acquired | `total_new_customer_orders` | Order count. |
| New vs. returning mix | `total_new_customer_orders` / `total_orders` | Computed share. |
| CAC · new customer CPA | `customer_acquisition_cost` | |
| MER · blended ROAS | `marketing_efficiency_ratio` | Total revenue ÷ total paid spend. |
| Ad-account ROAS | `return_on_ad_spend` | Platform-reported blended. |
| New-customer ROAS | `return_on_ad_spend_new` | |
| AOV | `total_revenue` / `total_orders` | Computed. |
| LTV | `customer_life_time_value` | |
| LTV : CAC | `customer_life_time_value_to_acquisition_cost_ratio` | |
| Ad spend | `ad_account_spend` | |
| Spend / revenue by channel | `platform_statistics[]` | Per-provider `spend`, `revenue`, `return_on_ad_spend`, `cost_per_click`. |

## Funnel (`tool__get_funnel_overview`)

| Framework row | Source | Notes |
|---|---|---|
| Conversion rate | `tool__get_funnel_overview` | Pass `compare_previous_period=true` so the prior window ships in one payload. |
| Traffic · sessions | `tool__get_funnel_overview` | Visitor volume. |
| Traffic quality | — | Prose placeholder. A per-platform CVR/quality cut needs a per-platform funnel grain the MCP doesn't expose yet; the row renders an interpretation note, not a measured value. |

## Channel mix / attribution (`tool__get_platform_footprints`)

| Framework row | Source | Notes |
|---|---|---|
| First-touch contribution | `tool__get_platform_footprints` | Channel share of top-of-journey. |
| Assisted conversions | `tool__get_platform_footprints` | Mid/assist share. |
| Attribution vs. incrementality gap | platform ROAS vs blended | Computed from `platform_statistics` + overview ROAS. |

## Creative / delivery (`tool__get_meta_recommendations`)

| Framework row | Source | Notes |
|---|---|---|
| Creative fatigue | `tool__get_meta_recommendations` | Meta's own fatigue + fragmentation flags. |
| Frequency | `tool__get_meta_recommendations` | Delivery frequency signal. |

## Campaign payloads (`tool__get_meta_campaign_insights`, `tool__get_google_campaign_insights`)

Used only to resolve excluded `campaign_id`s back to campaign names for the
exclusion note. No per-campaign scoring or ranking is done in the growth
report.

`spend` here is in the **ad-account currency**, not store currency. It is
multiplied by `meta_fx_to_store` / `google_fx_to_store` (from config,
default 1.0) before the `min_spend` gate, so cross-currency stores filter
on the right threshold. ROAS is a ratio, so FX cancels and it needs no
conversion. Campaign names are merchant-authored and HTML-escaped before
they reach the report.

## Confidence (`tool__detect_anomalies`)

Covers both windows; drives the confidence row and any "data looks off"
caveat in the narrative.
