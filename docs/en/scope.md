# Scope

[Français](../fr/perimetre.md) · [Repository home](../../README.md)

This page explains which files belong to the main documentary population, which are reported separately, and how the difference with the initial internal report is itemized. The rules are in [config/scope-rules.json](../../config/scope-rules.json) and the decisions in [config/scope-registry.csv](../../config/scope-registry.csv). For the role of each kind of file, see [file roles](file-roles.md).

## The registry

`config/scope-registry.csv` has one row per site-path pair examined: every path recorded by the collector in the window, every path registered by the producer without rows in the window, and the few paths examined in the source snapshots that the export does not carry (`window_rows_status = not_in_collector_window_export` in `resources.csv`). Its columns are `site_id`, `path`, `scope_class`, `scope_rule_id`, `family`, `format`, `language`, `role_en`, `role_fr`, `declares_canonical_source`, `mentions_runtime_or_mcp`, `found_in_snapshot`, `review_status` and `justification`.

The registry is built by `scripts/build_scope_registry.py` from content reviews of the site source snapshots, then kept and reviewed as a public, versioned file. `qualify` reads only the registry, never the review notes. It stops when a collector path has no registry entry (`missing_registry_entry: fail`), when a class or rule is unknown, when `/robots.txt` is not `control_resource`, or when `/.well-known/__undeclared__` is not `undeclared_bucket`.

## Classes

| Class | Main population | Function |
|---|---|---|
| `core_governance` | yes | states identity, context, scope, sources, claims, relations, policy, priorities or interpretation limits |
| `discovery_index` | yes | mainly orients toward other governance resources, for example `llms.txt` or an index of documents |
| `supporting_documentation` | no (extended layer) | explanatory, method, protocol or reference material that does not itself state identity, policy or orientation |
| `operational_descriptor` | no | static file describing a service, endpoint, runtime, MCP server, API or tool |
| `control_resource` | no | crawler-control file such as `robots.txt` |
| `technical_resource` | no | sitemap, `security.txt`, version or build file, measurement configuration |
| `undeclared_bucket` | no | collector bucket for requests to undeclared well-known names; not a document |
| `unresolved_scope` | no | content not found in the examined snapshot, or function ambiguous |

`technical_resource` was added to the initial list of classes, so that a sitemap or a version file is never counted as a governance file merely because a registry lists it.

## Rules and precedence

| Rule | Applies to | Assigns | Precedence |
|---|---|---|---|
| R01 | `path == /robots.txt` | `control_resource` | 1 |
| R02 | `/.well-known/__undeclared__` or producer category `well-known-probe` | `undeclared_bucket` | 2 |
| R03 | sitemap XML, `security.txt`, version or build file, measurement configuration | `technical_resource` | 3 |
| R04 | content reviewed in the source snapshot, evidence cited in `justification` | one of `core_governance`, `discovery_index`, `supporting_documentation`, `operational_descriptor` | 4 |
| R05 | content not found in the snapshot, or function still ambiguous after review | `unresolved_scope` | 5 |

The first applicable rule wins. R01, R02 and the R03 path pattern (sitemaps, `security.txt`, version and build files) are mechanical: they override any content proposal and apply even when the file is absent from the snapshot. R03 also applies when the content review found a technical file. R04 keeps the class chosen from the content. R05 applies when no content could be read or the function stays ambiguous.

## Review status

`review_status` takes three values: `rule_based` (class set by a mechanical rule: R01, R02 or the R03 path pattern), `content_reviewed_in_snapshot` (R04) and `content_not_found` (the other entries, R05 in particular). Whether the file itself was found is recorded separately in `found_in_snapshot`; read the two columns together.

## llms.txt is isolated, not excluded

`/llms.txt` belongs to the main population (class `discovery_index`) and is always reported separately (`llms_txt = true` in `resources.csv`, metrics `main.llms_get200` and `main.other_*`). Isolating it never removes the other resources. It is one possible orientation resource among others, not a protocol that every client must read first; see [llms.txt studies](llms-txt-studies.md) and [discovery and linking](discovery-and-linking.md).

## Operational descriptors

Files that describe a runtime, an MCP server, an API or a service are classed `operational_descriptor` and stay outside the main population. A request to such a file is a request for a document. It is never a call to the service described, and it says nothing about any use of that service. The column `mentions_runtime_or_mcp` is a separate flag: a governance file may mention a runtime and still be classed by its own function.

## Mirrors and language versions

A resource is a site-path pair. A file served at `/.well-known/name` and at `/name`, a French and an English version, or the same content in two formats are separate pairs, counted separately. The column `snapshot_sha256` of [resources.csv](../../data/editions/2026-09-15_2026-10-15-r1/resources.csv) gives the digest of each file in its source snapshot, so byte-identical mirrors can be recognized without merging their counts. A family view may group them later under its own name and method, without presenting them as independent documents.

## Historical version status

The registry is built from source snapshots, one per site, dated `graph_snapshot_at`: single points in time, not the whole window. The version of each file actually served during the window is not established, so every resource carries `historical_version_status = unknown`. A file present in today's snapshot is not thereby shown to have existed in September, and a relation found in the snapshot is not thereby shown to have existed during the window.

## Scope delta

<!-- dwr:begin scope-delta -->
| Scope class | Site-path pairs with rows | All requests | Provider-origin AI GET 200 |
|---|---:|---:|---:|
| `control_resource` | 1 | 4,167 | 419 |
| `operational_descriptor` | 14 | 617 | 12 |
| `supporting_documentation` | 99 | 4,589 | 111 |
| `technical_resource` | 4 | 201 | 4 |
| `undeclared_bucket` | 3 | 1,061 | 1 |

Main documentary population: 245 requests on 174 pairs. Initial report scope: 372 on 259. Removed by the scope review: 127. Extended layer with supporting documentation (secondary reading): 356 on 247 pairs. robots.txt and the undeclared bucket were already outside the initial report scope.
<!-- dwr:end scope-delta -->

How to read this block. Each row is a scope class outside the main population, with the site-path pairs that have rows in the window, all requests for every actor, and the provider-origin AI `GET 200` (the same stratum as the main result). The summary line compares the main population with the initial report scope: the requests "removed by the scope review" are the provider-origin AI `GET 200` of the initial report scope that fall in `supporting_documentation`, `operational_descriptor`, `technical_resource` or `unresolved_scope`. The `control_resource` and `undeclared_bucket` rows were already outside the initial report scope; they are shown for completeness, not as part of the delta. The source table is [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r1/exclusions.csv), which also lists the identification levels left out of the main stratum ([attribution](attribution.md)).

## The extended layer

The extended documentary layer adds `supporting_documentation` to the main population (`extended.get200`, `extended.site_path_pairs`). It is published as a secondary reading because method and protocol pages relate to the layer without stating identity, policy or orientation themselves. It never replaces the main result.

## Rules fixed before results

The scope classes, the rules R01 to R05 and their precedence were written and committed before any count of this edition was computed. The path-by-path registry was built afterwards from content reviews of the snapshots, independently of traffic volumes; the wording of R03 was then clarified to name the content-review case it was applied to, without changing any class. A later change of scope creates a new revision with its cause recorded as a scope change ([updates](updates.md)); it is never applied silently to a published edition.
