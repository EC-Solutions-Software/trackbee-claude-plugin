---
name: overtracking
description: >-
  Diagnose why a store's ad platforms report more conversions than it has real
  orders, and name what is counting twice. Trigger when the merchant says their
  conversions look too high, that platform numbers do not match Shopify, that
  two platforms both claim the same sales, or that they are being double
  counted. Also trigger for "why does Meta show more purchases than I have
  orders?", "my conversions are inflated", "the numbers don't add up", "am I
  tracking double?", or "where is my overtracking coming from?". For
  undercounting — broken connections, missing tags, expired tokens — use
  check-tracking-setup instead.
---

# Overtracking

This is a single-file skill. The canonical playbook lives in the TrackBee MCP context repo.

Call `skill__overtracking` from the TrackBee Insights MCP and follow the playbook it returns verbatim. The mcp-context body is the only source of truth — never edit this stub to add steps.
