# Updates

[Français](../fr/mises-a-jour.md) · [Repository home](../../README.md)

This repository follows an ongoing operation, not a timeless report. Each edition states when its data were measured, read, generated, published and revised, and these dates are kept distinct. The calendar is [config/edition-calendar.json](../../config/edition-calendar.json), the editions are listed in [config/editions.json](../../config/editions.json) and the reviews actually carried out in [config/operations.json](../../config/operations.json).

Current state: **Periodic update planned; manual preparation.** No automation is activated.

## Dates of the current edition

<!-- dwr:begin dates -->
| Date or state | Value |
|---|---|
| Edition | `2026-09-15_2026-10-15-r1` |
| Status | candidate, not reviewed, not published |
| Measured period | September 15 to October 14, 2026 inclusive, UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-16` |
| published_at | `null` (not published) |
| revised_at | `null` |
| latest_available_data_date | `2026-10-14` |
| next_review_target | weekly review `2026-10-19T13:17:00Z`, not guaranteed |
| Updates | periodic update planned; manual preparation (automation not activated) |
<!-- dwr:end dates -->

| Field | Meaning |
|---|---|
| `period_start_inclusive` | first UTC day of the measured window, included |
| `period_end_exclusive` | exclusive end of the window: the first day not included, which is not the last day counted |
| `last_included_date` | last UTC day actually included in the counts |
| `extracted_at` | interval (start and end, UTC) during which the joint aggregate was read from the producer; the earlier reading of the exports is in `exports_extracted_at` of `catalog.json` |
| `source_snapshot_at` | date of the pinned commit of the private archive used for coverage |
| `graph_snapshot_at` | per site, date of the source snapshot from which `links.csv` and the registry were built |
| `generated_at` | date on which this candidate was prepared; fixed in `config/editions.json` so that a rebuild of the same inputs gives the same bytes |
| `published_at` | first real public publication of the edition; `null` until then and never changed by a rebuild |
| `revised_at` | date of a published correction; `null` when there is none |
| `latest_available_data_date` | last day available and interpretable, not the date of the last successful run |
| `next_review_target` | next planned weekly review and next monthly window, explicitly without guarantee |

A rendering regenerated today from September data does not become an observation of today. A historical figure keeps its own period even when the home page points to a newer edition.

## Monthly windows anchored on the 15th

Reference editions use consecutive monthly windows in UTC, from the 15th (included) to the 15th of the next month (excluded) (`analysis/dwr/dates.py`). The first window is `[2026-09-15, 2026-10-15)`: 30 days, from September 15 to October 14 inclusive. The next one is `[2026-10-15, 2026-11-15)`: 31 days, from October 15 to November 14 inclusive. Editions are therefore not all "30 days". The current UTC day is never included, and an acquisition refuses a window that is not closed.

## Weekly preparation and manual dispatch

The calendar plans a weekly review on Monday at 13:17 UTC and a monthly edition. Both are templates with `activation_status = template_not_activated`, kept outside the automatic workflow folder. The offline CI workflow also accepts manual `workflow_dispatch` runs. It checks the existing public projection; it neither acquires new data nor publishes an edition.

What the preparation does: check that sources are available, prepare a candidate edition and a difference report, and record the operation state. What it never does: publish automatically, publish private data or an unreviewed candidate, or run the authenticated private acquisition. That acquisition runs only in the private environment, never in a public CI job; public jobs have no access to the producer database or to private sources.

GitHub documentation ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), consulted 2026-10-16) states that scheduled runs can be delayed during periods of high load and that some queued jobs may be dropped; schedules run only from the default branch, and in public repositories they are disabled after 60 days without activity. No time of update is promised here.

## Consolidation delay

A monthly edition is prepared no earlier than 48 hours after the window closes (`consolidation_delay_hours`). The wait gives late counts a chance to arrive; it guarantees nothing. If the source is still partial, the edition says so. Freshness thresholds (a weekly review overdue after 10 days, a monthly edition overdue 21 days after consolidation) are operating rules, not commitments.

## Operation states and retries

Each run ends in one of six states: `new_data`, `unchanged`, `source_unavailable`, `validation_failed`, `awaiting_review` and `published`. A successful run does not prove that new data arrived: a run that finds nothing new is `unchanged` and never advances the data date. Retries are bounded (at most 3 attempts) and idempotent. A late or retried run never moves the window to a more convenient one, and an incomplete or missed window stays visible.

## Frozen editions and revisions

An edition is identified as `<start>_<end>-r<n>`, for example `2026-09-15_2026-10-15-r1`. Code version, schema version, rule versions and edition identifier are separate (see `versions` in `catalog.json`). Once published, an edition is frozen. A correction creates `r2`, with its reason, the numeric delta, the author and reviewer of the correction, and links in both directions (`supersedes`, `superseded_by`). The cause is one of: late observations, classifier correction, scope change, transformation correction, privacy revision. None of these causes is growth. A removal required for privacy or rights is handled as a documented exception, not hidden by rewriting history. A classifier correction also opens a new measurement epoch (`measurement_epoch_id`); labels recorded under an earlier version are not relabelled.

## latest.json and status.json

[data/latest.json](../../data/latest.json) points only to a reviewed public edition, never to a draft or to the last successful run. It is `null` today, with its reason, because no edition has been reviewed and published.

[data/status.json](../../data/status.json) reports the real state with non-sensitive data only: `realtime = false`, the automation states, the candidate edition and its state, the last review, `latest_available_data_date` and `next_review_target`. It is not a real-time indicator. When a source fails, the last valid edition is kept and the unavailability is shown; series are never replaced by zeros and the data date does not advance.

## Rolling windows

A `rolling_30d` view (the last 30 closed days) may be added later as a secondary product, from the qualified joint daily aggregate; it is not produced in this edition. Rolling windows overlap: their totals are never added to build a trend. Main comparisons use non-overlapping monthly editions.
