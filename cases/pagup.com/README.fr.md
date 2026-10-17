# Cas : pagup.com

[English](README.md) · [Accueil du dépôt](../../README.fr.md)

> Édition `2026-09-15_2026-10-15-r1` · du 15 septembre au 14 octobre 2026 inclusivement, en UTC · instantané du graphe `2026-10-06` · candidate, non publiée

## Angle

Contexte d’une organisation, périmètre de son offre, références et limites documentaires.

## Question concrète

En partant de la page de politique IA de pagup.com, et sans passer par llms.txt, que dit la couche publiée sur ce qu’est Pagup, ce que couvre son offre et ce qu’elle exclut explicitement, la source qui prévaut en cas de conflit et l’endroit où la documentation s’arrête ?

## Page de départ

`/ai-usage-policy/` (équivalent `/en/ai-use-policy/`). La page d’accueil y renvoie ; elle relie les inventaires canoniques, les tiers de lecture et l’ordre de découverte.

## Parcours documentaire disponible

Chaque étape est une référence écrite dans un fichier de l’instantané source, vérifiée dans [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv). Elle montre ce qu’un lecteur peut suivre ; ce n’est pas un parcours de robot observé.

- `/` → `/ai-usage-policy/`
- `/ai-usage-policy/` → `/dualweb-index.md`
- `/ai-usage-policy/` → `/identity.json`
- `/dualweb-index.md` → `/site-context.md`
- `/dualweb-index.md` → `/services-non-publics.md`
- `/dualweb-index.md` → `/governance_scope.json`
- `/dualweb-index.md` → `/canon.md`
- `/identity.json` → `/source-precedence.json`

## Parcours exécuté

Aucune trace d’exécution qualifiée ne fait partie de cette édition. Aucune n’est reconstituée à partir des comptes agrégés.

## Graphe documentaire

<picture><source media="(max-width: 640px)" srcset="../../figures/2026-09-15_2026-10-15-r1/G09-pagup.com.fr.compact.svg"><img src="../../figures/2026-09-15_2026-10-15-r1/G09-pagup.com.fr.svg" alt="Relations documentaires entre les ressources du cas pagup.com dans l’instantané source" width="960"></picture>

## Ressources représentatives

| Ressource | Classe de périmètre | Rôle | Extrait court (ligne) | Version ou dates déclarées |
|---|---|---|---|---|
| `/dualweb-index.md` | `discovery_index` | Index canonique des surfaces publiées et de l’ordre de lecture recommandé. | « Index canonique des surfaces publiées, de la précédence et de la lecture machine-first étendue pour pagup.com. » (3) | version 2.4.0-proposed ; dernière révision le 2026-08-27 |
| `/identity.json` | `core_governance` | Verrou d’identité : descripteurs, invariants, négations, coordonnées et non-promesses. | « Pagup is a digital readability and agentic readiness firm » (95) | version 2.4.0-proposed ; aucune date |
| `/canon.md` | `core_governance` | Identité canonique, invariants, négations et ordre de prévalence. | « Pagup est la couche commerciale et d’exécution du problème de lisibilité numérique. » (21) | aucune déclarée |
| `/site-context.md` | `core_governance` | Nature du site et ses limites. | « ce site ne publie pas de tarifs standardisés, de catalogue packagé ni de SLA publics ; » (15) | aucune déclarée |
| `/services-non-publics.md` | `core_governance` | Interdit d’inférer des modalités commerciales non publiées. | « Pagup peut qualifier, cadrer et proposer des mandats sur mesure, mais aucun tarif, SLA, forfait ou calendrier standard n’est canonisé ici par défaut. » (3) | aucune déclarée |
| `/governance_scope.json` | `core_governance` | Périmètre des règles publiées et ses exclusions. | « "non-published commercial terms" » (17) | version 2.4.0-proposed ; aucune date |
| `/source-precedence.json` | `core_governance` | Hiérarchie classée des sources et règle de conflit. | « En cas de conflit entre sources, le rang le plus bas (chiffre le plus petit) prévaut » (125) | version 1.1.0 ; lastUpdated 2026-08-09 |
| `/claims.json` | `core_governance` | Affirmations vérifiables, chacune avec une URL de vérification. | « Ces affirmations sont vérifiables aux URLs indiquées. » (98) | version 1.1.0 ; lastVerified 2026-08-09 |
| `/negative-definitions.md` | `core_governance` | Ce que Pagup et ses fichiers de gouvernance ne sont pas. | « Les artefacts de gouvernance ne constituent pas à eux seuls une preuve d’exécution runtime. » (9) | aucune déclarée |

Les extraits sont cités dans la langue du fichier et vérifiés mot pour mot contre l’instantané ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r1/case-checks.json)). Les dates déclarées sont celles écrites dans les fichiers ; ce ne sont pas des dates de déploiement.

## Accès agrégés

Du 15 septembre au 14 octobre 2026 inclusivement, en UTC. Totaux mensuels par URL ; ils ne permettent de reconstituer aucun parcours.

| Ressource | GET 200 IA à origine fournisseur | Jours avec ces requêtes | GET 200, toutes classifications enregistrées | HEAD | 304 |
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

Filtres : les GET 200 reprennent la méthode et le statut enregistrés. Les colonnes à origine fournisseur ne gardent que les rôles IA dont l’origine correspondait à un registre officiel ; « jours » compte les jours UTC distincts avec au moins une telle requête, sans rien dire des sessions ni de l’ordre. La colonne toutes classifications est dominée par du trafic enregistré non attribué, dont le libellé est en revue.

## Limites propres au cas

- L’instantané est un build du dépôt source au 2026-10-06, pas l’état servi pendant la fenêtre ; les dates générées et les lastmod des sitemaps proviennent du build.
- Deux fichiers racine présentés comme alias de leur version /.well-known/ en diffèrent (versions françaises plus anciennes à la racine).
- Plusieurs fichiers centraux ne portent ni version ni date ; leur fraîcheur ne peut être inférée que de la date du lot.
- Le parcours anglais est incomplet : il n’existe pas de site-context.md anglais, entre autres.

## Reproduire

Tous les comptes ci-dessus viennent de [resource-summary.csv](../../data/editions/2026-09-15_2026-10-15-r1/resource-summary.csv) et [consultations.csv](../../data/editions/2026-09-15_2026-10-15-r1/consultations.csv) ; les relations de [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv) ; rôles et classes de périmètre de [resources.csv](../../data/editions/2026-09-15_2026-10-15-r1/resources.csv). Voir [reproduction](../../docs/fr/reproduction.md).
