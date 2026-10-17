# Méthode

[English](../en/methodology.md) · [Accueil du dépôt](../../README.fr.md)

Cette page décrit la production des chiffres d’une édition, telle qu’elle est implémentée dans `analysis/dwr/`. La méthode est descriptive : elle compte des requêtes HTTP enregistrées vers des fichiers documentaires de trois sites. Elle ne mesure ni les réponses produites par un système, ni l’adoption, l’indexation, la conformité ou un effet quelconque du maillage. Voir le [modèle](modele.md) pour la nature de la couche documentaire et les [limites](limites.md) pour ce que les résultats ne permettent pas d’affirmer.

## Une chaîne en quatre étapes

| Étape | Commandes | S’exécute sur | Sortie |
|---|---|---|---|
| 1. Acquisition privée | `import-existing`, `acquire-readonly` | espace de travail privé | reçu d’import et marges d’export typées ; résultats bruts des requêtes et journal d’acquisition de l’extraction conjointe |
| 2. Normalisation et qualification | `normalize`, `qualify` | espace de travail privé | fichiers de travail privés |
| 3. Projection publique minimisée | `project-public` | intrants privés, sorties publiques | tables, `reconciliation.json`, `case-checks.json`, `catalog.json` sous `data/editions/<edition>/` |
| 4. Présentation | `analyze`, `render`, `build-site` | fichiers publics seulement, hors ligne | `metrics.json`, figures, blocs générés, site statique |

Chaque indicateur publié est calculé une seule fois, par `analyze` (`analysis/dwr/metrics.py`), à partir des seules tables publiques. Les figures, les pages de cas et les blocs générés lisent `metrics.json` et ces mêmes tables publiques. Les intrants, les sorties et l’usage du réseau de chaque commande figurent dans [reproduction](reproduction.md).

Pour cette édition, l’étape 1 s’est déroulée en deux temps. D’abord, `import-existing` a contrôlé le paquet d’export local du relevé interne contre son manifeste (taille et SHA-256 de chaque fichier, limites d’archive, sommes de contrôle internes), puis en a chargé les tables avec des listes de colonnes fermées ; une empreinte concordante établit l’identité binaire du paquet, pas l’exactitude des événements enregistrés. Ensuite, avec l’accord du propriétaire, `acquire-readonly` a été exécuté une seule fois dans l’environnement privé, avec `--execute` et la confirmation exacte de la fenêtre `--confirm-scope 2026-09-15..2026-10-15`. Il n’a lancé que des requêtes revues, chacune formée d’une seule instruction `SELECT` (`analysis/dwr/acquire.py`) : le schéma des tables lues, des sommes de contrôle par jour avant et après, une requête par jour UTC de la fenêtre sur la table d’agrégats quotidiens du producteur, le registre courant des artefacts, les versions du classificateur et l’historique de déploiement du producteur. Aucune ligne n’a été écrite, la base n’a pas été modifiée, et les sommes de contrôle étaient identiques avant et après la lecture (intervalle dans `extracted_at`).

## Populations

- **Périmètre du collecteur** : tous les chemins enregistrés par le collecteur privé sur les trois sites, toutes méthodes, tous statuts et tous acteurs confondus (l’ensemble des lignes de `daily-summary.csv`, dont les populations sont `main_documentary`, `other_documentary`, `robots_control` et `undeclared_bucket` ; indicateur `collector.requests`).
- **Périmètre du relevé initial** (`historical_report_scope`) : tous les chemins sauf `/robots.txt`, `/.well-known/__undeclared__` et la catégorie de producteur `well-known-probe`. Il reprend le périmètre du relevé interne initial et ne sert qu’au rapprochement.
- **Population documentaire principale** : couples site-chemin des classes `core_governance` et `discovery_index` (voir [périmètre](perimetre.md)).
- **Couche documentaire élargie** : la population principale plus `supporting_documentation`. C’est une lecture secondaire, jamais le résultat mis en avant.

La strate du résultat principal est la suivante : population documentaire principale, `GET` avec statut `200`, niveau enregistré `provider_origin_verified_actor`, rôles `ai_training`, `ai_search` et `user_initiated_fetch`.

## Unités

