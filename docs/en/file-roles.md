# Roles of the documentary files

[Français](../fr/roles-des-fichiers.md) · [Repository home](../../README.md)

The files of the layer do not all play the same role. This page groups them by function, gives examples of file names seen in the three cases, and shows the scope class that each group usually maps to. The names are examples, not required names: each site chose its own, and none of them is a universal standard.

## The class comes from the content, never from the name

Every site-path pair receives exactly one scope class, assigned by the rules of [scope-rules.json](../../config/scope-rules.json) in order of precedence:

| Rule | Applies to | Class assigned |
|---|---|---|
| R01 | `/robots.txt` | `control_resource` |
| R02 | the collector bucket `/.well-known/__undeclared__` (and the producer category `well-known-probe`) | `undeclared_bucket` |
| R03 | sitemaps, `security.txt`, version or build files, measurement configuration | `technical_resource` |
| R04 | content reviewed in the source snapshot; the registry row cites the evidence | `core_governance`, `discovery_index`, `supporting_documentation` or `operational_descriptor` |
| R05 | content not found in the snapshot, or function still ambiguous after review | `unresolved_scope` |

Only a short list of technical or collector paths is classified by rule. Every other file is classified after its content has been read in the source snapshot, never from its extension or its name. The same name can therefore land in different classes:

- `/governance_scope.json` declares what the published rules apply to and what they exclude on pagup.com (`core_governance`); on gautierdorval.com it is an observation scope configuration (`technical_resource`).
- `/.well-known/ai-governance.json` is `discovery_index` on gautierdorval.com and pagup.com, where its main function is orientation; on better-robots.com it declares the role of the site, source precedence and response rules (`core_governance`).
- `/doctrine/ssa-e-a2-dual-web.md` is the Markdown reference of the definition on gautierdorval.com (`core_governance`) and an explanatory, non-contractual description on pagup.com (`supporting_documentation`).
- `humans.txt`, `llms.txt`, `robots.txt` and `security.txt` share an extension and fall in four different classes.

A file can carry several functions; its class follows its main function as reviewed. Each decision is recorded with its rule, review status and justification in [scope-registry.csv](../../config/scope-registry.csv), and published for the edition in [resources.csv](../../data/editions/2026-09-15_2026-10-15-r2/resources.csv). The `family` column of those tables is finer than the groups below.

## Groups and roles

| Group | Function | Example names seen in the cases | Usual class |
|---|---|---|---|
| Identity | States who or what the site is about: names, roles, negations, canonical identifiers | `identity.json`, `humans.txt`, `author.md` | `core_governance` |
| Context | Describes the purpose and nature of the site, organization or product, and how to read it | `site-context.md`, `editorial-context.md`, `plugin-context.md` | `core_governance` |
| Scope and limits | States what is covered, what is excluded and what must not be inferred | `non-goals.md`, `services-non-publics.md`, `negative-definitions.md`, `limitations-context.md`, `.well-known/anti-plausibility.json` | `core_governance` |
| Claims | Lists statements about the subject and separates them by kind (verified, attested, narrative, boundary) | `claims.json`, `canonical-claim-boundaries.json` | `core_governance` |
| Sources and precedence | Says which sources count, in what order, and which one prevails in a conflict | `authority-precedence.json`, `source-precedence.json`, `.well-known/eac-registry.json` | `core_governance` |
| Relations and entity graphs | Declares relations between the entity, the site, its pages and other entities | `entity-graph.jsonld`, `relationships.jsonld`, `entity-relations.md` | `core_governance` |
| Policy | Declares usage preferences and rules for interpreting, summarizing or answering | `ai-usage-policy.md`, `.well-known/interpretation-policy.json`, `response-legitimacy.md`, `output-constraints.md` | `core_governance` |
| Orientation indexes and manifests | Points to other files of the layer, sometimes in a recommended reading order | `llms.txt`, `llms-full.txt`, `dualweb-index.md`, `ai-manifest.json`, `.well-known/ai-governance.json`, `llm-intent-map.json` | `discovery_index` |
| Supporting documentation | Explains methods, protocols, vocabularies, registries or integrity digests related to the layer, without itself stating identity, policy or orientation | `doctrine-glossary.json`, `content-digests.json`, `situational-applicability-layer.json`, `proximity-causality-protocol.md` | `supporting_documentation` |
| Operational descriptors | Describes a service, endpoint, runtime, API, tool, or a server that exposes tools through the Model Context Protocol (MCP) | `.well-known/mcp.json`, `.well-known/ai-plugin.json`, `governed-context-runtime.json` | `operational_descriptor` |
| Control resources | Publishes crawl rules addressed to robots | `robots.txt` | `control_resource` |
| Technical resources | Supports the site technically: sitemaps, security contact, version or build files, measurement configuration | `sitemap.xml`, `.well-known/security.txt`, `version.json` | `technical_resource` |

Two classes are not groups of documents: `undeclared_bucket` is a label of the collector that aggregates requests to undeclared `/.well-known/` names, and `unresolved_scope` marks a registered path whose content was not found or whose function stays ambiguous.

A request to an operational descriptor is a request for the document, never a call to the service it describes. On better-robots.com, for instance, `.well-known/mcp.json` states in the source snapshot that no public MCP server is exposed on the domain. Likewise, `robots.txt` is reported in its own section and never added to the main population.

## Main population and extended layer

- **Main documentary population**: the pairs classified `core_governance` or `discovery_index`. The main result keeps, within it, GET requests with status 200 whose stored tier is `provider_origin_verified_actor`, for the roles `ai_training`, `ai_search` and `user_initiated_fetch`.
- **llms.txt** belongs to the main population and is always reported separately. Isolating it never removes any other resource from the population.
- **Extended documentary layer**: the main population plus `supporting_documentation`. It is a secondary reading, published beside the main result and never merged into it.
- **Outside both**: `operational_descriptor`, `control_resource`, `technical_resource`, `undeclared_bucket` and `unresolved_scope`. Each class kept out of the main population that has requests in the window, `supporting_documentation` included, has its own row in [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r2/exclusions.csv).

The unit is the site-path pair. Mirrors (for example `/ai-governance.json` and `/.well-known/ai-governance.json`), languages and formats (a Markdown file and its JSON or YAML variant) are separate resources. A view by family may group them, without presenting them as independent documents.

The counts per class for this edition are generated below. The difference with the scope of the initial internal report is explained in [scope.md](scope.md).

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
