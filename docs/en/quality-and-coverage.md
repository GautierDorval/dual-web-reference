# Quality and coverage

[Français](../fr/qualite-et-couverture.md) · [Repository home](../../README.md)

This page describes what is known about the completeness of the recorded data, how gaps and partial days are kept visible, and how the different kinds of "nothing" are told apart. The per-day table is [coverage.csv](../../data/editions/2026-09-15_2026-10-15-r1/coverage.csv) and the figure G08 draws it as a calendar.

## Where coverage information comes from

Coverage comes from the private daily-report archive, read at a pinned commit whose date is `source_snapshot_at` (`analysis/dwr/archive.py`). Only the governance-visibility source is used, and only four of its tables: reports, coverage windows, daily governance counts and per-site counts. No other table is read. A commit that is not a full pinned identifier is refused.

For each day of the window (`edition_id`, `date_utc`), `coverage.csv` records the observation state (`observation_status`), the coverage state (`coverage_status`), the archive state (`archive_status`), the report state (`archive_report_status`), the reason code (`archive_reason_code`), the two archived counts (`aggregate_count`, `v3_count`), their difference (`aggregate_minus_v3`), whether the daily total of the exports and that of the joint aggregate equal the archived aggregate count (`export_matches_archive`, `joint_matches_archive`), the number of snapshots for that date (`snapshots_for_date`), the classifier version (`classifier_version`) and the label of the producer deployment active that day (`producer_deployment_label`).

## Partial reports and reason codes

The archive declares its own reports partial when it cannot attest completeness. A partial report becomes `coverage_status = partial_declared`; it is never upgraded to complete. Partial days still hold requests that were really recorded, and they are kept as they are.

| Reason code | Meaning |
|---|---|
| `COLLECTOR_WINDOW_ATTESTATION_MISSING` | the collector did not attest the coverage window of that day |
| `AGGREGATE_V3_COUNT_MISMATCH` | the two counts kept by the archive for that day, the aggregate count and the V3 count, differ |

Both counts are published (`aggregate_count`, `v3_count`) with their difference (`aggregate_minus_v3`). The gap is reported, not corrected, and neither count is chosen over the other.

## One snapshot per date, never double counted

The archive may hold several snapshots of one date when a report is captured again. Exactly one of them must be marked current: that one is used, the others are listed as superseded and never added. If a date has no current snapshot or more than one, the stage stops (`archive_current_snapshot_ambiguous`) instead of choosing. `snapshots_for_date` shows how many snapshots exist for each date. A date without any report is recorded as `observation_unavailable`, never as zero.

## Coverage in this edition

<!-- dwr:begin coverage -->
30 of 30 days have archived rows; all 30 archive reports are partial (declared), 28 with missing collector window attestation and 2 with a one-request aggregate/V3 gap (2026-10-06, 2026-10-13). Archived aggregate sum 24,815, V3 sum 24,813. Rows on 30 days do not prove complete coverage.
<!-- dwr:end coverage -->

Agreement of the daily totals of the exports and of the joint aggregate with the archived aggregate counts (`export_matches_archive`, `joint_matches_archive`) is not an independent validation: all of them come from the same producer chain. The presence of rows on a day shows that something was recorded, not that everything was.

## Five states that are never confused

| State | How it appears | Meaning |
|---|---|---|
| Measured zero | `request_count = 0`, `observation_status = observed_zero`, in `daily-family-summary.csv` only | the cell is written explicitly: the producer table has no such request for that day, family and role |
| Absent row | no row for a combination in `consultations.csv` or `daily-summary.csv`; for a whole pair, `window_rows_status` in `resources.csv` is `registered_now_no_row_in_window` or `not_in_collector_window_export` | the producer table holds no recorded request for this combination in the window; this is not a measured absence on the web |
| Null | empty cell, with a status column or a metric `status` | the value is not available or not calculable, for example a share whose denominator is zero (`status = not_calculable`) |
| Suppressed | `suppression_status` other than `not_suppressed`, value empty | the value was withheld for privacy; it is never written as zero (no cell is suppressed in this edition) |
| Source unavailable | the stage stops with `source_unavailable`; a graph keeps `status = source_unavailable`; `status.json` keeps the last valid edition | the source could not be read; nothing is published in its place |

An empty table is published with its reason in `catalog.json` (`status = empty_with_reason`, `empty_reason`); no table of this edition is empty. A metric that cannot be computed is null with its status and reason, never zero.

## Producer deployments

`producer_deployment_label` (`pd01`, `pd02` and so on, in order of effective date) names the producer deployment, or the deployments joined by `+`, active at any time during each UTC day, according to the producer's own deployment history, recorded from the Cloudflare control plane and read with the joint aggregate. Labels replace private deployment, version and commit identifiers, which stay in the internal lock. The history is a series of observations: a deployment shorter than the longest gap between two of them cannot be excluded (`producer_deployment_history` in `catalog.json`). The commit identifiers attached to the archived daily reports change during the window without any deployment in that history; they are not deployed versions and are not used. Code that was merely available in a repository is never treated as deployed. The [incidence table](attribution.md) uses these labels.

## Graph snapshot versus deployed bytes

[links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv) is extracted from the site source repositories at pinned commits; `graph_snapshot_at` gives the date for each site. These are source files, not the bytes served to clients during the window. A relation means "this reference is written in this file of this snapshot", with the file and line as evidence. It is not evidence that any client followed it, and an absent relation means "not found in this graph", not absence of any reference elsewhere. No URL found in a snapshot is fetched. Case excerpts are checked verbatim (whitespace-normalized) against the same snapshot files ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r1/case-checks.json)). See [discovery and linking](discovery-and-linking.md).

## Counts that are not re-verified

`GET 200` is the status recorded by the collector. The content type and bytes served are not re-verified, and counters are daily aggregates written by the producer while it runs. The per-day checksums of the joint extraction (`acquire-readonly`), read before and after it, were identical: the counters did not change during the read. They do not turn the extraction into a transactional snapshot.
