# Rôles des fichiers documentaires

[English](../en/file-roles.md) · [Accueil du dépôt](../../README.fr.md)

Les fichiers de la couche ne jouent pas tous le même rôle. Cette page les regroupe par fonction, donne des exemples de noms de fichiers relevés dans les trois cas et indique la classe de périmètre à laquelle chaque groupe correspond habituellement. Ces noms sont des exemples, pas des noms obligatoires : chaque site a choisi les siens, et aucun ne constitue un standard universel.

## La classe vient du contenu, jamais du nom

Chaque couple site-chemin reçoit une seule classe de périmètre, attribuée par les règles de [scope-rules.json](../../config/scope-rules.json) selon leur ordre de priorité :

| Règle | S’applique à | Classe attribuée |
|---|---|---|
| R01 | `/robots.txt` | `control_resource` |
| R02 | le compartiment du collecteur `/.well-known/__undeclared__` (et la catégorie de producteur `well-known-probe`) | `undeclared_bucket` |
| R03 | sitemaps, `security.txt`, fichiers de version ou de build, configuration de mesure | `technical_resource` |
| R04 | contenu examiné dans l’instantané source ; la ligne du registre cite la preuve | `core_governance`, `discovery_index`, `supporting_documentation` ou `operational_descriptor` |
| R05 | contenu introuvable dans l’instantané, ou fonction encore ambiguë après examen | `unresolved_scope` |

Seule une courte liste de chemins techniques ou propres au collecteur est classée par règle. Tout autre fichier est classé après la lecture de son contenu dans l’instantané source, jamais d’après son extension ou son nom. Un même nom peut donc relever de classes différentes :

- `/governance_scope.json` déclare, sur pagup.com, à quoi s’appliquent les règles publiées et ce qu’elles excluent (`core_governance`) ; sur gautierdorval.com, c’est une configuration du périmètre d’observation (`technical_resource`).
- `/.well-known/ai-governance.json` relève de `discovery_index` sur gautierdorval.com et sur pagup.com, où sa fonction principale est d’orienter ; sur better-robots.com, il déclare le rôle du site, la préséance des sources et des règles de réponse (`core_governance`).
- `/doctrine/ssa-e-a2-dual-web.md` est la référence Markdown de la définition sur gautierdorval.com (`core_governance`), et une description explicative, non contractuelle, sur pagup.com (`supporting_documentation`).
- `humans.txt`, `llms.txt`, `robots.txt` et `security.txt` partagent la même extension et relèvent de quatre classes différentes.

Un fichier peut remplir plusieurs fonctions ; sa classe suit sa fonction principale, telle qu’elle a été examinée. Chaque décision est consignée avec sa règle, son état de revue et sa justification dans [scope-registry.csv](../../config/scope-registry.csv), puis publiée pour l’édition dans [resources.csv](../../data/editions/2026-09-15_2026-10-15-r2/resources.csv). La colonne `family` de ces tables est plus fine que les groupes ci-dessous.

## Groupes et rôles

| Groupe | Fonction | Exemples de noms relevés dans les cas | Classe habituelle |
|---|---|---|---|
| Identité | Énonce de qui ou de quoi traite le site : noms, rôles, négations, identifiants canoniques | `identity.json`, `humans.txt`, `author.md` | `core_governance` |
| Contexte | Décrit l’objet et la nature du site, de l’organisation ou du produit, et la façon de les lire | `site-context.md`, `editorial-context.md`, `plugin-context.md` | `core_governance` |
| Périmètre et limites | Énonce ce qui est couvert, ce qui est exclu et ce qui ne doit pas être inféré | `non-goals.md`, `services-non-publics.md`, `negative-definitions.md`, `limitations-context.md`, `.well-known/anti-plausibility.json` | `core_governance` |
| Affirmations | Recense les énoncés sur le sujet et les sépare selon leur nature (vérifiés, attestés, narratifs, de limite) | `claims.json`, `canonical-claim-boundaries.json` | `core_governance` |
| Sources et préséance | Indique quelles sources comptent, dans quel ordre, et laquelle prévaut en cas de conflit | `authority-precedence.json`, `source-precedence.json`, `.well-known/eac-registry.json` | `core_governance` |
| Relations et graphes d’entités | Déclare les relations entre l’entité, le site, ses pages et d’autres entités | `entity-graph.jsonld`, `relationships.jsonld`, `entity-relations.md` | `core_governance` |
| Politique | Déclare des préférences d’usage et des règles d’interprétation, de résumé ou de réponse | `ai-usage-policy.md`, `.well-known/interpretation-policy.json`, `response-legitimacy.md`, `output-constraints.md` | `core_governance` |
| Index d’orientation et manifestes | Renvoie vers d’autres fichiers de la couche, parfois selon un ordre de lecture recommandé | `llms.txt`, `llms-full.txt`, `dualweb-index.md`, `ai-manifest.json`, `.well-known/ai-governance.json`, `llm-intent-map.json` | `discovery_index` |
| Documentation de soutien | Explique des méthodes, des protocoles, des vocabulaires, des registres ou des empreintes d’intégrité liés à la couche, sans énoncer elle-même d’identité, de politique ni d’orientation | `doctrine-glossary.json`, `content-digests.json`, `situational-applicability-layer.json`, `proximity-causality-protocol.md` | `supporting_documentation` |
| Descripteurs opérationnels | Décrit un service, un point d’accès, un environnement d’exécution, une API, un outil, ou un serveur qui expose des outils par le Model Context Protocol (MCP) | `.well-known/mcp.json`, `.well-known/ai-plugin.json`, `governed-context-runtime.json` | `operational_descriptor` |
| Ressources de contrôle | Publie des règles d’exploration destinées aux robots | `robots.txt` | `control_resource` |
| Ressources techniques | Soutient le site sur le plan technique : sitemaps, contact de sécurité, fichiers de version ou de build, configuration de mesure | `sitemap.xml`, `.well-known/security.txt`, `version.json` | `technical_resource` |

