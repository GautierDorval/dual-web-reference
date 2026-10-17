# Case: pagup.com

[Français](README.fr.md) · [Repository home](../../README.md)

> Edition `2026-09-15_2026-10-15-r1` · September 15 to October 14, 2026 inclusive, UTC · graph snapshot `2026-10-06` · candidate, not published

## Angle

Context of an organization, scope of its offer, references and documentary limits.

## Concrete question

Starting from the pagup.com AI policy page, and without going through llms.txt, what does the published layer say about what Pagup is, what its offer covers and explicitly excludes, which source prevails in a conflict, and where the documentation stops?

## Starting page

`/ai-usage-policy/` (counterpart `/en/ai-use-policy/`). The home page links to it; it links the canonical inventories, reading tiers and discovery order.

## Available documentary path

Each step is a reference written in a file of the source snapshot, verified in [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv). It shows what a reader can follow; it is not an observed robot path.

- `/` → `/ai-usage-policy/`
- `/ai-usage-policy/` → `/dualweb-index.md`
- `/ai-usage-policy/` → `/identity.json`
- `/dualweb-index.md` → `/site-context.md`
- `/dualweb-index.md` → `/services-non-publics.md`
- `/dualweb-index.md` → `/governance_scope.json`
- `/dualweb-index.md` → `/canon.md`
- `/identity.json` → `/source-precedence.json`

## Executed path

No qualified execution trace is part of this edition. None is reconstructed from aggregate counts.

## Documentary graph

<picture><source media="(max-width: 640px)" srcset="../../figures/2026-09-15_2026-10-15-r1/G09-pagup.com.en.compact.svg"><img src="../../figures/2026-09-15_2026-10-15-r1/G09-pagup.com.en.svg" alt="Documentary relations between the case resources of pagup.com in the source snapshot" width="960"></picture>

## Representative resources

| Resource | Scope class | Role | Short excerpt (line) | Declared version or dates |
|---|---|---|---|---|
| `/dualweb-index.md` | `discovery_index` | Canonical index of published surfaces and recommended reading order. | “Index canonique des surfaces publiées, de la précédence et de la lecture machine-first étendue pour pagup.com.” (3) | version 2.4.0-proposed; last revision 2026-08-27 |
| `/identity.json` | `core_governance` | Identity lock: descriptors, invariants, negations, contact data and non-promises. | “Pagup is a digital readability and agentic readiness firm” (95) | version 2.4.0-proposed; no date |
| `/canon.md` | `core_governance` | Canonical identity, invariants, negations and order of precedence. | “Pagup est la couche commerciale et d’exécution du problème de lisibilité numérique.” (21) | none declared |
| `/site-context.md` | `core_governance` | Nature of the site and its limits. | “ce site ne publie pas de tarifs standardisés, de catalogue packagé ni de SLA publics ;” (15) | none declared |
| `/services-non-publics.md` | `core_governance` | Forbids inferring unpublished commercial terms. | “Pagup peut qualifier, cadrer et proposer des mandats sur mesure, mais aucun tarif, SLA, forfait ou calendrier standard n’est canonisé ici par défaut.” (3) | none declared |
| `/governance_scope.json` | `core_governance` | Perimeter of the published rules and its exclusions. | “"non-published commercial terms"” (17) | version 2.4.0-proposed; no date |
| `/source-precedence.json` | `core_governance` | Ranked source hierarchy and conflict rule. | “En cas de conflit entre sources, le rang le plus bas (chiffre le plus petit) prévaut” (125) | version 1.1.0; lastUpdated 2026-08-09 |
| `/claims.json` | `core_governance` | Verifiable claims, each with a verification URL. | “Ces affirmations sont vérifiables aux URLs indiquées.” (98) | version 1.1.0; lastVerified 2026-08-09 |
| `/negative-definitions.md` | `core_governance` | What Pagup and its governance files are not. | “Les artefacts de gouvernance ne constituent pas à eux seuls une preuve d’exécution runtime.” (9) | none declared |

Excerpts are quoted in the language of the file and verified verbatim against the snapshot ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r1/case-checks.json)). Declared dates are those written in the files; they are not deployment dates.

## Aggregated accesses

September 15 to October 14, 2026 inclusive, UTC. Monthly totals per URL; they do not allow any path to be reconstructed.

| Resource | Provider-origin AI GET 200 | Days with these requests | GET 200, all recorded classifications | HEAD | 304 |
|---|---:|---:|---:|---:|---:|
| `/dualweb-index.md` | 3 | 3 | 112 | 0 | 2 |
| `/identity.json` | 1 | 1 | 36 | 0 | 2 |
| `/canon.md` | 3 | 3 | 128 | 1 | 2 |
| `/site-context.md` | 1 | 1 | 42 | 1 | 2 |
| `/services-non-publics.md` | 1 | 1 | 52 | 1 | 2 |
| `/governance_scope.json` | 1 | 1 | 29 | 0 | 2 |
| `/source-precedence.json` | 1 | 1 | 32 | 0 | 2 |
| `/claims.json` | 1 | 1 | 29 | 0 | 2 |
| `/negative-definitions.md` | 1 | 1 | 42 | 1 | 2 |

Filters: GET 200 counts use the recorded method and status. The provider-origin columns keep only AI roles whose origin matched an official registry; “days” counts distinct UTC days with at least one such request, which says nothing about sessions or order. The all-classifications column is dominated by traffic recorded as unattributed, whose label is under review.

## Limits of this case

- The snapshot is a build of the source repository on 2026-10-06, not the live state during the window; generated dates and sitemap lastmod values come from the build.
- Two root files described as aliases of their /.well-known/ versions differ from them (older French versions at the root).
- Several core files carry no version or date; their freshness can only be inferred from the bundle date.
- The English path is incomplete: there is no English site-context.md, among others.

## Reproduce

All counts above come from [resource-summary.csv](../../data/editions/2026-09-15_2026-10-15-r1/resource-summary.csv) and [consultations.csv](../../data/editions/2026-09-15_2026-10-15-r1/consultations.csv); relations from [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv); roles and scope classes from [resources.csv](../../data/editions/2026-09-15_2026-10-15-r1/resources.csv). See [reproduction](../../docs/en/reproduction.md).
