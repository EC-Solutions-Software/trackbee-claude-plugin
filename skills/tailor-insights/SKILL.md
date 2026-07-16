---
name: tailor-insights
description: >-
  Set up or update the marketing-strategy context TrackBee Insights uses to
  tailor its answers. Trigger when the user wants to record their goals or
  strategy for the first time, or change answers they gave before — "set up my
  strategy", "tailor insights to my goals", "update my strategy context",
  "change my answers", "edit my goals", "redo the strategy questions". Not a
  data tool — it captures the user's own context, it does not report store
  numbers.
---

# Tailor Insights

Call `tool__tailor_insights` from TrackBee Insights and follow the guidance it returns.

With no arguments it returns the strategy questions, each with the user's current answer (blank if unanswered). Show them as a form seeded with those answers so the user can fill in or change any, then call it again with `answers` mapping each filled-or-changed slug to its reply. The tool's own returned guidance is the source of truth — follow it verbatim.
