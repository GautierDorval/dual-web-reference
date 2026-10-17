# Périmètre

[English](../en/scope.md) · [Accueil du dépôt](../../README.fr.md)

Cette page précise quels fichiers appartiennent à la population documentaire principale, lesquels sont présentés à part, et comment l’écart avec le relevé interne initial est détaillé. Les règles se trouvent dans [config/scope-rules.json](../../config/scope-rules.json) et les décisions dans [config/scope-registry.csv](../../config/scope-registry.csv). Pour le rôle de chaque type de fichier, voir [rôles des fichiers](roles-des-fichiers.md).

## Le registre

`config/scope-registry.csv` compte une ligne par couple site-chemin examiné : chaque chemin enregistré par le collecteur dans la fenêtre, chaque chemin inscrit par le producteur sans ligne dans la fenêtre, et les quelques chemins examinés dans les instantanés des sources que l’export ne porte pas (`window_rows_status = not_in_collector_window_export` dans `resources.csv`). Ses colonnes sont `site_id`, `path`, `scope_class`, `scope_rule_id`, `family`, `format`, `language`, `role_en`, `role_fr`, `declares_canonical_source`, `mentions_runtime_or_mcp`, `found_in_snapshot`, `review_status` et `justification`.

Le registre est construit par `scripts/build_scope_registry.py` à partir de revues de contenu des instantanés des sources des sites, puis conservé et revu comme fichier public versionné. `qualify` ne lit que le registre, jamais les notes de revue. L’étape s’arrête si un chemin du collecteur n’a pas d’entrée (`missing_registry_entry: fail`), si une classe ou une règle est inconnue, si `/robots.txt` n’est pas `control_resource` ou si `/.well-known/__undeclared__` n’est pas `undeclared_bucket`.

## Classes

| Classe | Population principale | Fonction |
|---|---|---|
| `core_governance` | oui | énonce une identité, un contexte, un périmètre, des sources, des affirmations, des relations, une politique, des priorités ou des limites d’interprétation |
| `discovery_index` | oui | oriente surtout vers d’autres ressources de gouvernance, par exemple `llms.txt` ou un index de documents |
| `supporting_documentation` | non (couche élargie) | documentation explicative, de méthode, de protocole ou de référence, qui n’énonce pas elle-même d’identité, de politique ou d’orientation |
| `operational_descriptor` | non | fichier statique décrivant un service, un point d’accès, un runtime, un serveur MCP, une API ou un outil |
| `control_resource` | non | fichier de contrôle des robots, comme `robots.txt` |
| `technical_resource` | non | sitemap, `security.txt`, fichier de version ou de build, configuration de mesure |
| `undeclared_bucket` | non | compartiment du collecteur pour les requêtes vers des noms well-known non déclarés ; ce n’est pas un document |
| `unresolved_scope` | non | contenu introuvable dans l’instantané examiné, ou fonction ambiguë |

`technical_resource` a été ajoutée à la liste initiale des classes, pour qu’un sitemap ou un fichier de version ne soit jamais compté comme fichier de gouvernance du seul fait qu’un registre le mentionne.

## Règles et ordre de priorité

| Règle | S’applique à | Attribue | Priorité |
|---|---|---|---|
| R01 | `path == /robots.txt` | `control_resource` | 1 |
| R02 | `/.well-known/__undeclared__` ou catégorie de producteur `well-known-probe` | `undeclared_bucket` | 2 |
| R03 | sitemap XML, `security.txt`, fichier de version ou de build, configuration de mesure | `technical_resource` | 3 |
| R04 | contenu revu dans l’instantané des sources, pièce citée dans `justification` | l’une de `core_governance`, `discovery_index`, `supporting_documentation`, `operational_descriptor` | 4 |
| R05 | contenu introuvable dans l’instantané, ou fonction encore ambiguë après revue | `unresolved_scope` | 5 |

La première règle applicable l’emporte. R01, R02 et le motif de chemin de R03 (sitemaps, `security.txt`, fichiers de version et de build) sont mécaniques : ils priment sur toute proposition fondée sur le contenu et s’appliquent même si le fichier est absent de l’instantané. R03 s’applique aussi lorsque la revue de contenu a reconnu un fichier technique. R04 conserve la classe choisie d’après le contenu. R05 s’applique lorsqu’aucun contenu n’a pu être lu ou que la fonction reste ambiguë.

## État de revue

