# Privacy and combined releases

[Français](../fr/confidentialite.md) · [Repository home](../../README.md)

The [current policy](../../config/small-cell-policy.json) is **version 2.0.0**; its distribution review is recorded in the external edition registry. It describes tested aggregate protections, not universal anonymity or an assurance that no information can be inferred. r1 and its [original rules](../../config/history/2026-09-15_2026-10-15-r1/small-cell-policy.json) remain immutable historical evidence.

## What changed

The former threshold of ten protected paths across an edition did not prove that daily cells could not be reconstructed. Two synthetic tests exercise the actual historical function: one active day can date ten monthly cells; differencing two revisions can locate one added path/day cell. The new gate refuses these combinations. They demonstrate control defects, not a real disclosure or identification of a person in r1. Its documentary protected groups span the full window, rather than the single-day shape of the first example. No withdrawal is initiated on that basis.

The old prose also overstated the absence of user-initiated fetches from daily output. In r1 they were **included inside the combined protected daily group**, without a separate role, even though G01 and the automated daily metrics excluded them. Named software agents at edition level had already been approved by the owner on 2026-10-17; they were not awaiting that same approval.

## Current distribution contract

| Surface | Current rule |
|---|---|
| Edition resource/actor cells and recurrence summaries | r2 repeats the same inventoried historical cells. New or revised fine protected observations are blocked pending a separately assessed coarser contract. |
| Protected daily rows | Withheld, including user-initiated, unattributed, unverified, failed-verification and network-claimed strata. A stored network label whose predicate is under review cannot exclude a browser. |
| Daily coverage totals and differences | Withheld together, since subtracting non-protected traffic can recover a protected total. Empty cells mean withheld, never measured zero. |
| Automated provider-origin daily and family cells | Retained from exact joint aggregates; no redistribution of monthly counts. |
| Prior accessible editions, including superseded revisions | Included in the publication inventory. A changed or missing inventory blocks fine diffusion as `not_assessed`. |
| Derived metrics, figures, alternatives, cases and downloads | Generated from those canonical tables and verified against them. New independent output surfaces require assessment. |

The [combined-release report](../../data/editions/2026-09-15_2026-10-15-r2/disclosure.json) records the decision and residual limits. The control cannot erase already public r1 margins or account for every unknown third-party source. A single automated actor can be inferred from a role, and a single-resource family can reveal that automated resource's daily count. Those are software-agent aggregate inferences, distinct from identification of a person. Historical exceptions for `robots_control` and probe buckets were release decisions, not anonymizing properties of the paths.

## Structural minimization and evidence

Public projections have no request IP, raw or hashed user-agent string, cookie/session/device identifier, secret, free referrer, query string, conversation transcript or per-path first/last timestamp. Unknown traffic is not relabelled as owner activity. No new retention period or retrospective collection is authorized.

The publication gate checks configured private terms and identifiers as well as known unsafe representations. Private exports and source snapshots stay outside this repository. Public hashes establish byte identity, not the truth of collection, and synthetic privacy tests are not evidence of an actual personal disclosure. Report a concern through [the approved private channel](../../SECURITY.md).

<!-- dwr:begin history-inventory -->
The inventory describes 8 named historical states, not 8 commits. Declared bytes are checked locally; completeness of Git references requires separate evidence. Unknown third-party copies and auxiliary data remain outside that evidence.
<!-- dwr:end history-inventory -->

The combined gate reconciles resource request totals but cannot independently reconstruct per-resource active-day counts from edition-level cells. For repeated historical protected output, those day-count bytes must match the inventoried release. For a new private preparation, validate_inputs checks the complete per-resource counts, including day counts, against the real joint source. An arbitrary standalone synthetic projection is not that source-backed preparation.
