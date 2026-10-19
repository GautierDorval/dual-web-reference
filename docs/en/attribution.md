# Attribution

[Français](../fr/attribution.md) · [Repository home](../../README.md)

This page explains how requests are attributed to actors, what the stored labels mean, which of them are under review and why. Labels are recorded by the producer, the private collector (a Cloudflare Worker), with classifier version 2026-08-24.1. This repository keeps them as recorded and adds a separate assessment, whose rules are in [config/attribution-rules.json](../../config/attribution-rules.json).

## Four independent dimensions

1. **Actor role** (`actor_role`): the function recorded by the producer, among `ai_training`, `ai_search`, `user_initiated_fetch`, `search_indexing`, `seo_tool`, `generic_automation` and `unknown`.
2. **Identification quality**: the stored tier (`stored_identity_tier`), plus a separate assessment of that tier (`attribution_assessment`).
3. **Initiation provenance** (`initiation_provenance`, `initiation_evidence_status`): who triggered the request. In this edition it is `unknown` and `not_established` everywhere.
4. **Coverage and availability** (`coverage_status`, `observation_status`): see [quality and coverage](quality-and-coverage.md).

No dimension replaces another. A request whose provider origin matched an official registry may have been triggered by the site operator. A monitoring robot can be legitimate without being an AI actor. A partial day can hold requests that were really recorded.

## Stored tier and assessment

| `stored_identity_tier` | `attribution_assessment` | Uses the predicate under review | Main population |
|---|---|---|---|
| `provider_origin_verified_actor` | `registry_match_not_affected_by_predicate` | no | eligible |
| `spoofed_or_failed_verification` | `registry_mismatch_not_affected_by_predicate` | no | no |
| `network_verified_claimed_actor` | `recorded_classification_reliability_under_review` | yes | no |
| `cloudflare_verified_unattributed` | `recorded_classification_reliability_under_review` | yes | no |
| `claimed_actor_unverified` | `unverified_claim` | no | no |
| `unknown_automation` | `unverified_unknown` | no | no |
| `synthetic_probe` | `synthetic_marker` | no | no |
| `cryptographically_verified_actor` | `not_observed_in_covered_versions` | no | no |

The stored tier is never overwritten, redated or redistributed. The assessment is an interpretation with its own method, written next to the tier in `consultations.csv` and `actor-summary.csv`. The label "Recorded classification, reliability under review" means exactly that: the producer recorded this tier, and its reliability is being examined.

## The predicate under review

The producer decides whether Cloudflare verified a client with this predicate:

```js
cloudflareVerified(cf) = cf?.botManagement?.verifiedBot === true || cf?.verifiedBotCategory != null
```

In JavaScript, `"" != null` is true, so an empty category string satisfies the predicate even when `verifiedBot` is explicitly `false`. The defect was reproduced in the producer's real test module with the input `{botManagement: {verifiedBot: false}, verifiedBotCategory: ""}`: an undeclared client, and even a browser user agent, receive `cloudflare_verified_unattributed`; a declared actor without registry evidence (for example `ClaudeBot`) receives `network_verified_claimed_actor`.

## Reproduction is not production incidence

The reproduction shows what the code does with that input. It does not show that an empty category was received in production, nor that it explains the traffic recorded as unattributed. The two questions are kept apart. What can be established about production is limited to the deployments recorded in the producer's own deployment history and to their code:

<!-- dwr:begin incidence -->
| Producer deployment (label) | Effective | Measured days covered | Source code available | Deployment established by | Classifier | Predicate `verifiedBotCategory != null` | Signals kept | Defect applies to | Re-evaluation possible |
|---|---|---|---|---|---|---|---|---|---|
| pd01 | 2026-09-13T17:18:49Z, 100% | 2026-09-15 to 2026-10-14 | yes (private repository) | producer deployment history, 127 observations, longest gap 11.5 h | 2026-08-24.1 | present (same file blob) | stored tier and role only; no raw Cloudflare signal | `cloudflare_verified_unattributed`, `network_verified_claimed_actor` | no for these two levels; the provider-origin level does not use the predicate |

Deployment labels replace private identifiers, which are kept in the internal lock. The commit identifiers attached to the archived daily reports change during the window without any deployment in this history; they are not treated as deployed versions. Reproducing the defect locally does not show that an empty category was received in production, nor that it explains the unattributed traffic.
<!-- dwr:end incidence -->