`review_status` prend trois valeurs : `rule_based` (classe fixée par une règle mécanique : R01, R02 ou le motif de chemin de R03), `content_reviewed_in_snapshot` (R04) et `content_not_found` (les autres entrées, notamment R05). La présence du fichier lui-même est consignée à part dans `found_in_snapshot` ; il faut lire les deux colonnes ensemble.

## llms.txt est isolé, pas exclu

`/llms.txt` appartient à la population principale (classe `discovery_index`) et il est toujours présenté à part (`llms_txt = true` dans `resources.csv`, indicateurs `main.llms_get200` et `main.other_*`). L’isoler ne retire jamais les autres ressources. C’est une ressource d’orientation possible parmi d’autres, pas un protocole que tout client devrait lire en premier ; voir [études llms.txt](etudes-llms-txt.md) et [découverte et maillage](decouverte-et-maillage.md).

## Descripteurs opérationnels

Les fichiers qui décrivent un runtime, un serveur MCP, une API ou un service sont classés `operational_descriptor` et restent hors de la population principale. Une requête vers un tel fichier est une requête de document. Ce n’est jamais un appel au service décrit, et elle ne dit rien d’un usage éventuel de ce service. La colonne `mentions_runtime_or_mcp` est un indicateur distinct : un fichier de gouvernance peut mentionner un runtime et rester classé selon sa propre fonction.

## Miroirs et versions linguistiques

Une ressource est un couple site-chemin. Un fichier servi à `/.well-known/nom` et à `/nom`, une version française et une version anglaise, ou un même contenu en deux formats sont des couples distincts, comptés séparément. La colonne `snapshot_sha256` de [resources.csv](../../data/editions/2026-09-15_2026-10-15-r1/resources.csv) donne l’empreinte de chaque fichier dans son instantané source, ce qui permet de reconnaître les miroirs identiques à l’octet près sans fusionner leurs comptes. Une vue par famille pourra les regrouper plus tard, sous un autre nom et avec sa propre méthode, sans les présenter comme des documents indépendants.

## État de la version historique

Le registre est construit à partir d’instantanés des sources, un par site, datés par `graph_snapshot_at` : ce sont des points dans le temps, pas la fenêtre entière. La version réellement servie de chaque fichier pendant la fenêtre n’est pas établie ; chaque ressource porte donc `historical_version_status = unknown`. Un fichier présent dans l’instantané actuel n’est pas, de ce fait, réputé exister en septembre, et une relation trouvée dans l’instantané n’est pas réputée exister pendant la fenêtre.

## Delta de périmètre

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

Lecture de ce bloc. Chaque ligne est une classe de périmètre hors de la population principale, avec les couples site-chemin ayant des lignes dans la fenêtre, toutes les requêtes de tous les acteurs, et les GET 200 IA à origine fournisseur (la même strate que le résultat principal). La phrase de synthèse compare la population principale au périmètre du relevé initial : les requêtes « retirées par la revue du périmètre » sont les GET 200 IA à origine fournisseur du périmètre du relevé initial qui relèvent de `supporting_documentation`, `operational_descriptor`, `technical_resource` ou `unresolved_scope`. Les lignes `control_resource` et `undeclared_bucket` étaient déjà hors du périmètre du relevé initial ; elles figurent par souci d’exhaustivité, pas comme partie du delta. La table source est [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r1/exclusions.csv), qui liste aussi les niveaux d’identification écartés de la strate principale ([attribution](attribution.md)).

## La couche élargie

La couche documentaire élargie ajoute `supporting_documentation` à la population principale (`extended.get200`, `extended.site_path_pairs`). Elle est publiée comme lecture secondaire, parce que les pages de méthode et de protocole se rattachent à la couche sans énoncer elles-mêmes d’identité, de politique ou d’orientation. Elle ne remplace jamais le résultat principal.

## Règles fixées avant les résultats

Les classes de périmètre, les règles R01 à R05 et leur ordre de priorité ont été rédigés et versionnés avant le calcul de tout compte de cette édition. Le registre chemin par chemin a été construit ensuite à partir de revues de contenu des instantanés, indépendamment des volumes de trafic ; le libellé de R03 a ensuite été précisé pour nommer le cas de revue de contenu auquel elle a été appliquée, sans changer aucune classe. Un changement ultérieur de périmètre crée une nouvelle révision, avec la cause consignée comme changement de périmètre ([mises à jour](mises-a-jour.md)) ; il n’est jamais appliqué en silence à une édition publiée.
