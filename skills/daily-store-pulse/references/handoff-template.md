# Daily Store Pulse — handoff template

What to print to chat after the build finishes. Keep it to **one or two
sentences** plus the artifact link — the pulse does the talking.

## Template

```
[TrackBee daily store pulse](computer:///<abs-path-to-html>)

<K of M> stores flagged an anomaly today — <flagged store names>. The rest had
nothing flagged. Live artifact created and a daily 08:00 refresh is scheduled.
```

When nothing is flagged:

```
[TrackBee daily store pulse](computer:///<abs-path-to-html>)

No anomalies flagged across all <M> stores this morning. Live artifact
created and a daily 08:00 refresh is scheduled.
```

## Example

```
[TrackBee daily store pulse](computer://<workspace>/trackbee-daily-store-pulse-2026-06-03.html)

2 of 4 stores flagged an anomaly today — <STORE_A> (a revenue anomaly and a
Meta creative-limited flag) and <STORE_B>. The rest had nothing flagged. Live
artifact created and a daily 08:00 refresh is scheduled.
```

## What NOT to print

- Don't restate each store's KPIs in chat — every card is in the artifact.
- Don't run the deep analysis in the hand-off. The pulse points at the
  go-deeper dock; let the user click through to `/performance`,
  `/scale-ads-profitably`, or `/attribution`.
- Don't ask which store to look at — the artifact already covers all of them
  and the filter narrows them.
- Don't explain the methodology — the footer and `dashboard-spec.md` cover it.
