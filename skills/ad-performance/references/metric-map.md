# Ad Performance — Metric Map

Maps user-facing metric names to TrackBee MCP field names.

## Meta (`tool__get_meta_campaign_insights` / `tool__get_meta_ad_insights`)

| Dashboard Column  | MCP Field                | Notes |
|-------------------|--------------------------|-------|
| Spend             | `spend`                  | In `ad_account_currency`. Convert with `meta_fx_to_store`. |
| Avg Daily Spend   | `spend / n_days`         | Proxy — `daily_budget` not in API. |
| Reach             | `reach`                  | Unique people. |
| Impressions       | `impressions`            | |
| Frequency         | `frequency`              | Flag ≥ 3.0 as fatigue risk. |
| CPM               | `cpm`                    | Per 1k impressions, in `ad_account_currency`. |
| CTR               | `ctr`                    | Already in %. |
| CPC               | `cpc`                    | In `ad_account_currency`. |
| Clicks            | `clicks`                 | Link clicks. |
| ATC               | `add_to_carts`           | Add-to-cart events. |
| Checkouts         | —                        | **Not available** via campaign insights API. |
| Results           | `purchases`              | |
| Revenue           | `revenue_1d_click`       | 1-day click attribution window. |
| ROAS              | `purchase_roas`          | Platform-reported. |
| Cost/ATC          | `spend / add_to_carts`   | Computed. |
| New Cust.         | `new_customer_purchases` | |
| NC Revenue        | `new_customer_revenue`   | |

## Google (`tool__get_google_campaign_insights` / `tool__get_google_ad_insights`)

| Dashboard Column  | MCP Field                          | Notes |
|-------------------|------------------------------------|-------|
| Spend             | `spend`                            | In `ad_account_currency`. Convert with `google_fx_to_store`. |
| Avg Daily Spend   | `spend / n_days`                   | |
| Reach             | —                                  | **Not in Google API.** |
| Impressions       | `impressions`                      | |
| Frequency         | —                                  | **Not in Google API.** |
| CPM               | `average_cpm`                      | |
| CTR               | `ctr` × 100                        | Google returns as a fraction (0–1); multiply by 100. |
| CPC               | `average_cpc`                      | |
| Clicks            | `clicks`                           | |
| ATC               | —                                  | **Not in Google API.** |
| Checkouts         | —                                  | **Not available.** |
| Results           | `conversions`                      | Google-tracked conversions. |
| Revenue           | `conversions_value`                | Google conversion value. |
| ROAS              | `conversions_value / spend`        | Computed. |
| New Cust.         | `new_customer_conversions`         | |
| NC Revenue        | `new_customer_conversions_value`   | |

## Store-level KPIs (`tool__get_dashboard_overview`)

All values in **cents** of `store_currency` — divide by 100 for display.

| Dashboard KPI  | Overview Field                                       |
|----------------|------------------------------------------------------|
| Total Revenue  | `overview.total_revenue`                             |
| Total Orders   | `overview.total_orders`                              |
| MER            | `overview.marketing_efficiency_ratio`                |
| Total Ad Spend | `overview.ad_account_spend`                          |
| Platform ROAS  | `overview.platform_statistics[].return_on_ad_spend`  |

## Scaling decision framework

Thresholds live in `components/insights/thresholds.py`. Spend thresholds
are expressed in **store currency units** — every monetary cell rendered
in the dashboard uses the store's symbol from config, not a hardcoded one.

| Signal                                          | Action                  |
|-------------------------------------------------|-------------------------|
| ROAS ≥ 1.8 AND Frequency < 2.5                  | Scale +20–30%           |
| ROAS 1.5–1.8 AND Frequency < 3.0                | Hold — monitor weekly   |
| Frequency ≥ 3.5 AND ROAS ≥ 1.2                  | Refresh creative        |
| ROAS < 1.2 AND Spend > 200 (store currency)     | Review / pause          |
| Google ROAS ≥ 4.0 AND Spend > 50 (store ccy)    | Scale aggressively      |
| Google branded cannibalization = "high"         | Add negative keywords   |
