# Attribution

[English](../en/attribution.md) · [Accueil du dépôt](../../README.fr.md)

Cette page explique comment les requêtes sont attribuées à des acteurs, ce que signifient les libellés enregistrés, lesquels sont en revue et pourquoi. Les libellés sont enregistrés par le producteur, le collecteur privé (un Worker Cloudflare), avec la version 2026-08-24.1 du classificateur. Ce dépôt les conserve tels quels et y ajoute une appréciation distincte, dont les règles figurent dans [config/attribution-rules.json](../../config/attribution-rules.json).

## Quatre dimensions indépendantes

1. **Rôle de l’acteur** (`actor_role`) : la fonction enregistrée par le producteur, parmi `ai_training`, `ai_search`, `user_initiated_fetch`, `search_indexing`, `seo_tool`, `generic_automation` et `unknown`.
2. **Qualité d’identification** : le niveau enregistré (`stored_identity_tier`), plus une appréciation distincte de ce niveau (`attribution_assessment`).
3. **Provenance de la sollicitation** (`initiation_provenance`, `initiation_evidence_status`) : qui a déclenché la requête. Dans cette édition, elle vaut partout `unknown` et `not_established`.
4. **Couverture et disponibilité** (`coverage_status`, `observation_status`) : voir [qualité et couverture](qualite-et-couverture.md).

Aucune dimension n’en remplace une autre. Une requête dont l’origine fournisseur correspondait à un registre officiel peut avoir été provoquée par l’exploitant du site. Un robot de surveillance peut être légitime sans être un acteur IA. Une journée partielle peut contenir des requêtes réellement enregistrées.

## Niveau enregistré et appréciation

| `stored_identity_tier` | `attribution_assessment` | Utilise le prédicat en revue | Population principale |
|---|---|---|---|
| `provider_origin_verified_actor` | `registry_match_not_affected_by_predicate` | non | admissible |
| `spoofed_or_failed_verification` | `registry_mismatch_not_affected_by_predicate` | non | non |
| `network_verified_claimed_actor` | `recorded_classification_reliability_under_review` | oui | non |
| `cloudflare_verified_unattributed` | `recorded_classification_reliability_under_review` | oui | non |
| `claimed_actor_unverified` | `unverified_claim` | non | non |
| `unknown_automation` | `unverified_unknown` | non | non |
| `synthetic_probe` | `synthetic_marker` | non | non |
| `cryptographically_verified_actor` | `not_observed_in_covered_versions` | non | non |

Le niveau enregistré n’est jamais écrasé, redaté ni redistribué. L’appréciation est une interprétation dotée de sa propre méthode, inscrite à côté du niveau dans `consultations.csv` et `actor-summary.csv`. Le libellé « Classification enregistrée, fiabilité en cours de revue » dit exactement cela : le producteur a enregistré ce niveau, et sa fiabilité est en cours d’examen.

## Le prédicat en revue

Le producteur décide si Cloudflare a vérifié un client au moyen de ce prédicat :

```js
cloudflareVerified(cf) = cf?.botManagement?.verifiedBot === true || cf?.verifiedBotCategory != null
```

En JavaScript, `"" != null` est vrai : une catégorie réduite à une chaîne vide satisfait donc le prédicat, même si `verifiedBot` vaut explicitement `false`. Le défaut a été reproduit dans le vrai module de test du producteur avec l’entrée `{botManagement: {verifiedBot: false}, verifiedBotCategory: ""}` : un client non déclaré, et même un user agent de navigateur, reçoivent `cloudflare_verified_unattributed` ; un acteur déclaré sans preuve de registre (par exemple `ClaudeBot`) reçoit `network_verified_claimed_actor`.

## Reproduire n’est pas établir l’incidence en production

La reproduction montre ce que fait le code avec cette entrée. Elle ne montre pas qu’une catégorie vide a été reçue en production, ni qu’elle explique le trafic enregistré comme non attribué. Les deux questions restent séparées. Ce qui peut être établi pour la production se limite aux déploiements consignés dans l’historique de déploiement du producteur lui-même et à leur code :

<!-- dwr:begin incidence -->
| Déploiement du producteur (étiquette) | Effectif | Jours mesurés couverts | Code source disponible | Déploiement établi par | Classificateur | Prédicat `verifiedBotCategory != null` | Signaux conservés | Défaut applicable à | Réévaluation possible |
|---|---|---|---|---|---|---|---|---|---|
| pd01 | 2026-09-13T17:18:49Z, 100 % | du 2026-09-15 au 2026-10-14 | oui (dépôt privé) | historique de déploiement du producteur, 127 relevés, plus long intervalle 11.5 h | 2026-08-24.1 | présent (même blob de fichier) | niveau et rôle enregistrés seulement ; aucun signal Cloudflare brut | `cloudflare_verified_unattributed`, `network_verified_claimed_actor` | non pour ces deux niveaux ; le niveau à origine fournisseur n’utilise pas le prédicat |

Les étiquettes de déploiement remplacent les identifiants privés, conservés dans le verrou interne. Les identifiants de commit attachés aux rapports quotidiens archivés changent pendant la fenêtre sans aucun déploiement dans cet historique ; ils ne sont pas traités comme des versions déployées. Reproduire le défaut localement ne montre pas qu’une catégorie vide a été reçue en production, ni qu’elle explique le trafic non attribué.
<!-- dwr:end incidence -->

