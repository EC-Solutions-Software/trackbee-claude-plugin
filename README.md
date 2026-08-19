# TrackBee Claude Plugin

> **Note:** Building Live Artifacts only works in **Claude CoWork**. Other Claude clients can still run the skills, but they will not render the Live Artifact.

TrackBee Insights Claude plugin. Each skill below is invoked through its `/<name>` slash command — the plugin provides the trigger. An active TrackBee Insights connection is required. Type any of the following:

- `/discover-insights` — getting-started entry point: pick a store, see what TrackBee Insights can answer, and route to the right skill.
- `/check-tracking-setup` — check which ad and analytics platforms are connected for a store and whether each connection is set up correctly.
- `/analyze-ad-performance` — build the Ad Performance Dashboard: Meta + Google campaigns with a KPI bar, a sortable per-campaign / per-ad table (spend, ROAS, frequency, reach, CTR, CPC and more), and per-platform key observations, packaged as one Live Artifact.
- `/attribution` — build the Attribution Overview: Executive Summary, Blended Overview, Platform Overview, Channel Attribution, Customer Journeys, a Store Funnel Analysis, and a "Where to go next" prompt dock, packaged as one self-contained Live Artifact.
- `/creatives-report` — build the Creatives Report Dashboard: present each spending ad's last-7-day statistics (spend, ROAS, frequency, reach, net-new-reach share, purchases, new-customer share, 1d/28d), grouped by product and format, packaged as one self-contained Live Artifact.
- `/growth-report` — build the Growth Report: a last-7-days vs prior-7-days narrative answer to "what's driving profitable growth?", a what's-working / what's-breaking split, and the full TrackBee growth metric framework, packaged as one self-contained Live Artifact.
- `/daily-store-pulse` — the fast morning check-in across every store: a portfolio summary of which stores have a flagged anomaly today plus one pulse card per store (KPI tiles vs a trailing-7-day baseline, month-to-date pacing, anomalies + Meta flags, top movers, a go-deeper dock) with a client-side store filter, packaged as one Live Artifact.
- `/performance` — investigate ad-account performance: diagnose drops, surface what changed, and recommend next moves.
- `/diagnose-audience-health` — investigate frequency, reach saturation, and audience overlap across ad sets.
- `/find-undervalued-ads` — surface high-performing creatives with low spend that deserve more budget.
- `/scale-ads-profitably` — identify which ads to scale and at what cadence, based on ROAS, spend headroom, and audience saturation.
- `/audit-creatives` — audit ad creatives: detect fatigue, compare content types, measure creative lifetime, and propose what to create next.
- `/audit-klaviyo-campaign-creatives` — review a Klaviyo campaign's actual creative before or after it sends: either the individual images, or the finished email rendered as a shopper sees it. Covers email, SMS/MMS and push, and needs your Klaviyo connector.
- `/store-funnel` — quick text read on the store conversion funnel (page view → product view → add to cart → checkout started → order) with the step-to-step drop-off and the single biggest leak named first; for a visual, persistent funnel use `/attribution`.
- `/discuss-artifact` — answer follow-up questions about a Live Artifact already open in the conversation.
- `/get-help-faq` — troubleshooting and FAQ for common questions and stuck states.
- `/product-feedback` — share what's missing or could be improved in TrackBee Insights (also surfaces on its own after a few questions).
- `/tailor-insights` — set up or update your marketing-strategy context (goals, strategy) so TrackBee Insights tailors its answers to you; captures your own context, does not report store numbers.

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