Les comptes distincts portent sur des couples site-chemin : une URL, repérée par un `resource_id` comme `gd:/llms.txt`. Un couple n’est ni un consommateur, ni un visiteur, ni une session. Les miroirs, les versions linguistiques et les formats sont des couples distincts. Les chemins distincts par groupe d’acteurs (`distinct_paths_in_group` dans `actor-summary.csv`) ne s’additionnent jamais, puisque deux acteurs peuvent demander la même URL.

## Méthode et statut

Seul un `GET` de statut `200` compte comme une requête servie avec un corps de document. `HEAD`, `304`, `301`, `404`, `405` et `5xx` restent dans des cellules distinctes et ne s’ajoutent jamais aux `GET 200`. Selon la [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) (consultée le 2026-10-16), une réponse à `HEAD` et une réponse `304` ne contiennent aucun contenu (sections 9.3.2 et 15.4.5), et `405` signifie que la méthode n’est pas prise en charge par la ressource cible (section 15.5.6). `GET 200` est le statut enregistré par le collecteur ; les octets servis ne sont pas revérifiés.

## Indicateurs principaux

Chaque entrée de `metrics.json` porte `metric_id`, `value`, `unit`, `status`, `numerator`, `denominator`, `filters` et `source_files`, ainsi que `label_en` et `label_fr`, et aussi `reason` et `attribution_quality` lorsqu’ils s’appliquent. `status` vaut `calculated`, ou `not_calculable` lorsqu’un dénominateur est nul.

| Indicateur | Définition | Unité |
|---|---|---|
| `main.get200` | somme, sur les couples de la population principale, des cellules de `consultations.csv` qui portent `GET`, `200`, le niveau enregistré `provider_origin_verified_actor` et l’un des rôles `ai_training`, `ai_search`, `user_initiated_fetch` | requêtes |
| `main.site_path_pairs` | couples de la population principale dont la somme vaut au moins 1 | couples site-chemin |
| `main.llms_get200` | la même somme sur `/llms.txt` seulement | requêtes |
| `main.other_get200`, `main.other_site_path_pairs` | la même somme et le même compte sur les chemins autres que `/llms.txt` | requêtes, couples site-chemin |
| `main.other_share` | `main.other_get200` divisé par `main.get200` | ratio, 6 décimales |
| `main.site.<site>.*` | les mêmes quantités pour un site | comme ci-dessus |
| `main.role.<role>.get200`, `main.role.<role>.site.<site>.get200` | la même somme pour un rôle, sur tous les sites ou sur un site | requêtes |
| `main.sensitivity.without_user_fetch.get200`, `main.sensitivity.without_user_fetch.site_path_pairs` | la même somme et le même compte sans le rôle `user_initiated_fetch` | requêtes, couples site-chemin |
| `main.recurrence.pairs_with_<n>_days`, `main.recurrence.max_days` | nombre de couples de la population principale, parmi ceux comptés dans `main.site_path_pairs`, dont la valeur `provider_origin_ai_get200_days` de `resource-summary.csv` tombe dans la tranche `<n>` (`1`, `2_to_3`, `4_to_7`, `8_or_more`) ; et la plus grande valeur | couples site-chemin, jours |
| `main.daily.sum_check`, `main.daily.days_with_requests`, `main.daily.site.<site>.days_with_requests` | à partir des lignes `main_documentary` de `daily-summary.csv`, avec les mêmes filtres limités aux rôles automatisés `ai_training` et `ai_search` (la politique des petites cellules exclut les récupérations à la demande des séries quotidiennes) : la somme de la série quotidienne, égale à `main.get200` moins `main.role.user_initiated_fetch.get200`, et les jours UTC qui comptent au moins une telle requête, tous sites confondus ou pour un site | requêtes, jours |
| `main_population.tier.<tier>.get200` | `GET 200` de la population principale par niveau enregistré, tous rôles confondus | requêtes |
| `extended.get200`, `extended.site_path_pairs` | la même somme et le même compte sur la couche élargie | requêtes, couples site-chemin |
| `main.scope_delta.provider_ai_get200_excluded` | GET 200 IA à origine fournisseur du périmètre du relevé initial, moins `main.get200` | requêtes |
| `historical.*` | les mêmes quantités sur le périmètre du relevé initial, par rôle, et les `GET 200` par niveau enregistré, tirés de `consultations.csv` | requêtes, couples, ratio |
| `coverage.*` | nombres de jours et sommes archivées tirés de `coverage.csv`, y compris les jours dont le total conjoint égale le compte agrégé archivé | jours, requêtes |
| `collector.requests` | somme de `request_count` sur toutes les lignes de `daily-summary.csv` | requêtes |