L’historique de déploiement est consigné par le producteur à partir du plan de contrôle de Cloudflare et a été lu avec l’agrégat conjoint (`producer_deployment_history` dans `catalog.json` : nombre de relevés, premier et dernier relevé, plus long intervalle). Il indique quel déploiement était actif chaque jour de la fenêtre ; le fichier du classificateur de la version servie est la même version de fichier qui porte le prédicat, introduit le 2026-08-24 et inchangé depuis. Un déploiement plus court que le plus long intervalle entre deux relevés ne peut pas être exclu. Les identifiants de commit attachés aux rapports quotidiens archivés ne sont pas des versions déployées et ne servent pas à établir l’incidence.

Une observation est compatible avec le défaut sans le prouver : dans cette fenêtre, aucune requête n’est enregistrée comme `unknown_automation` ni comme `claimed_actor_unverified` (voir [actor-summary.csv](../../data/editions/2026-09-15_2026-10-15-r1/actor-summary.csv)).

## Pourquoi les deux niveaux dépendants ne peuvent pas être réévalués

Le collecteur ne conserve pas les signaux Cloudflare bruts : seulement le niveau, le rôle et des identifiants de règle. La valeur de `verifiedBot` ou de la catégorie reçue pour une requête passée est donc inconnue, et les deux niveaux qui dépendent du prédicat ne peuvent pas être recalculés après coup. Ils gardent leurs libellés enregistrés, avec `attribution_assessment = recorded_classification_reliability_under_review`. Rien n’est déplacé entre surveillance, IA, navigateur ou faux positif. Ils sont écartés de la strate principale et publiés à part dans [exclusions.csv](../../data/editions/2026-09-15_2026-10-15-r1/exclusions.csv) et `actor-summary.csv`.

## La branche à origine fournisseur

`provider_origin_verified_actor` est décidé avant toute utilisation du prédicat. Ce niveau exige un acteur déclaré disposant d’une source de registre officielle (OpenAI `GPTBot`, `OAI-SearchBot`, `ChatGPT-User` ; Perplexity `PerplexityBot`, `Perplexity-User` ; `Googlebot` ; `Applebot`) et la correspondance de l’IP de la requête (`CF-Connecting-IP`) avec les plages IP officielles d’un instantané récent du registre (durée de vie de 24 heures, rafraîchi toutes les 6 heures). Cette branche n’est donc pas touchée par le défaut. Les acteurs d’Anthropic n’ont pas de tel registre et ne peuvent jamais atteindre ce niveau.

Il s’agit d’une séparation des chemins de code, pas d’un audit de toute la chaîne. L’exactitude des registres des fournisseurs, la provenance de l’en-tête IP dans les cas de Worker à Worker et les métadonnées de déploiement ne sont pas auditées de bout en bout. Le résultat principal est qualifié en conséquence : origine fournisseur enregistrée comme vérifiée par correspondance avec des plages IP officielles.

## Le contrat de Cloudflare

Documentation de Cloudflare consultée le 2026-10-16 :

- [Bot Management variables](https://developers.cloudflare.com/bots/reference/bot-management-variables/) (dernière mise à jour le 2026-09-16) définit `cf.bot_management.verified_bot` comme un booléen et `cf.verified_bot_category` comme une chaîne servant à segmenter le trafic des robots vérifiés par type et par finalité. La page ne documente pas la valeur reçue pour une requête qui ne vient pas d’un robot vérifié : chaîne vide, null ou absence.
- [Verified bots](https://developers.cloudflare.com/bots/concepts/bot/verified-bots/) (dernière mise à jour le 2026-10-08) énumère 17 chaînes de catégories historiques : Academic Research, Accessibility, Advertising & Marketing, Aggregator, AI Assistant, AI Crawler, AI Search, Archiver, Feed Fetcher, Monitoring & Analytics, Page Preview, Search Engine Crawler, Search Engine Optimization, Security, Social Media Marketing, Webhooks, Other. Une catégorie décrit un type et une finalité, jamais l’opérateur.
- [Workers Request](https://developers.cloudflare.com/workers/runtime-apis/request/) (dernière mise à jour le 2026-07-02) ne mentionne pas `verifiedBotCategory` parmi les propriétés de `request.cf`, et le paquet de types `@cloudflare/workers-types` 5.20261016.1 ne le déclare pas.

## Un correctif candidat, préparé à part

Un correctif candidat est préparé localement dans une branche distincte du producteur ; il n’est ni poussé ni déployé. La règle est fermée : seul un booléen strictement égal à `true` vaut vérification ; un `false` explicite ou une valeur malformée entraîne un refus, même à côté d’une catégorie (fermeture par défaut) ; sinon, seule une correspondance exacte avec l’une des 17 catégories historiques, épinglées le 2026-10-16, vaut vérification, et une valeur inconnue n’améliore jamais l’attribution. Il porterait une nouvelle version du classificateur, 2026-10-16.1, et laisserait intacts les libellés historiques. Il ne modifie aucun chiffre de cette édition.

## Provenance, sensibilité et trafic inconnu

- La provenance de la sollicitation ne se déduit jamais du rôle, du fournisseur ni du niveau. Une requête à origine fournisseur peut avoir été provoquée par l’exploitant du site.
- Le compte sans récupérations à la demande (`main.sensitivity.without_user_fetch.get200`, exact dans cette édition) est une analyse de sensibilité. Il ne prouve pas que les requêtes restantes sont indépendantes de toute personne.
- Le trafic inconnu ou non attribué n’est jamais imputé à l’exploitant faute d’autre explication, et n’est jamais qualifié d’IA vérifiée. Une coïncidence d’horaires est un indice, pas un appariement de requêtes.
