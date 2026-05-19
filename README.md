# TrackBee Claude Plugin

> **This is a public repository.** Source code, skill bodies, and dashboard assets here are visible to anyone on the internet. Do not commit anything you would not paste into a public forum.

TrackBee Insights dashboards as a Claude plugin. Two skills that turn a Shopify store's TrackBee data into a self-contained Live Artifact HTML report:

- **`build-ad-performance-dashboard`** — cross-platform Meta + Google campaign analysis with a sortable per-campaign / per-ad table, KPI bar, and Scale / Hold / Refresh / Pause recommendations.
- **`build-attribution-dashboard`** — blended KPIs, daily NC-ROAS trend, platform tiles, channel attribution, and customer-journey Sankey + heatmap.

## Layout

```
.claude-plugin/      plugin + marketplace manifests
skills/
  build-ad-performance-dashboard/
    SKILL.md         build instructions
    resources/       layout, transforms, insights, views, orchestrators
  build-attribution-dashboard/
    SKILL.md         build instructions
    resources/       layout, charts, transforms, insights, orchestrators
```

Each `SKILL.md` is the source of truth for the build it drives. Resource files are self-contained (no inter-component imports) so the orchestrator can load them by relative path.
