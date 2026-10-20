# Glossary

[Français](../fr/glossaire.md) · [Repository home](../../README.md)

Plain-language definitions of the labels, codes and acronyms that appear in the tables and pages. Labels in `code` format are kept exactly as stored: they are identifiers, not translations.

## Units and time

- **Site-path pair**: one path on one site, for example pagup.com with `/llms.txt`. It is the unit of every distinct count. It counts URLs, never consumers, and distinct counts per actor are never added together.
- **Edition**: a frozen set of public tables for one window, identified as `<start>_<end>-r<n>`, for example `2026-09-15_2026-10-15-r1`. Candidate status means reference approval is pending; it does not determine public availability. Current availability and approval are recorded in `config/editions.json`, outside each frozen catalog.
- **Revision**: the `r<n>` suffix. A correction creates a new revision (`r2`) with its reason, numeric delta, author, reviewer and a link to the previous revision; the earlier revision is never edited ([updates.md](updates.md)).
- **Window**: the measured period of an edition. Monthly reference windows start on the 15th, in UTC.
- **Exclusive end**: the end date is not included. The window `[2026-09-15, 2026-10-15)` covers September 15 to October 14 inclusive, that is 30 days; the next one, `[2026-10-15, 2026-11-15)`, has 31 days.

## HTTP methods and statuses

- **GET 200**: a GET request answered with status 200 (success), as recorded by the collector. The bytes served are not verified again. It is the counting status of the main result.
- **HEAD**: a request identical to GET except that the response carries no body (RFC 9110). It is not a document read.
- **304 (Not Modified)**: the answer to a conditional request when the copy held by the client is still current; it carries no body.
- **405 (Method Not Allowed)**: the method is known but not supported for this resource. In the initial report scope of this edition, the joint aggregate records every error as a POST request answered with 405.
- **301, 404, 5xx**: redirection, not found, server error. None of them is a successful document body.

## Stored identification tiers

The private collector stores one tier per request (classifier version 2026-08-24.1). This repository keeps it as recorded; see [attribution.md](attribution.md).

- `provider_origin_verified_actor`: a declared actor whose provider publishes an official registry (GPTBot, OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, Googlebot, Applebot), and whose request address matched that provider's official IP ranges. This branch does not use the Cloudflare predicate under review. It qualifies the origin of the request, not the whole chain. Anthropic actors have no such registry in the collector and cannot reach this tier.
- `network_verified_claimed_actor`: a declared actor name (for example ClaudeBot) without an official registry match, accepted by the network-verification predicate under review.
- `cloudflare_verified_unattributed`: no provider identity; the label also depends on the predicate under review, which can let through clients that are not bots at all.
- `spoofed_or_failed_verification`: a declared provider name whose request origin did not match the official registry.
- `claimed_actor_unverified`: a declared name only, without verification.
- `unknown_automation`: no identification.
- `synthetic_probe`: a signed synthetic control request sent by the collector itself.
- `cryptographically_verified_actor`: defined by the producer contract; not produced by classifier 2026-08-24.1.

**Predicate under review**: the test that the collector uses to treat a request as verified by Cloudflare. It passes when the verified-bot flag is true, or when the verified-bot category field is anything other than null or absent; an empty string passes too.

## attribution_assessment

A separate interpretation made by this repository ([attribution-rules.json](../../config/attribution-rules.json)); it never overwrites the stored tier.

- `registry_match_not_affected_by_predicate`: origin matched an official registry; the predicate under review is not used.
- `registry_mismatch_not_affected_by_predicate`: origin did not match the registry of the declared provider.
- `recorded_classification_reliability_under_review`: “Recorded classification, reliability under review”. The label depends on the predicate under review; it is kept and never redistributed.
- `unverified_claim`: a declared name without verification.
- `unverified_unknown`: no identification.
- `synthetic_marker`: a control request of the collector.
- `not_observed_in_covered_versions`: a tier that the covered classifier versions do not produce.

## Actor roles

Recorded by the producer from the declared actor name. A role describes the declared client, never who initiated a request.

- `ai_training`: a crawler declared as collecting content for model training (for example GPTBot).
- `ai_search`: a crawler for an AI search or answer service (for example OAI-SearchBot, PerplexityBot).
- `user_initiated_fetch`: a fetch made by an assistant for a request from a user (for example ChatGPT-User, Perplexity-User).
- `search_indexing`: a search engine crawler (for example Googlebot, Bingbot, Applebot).
- `seo_tool`: an SEO crawler (for example AhrefsBot, SemrushBot).
- `generic_automation`: other declared automation.
- `unknown`: no recorded role.

The main result keeps the first three roles.

## Scope classes

`core_governance`, `discovery_index`, `supporting_documentation`, `operational_descriptor`, `control_resource`, `technical_resource`, `undeclared_bucket` and `unresolved_scope` are defined, with examples, in [file-roles.md](file-roles.md) and [scope.md](scope.md).