The deployment history is recorded by the producer from the Cloudflare control plane and was read with the joint aggregate (`producer_deployment_history` in `catalog.json`: number of observations, first and last observation, longest gap). It shows which deployment was active on each day of the window; the classifier file of the version it serves is the same file version that carries the predicate, which was introduced on 2026-08-24 and has not changed since. A deployment shorter than the longest gap between two observations cannot be excluded. The commit identifiers attached to the archived daily reports are not deployed versions and are not used to establish incidence.

One observation is compatible with the defect without proving it: in this window, no request is recorded as `unknown_automation` or `claimed_actor_unverified` (see [actor-summary.csv](../../data/editions/2026-09-15_2026-10-15-r2/actor-summary.csv)).

## Why the two dependent levels cannot be re-evaluated

The collector does not store raw Cloudflare signals: only the tier, the role and rule identifiers. The value of `verifiedBot` or of the category received for a past request is therefore unknown, and the two levels that depend on the predicate cannot be recomputed after the fact. They keep their stored labels, with `attribution_assessment = recorded_classification_reliability_under_review`. Nothing is moved between monitoring, AI, browser or false positive. They are left out of the main stratum and published separately in [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r2/exclusions.csv) and `actor-summary.csv`.

## The provider-origin branch

`provider_origin_verified_actor` is decided before any use of the predicate. It requires a declared actor with an official registry source (OpenAI `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`; Perplexity `PerplexityBot`, `Perplexity-User`; `Googlebot`; `Applebot`) and a match of the request IP (`CF-Connecting-IP`) with the official IP ranges of a fresh registry snapshot (24-hour lifetime, refreshed every 6 hours). This branch is therefore not affected by the defect. Anthropic actors have no such registry and can never reach this tier.

This is a separation of code paths, not an audit of the whole chain. The correctness of the provider registries, the provenance of the IP header in Worker-to-Worker cases and the deployment metadata are not audited end to end. The main result is qualified accordingly: provider origin recorded as verified by an official IP-range match.

## The Cloudflare contract

Cloudflare documentation consulted on 2026-10-16:

- [Bot Management variables](https://developers.cloudflare.com/bots/reference/bot-management-variables/) (last updated 2026-09-16) defines `cf.bot_management.verified_bot` as a boolean and `cf.verified_bot_category` as a string used to segment verified bot traffic by type and purpose. It does not document the value for a request that is not a verified bot: empty string, null or absent.
- [Verified bots](https://developers.cloudflare.com/bots/concepts/bot/verified-bots/) (last updated 2026-10-08) lists 17 legacy category strings: Academic Research, Accessibility, Advertising & Marketing, Aggregator, AI Assistant, AI Crawler, AI Search, Archiver, Feed Fetcher, Monitoring & Analytics, Page Preview, Search Engine Crawler, Search Engine Optimization, Security, Social Media Marketing, Webhooks, Other. A category describes a type and a purpose, never the operator.
- [Workers Request](https://developers.cloudflare.com/workers/runtime-apis/request/) (last updated 2026-07-02) does not list `verifiedBotCategory` among the properties of `request.cf`, and the type package `@cloudflare/workers-types` 5.20261016.1 does not declare it.

## Correction prepared after the measurement window

At the data extraction on 2026-10-16, a corrective candidate had been prepared locally in a separate branch of the producer; it had not yet been pushed or deployed. The rule is closed: a strict boolean `true` verifies; an explicit `false` or a malformed value fails closed, even next to a category; otherwise only an exact match with one of the 17 legacy categories, pinned on 2026-10-16, verifies, and an unknown value never improves attribution. The proposed classifier version was 2026-10-16.1, with historical labels left untouched. This paragraph records the preparation state on 2026-10-16, not the current deployment state. Any later deployment and its collection follow-up belong to a subsequent measurement epoch; no number or historical label of this edition changes.

## Provenance, sensitivity and unknown traffic

- Initiation provenance is never inferred from the role, the provider or the tier. A provider-origin request may have been triggered by the site operator.
- The count without user-initiated fetches (`main.sensitivity.without_user_fetch.get200`, exact in this edition) is a sensitivity analysis. It is not evidence that the remaining requests are independent of any person.
- Unknown or unattributed traffic is never attributed to the operator for lack of another explanation, and never called verified AI. A coincidence of timing is a clue, not a match between requests.
