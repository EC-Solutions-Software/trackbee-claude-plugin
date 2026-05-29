# Metric map — standard attribution metrics → TrackBee fields

Reference for when extending the dashboard with new metrics. The build script already implements every metric in this map; only consult when adding new ones.

All revenue values from TrackBee are in CENTS of `store_currency` — divide by 100 to display.
All ad-platform spend values are in UNITS of `ad_account_currency` — convert to store currency via the `fx_to_eur` map in config.json before combining.

## Revenue & profit

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Total Revenue | `tool__get_daily_store_statistics` → sum `total_revenue` | Sum, ÷ 100 |
| Revenue per session | Total Revenue ÷ Sessions | — |
| Gross Profit, Net Profit | Not in MCP yet — render `—` with a "requires COGS feed" tooltip | — |

## Orders & conversion

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Orders | `tool__get_daily_store_statistics` → sum `total_orders` | Sum |
| AOV | Total Revenue ÷ Orders | — |
| Conversion rate | `tool__get_funnel_overview` → orders ÷ page_view | rate_from_top |
| Added-to-cart rate | `tool__get_funnel_overview` → ATC count ÷ page_view | — |
| Started-checkout rate | `tool__get_funnel_overview` → checkout_started ÷ page_view | Caveat: client-side only |

## Sessions & traffic

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Sessions | `tool__get_funnel_overview` → page_view count | TrackBee tracks page_views, not session boundaries — note this if asked |

## Blended advertising

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Ad spend | Sum of `tool__get_*_campaign_insights` spend across platforms | Convert to store currency first |
| Blended ROAS | Total Revenue ÷ Ad spend | Both in store currency |
| Blended ACOS | 1 ÷ Blended ROAS | — |
| Blended CPA | Ad spend ÷ Orders | — |
| Web MER | Same as Blended ROAS for web-only stores | — |

## New customer

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| New Customer Revenue | `tool__get_daily_store_statistics` → sum `total_new_customer_revenue` | ÷ 100 |
| New customers | `tool__get_daily_store_statistics` → sum `total_new_customer_orders` | Proxy — orders not unique customers |
| Blended NC-CPA | Ad spend ÷ NC orders | — |
| Blended NC-ROAS / Acquisition MER | NC Revenue ÷ Ad spend | The headline retention metric |

## Per-platform (in-platform side)

| Metric | TrackBee source |
| --- | --- |
| Spend, Impressions, Clicks, CTR, CPC, CPM | `tool__get_meta_campaign_insights` / `tool__get_google_campaign_insights` (sum across campaigns) |
| ROAS (in-platform) | sum(revenue) ÷ sum(spend) per platform |
| Conversions (in-platform) | sum(purchases) per platform |

## Channel Attribution table — per channel

| Column | Source |
| --- | --- |
| Sessions | `tool__get_platform_funnel_breakdown` → per-platform `page_view` count |
| TrackBee Purchases | `tool__get_platform_funnel_breakdown` → per-platform `orders.count` |
| Purchases (in-platform) | `tool__get_meta_campaign_insights.purchases` / `tool__get_google_campaign_insights.conversions` |
| TrackBee Revenue | `tool__get_platform_funnel_breakdown` → per-platform revenue ÷ 100 |
| Revenue (in-platform) | sum(`purchase_roas` × `spend`) for Meta; sum(`conversions_value`) for Google |
| Spend | `tool__get_meta_campaign_insights` / `tool__get_google_campaign_insights` summed per platform, FX-converted |
| CPA | Spend ÷ Purchases (in-platform) |
| ROAS | Revenue (in-platform) ÷ Spend |

**Critical: CPA and ROAS are pure in-platform.** They never use TrackBee orders/revenue. This guarantees Meta's ROAS in Channel Attribution matches Meta's ROAS in Platform Overview to the cent.

For platforms TrackBee tracks but doesn't have ad insights for (Klaviyo, Pinterest, TikTok organic), Spend/CPA/ROAS show `—`.

## Customer Journeys

- `tool__get_platform_footprints` → per-channel `share_of_orders` and `solo_share`; assemble the touch-points envelope.
- `tool__get_platform_breakdown(platform=<plat>)` per top channel → co-occurrence matrix + transition matrix entries for that platform.
- `tool__get_platform_journeys(platform=<plat>)` per top channel → top sankey paths (sequences + share_of_orders).
- Use multi-touch journey count for confidence: <50 = noise, 50–200 = directional, 200–1000 = reliable, >1000 = high confidence.

## NC-ROAS daily series (Acquisition MER over time)

Daily spend uses a tiered approximation so the same calendar day shows the same value across windows:

```
total_3d  = meta_3d + google_3d                          # last 3 days
total_7d  = meta_7d + google_7d                          # last 7 days
total_28d = meta_28d + google_28d                        # last 28 days

tiers = [
  (last 3 days,           total_3d / 3),                 # most recent
  (days 4–7 from end,     (total_7d - total_3d) / 4),    # mid
  (days 8–28 from end,    (total_28d - total_7d) / 20),  # earliest
]
```

Each daily row gets its spend from whichever tier its date falls into. Period avg in the chart header = sum(daily_nc_revenue) ÷ sum(daily_spend) — matches the Blended NC-ROAS tile exactly.