```text
other_share = other_get200 / total_get200
```

Numérateur et dénominateur partagent la fenêtre, les sites, le périmètre, la méthode, le statut et le niveau d’identification. Si le dénominateur est nul, la valeur est vide (`null`) avec le statut `not_calculable` et le motif `denominator_zero_or_unavailable`, jamais 0 %. Cette part décrit la répartition des requêtes enregistrées dans une sélection ; ce n’est ni un taux d’adoption ni une mesure d’efficacité.

La répartition par rôle, la sensibilité sans récupérations à la demande, la récurrence et la série quotidienne sont des sommes exactes de cellules de l’agrégat conjoint. Rien n’est estimé, et aucune valeur quotidienne ou par rôle n’est répartie à partir de totaux mensuels. La lecture sans récupérations à la demande est une analyse de sensibilité, pas une preuve d’indépendance. La récurrence compte des jours UTC distincts par couple ; elle ne dit rien des sessions, de l’ordre ni du nombre de clients.

## Le mode joint_acquisition

Cette édition porte `source_mode = joint_acquisition`. Elle repose sur l’agrégat quotidien conjoint du producteur : une ligne par jour UTC, site, chemin, méthode, statut, famille d’acteur, nom d’acteur, rôle et niveau enregistré. `normalize` charge les lignes de chaque jour de la fenêtre et s’arrête devant toute méthode, tout rôle ou tout niveau inconnus, tout statut hors de l’intervalle 100 à 599, tout compte qui n’est pas un entier non négatif, toute clé en double, ou un total qui diffère des sommes de contrôle par jour de l’extraction (`analysis/dwr/joint.py`).

Les exports du relevé interne, lus plus tôt le même jour (`exports_extracted_at` dans `catalog.json`), sont conservés pour le rapprochement. `normalize` leur compare les lignes conjointes et s’arrête au moindre écart (`joint_acquisition_inconsistent_with_exports`) : marges mensuelles par chemin, marges par groupe d’acteurs du périmètre du relevé initial, totaux quotidiens par site, méthodes et statuts par site. L’agrégat conjoint les reproduit exactement ; chaque contrôle et son résultat figurent dans `reconciliation.json` (`joint_aggregate_vs_exports`). Il s’agit de la cohérence entre deux lectures d’une même table du producteur, pas d’une validation indépendante.

Avant l’acquisition conjointe, la ventilation de chaque chemin par méthode et statut avait été déduite des exports par masse nulle : sur le périmètre du relevé initial, toutes les requêtes de chaque site tombaient dans `GET 200`, `HEAD 200`, `GET 304` ou `POST 405`, et les colonnes par chemin s’additionnaient, de sorte que la non-négativité des comptes fixait la ventilation de chaque chemin. L’agrégat conjoint confirme cette déduction pour chaque combinaison de chemin, de méthode et de statut (contrôle `deduced_method_status_split_confirmed`, et `method_status_split` dans `catalog.json`). La déduction n’est plus qu’un fait de rapprochement : les cellules publiées proviennent des lignes conjointes.

## Des cellules exactes aux grains autorisés

`project-public` refuse de s’exécuter sans acquisition conjointe acceptée (`joint_aggregate_required`). Il additionne les lignes conjointes aux seuls grains permis par la [politique des petites cellules](confidentialite.md) (`analysis/dwr/project.py`) :

- `consultations.csv` : grain de l’édition, site × chemin × méthode × statut × famille d’acteur × nom d’acteur × rôle × niveau enregistré ;
- `daily-summary.csv` : jour × site × population × rôle × niveau enregistré × méthode × statut, jamais de chemin ni de nom d’acteur ; les strates protégées sont regroupées en une ligne par jour, site et population (`protected_strata`, méthode et statut `ANY`, voir [confidentialité](confidentialite.md)) ; colonnes `edition_id`, `date_utc`, `site_id`, `population`, `actor_role`, `stored_identity_tier`, `http_method`, `http_status`, `request_count`, `coverage_status` et `archive_report_status` ; populations `main_documentary`, `other_documentary` (toutes les autres classes de périmètre, sauf les deux suivantes), `robots_control` (`/robots.txt`) et `undeclared_bucket` ;
- `actor-summary.csv` : population × site × famille d’acteur × nom d’acteur × rôle × niveau enregistré, avec `requests`, `get200`, `distinct_paths_in_group` et `days_with_rows`, pour chaque population ;
- `resource-summary.csv` : une ligne par couple ayant des lignes dans la fenêtre, y compris le nombre de jours UTC avec au moins un `GET 200` IA à origine fournisseur (`provider_origin_ai_get200_days`) ;
- `daily-family-summary.csv` : jour × famille documentaire × rôle, pour la population principale, le niveau à origine fournisseur, les `GET 200` et les seuls rôles `ai_training` et `ai_search` ; la politique des petites cellules en écarte les récupérations à la demande.

