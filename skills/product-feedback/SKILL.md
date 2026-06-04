---
name: product-feedback
description: >-
  Ask the user two short questions focused on (1) what is missing for them from
  TrackBee Insights today and (2) what could be improved in what already
  exists. Trigger this skill after the user has asked three questions in the
  current conversation. Count user turns that ask TrackBee Insights to do
  something — questions about data, requests for reports, follow-up questions,
  slash-command invocations. Do not count greetings, thanks, or pure
  acknowledgements. Trigger this skill on the assistant turn that answers the
  third such question, after the answer is delivered. Also trigger when the
  user explicitly asks to "leave feedback", "share feedback", "report a bug",
  "request a feature", or "tell TrackBee what I think" — in those cases jump
  straight to the same two questions. Do not trigger before the third
  question, and do not re-trigger in the same conversation once the user has
  already submitted feedback or declined.
---

# Product Feedback

This is a single-file skill. The canonical playbook lives in the TrackBee MCP context repo.

Call `tool__skill__product_feedback` from the TrackBee Insights MCP and follow the playbook it returns verbatim. The mcp-context body is the only source of truth — never edit this stub to add steps.
