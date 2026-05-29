# Hand-off template

After the build script finishes, print:

1. A `[View the dashboard](computer://<absolute-path-to-html>)` link.
2. A three-sentence headline:
   - **Top KPI sentence** — Blended ROAS for the last 28 days, plus a delta vs the previous period.
   - **Most striking attribution finding** — largest TrackBee-vs-platform gap or highest-ROAS channel.
   - **Most useful journey insight** — top opener / closer / handoff or the strongest cooccurrence pair.
3. A one-line note on the filter behaviour: "Toggle 3d / 7d / 28d at the top, plus the sankey filters under Customer Journeys."

**Don't paste the tables into chat.** The dashboard is the deliverable.

## Example

> [View the dashboard](computer://<workspace>/<store-slug>-attribution-report-<YYYY-MM-DD>.html)
>
> Blended ROAS for the last 28 days is <X.XX>, <up|down|flat> vs the previous 28d. <Channel A> is over-reporting purchases by ~<N>% versus first-party tracking — discount its in-platform ROAS when comparing across channels. <N>% of journeys touching <Channel B> also touch <Channel A>, meaning <Channel B> is sitting downstream of paid acquisition rather than driving it independently.
>
> Toggle 3d / 7d / 28d at the top; under Customer Journeys, switch the sankey between Multi-touch / Top 5 / Single-touch / All.