Chaque cellule est une somme exacte de lignes conjointes (`cell_derivation = joint_exact`) ; rien n’est attribué au prorata. Une combinaison absente d’une table n’a aucune requête enregistrée dans la table du producteur ; ce n’est pas une absence mesurée sur le Web. Les zéros explicites ne figurent que dans `daily-family-summary.csv` (`observation_status = observed_zero`). La carte de chaleur G06 est tracée à partir de cette table, jamais à partir de marges.

## Rapprochement

<!-- dwr:begin reconciliation -->
| Chiffre historique | Attendu | Recalculé | État |
|---|---:|---:|---|
| `all_collector_requests` | 24 815 | 24 815 | match |
| `governance_get200` | 14 126 | 14 126 | match |
| `governance_requests` | 19 587 | 19 587 | match |
| `governance_site_path_pairs` | 386 | 386 | match |
| `heterogeneous_provider_plus_network_ai_get200` | 933 | 933 | match |
| `stored_cloudflare_unattributed_get200` | 12 476 | 12 476 | match |
| `stored_cloudflare_unattributed_percent_of_get200` | 88.32 | 88.32 | match |
| `stored_network_claimed_ai_get200` | 561 | 561 | match |
| `stored_provider_origin_ai_get200` | 372 | 372 | match |
| `stored_provider_origin_ai_llms_get200` | 6 | 6 | match |
| `stored_provider_origin_ai_other_get200` | 366 | 366 | match |
| `stored_provider_origin_ai_other_percent` | 98.39 | 98.39 | match |
| `stored_provider_origin_ai_other_site_path_pairs` | 257 | 257 | match |
| `stored_provider_origin_ai_search_get200` | 44 | 44 | match |
| `stored_provider_origin_ai_site_path_pairs` | 259 | 259 | match |
| `stored_provider_origin_ai_training_get200` | 302 | 302 | match |
| `stored_provider_origin_excluding_user_fetch_get200` | 346 | 346 | match |
| `stored_provider_origin_user_fetch_get200` | 26 | 26 | match |

Mêmes exports, mêmes filtres, code propre à ce dépôt. C’est une reproduction arithmétique, pas un audit indépendant : les exports et le relevé initial viennent de la même chaîne productrice. Le total combiné de 933 mêle deux niveaux d’identification et n’est jamais présenté comme un total homogène.
<!-- dwr:end reconciliation -->

`import-existing` recalcule les chiffres du relevé interne initial avec le code propre à ce dépôt (`analysis/dwr/reconcile.py`) et les compare aux valeurs de référence ; tout écart arrête l’import. Il compare aussi les totaux quotidiens de l’export aux comptes agrégés archivés, et `project-public` fait de même pour les totaux quotidiens de l’agrégat conjoint (`export_matches_archive` et `joint_matches_archive` dans `coverage.csv`). Toutes ces comparaisons reposent sur des intrants de la même chaîne productrice : leur concordance montre que l’arithmétique est reproduite, pas que la collecte est juste. Le rapprochement ne vaut que pour le périmètre du relevé initial : le résultat principal utilise le périmètre revu et n’est pas contraint de retrouver un chiffre historique. L’écart est détaillé dans [périmètre](perimetre.md).

## Ce qui n’a pas été fait

- Aucune nouvelle collecte : l’édition utilise les requêtes déjà enregistrées par le collecteur privé.
- Aucune consultation en direct des trois sites : les relations viennent d’instantanés des sources, et aucune URL qui s’y trouve n’est visitée.
- Aucune écriture dans la base du producteur : l’unique extraction bornée n’a lancé que des requêtes `SELECT` en lecture seule, n’a écrit aucune ligne et a laissé la base inchangée.
- Aucun libellé enregistré n’a été réécrit (voir [attribution](attribution.md)).
