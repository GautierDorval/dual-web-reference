# Case: better-robots.com

[Français](README.fr.md) · [Repository home](../../README.md)

> Edition `2026-09-15_2026-10-15-r2` · September 15 to October 14, 2026 inclusive, UTC · graph snapshot `2026-10-06` · local candidate; reference not approved

**90 documentary URLs; 122 provider-origin AI GET 200 on this site.** Partial coverage; one of three cases in the same author's ecosystem, not an independent replication.

## Question and scope

Context of a product, declared capabilities, limits, and the difference between publishing a rule and how a robot actually behaves.

## Concrete question

According to better-robots.com’s own governance files, what does the Better Robots.txt plugin let a site owner publish, and what may a reader not conclude, from a published rule alone, about how a given crawler actually behaves?

## Starting page

`/governance/ai-usage-policy` (counterpart `/fr/governance/ai-usage-policy`). The home page links to it; its level-3 section links the product-context and limits files.

## Available documentary path

Each step is a reference written in a file of the source snapshot, verified in [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv). It shows what a reader can follow; it is not an observed robot path.

Copyable paths only. A manually visited online resource may differ from the dated snapshot; full private snapshot bytes are not distributed.

## Read by function

- `/plugin-context.md` : Product context: what the plugin is for and what it does not guarantee.
- `/plugin-scope.md` : Declared in-scope and out-of-scope capabilities, and the boundary between the plugin and the /check audit.
- `/limitations-context.md` : Public limits of the product as a publishing tool.
- `/robots-txt-context.md` : Defines robots.txt as a statement of intent, not proof of crawler behaviour.
- `/robots.txt` : The site’s own published crawl rule, an instance of the rule layer (control resource, outside the main population).
- `/ai-usage-policy.md` : Markdown policy text, including the declared usage preference on model training.
- `/.well-known/anti-plausibility.json` : Completions a reader must not invent about the product.

These seven reading landmarks introduce the full source and count tables below; no observation or scope is removed.

- `/` → `/governance/ai-usage-policy`
- `/governance/ai-usage-policy` → `/plugin-context.md`
- `/governance/ai-usage-policy` → `/plugin-scope.md`
- `/governance/ai-usage-policy` → `/robots-txt-context.md`
- `/governance/ai-usage-policy` → `/limitations-context.md`
- `/governance/ai-usage-policy` → `/robots.txt`

## Executed path

No qualified execution trace is part of this edition. None is reconstructed from aggregate counts.

## Documentary graph

<picture><source media="(max-width: 640px)" srcset="../../figures/2026-09-15_2026-10-15-r2/G09-better-robots.com.en.compact.svg"><img src="../../figures/2026-09-15_2026-10-15-r2/G09-better-robots.com.en.svg" alt="Documentary relations between the case resources of better-robots.com in the source snapshot" width="960"></picture>

## Representative resources

| Resource | Scope class | Role | Short excerpt (line) | Declared version or dates |
|---|---|---|---|---|
| `/plugin-context.md` | `core_governance` | Product context: what the plugin is for and what it does not guarantee. | “It does not guarantee crawler compliance, technical enforcement, or live-site configuration state without inspection.” (11) | none declared |
| `/plugin-scope.md` | `core_governance` | Declared in-scope and out-of-scope capabilities, and the boundary between the plugin and the /check audit. | “is not proof that the plugin was installed or configured on the audited site.” (27) | none declared |
| `/limitations-context.md` | `core_governance` | Public limits of the product as a publishing tool. | “It cannot, by itself, guarantee obedience, indexing outcomes, legal force, or security enforcement.” (11) | none declared |
| `/robots-txt-context.md` | `core_governance` | Defines robots.txt as a statement of intent, not proof of crawler behaviour. | “It is not proof of blocking, proof of compliance, or a security control.” (10) | none declared |
| `/robots.txt` | `control_resource` | The site’s own published crawl rule, an instance of the rule layer (control resource, outside the main population). | “User-agent: GPTBot” (38) | “last updated 2026-05-16” |
| `/ai-usage-policy.md` | `core_governance` | Markdown policy text, including the declared usage preference on model training. | “Not permitted without explicit written permission.” (233) | mirror of the policy page dated 2026-03-19 |
| `/.well-known/anti-plausibility.json` | `core_governance` | Completions a reader must not invent about the product. | “claiming the plugin enforces or verifies compliance” (8) | schema\_version 1.1 |
| `/.well-known/ai-governance.json` | `core_governance` | Entrypoint stating usage intent and that it replaces no real control. | “They do not replace infrastructure controls, private contracts, or human verification.” (290) | schema\_version 2.4 |
| `/llms.txt` | `discovery_index` | Discovery index routing plugin questions to the context and scope files. | “is not the plugin runtime.” (266) | none declared |

Excerpts are quoted in the language of the file and verified verbatim against the snapshot ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r2/case-checks.json)). Declared dates are those written in the files; they are not deployment dates.

## Aggregated accesses

September 15 to October 14, 2026 inclusive, UTC. Monthly totals per URL; they do not establish an executed session or navigation order.

| Resource | Provider-origin AI GET 200 | Days with these requests | GET 200, all recorded classifications | HEAD | 304 |
|---|---:|---:|---:|---:|---:|
| `/plugin-context.md` | 1 | 1 | 36 | 1 | 2 |
| `/plugin-scope.md` | 1 | 1 | 34 | 1 | 2 |
| `/limitations-context.md` | 1 | 1 | 35 | 1 | 3 |
| `/robots-txt-context.md` | 1 | 1 | 38 | 1 | 2 |
| `/robots.txt` | 419 | 30 | 4,146 | 17 | 4 |
| `/ai-usage-policy.md` | 3 | 3 | 76 | 1 | 2 |
| `/.well-known/anti-plausibility.json` | 2 | 2 | 16 | 0 | 1 |
| `/.well-known/ai-governance.json` | 3 | 3 | 61 | 0 | 1 |
| `/llms.txt` | 3 | 3 | 148 | 1 | 3 |

Filters: GET 200 counts use the recorded method and status. The provider-origin columns keep only AI roles whose origin matched an official registry; “days” counts distinct UTC days with at least one such request, which says nothing about sessions or order. The all-classifications column is dominated by traffic recorded as unattributed, whose label is under review.

## Limits of this case

- Requests for these files are accesses to product documentation. They are not plugin installations, activations or plugin events: the plugin runs on other WordPress sites.
- The site’s robots.txt grants crawl access (Allow) to the listed crawlers, while the usage policy states a separate preference on training. Both are declarations; neither shows what a crawler does with the content.
- The snapshot is the source repository on 2026-10-06; deployment of these exact bytes during the window is assumed, not established. Edge features such as a CDN-managed robots.txt cannot be ruled out from the repository.
- robots.txt is a control resource: it is reported in its own section and never added to the main documentary population.

## Reproduce

All counts above come from [resource-summary.csv](../../data/editions/2026-09-15_2026-10-15-r2/resource-summary.csv) and [consultations.csv](../../data/editions/2026-09-15_2026-10-15-r2/consultations.csv); relations from [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv); roles and scope classes from [resources.csv](../../data/editions/2026-09-15_2026-10-15-r2/resources.csv). See [reproduction](../../docs/en/reproduction.md).
