# Privacy

[Français](../fr/confidentialite.md) · [Repository home](../../README.md)

This page explains what the public files never contain, at which grains counts are published, and why no published value needs to be suppressed. The policy is [config/small-cell-policy.json](../../config/small-cell-policy.json). It was fixed before any result was computed (`fixed_before_results = true`) and applies to every edition table, figure, README, document, case page, the static site and future editions with their deltas. It was amended once afterwards, only to tighten it (`small-cell-policy/1.1.0`, see [amendment](#amendment-of-2026-10-16)). The owner validated it on 2026-10-17, amendment included (`status: validated_by_owner`).

## Structural exclusions

The public repository never contains:

- request IP addresses;
- user-agent strings, raw or hashed;
- cookie, session or device identifiers;
- tokens or credentials;
- free-form referrers;
- query strings;
- conversation transcripts;
- per-cell first-seen and last-seen timestamps;
- per-path first and last access dates.

These fields are excluded by construction: the public projection has no column for them. The exports' per-path first and last dates, for example, are only checked to fall inside the window and are then dropped.

## Allowed grains

| Grain | Time | Dimensions | Strata | Files |
|---|---|---|---|---|
| `edition_resource_actor` | edition | site, path, method, status, actor family, actor name, role, stored tier, assessment | all | `consultations.csv`, `resource-summary.csv`, `actor-summary.csv` |
| `daily_site_population` | day | site, population, role, stored tier, method, status | non-protected strata in full detail; protected strata combined into one group per day, site and population | `daily-summary.csv` |
| `daily_family_automated_main` | day | family, role | main population, provider-origin tier, roles `ai_training` and `ai_search` only | `daily-family-summary.csv` |

Forbidden combinations: day × path, day × actor name, day × role, stored tier, method or status for any protected stratum, day × family for any protected stratum, and `user_initiated_fetch` in any daily series, figure or metric. Day-level outputs therefore never carry a path or an actor name: these appear only at edition level. A heat map by day and family is allowed only for automated provider-origin roles; in this edition it is the figure G06, drawn from `daily-family-summary.csv` ([methodology](methodology.md)).

## Protected strata

Some strata may contain requests initiated by a person: user-initiated fetches (`user_initiated_fetch`), and unattributed, unverified or failed-verification clients whose stored label cannot exclude a browser (`cloudflare_verified_unattributed`, `unknown_automation`, `claimed_actor_unverified`, `spoofed_or_failed_verification`). At the day grain, all their requests are counted in a single row per day, site and population, whose `actor_role` and `stored_identity_tier` are `protected_strata` and whose `http_method` and `http_status` are `ANY`. They never appear in a daily family view, and user-initiated fetches appear in no daily series, figure or metric: they are counted for the edition only. Naming a software agent family, such as a crawler, does not identify an individual visitor; publication of such names at edition level still awaits the owner's confirmation (see below).

## Why no suppression is needed

At the allowed grains, no cell can isolate a person: day-level tables carry neither path nor actor name, protected strata are combined per day into groups that span many paths, and edition-level tables cover a whole window. The policy therefore sets `numeric_suppression = none_required_at_the_allowed_grains`, with a minimum published count of 1. Since no value is suppressed, complementary suppression does not apply (`not_applicable_because_no_value_is_suppressed`), and every published cell has `suppression_status = not_suppressed`.

## Crossing and differencing

Every published table is a marginal of one of the three grains above, but a marginal can still isolate a cell when it is crossed with another one. If a daily stratum covers a single path at the edition grain, its daily series is path-level: reading `daily-summary.csv` next to `consultations.csv` then gives the day of each request to that path. This is why protected strata are published per day only as the combined group described above, and why user-initiated fetches stay out of every daily output, including the figure G01 and the `main.daily` metrics.

Two checks of `verify` hold this in place: `protected_strata_combined_in_daily_outputs` (no daily row carries a protected role or tier outside the combined group) and `no_daily_group_isolates_a_protected_path` (outside the accepted single-path populations, each combined group spans at least `minimum_paths` paths with protected requests at the edition grain; the policy sets 10). If a future edition fails the second check, verify fails and a coarser grouping must be chosen before any publication. Subtracting tables, combining filters, or comparing two editions or revisions then yields, for protected strata, nothing finer than day × site × population. There is also no suppressed value to recover.

## Accepted residual cases

The policy lists four cases that are accepted as they are:

- the `robots_control` population is made of `/robots.txt` alone, so its daily counts, including the combined protected group, are path-level. It is a public crawler-control file outside the main population;
- the `undeclared_bucket` population is one collector bucket per site (`/.well-known/__undeclared__`), so its daily counts are bucket-level. The bucket is not a document and aggregates requests to many undeclared names;
- a non-protected automated stratum (a named software agent with a provider-origin or network-verified stored tier, in a role other than `user_initiated_fetch`) whose edition cells cover a single path makes its daily row path-level for that software agent. No protected stratum is involved;
- a documentary family that contains a single path on all sites makes a cell of `daily-family-summary.csv` path-level, for automated provider-origin crawlers only. No protected stratum is involved.

## Amendment of 2026-10-16

A crossing check run on the candidate edition, before any publication, found three protected daily strata whose edition cells covered a single path, so the day of those requests to that path could be recovered by crossing `daily-summary.csv` with `consultations.csv`. One of them was a single user-initiated fetch. The policy was tightened in version `small-cell-policy/1.1.0`: protected strata combined in the daily grain, `spoofed_or_failed_verification` added to the protected tiers as their definition requires, user-initiated fetches removed from daily series, the undeclared bucket and non-protected single-path strata listed as accepted residual cases, and the differencing argument corrected. No edition-level count changed: the main result, the split by role and the scope delta are the same. Daily views now count automated roles only. The amendment is recorded in the policy file (`amendments`); the owner validated the policy, amendment included, on 2026-10-17.

## Owner decisions

- Validated on 2026-10-17: this policy, including its amendment and its accepted residual cases.
- Validated on 2026-10-17: named software-agent families (for example `GPTBot`) are published as actor names at edition level only; day-level outputs never carry an actor name.

The edition remains an unpublished candidate until its publication ([updates](updates.md)).

## Unknown traffic is never imputed

Traffic recorded as unknown or unattributed never becomes operator traffic for lack of another explanation. A coincidence between a time of day and a known activity is a clue, not a match between requests, and no conversation history is exported to settle such a question. See [attribution](attribution.md).

## Retention and private material

- No retention period is extended and no data intended to be purged is saved. The edition reuses exports and daily aggregates already kept by the producer, under the retention already authorized; any change would be a separate decision.
- Private material (exports, raw results of the joint extraction, archive reads, source snapshots, the internal lock) lives in a private workspace outside the repository root. The private stages refuse a workspace located inside the repository (`private_root_inside_public_repository`), and `.gitignore` patterns are only a second line of defence.
- Public files carry labels instead of private identifiers: producer deployment labels instead of deployment, version and commit identifiers, and a digest of the internal lock (`private_lock_sha256` in `catalog.json`) instead of its content.
