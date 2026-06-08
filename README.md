# TrackBee Claude Plugin

TrackBee Insights Claude plugin. Each skill below is invoked through its `/<name>` slash command — the plugin provides the trigger. An active TrackBee Insights connection is required. Type any of the following:

- `/get-started` — onboarding entry point: pick a store and route to the right skill.
- `/discover-insights` — surface what TrackBee Insights can answer and route to the right skill.
- `/analyze-ad-performance` — build the Ad Performance Dashboard: Meta + Google campaigns with KPI bar, sortable per-campaign / per-ad table, and Scale / Hold / Refresh / Pause recommendations, packaged as one Live Artifact.
- `/attribution` — build the Attribution Overview: Executive Summary, Blended Overview, Platform Overview, Channel Attribution, Customer Journeys, a Store Funnel Analysis, and a "Where to go next" prompt dock, packaged as one self-contained Live Artifact.
- `/creatives-report` — build the Creatives Report Dashboard: score every spending ad over the last 7 days as Scale / Hold / Refresh / Kill, group by product and format, and turn it into a prioritised production plan, packaged as one self-contained Live Artifact.
- `/growth-report` — build the Growth Report: a last-7-days vs prior-7-days narrative answer to "what's driving profitable growth?", a what's-working / what's-breaking split, and the full TrackBee growth metric framework, packaged as one self-contained Live Artifact.
- `/daily-store-pulse` — the fast morning check-in across every store: a portfolio verdict plus one pulse card per store (On track / Watch / Act now, KPI tiles vs a trailing-7-day baseline, month-to-date pacing, anomalies + Meta warnings, top movers, a go-deeper dock) with a client-side store filter, packaged as one Live Artifact.
- `/performance` — investigate ad-account performance: diagnose drops, surface what changed, and recommend next moves.
- `/diagnose-audience-health` — investigate frequency, reach saturation, and audience overlap across ad sets.
- `/find-undervalued-ads` — surface high-performing creatives with low spend that deserve more budget.
- `/scale-ads-profitably` — identify which ads to scale and at what cadence, based on ROAS, spend headroom, and audience saturation.
- `/discuss-artifact` — answer follow-up questions about a Live Artifact already open in the conversation.
- `/get-help-faq` — troubleshooting and FAQ for common questions and stuck states.

Skills that render a Live Artifact (`analyze-ad-performance`, `attribution`, `creatives-report`, `daily-store-pulse`, `growth-report`) ship their build pipeline here. Every other skill is a minimal `SKILL.md` that delegates to the TrackBee Insights MCP at invocation time.

## Layout

```markdown
.claude-plugin/      plugin + marketplace manifests
skills/
  <name>/
    SKILL.md         skill body
    components/      orchestrator, transforms, insights, charts, views, chrome
    references/      specs, metric maps, hand-off templates
    assets/          brand icon + wordmark
    scripts/         entry script
```
