# Metric map — standard attribution metrics → TrackBee fields

Reference for when extending the report with new metrics. The build already
implements every metric in this map; only consult when adding new ones.

All revenue values from `tool__get_dashboard_overview` and
`tool__get_platform_funnel_breakdown` are in CENTS of `store_currency` —
divide by 100 to display. All ad-platform spend values are in UNITS of
`ad_account_currency` — convert to store currency via the `fx_to_eur` map in
config.json before combining.

**`tool__get_dashboard_overview` is the authoritative source for spend,
revenue, and ROAS.** The daily / campaign feeds are fallbacks and side
inputs (see notes per row). This is what keeps Channel Attribution and
Platform Overview reconciled to the cent.

## Revenue & profit

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Total Revenue | `tool__get_dashboard_overview` → `total_revenue` (fallback: sum `daily.total_revenue`) | ÷ 100 |
| Revenue per session | Total Revenue ÷ Sessions | — |

## Orders & conversion

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Orders | `tool__get_dashboard_overview` → `total_orders` (fallback: sum `daily.total_orders`) | — |
| AOV | Total Revenue ÷ Orders | — |
| Conversion rate | `tool__get_funnel_overview` → orders ÷ page_view | from current-window funnel |
| Added-to-cart rate | `tool__get_funnel_overview` → ATC ÷ page_view | — |
| Started-checkout rate | `tool__get_funnel_overview` → checkout_started ÷ page_view | Caveat: client-side only |

Tile deltas (Revenue, Orders, Sessions, ATC/checkout/conversion rates) use
the funnel's `previous` block plus the funnel `previous` totals — supplied by
`compare_previous_period=true` on `tool__get_funnel_overview`.

## Sessions & traffic

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Sessions | `tool__get_funnel_overview` → `total_page_view_events` count | TrackBee counts page-views, not session boundaries — note this if asked |

## Blended advertising

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| Ad spend | `tool__get_dashboard_overview` → `ad_account_spend` ÷ 100 (fallback: sum campaign spend, FX-converted) | store currency |
| Blended ROAS | Total Revenue ÷ Ad spend | both in store currency |
| Blended CPA | Ad spend ÷ Orders | — |

## New customer

| Metric | TrackBee source | Computation |
| --- | --- | --- |
| New Customer Revenue | `tool__get_dashboard_overview` → `total_new_customer_revenue` (fallback: sum `daily`) | ÷ 100 |
| New customers | `tool__get_dashboard_overview` → `total_new_customer_orders` (fallback: sum `daily`) | Proxy — orders, not unique customers |
| Blended NC-CPA | Ad spend ÷ NC orders | — |
| Blended NC-ROAS / Acquisition MER | NC Revenue ÷ Ad spend | The headline retention metric |

## Per-platform (Platform Overview tiles)

| Metric | TrackBee source |
| --- | --- |
| Spend, Revenue (in-platform), ROAS, CPC | `tool__get_dashboard_overview` → `platform_statistics[]` (`spend`, `revenue`, `return_on_ad_spend`, `cost_per_click`), keyed on `conversion_provider` (FACEBOOK / GOOGLE), all ÷ 100 |
| Impressions, Clicks, Purchases/Conversions | `tool__get_meta_campaign_insights` / `tool__get_google_campaign_insights` summed across campaigns |
| CTR, CPC, CPM | derived: clicks ÷ impressions, spend ÷ clicks, spend ÷ impressions × 1000 |

Spend falls back to summed campaign spend (FX-converted) only when overview
has no `platform_statistics` entry for the platform.

## Channel Attribution table — per channel

| Column | Source |
| --- | --- |
| Sessions | `tool__get_platform_funnel_breakdown` → per-platform `page_view_events` count |
| TrackBee Purchases | `tool__get_platform_funnel_breakdown` → per-platform `orders` count |
| Purchases (in-platform) | `tool__get_meta_campaign_insights.purchases` / `tool__get_google_campaign_insights.conversions` |
| TrackBee Revenue | `tool__get_platform_funnel_breakdown` → per-platform `revenue` ÷ 100 |
| Revenue (in-platform) | `tool__get_dashboard_overview` → `platform_statistics[].revenue` ÷ 100 |
| Spend | `tool__get_dashboard_overview` → `platform_statistics[].spend` ÷ 100 |
| CPA | Spend ÷ Purchases (in-platform) |
| ROAS | Revenue (in-platform) ÷ Spend |

**Critical: CPA and ROAS are pure in-platform.** They never use TrackBee
orders/revenue. This guarantees Meta's ROAS in Channel Attribution matches
Meta's ROAS in Platform Overview to the cent. The TrackBee columns sit
alongside for reconciliation only.

For platforms TrackBee tracks but has no ad insights for (Klaviyo, Pinterest,
TikTok organic, etc.), Spend / CPA / ROAS show `—`. Channels with zero spend
but TrackBee revenue are surfaced as "earned" contributors in the insights.

## Store Funnel Analysis

| Stage | Source step (`tool__get_funnel_overview` current window) |
| --- | --- |
| Page views | `total_page_view_events` |
| Product views | `total_product_view_events` |
| Add to cart | `total_add_to_cart_events` |
| Checkout started | `total_checkout_started_events` |
| Orders | `total_orders` |

Each stage keeps its raw count, `rate_from_previous`, and `rate_from_top`.
The "lowest step rate" is the lowest step-to-step rate, **excluding** the page
view → product view drop by default (that is usually browsing behaviour — it
is surfaced as a secondary callout only when below 25%). Each stage's
conversion rate and lost-shopper count are stated as factual observations in
`components/insights/funnel.py`.

## Customer Journeys

- `tool__get_platform_footprints` → per-channel `share_of_orders` and
  `solo_share`; assemble the touch-points envelope.
- `tool__get_platform_breakdown(platform=<plat>)` per top channel →
  co-occurrence matrix entries for that platform.
- `tool__get_platform_journeys(platform=<plat>)` per top channel → sankey
  paths (sequences + `share_of_orders`).
- The co-occurrence insights apply a per-platform sample guard: platforms
  with fewer than 50 attributed orders (28d) are excluded from the
  strongest-overlap insight and named in a footer caveat.

## NC-ROAS daily series (Acquisition MER over time)

Daily spend uses a tiered approximation (the MCP gives window totals, not
per-day spend) so the same calendar day shows the same value across windows.
Window totals come from `tool__get_dashboard_overview.ad_account_spend`
(fallback: summed campaign spend):

```
total_3d, total_7d, total_28d   # store-currency window spend totals

tiers = [
  (last 3 days,           total_3d / n_3d),
  (days inside 7d not 3d, (total_7d - total_3d) / (n_7d - n_3d)),
  (days inside 28d not 7d, (total_28d - total_7d) / (n_28d - n_7d)),
]
```

Each daily row's NC-ROAS = `total_new_customer_revenue` (that day, ÷ 100) ÷
its tier's daily spend. Period avg in the chart header =
sum(daily_nc_revenue) ÷ sum(daily_spend) — matches the Blended NC-ROAS tile.
