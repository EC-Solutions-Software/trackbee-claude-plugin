# TrackBee Claude Plugin

TrackBee Insights Claude plugin. Each skill below is invoked through its `/<name>` slash command — the plugin provides the trigger. An active TrackBee Insights connection is required. Type any of the following:

- `/get-started` — onboarding entry point: pick a store and route to the right skill.
- `/discover-insights` — surface what TrackBee Insights can answer and route to the right skill.
- `/analyze-ad-performance` — build the Ad Performance Dashboard: Meta + Google campaigns with KPI bar, sortable per-campaign / per-ad table, and Scale / Hold / Refresh / Pause recommendations, packaged as one Live Artifact.
- `/attribution` — build the Attribution Report: Executive Summary, Blended Overview, Platform Overview, Channel Attribution, and Customer Journeys, packaged as one self-contained Live Artifact.
- `/performance` — investigate ad-account performance: diagnose drops, surface what changed, and recommend next moves.
- `/audit-creatives` — detect fatigue, compare content types, measure creative lifetime, and propose what to create next.
- `/diagnose-audience-health` — investigate frequency, reach saturation, and audience overlap across ad sets.
- `/find-undervalued-ads` — surface high-performing creatives with low spend that deserve more budget.
- `/scale-ads-profitably` — identify which ads to scale and at what cadence, based on ROAS, spend headroom, and audience saturation.
- `/discuss-artifact` — answer follow-up questions about a Live Artifact already open in the conversation.
- `/get-help-faq` — troubleshooting and FAQ for common questions and stuck states.

Skills that render a Live Artifact (`analyze-ad-performance`, `attribution`) ship their build pipeline here. Every other skill is a minimal `SKILL.md` that delegates to the TrackBee Insights MCP at invocation time.

## Layout

```markdown
.claude-plugin/      plugin + marketplace manifests
skills/
  <name>/
    SKILL.md         skill body
    components/      orchestrator, transforms, insights, charts, chrome
    references/      specs, metric maps, hand-off templates
    assets/          brand icon + wordmark
    scripts/         entry script
```
