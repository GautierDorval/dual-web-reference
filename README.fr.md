# Dual Web Reference

[English](README.md)

Ce dépôt documente une couche de **fichiers de gouvernance** publiée sur trois sites d’un même écosystème (gautierdorval.com, pagup.com, better-robots.com), explique le rôle de ces fichiers et décrit les accès HTTP enregistrés vers eux. Son sujet est exclusivement documentaire.

Le Dual Web, au sens de sa [définition canonique](https://gautierdorval.com/definitions/ssa-e-a2-dual-web/), présente une couche documentaire complémentaire aux pages d’un site. Ses fichiers explicitent notamment l’identité, le contexte, les sources, les relations et les limites d’interprétation. Ils sont publiés comme des ressources accessibles, reliées au site ou à d’autres documents. La couche n’est ni cachée ni réservée aux machines, et une politique publiée déclare un cadre sans prouver qu’un système l’applique. Voir [le modèle](docs/fr/modele.md).

Cette première édition décrit **l’existence et la répartition des accès enregistrés**, y compris au-delà de `llms.txt`. Elle ne mesure ni de meilleures réponses, ni une adoption, ni une visibilité dans les moteurs, ni une indexation, ni une conformité, ni un effet causal du maillage.

## Édition courante : dates et statut

<!-- dwr:begin dates -->
| Date ou état | Valeur |
|---|---|
| Édition | `2026-09-15_2026-10-15-r1` |
| Statut | candidate, non revue, non publiée |
| Période mesurée | du 15 septembre au 14 octobre 2026 inclusivement, en UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-16` |
| published_at | `null` (non publiée) |
| revised_at | `null` |
| latest_available_data_date | `2026-10-14` |
| next_review_target | revue hebdomadaire `2026-10-19T13:17:00Z`, non garantie |
| Mises à jour | actualisation périodique prévue ; préparation manuelle (automatisation non activée) |
<!-- dwr:end dates -->

## Résultat principal et sa qualification

<!-- dwr:begin headline -->
Dans la population documentaire principale, le collecteur a enregistré **245 requêtes GET 200** de rôles IA dont l’origine fournisseur a été enregistrée comme vérifiée par correspondance avec des plages IP officielles, sur **174 couples site-chemin distincts**.

Parmi ces requêtes, **6** visaient `/llms.txt` et **239** d’autres fichiers de gouvernance, soit **97.6 %** de la même sélection (même période, mêmes sites, même périmètre, même méthode, même statut et même niveau d’identification). Cette part décrit la répartition des requêtes enregistrées ; ce n’est pas un taux d’adoption.

Par site : gautierdorval.com 62, pagup.com 61, better-robots.com 122. Par rôle d’acteur enregistré : collecte pour entraînement 200, recherche IA 30, récupération à la demande 15 ; sans les récupérations à la demande, il reste 230 requêtes (une lecture de sensibilité, pas une preuve d’indépendance).

Qualification : l’attribution à origine fournisseur n’utilise pas le prédicat Cloudflare en revue ; les niveaux qui l’utilisent restent à part. Le relevé interne initial comptait 372 requêtes de cette nature sur un périmètre plus large incluant des fichiers de méthode, de protocole et de description de services ; l’écart est détaillé dans [le delta de périmètre](docs/fr/perimetre.md).
<!-- dwr:end headline -->

## Deux graphiques

<!-- dwr:begin figures-main -->
<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r1/G02.fr.compact.svg"><img src="figures/2026-09-15_2026-10-15-r1/G02.fr.svg" alt="Barres horizontales empilées, trois sites et par site, répartissant les requêtes GET 200 des rôles IA à origine fournisseur entre /llms.txt et les autres fichiers de gouvernance ; comptes, totaux et parts sont écrits sous chaque barre." width="960"></picture>

Table de données : [G02.csv](figures/2026-09-15_2026-10-15-r1/G02.csv)

<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r1/G05.fr.compact.svg"><img src="figures/2026-09-15_2026-10-15-r1/G05.fr.svg" alt="Trois listes de barres horizontales classées, une par site, des dix fichiers de la population principale ayant le plus de requêtes GET 200 IA à origine fournisseur." width="960"></picture>

Table de données : [G05.csv](figures/2026-09-15_2026-10-15-r1/G05.csv)
<!-- dwr:end figures-main -->

Toutes les figures (G01 à G10), avec leurs tables de données et leurs textes alternatifs, sont listées dans [figures.json](data/editions/2026-09-15_2026-10-15-r1/figures.json) et dans le [dossier des figures](figures/2026-09-15_2026-10-15-r1/).

## Trois cas

<!-- dwr:begin cases -->
| Site | Angle | Page de départ | Ressources | GET 200 IA à origine fournisseur sur ces ressources |
|---|---|---|---:|---:|
| [gautierdorval.com](cases/gautierdorval.com/README.fr.md) | Identité d’une personne, et distinction entre définitions, affirmations, sources, limites et contenus ordinaires du site. | `/en/ai-use-policy/` | 9 | 10 |
| [pagup.com](cases/pagup.com/README.fr.md) | Contexte d’une organisation, périmètre de son offre, références et limites documentaires. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](cases/better-robots.com/README.fr.md) | Contexte d’un produit, capacités déclarées, limites, et différence entre la publication d’une règle et le comportement effectif d’un robot. | `/governance/ai-usage-policy` | 9 | 15 |

Les trois sites appartiennent à l’écosystème d’un même auteur : trois applications d’une même démarche, pas trois réplications indépendantes. robots.txt est exclu de la dernière colonne.
<!-- dwr:end cases -->

## Fichiers, données, méthode et reproduction

- Catalogue de l’édition avec empreintes et dates : [catalog.json](data/editions/2026-09-15_2026-10-15-r1/catalog.json) ; résultats nommés : [metrics.json](data/editions/2026-09-15_2026-10-15-r1/metrics.json).
- Ressources et périmètre : [resources.csv](data/editions/2026-09-15_2026-10-15-r1/resources.csv), produit à partir du [registre de périmètre](config/scope-registry.csv) versionné.
- Relations documentaires trouvées dans les instantanés sources : [links.csv](data/editions/2026-09-15_2026-10-15-r1/links.csv).
- Accès : [consultations.csv](data/editions/2026-09-15_2026-10-15-r1/consultations.csv), [resource-summary.csv](data/editions/2026-09-15_2026-10-15-r1/resource-summary.csv), [daily-summary.csv](data/editions/2026-09-15_2026-10-15-r1/daily-summary.csv), [actor-summary.csv](data/editions/2026-09-15_2026-10-15-r1/actor-summary.csv) ; couverture et exclusions : [coverage.csv](data/editions/2026-09-15_2026-10-15-r1/coverage.csv), [exclusions.csv](data/editions/2026-09-15_2026-10-15-r1/exclusions.csv) ; schémas des tables dans [schemas](schemas/).
- Méthode : [méthode](docs/fr/methode.md), [périmètre](docs/fr/perimetre.md), [attribution](docs/fr/attribution.md), [qualité et couverture](docs/fr/qualite-et-couverture.md), [rôles des fichiers](docs/fr/roles-des-fichiers.md), [découverte et maillage](docs/fr/decouverte-et-maillage.md), [confidentialité](docs/fr/confidentialite.md), [glossaire](docs/fr/glossaire.md).
- Recalculer hors ligne chaque chiffre publié : [reproduction](docs/fr/reproduction.md). La collecte, la classification du producteur et l’extraction reposent sur des sources privées et ne peuvent pas être rejouées à partir des seuls fichiers publics.
- Présentation statique (français et anglais), construite localement avec `python -I scripts/dwr.py build-site`.

## Limites essentielles

- **Attribution.** Le résultat principal ne garde que les requêtes dont l’origine fournisseur a été enregistrée par correspondance avec des plages IP officielles. Deux autres niveaux enregistrés dépendent d’un prédicat Cloudflare qui accepte aussi une catégorie vide ; ils portent la mention « classification enregistrée, fiabilité en cours de revue » et restent à part. Reproduire le défaut ne montre pas qu’il s’est produit en production. Voir [attribution](docs/fr/attribution.md).
- **Qui a déclenché une requête est inconnu.** Une requête à origine fournisseur peut avoir été déclenchée par n’importe qui, y compris l’exploitant du site. Rien ici n’est une adoption extérieure indépendante.
- **Voies de découverte.** `llms.txt` est un point d’entrée possible, pas un protocole obligatoire. Une URL peut être connue autrement que par un lien interne. Le graphe des relations montre ce qu’un lecteur peut suivre dans un instantané, pas des parcours suivis par des robots. Voir [découverte et maillage](docs/fr/decouverte-et-maillage.md) et la [comparaison avec les études centrées sur llms.txt](docs/fr/etudes-llms-txt.md).
- **Couverture.** Tous les rapports quotidiens archivés de la fenêtre sont partiels (déclarés). Des lignes pour chaque jour ne prouvent pas une couverture intégrale. Voir [qualité et couverture](docs/fr/qualite-et-couverture.md).
- **Données de cette édition.** Les comptes viennent d’une extraction unique, bornée et en lecture seule, de la table d’agrégats quotidiens du collecteur, contre-vérifiée avec les exports du relevé interne initial : les deux concordent partout, mais proviennent de la même chaîne productrice ; c’est une cohérence, pas une validation indépendante. Voir [limites](docs/fr/limites.md).

## Mises à jour, historique et citation

Le projet est une opération suivie dans le temps, pas un rapport intemporel. Les éditions mensuelles de référence utilisent des fenêtres consécutives ancrées le 15 (UTC, fin exclusive) ; la suivante couvre du 15 octobre au 14 novembre 2026 inclusivement (31 jours). Une revue hebdomadaire est prévue. **Actualisation périodique prévue ; préparation manuelle** : aucune automatisation n’est active. Une correction crée une nouvelle révision de l’édition, avec son motif et son delta. Voir [mises à jour](docs/fr/mises-a-jour.md), [CHANGELOG.md](CHANGELOG.md), [data/index.json](data/index.json) et [data/status.json](data/status.json).

Pour citer une édition, indiquer son identifiant et l’empreinte SHA-256 de son `catalog.json` ; voir [CITATION.cff](CITATION.cff). Licences : MIT pour le code, CC BY 4.0 pour la documentation et les données, hors extraits cités et noms de tiers ; voir [NOTICE.md](NOTICE.md).
