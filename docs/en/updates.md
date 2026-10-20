# Editions, reviews and updates

[Français](../fr/mises-a-jour.md) · [Repository home](../../README.md)

<!-- dwr:begin edition-state -->
Edition r2: publicly accessible; reference not approved; no independent scientific review documented. r1 remains accessible as a byte-frozen, unapproved historical edition.
<!-- dwr:end edition-state -->

A public repository, passing tests, a technical review and a scientific review are different facts.

## Four distinct states

[config/editions.json](../../config/editions.json) records availability, review progress, reference approval and scientific review separately, outside the immutable payload. r1 became public within the interval recorded in `public_availability_evidence`, bounded by the existing mutation and anonymous readback receipts. A repository creation date or a commit timestamp is not its exact public-availability time.

The old r1 `catalog.json` remains byte-for-byte unchanged, including its historical `candidate_not_reviewed` and null `published_at` fields. Those fields describe the original preparation; they do not deny today's public availability. `approved_release_at` is a separate approval date recorded only in the external edition registry. `revised_at` dates a correction candidate and need not imply publication.

<!-- dwr:begin dates -->
| Date or state | Value |
|---|---|
| Edition | `2026-09-15_2026-10-15-r2` |
| Status | publicly accessible; reference not approved; no independent scientific review documented |
| Availability | `publicly_accessible` |
| Reference approval | `not_approved` |
| Measured period | September 15 to October 14, 2026 inclusive, UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-19` |
| approved_release_at | `null` |
| revised_at | `2026-10-19` |
| latest_available_data_date | `2026-10-14` |
| Updates | periodic update planned; manual preparation (automation not activated) |
<!-- dwr:end dates -->

## Approval without changing the cited catalog

A review receipt in the external edition configuration identifies the edition, reviewer, evidence, review time and separate technical, editorial and distribution decisions. Its `content_digest` is the deterministic SHA-256 of the ordered path-to-SHA-256 manifest of all files under the edition data and figures directories, including PNG fallbacks, excluding only the derived `SHA256SUMS.txt`. Receipts, operational pointers and repository landing pages are outside that payload scope. Their text must not claim a wider approval. This avoids a circular hash; changing a payload byte invalidates the receipt.

The shared `latest_pointer` function checks actual bytes, receipt completeness and public availability, then orders eligible editions by window end and revision. An unapproved superseding candidate cannot hide a valid approved release. [latest.json](../../data/latest.json) remains null because no matching reference-approval receipt exists, even though r1 is public.

## Immutable observations and privacy revision

The original five revision causes remain: late observations, classifier correction, scope change, transformation correction and privacy revision. r2 uses **privacy revision**: protected daily rows and coverage complements are withheld together. Metadata, derived metrics and presentation accompany that change. The [delta report](../../data/editions/2026-09-15_2026-10-15-r2/delta-report.json) states that observations did not change. This is not temporal growth. Reverse links and operational changes live outside the frozen r1 catalog.

Historical payload, figures, schemas and rule bytes are checked by [historical-editions.json](../../config/historical-editions.json). `analyze` and `render --edition ...-r1` check those bytes without rewriting them; projection and preparation into r1 are refused. The [public history inventory](../../config/publication-inventory.json) includes superseded accessible states. An earlier graph presentation differs; its canonical count tables do not. See [privacy](privacy.md) for the limited combined-release contract.

## Manual next-window preparation

Windows run from the 15th included to the next 15th excluded, in UTC. The historical window has 30 days; `[2026-10-15, 2026-11-15)` has 31. Preparation waits 48 hours after close. Calendar tests include February with 28 and 29 days, 30 and 31 days, year boundaries and UTC consolidation. Rolling windows cannot be added.

Run `python -I scripts/dwr.py prepare-next --private-root <existing-private-directory>` after the existing offline normalization and qualification stages have produced the matching window's local inputs. This command selects the **next missing window**, never jumps over it, validates the local inputs, computes provenance and coverage, writes a private candidate, regenerates metrics and all figure variants, prepares the delta and combined-disclosure report, records preparation and distribution separately. A blocked disclosure report remains blocked; a private candidate is not a publishable projection.

The receipt authenticates inputs and outputs. An identical retry returns `unchanged`; changed inputs require a separate revision, and an interrupted partial candidate requires inspection. Missing sources return `source_unavailable`; invalid inputs return `validation_failed`. Neither state advances data freshness or the latest approved reference. The private status file records the actual UTC run time. A synthetic full rehearsal passed; no new real observations were acquired and the real next window is not yet available.

## Planning remains inactive

The Monday 13:17 UTC weekly review and monthly preparation are **inactive templates**, not a service guarantee. Manual offline CI validates existing public files; it does not collect data. [status.json](../../data/status.json) distinguishes code readiness, synthetic execution, real-source availability, planning and approval. Public events in [operations.json](../../config/operations.json) use dates or evidence bounds; a publication annotation does not prove causality.

Catalog schema 2 excludes availability, approval, scientific-review state, publication dates, the superseded-by pointer and planning targets. These mutable facts are read from the edition registry and operational configuration. Updating them and regenerating the presentation does not alter the approved payload digest. The historical r1 catalog keeps its original schema and bytes.

Approval requires matching technical, editorial and distribution decisions in review_status and in the content-bound receipt. The editions page displays effective approval after receipt validation, readable declared decisions and approved_release_at only while that approval is valid. data/status.json derives the candidate state from the same rule; the last successful approval review supersedes the earlier preparation record in its current summary.

The generated edition index separates declared_reference_release_status from the effective reference_release_status after receipt validation.

## Current write and preparation boundary

Every canonical writer uses the same registry admission: historical, publicly accessible, approved or inventoried exposed editions are immutable, even after a registry status downgrade. Unknown or malformed registries fail closed. A new local unapproved edition may be staged under an exclusive lock. Validation precedes installation; caught errors roll back. Two directory renames are not an atomic filesystem transaction: interruption leaves a lock and recovery journal, and readers refuse the edition pending inspection. No force override exists. Public metrics and SVG reproduction compares in a separate temporary directory. PNG reproduction requires `--preview` outside the repository and never replaces public figures.

`prepare-next` separates `preparation_status = complete_private` from `distribution_blocked_pending_contract` and `distribution_blocked_pending_policy_approval`. Neither approves publication. An exclusive preparation lock, staging rename and atomic state replacement prevent concurrent or half-written candidates. A receipt detects changed inputs or output bytes on replay. The cursor `last_processed_window_end_exclusive` is separate from `latest_available_data_date`; `pending_window_start` keeps a candidate pending until an explicit disposition. An unavailable whole window remains pending. Clearing a pending state for a test is not a production promotion.

The inactive `future_projection.prepare_synthetic` contract accepts synthetic fixtures only: main documentary resources, GET 200, `ai_training` or `ai_search`, and `provider_origin_verified_actor`. Every output is derived after that filter, including inventories, metrics and figure data. Rejected-row totals, hashes and coverage margins are excluded. This candidate has no CLI activation. Owner decisions remain separate: treatment of the historical r2 contract, and adoption of a future distribution contract. The historical 245-request selection is not renamed as the 230-request automated subset.

## Historical metadata errata and trust

r1 remains historical, unapproved and accessible. r2 proposes supersession through `supersedes`; `superseded_by` describes approved supersession only, so it remains null. `latest` remains null. No preparation or software correction changes those decisions.

The r2 catalog is kept byte-identical. Its file list omits `disclosure.json` and `delta-report.json`: use its existing `SHA256SUMS.txt` for the complete edition-file integrity list. New catalogs list their direct files and explicitly classify derived files and self-reference exclusions. Do not silently repair an already exposed catalog.

A SHA-256 receipt binds decisions to content and validates structure; it does not cryptographically authenticate a named reviewer. Authority relies on authorized repository writes and review evidence. Software version 0.1.0, policy version 2.0.0, catalog/metrics schemas and public table schemas are separate version spaces.

The historical V3 discrepancy still lacks a source-qualified resolution. Synthetic epoch tests cannot close it. Existing r2 metadata does not attest the classifier epoch or complete coverage; no missing provenance is inferred from current software, labels or timestamps. The availability registry states its own evidence precision, not a guessed first publication instant.