Deux classes ne sont pas des groupes de documents : `undeclared_bucket` est une étiquette du collecteur qui regroupe les requêtes vers des noms `/.well-known/` non déclarés, et `unresolved_scope` signale un chemin enregistré dont le contenu est introuvable ou dont la fonction reste ambiguë.

Une requête vers un descripteur opérationnel est une requête du document, jamais un appel au service qu’il décrit. Sur better-robots.com, par exemple, `.well-known/mcp.json` indique dans l’instantané source qu’aucun serveur MCP public n’est exposé sur le domaine. De même, `robots.txt` est présenté dans sa propre section et n’est jamais ajouté à la population principale.

## Population principale et couche élargie

- **Population documentaire principale** : les couples classés `core_governance` ou `discovery_index`. Le résultat principal y retient les requêtes GET de statut 200 dont le niveau enregistré est `provider_origin_verified_actor`, pour les rôles `ai_training`, `ai_search` et `user_initiated_fetch`.
- **llms.txt** fait partie de la population principale et est toujours présenté à part. L’isoler ne retire jamais aucune autre ressource de la population.
- **Couche documentaire élargie** : la population principale, plus `supporting_documentation`. C’est une lecture secondaire, publiée à côté du résultat principal et jamais fusionnée avec lui.
- **Hors de l’une et de l’autre** : `operational_descriptor`, `control_resource`, `technical_resource`, `undeclared_bucket` et `unresolved_scope`. Chaque classe tenue hors de la population principale qui a des requêtes dans la fenêtre, `supporting_documentation` comprise, a sa propre ligne dans [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r2/exclusions.csv).

L’unité est le couple site-chemin. Les miroirs (par exemple `/ai-governance.json` et `/.well-known/ai-governance.json`), les langues et les formats (un fichier Markdown et sa variante JSON ou YAML) sont des ressources distinctes. Une vue par famille peut les regrouper, sans les présenter comme des documents indépendants.

Les comptes par classe de cette édition sont générés ci-dessous. L’écart avec le périmètre du relevé interne initial est expliqué dans [perimetre.md](perimetre.md).

<!-- dwr:begin scope-delta -->
| Classe de périmètre | Couples site-chemin avec lignes | Toutes requêtes | GET 200 IA à origine fournisseur |
|---|---:|---:|---:|
| `control_resource` | 1 | 4 167 | 419 |
| `operational_descriptor` | 14 | 617 | 12 |
| `supporting_documentation` | 99 | 4 589 | 111 |
| `technical_resource` | 4 | 201 | 4 |
| `undeclared_bucket` | 3 | 1 061 | 1 |

Population documentaire principale : 245 requêtes sur 174 couples. Périmètre du relevé initial : 372 sur 259. Retirées par la revue du périmètre : 127. Couche élargie avec la documentation de soutien (lecture secondaire) : 356 sur 247 couples. robots.txt et le compartiment non déclaré étaient déjà hors du périmètre du relevé initial.
<!-- dwr:end scope-delta -->