## Table conventions

- `coverage_status` = `partial_declared`: the producer archive declares the report of the day partial; rows exist, but completeness is not attested ([quality-and-coverage.md](quality-and-coverage.md)).
- `observed`: the cell is recorded with a count above zero. `observed_zero`: an explicit zero, written only in `daily-family-summary.csv`, for a day, family and role without any such request in the producer table; under partial coverage, this is not proof of absence. An empty cell (null) means not available or not calculable, never zero.
- Absent row: in the frozen r1 tables, no row indicates no recorded request at the specified grain. In r2 daily tables, protected rows are withheld: their absence never means zero.
- `protected_strata`, with `http_method` and `http_status` = `ANY`: in frozen r1 `daily-summary.csv`, the single daily row per site and population that combines every request of the protected strata, whatever their role, stored tier, method or status ([privacy.md](privacy.md)).
- `cell_derivation` = `joint_exact`: the cell is an exact sum of rows of the joint aggregate ([methodology.md](methodology.md)).
- `initiation_provenance` = `unknown`, `initiation_evidence_status` = `not_established`: who triggered the request is not established.
- `source_mode` = `joint_acquisition`: the edition was built from a bounded read-only extraction of the producer's joint aggregate (day, site, path, method, status, actor and tier crossed together), checked against the exports of the internal report.
- `other_share`: GET 200 requests to files other than llms.txt divided by all GET 200 requests of the same selection; not an adoption rate.

## Layers named by the sites

Several file names and roles in the cases use the vocabulary of the author's framework. This repository does not need these terms to count accesses. They are explained by function, as stated in the canonical definition, the site files and the roles of the registry; where the letters of an acronym are not spelled out there, this is said.

- **SSA-E**: according to the canonical definition, the semantic stabilization layer for entities and relations (definitions, perimeters, hierarchies, coherence).
- **A2**: according to the same definition, a sub-layer of targeted interpretive constraints for pages or zones at high risk of drift.
- **Dual Web**: the dual reading layer described in [model.md](model.md).
- **Q-Layer**: according to the same definition, a response legitimacy layer: when an answer is authorized, must be clarified, suspended or not produced (`response-legitimacy.md`). The meaning of the letter Q is not stated there.
- **EAC**: named External Authority Control in the site files; declares which external sources are admissible, for which claim families, under which proof requirements and output ceilings (`eac-registry.json`, `eac-claims.json`).
- **CCL**: named Causal Context Layer in the site files; describes the situations that trigger a need, the latent need, the intended outcomes and the derivations to avoid (`causal-context-map.json`).
- **SAL**: named Situational Applicability Layer in the site files; states when a capability applies and when it does not, with the evidence required (`situational-applicability-map.json`).
- **CPI**: described in the site files as an interpretive weighting layer: sources weighted by claim class and authority scope (`interpretive-weighting-policy.json`). The expansion of the letters is not established here.
- **CAI**: described in the site files as an attested integrity layer: digests of selected canonical statements, and what those digests do not prove (`attested-interpretive-units.json`, `content-digests.json`). The expansion of the letters is not established here.
- **MCP**: the Model Context Protocol, through which a server exposes tools or context; a file that describes such a server is an operational descriptor.
- **`/.well-known/`**: a path prefix reserved for site-wide metadata files (RFC 8615).


## Epochs and coverage states

`classifier_version` identifies the classifier; `measurement_epoch_id` identifies an attested measurement segment. Several fully resolved segments mean `multiple_epochs_resolved`, not `mixed_epoch_unresolved`. The latter means an inseparable mixture; `unknown` means missing evidence. Future schema 2 carries the epoch in daily, actor and family keys. Coverage is one of `complete_declared`, `partial_declared`, `coverage_unknown` or `observation_unavailable`; an edition may summarize heterogeneous days as `mixed_coverage`. Completeness and epoch resolution are independent.

Historical classifier scalars are adapted to a singleton list with the raw value and transformation retained. No prefix is stripped to guess a classifier. Future resource summaries use unions of resources and days across epochs, not sums of distinct counts.

`epoch_resolution` describes segment resolution: `single_epoch_resolved` for one attested segment, `multiple_epochs_resolved` for several attested separable segments, `mixed_epoch_unresolved` for an inseparable mixture, and `unknown` for insufficient evidence. It is not a classifier version. In schema 2, `classifier_versions` contains recorded versions only; `unknown` and `mixed_epoch_unresolved` markers are excluded. States remain in `measurement_epoch_id` and `epoch_resolution`.

In version 2 CSVs, `classifier_versions` and `measurement_epochs` are strings containing a JSON array of sorted unique strings, encoded using CSV quoting rules. `[]` means no recorded value; it is neither a version nor evidence of comparability. Historical scalars preserve their bytes and separate adaptation.
