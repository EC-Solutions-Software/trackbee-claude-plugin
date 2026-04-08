# Vibe Scaling Plugin

Stop guessing. Start vibescaling.

Talk to your Shopify ad data like you talk to a colleague. No dashboards to learn. No SQL to write. No analyst to wait for. Just ask — and get data-backed answers in seconds.

This plugin connects Claude to your TrackBee store data and gives it the skills to analyze your ads, spot problems, and tell you what to do next.

---

## Get started

### 1. Install the plugin

1. Open Claude Desktop
2. Go to Settings (gear icon) > Plugins
3. Click Add Marketplace
4. Enter `EC-Solutions-Software/vibe-scaling` as the URL
5. Confirm when prompted

### 2. Connect your store data

The plugin talks to your store through the TrackBee MCP server.

1. In Claude Desktop, go to Settings > MCP Servers
2. Click Add Server
3. Set it up as:
   - Name: `trackbee-mcp`
   - Type: Streamable HTTP
   - URL: your TrackBee contact will give you this
4. Save it
5. A browser window opens for sign-in — use your Google account
6. You're connected when the TrackBee MCP shows as active

If you hit a permission error, ask your TrackBee contact to add your account.

### 3. Check it works

Start a new conversation and ask:

> "List my stores"

See your stores? You're in. 🚀

---

## What you can ask

You don't need to memorize commands. Just ask naturally and Claude picks the right skill. But if you want to go direct:

### `/analyze-ad-performance`

Find the ads that get great reach but don't convert. Figure out what to scale, what to adjust, and what to kill.

Ask things like:
- "Which ads have high CTR but low ROAS?"
- "This campaign moved to scaling — can we push more budget or should we kill it?"
- "Which ads got budget increases this week and did the results hold up?"

### `/diagnose-audience-health`

Catch the moment your audience starts getting stale. Rising CPM, dropping CTR, climbing frequency — the classic signs you're paying more to reach the same people.

Ask things like:
- "Is my CPM trending up across campaigns?"
- "Show me frequency trends — am I saturating my audience?"
- "Am I still reaching new customers or just showing ads to the same people?"

### `/audit-creatives`

See which creatives are dying, which are thriving, and what you should make next.

Ask things like:
- "Are any of my creatives showing fatigue?"
- "What content type works best for [product]?"
- "How long do my video ads last before performance drops?"

### `/discover-insights`

Not sure what to ask? Start here. Get a list of high-value questions tailored to your store, review seasonal investments, or see what high-growth brands are doing differently.

Ask things like:
- "What should I be looking at to grow my business?"
- "Were my Black Friday campaigns worth it? Should I do it again?"
- "What are other brands doing that I'm not?"

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "No stores found" | Your Google account doesn't have access yet. Ask your TrackBee contact. |
| MCP connection failed | Double-check the URL and make sure your Google account has been granted access. |
| Permission error on sign-in | Your account needs to be added to the access list. Ask your TrackBee contact. |
