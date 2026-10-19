# Dual Web Reference

[English](README.md)

Ce dépôt étudie les fichiers de gouvernance, leurs relations documentaires et leurs accès HTTP enregistrés.

<!-- dwr:begin edition-state -->
Édition r2 : accessible publiquement ; référence non approuvée ; aucune évaluation scientifique indépendante documentée. r1 demeure publique et figée.
<!-- dwr:end edition-state -->

<!-- dwr:begin headline -->
**174 URL documentaires touchées · 245 accès · 3 sites d’un même écosystème.** Du 15 septembre au 14 octobre 2026 inclusivement, en UTC.

[Voir le cas Gautier Dorval](cases/gautierdorval.com/README.fr.md) : partir de la politique IA, distinguer identité, sources et limites, puis examiner les relations de l’instantané.

Sélection principale : requêtes GET 200 de rôles IA, origine fournisseur enregistrée comme vérifiée par correspondance avec des plages IP officielles. **Couverture partielle déclarée.** Une requête ne prouve ni compréhension, ni adoption, ni effet causal.

**6** accès visaient `llms.txt` et **239** les autres fichiers. La part de 97.6 % hors `llms.txt` décrit cette sélection ; elle ne mesure pas une préférence. Parmi les 269 ressources principales ayant des lignes, tous acteurs, méthodes et statuts confondus, 174 ont été touchées dans la sélection principale. Ce dénominateur n’est pas l’inventaire historique complet du Web documentaire.

Par ressource avec lignes : 6/3 = 2 accès pour `llms.txt`, contre 239/266 = 0.90 ailleurs. Disponibilité et exposition ne sont pas contrôlées.

GPTBot : 200 ; OAI-SearchBot : 14 ; PerplexityBot : 16 ; ChatGPT-User : 15. La famille OpenAI représente 229/245 accès ; ce n’est pas une part de marché de tous les agents.

Hors récupérations à la demande : 230 accès automatisés sur 12 jours ; les trois journées les plus actives en portent 185, soit 80.4 %. 133 des 174 couples ont des accès sur un seul jour.

Exclusion explicite : 17 requêtes sous ces quatre noms ont une **vérification d’origine échouée selon le producteur**, sur 262 requêtes des seuls niveaux fournisseur vérifié et vérification échouée retenus. Aucune usurpation n’est démontrée. Sur PAGUP : aucun GET 200 de `llms.txt` dans cette sélection et cette fenêtre ; un accès antérieur reste possible.
<!-- dwr:end headline -->

## Lire un instantané documentaire

La politique IA du cas Gautier Dorval part de `/en/ai-use-policy/` (français : `/ai-usage-policy/`). Son entrée machine déclarée est `/.well-known/ai-governance.json`. L’instantané du cas est daté dans sa fiche ; ces liens documentaires ne sont pas une session observée. Les chemins restent copiables pour éviter de créer du trafic depuis cette présentation.

## Deux lectures complémentaires

<!-- dwr:begin figures-main -->
<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r2/G02.fr.compact.svg"><img src="figures/2026-09-15_2026-10-15-r2/G02.fr.svg" alt="Barres horizontales empilées, trois sites et par site, répartissant les requêtes GET 200 des rôles IA à origine fournisseur entre /llms.txt et les autres fichiers de gouvernance ; comptes, totaux et parts sont écrits sous chaque barre." width="960"></picture>

Table de données : [G02.csv](figures/2026-09-15_2026-10-15-r2/G02.csv)

<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r2/G05.fr.compact.svg"><img src="figures/2026-09-15_2026-10-15-r2/G05.fr.svg" alt="Trois listes de barres horizontales classées, une par site, des dix fichiers de la population principale ayant le plus de requêtes GET 200 IA à origine fournisseur." width="960"></picture>

Table de données : [G05.csv](figures/2026-09-15_2026-10-15-r2/G05.csv)
<!-- dwr:end figures-main -->

## Trois cas, un même écosystème

<!-- dwr:begin cases -->
| Site | Angle | Page de départ | Ressources | GET 200 IA à origine fournisseur sur ces ressources |
|---|---|---|---:|---:|
| [gautierdorval.com](cases/gautierdorval.com/README.fr.md) | Identité d’une personne, et distinction entre définitions, affirmations, sources, limites et contenus ordinaires du site. | `/en/ai-use-policy/` (EN ; FR : `/ai-usage-policy/`) | 9 | 10 |
| [pagup.com](cases/pagup.com/README.fr.md) | Contexte d’une organisation, périmètre de son offre, références et limites documentaires. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](cases/better-robots.com/README.fr.md) | Contexte d’un produit, capacités déclarées, limites, et différence entre la publication d’une règle et le comportement effectif d’un robot. | `/governance/ai-usage-policy` | 9 | 15 |

Les trois sites appartiennent à l’écosystème d’un même auteur : trois applications d’une même démarche, pas trois réplications indépendantes. robots.txt est exclu de la dernière colonne.
<!-- dwr:end cases -->

## Méthode et données

1. Délimiter les fichiers et leurs fonctions dans un registre daté.
2. Conserver les catégories, méthodes et statuts enregistrés.
3. Appliquer le périmètre principal et les contrôles de diffusion.
4. Recalculer tables, indicateurs et figures depuis les mêmes observations.

[Comprendre les fichiers](docs/fr/roles-des-fichiers.md) · [Méthode](docs/fr/methode.md) · [Attribution](docs/fr/attribution.md) · [Confidentialité](docs/fr/confidentialite.md) · [Reproduction](docs/fr/reproduction.md).

[Catalogue r2](data/editions/2026-09-15_2026-10-15-r2/catalog.json) · [Métriques](data/editions/2026-09-15_2026-10-15-r2/metrics.json) · [Ressources](data/editions/2026-09-15_2026-10-15-r2/resources.csv) · [Accès](data/editions/2026-09-15_2026-10-15-r2/consultations.csv) · [Relations](data/editions/2026-09-15_2026-10-15-r2/links.csv).

## Limites essentielles

Trois sites d’un seul écosystème ne sont pas trois réplications indépendantes. La couverture est partielle, les voies de découverte ne sont pas établies et l’origine fournisseur reste une classification du producteur. Un GET 200 ne prouve ni lecture sémantique, ni adoption, ni meilleure réponse, ni effet SEO. Les données privées de collecte ne sont pas réexécutables depuis ce dépôt. [Limites détaillées](docs/fr/limites.md).

## Dates, éditions et maintenance

<!-- dwr:begin dates -->
| Date ou état | Valeur |
|---|---|
| Édition | `2026-09-15_2026-10-15-r2` |
| Statut | accessible publiquement ; référence non approuvée ; aucune évaluation scientifique indépendante documentée |
| Disponibilité | `publicly_accessible` |
| Approbation de référence | `not_approved` |
| Période mesurée | du 15 septembre au 14 octobre 2026 inclusivement, en UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-19` |
| approved_release_at | `null` |
| revised_at | `2026-10-19` |
| latest_available_data_date | `2026-10-14` |
| Mises à jour | actualisation périodique prévue ; préparation manuelle (automatisation non activée) |
<!-- dwr:end dates -->

[Statuts et revue](docs/fr/mises-a-jour.md) · [CHANGELOG](CHANGELOG.md) · [CITATION.cff](CITATION.cff) · [NOTICE](NOTICE.md) · [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md).

Prévisualisation locale, sans publication ni cadence active :

```powershell
python -I scripts/dwr.py analyze
python -I scripts/dwr.py render
python -I scripts/dwr.py build-site
python -m http.server 8000 --directory site/dist --bind localhost
```
