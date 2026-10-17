# Qualité et couverture

[English](../en/quality-and-coverage.md) · [Accueil du dépôt](../../README.fr.md)

Cette page décrit ce que l’on sait de la complétude des données enregistrées, comment les lacunes et les journées partielles restent visibles, et comment les différentes formes de « rien » sont distinguées. La table par jour est [coverage.csv](../../data/editions/2026-09-15_2026-10-15-r1/coverage.csv) ; la figure G08 la présente sous forme de calendrier.

## D’où vient l’information de couverture

La couverture provient de l’archive privée des rapports quotidiens, lue à un commit épinglé dont la date est `source_snapshot_at` (`analysis/dwr/archive.py`). Seule la source de visibilité de la gouvernance est utilisée, et seulement quatre de ses tables : rapports, fenêtres de couverture, comptes quotidiens de gouvernance et comptes par site. Aucune autre table n’est lue. Un commit qui n’est pas désigné par son identifiant complet est refusé.

Pour chaque jour de la fenêtre (`edition_id`, `date_utc`), `coverage.csv` consigne l’état d’observation (`observation_status`), l’état de couverture (`coverage_status`), l’état de l’archive (`archive_status`), l’état du rapport (`archive_report_status`), le code de motif (`archive_reason_code`), les deux comptes archivés (`aggregate_count`, `v3_count`), leur différence (`aggregate_minus_v3`), l’égalité du total quotidien des exports et de celui de l’agrégat conjoint avec le compte agrégé archivé (`export_matches_archive`, `joint_matches_archive`), le nombre d’instantanés pour cette date (`snapshots_for_date`), la version du classificateur (`classifier_version`) et l’étiquette du déploiement du producteur actif ce jour-là (`producer_deployment_label`).

## Rapports partiels et codes de motif

L’archive déclare ses propres rapports partiels lorsqu’elle ne peut pas en attester la complétude. Un rapport partiel devient `coverage_status = partial_declared` ; il n’est jamais requalifié en rapport complet. Les journées partielles contiennent tout de même des requêtes réellement enregistrées, et elles sont conservées telles quelles.

| Code de motif | Sens |
|---|---|
| `COLLECTOR_WINDOW_ATTESTATION_MISSING` | le collecteur n’a pas attesté la fenêtre de couverture de ce jour |
| `AGGREGATE_V3_COUNT_MISMATCH` | les deux comptes que l’archive conserve pour ce jour, le compte agrégé et le compte V3, diffèrent |

Les deux comptes sont publiés (`aggregate_count`, `v3_count`) avec leur différence (`aggregate_minus_v3`). L’écart est signalé, pas corrigé, et aucun des deux comptes n’est préféré à l’autre.

## Un instantané par date, jamais compté deux fois

L’archive peut contenir plusieurs instantanés d’une même date lorsqu’un rapport est capturé de nouveau. Un seul doit être marqué comme courant : c’est lui qui est utilisé, les autres sont listés comme remplacés et ne sont jamais additionnés. Si une date n’a aucun instantané courant ou en a plusieurs, l’étape s’arrête (`archive_current_snapshot_ambiguous`) au lieu de choisir. `snapshots_for_date` indique combien d’instantanés existent pour chaque date. Une date sans aucun rapport est consignée comme `observation_unavailable`, jamais comme zéro.

## Couverture de cette édition

<!-- dwr:begin coverage -->
30 jours sur 30 ont des lignes archivées ; les 30 rapports d’archive sont partiels (déclarés), 28 sans attestation de fenêtre du collecteur et 2 avec un écart agrégat/V3 d’une requête (2026-10-06, 2026-10-13). Somme agrégée archivée 24 815, somme V3 24 813. Des lignes sur 30 jours ne prouvent pas une couverture intégrale.
<!-- dwr:end coverage -->

La concordance des totaux quotidiens des exports et de l’agrégat conjoint avec les comptes agrégés archivés (`export_matches_archive`, `joint_matches_archive`) n’est pas une validation indépendante : tous proviennent de la même chaîne productrice. La présence de lignes un jour donné montre que quelque chose a été enregistré, pas que tout l’a été.

## Cinq états jamais confondus

| État | Forme dans les fichiers | Sens |
|---|---|---|
| Zéro mesuré | `request_count = 0`, `observation_status = observed_zero`, dans `daily-family-summary.csv` seulement | la cellule est écrite explicitement : la table du producteur ne compte aucune requête de ce type pour ce jour, cette famille et ce rôle |
| Ligne absente | aucune ligne pour une combinaison dans `consultations.csv` ou `daily-summary.csv` ; pour un couple entier, `window_rows_status` vaut `registered_now_no_row_in_window` ou `not_in_collector_window_export` dans `resources.csv` | la table du producteur ne contient aucune requête enregistrée pour cette combinaison dans la fenêtre ; ce n’est pas une absence mesurée sur le Web |
| Null | cellule vide, avec une colonne d’état ou un `status` d’indicateur | la valeur n’est pas disponible ou pas calculable, par exemple une part dont le dénominateur est nul (`status = not_calculable`) |
| Supprimé | `suppression_status` autre que `not_suppressed`, valeur vide | la valeur a été retenue pour confidentialité ; elle n’est jamais écrite comme zéro (aucune cellule n’est supprimée dans cette édition) |
| Source indisponible | l’étape s’arrête avec `source_unavailable` ; un graphe garde `status = source_unavailable` ; `status.json` conserve la dernière édition valide | la source n’a pas pu être lue ; rien n’est publié à sa place |

Une table vide est publiée avec son motif dans `catalog.json` (`status = empty_with_reason`, `empty_reason`) ; aucune table de cette édition n’est vide. Un indicateur qui ne peut pas être calculé est vide, avec son statut et son motif, jamais zéro.

## Déploiements du producteur

`producer_deployment_label` (`pd01`, `pd02`, etc., dans l’ordre de leur date d’effet) désigne le déploiement du producteur, ou les déploiements joints par `+`, actifs à un moment quelconque de chaque jour UTC, d’après l’historique de déploiement du producteur lui-même, consigné à partir du plan de contrôle de Cloudflare et lu avec l’agrégat conjoint. Les étiquettes remplacent les identifiants privés de déploiement, de version et de commit, qui restent dans le verrou interne. L’historique est une suite de relevés : un déploiement plus court que le plus long intervalle entre deux d’entre eux ne peut pas être exclu (`producer_deployment_history` dans `catalog.json`). Les identifiants de commit attachés aux rapports quotidiens archivés changent pendant la fenêtre sans aucun déploiement dans cet historique ; ce ne sont pas des versions déployées, et ils ne sont pas utilisés. Un code simplement disponible dans un dépôt n’est jamais traité comme déployé. Le [tableau d’incidence](attribution.md) utilise ces étiquettes.

## Instantané du graphe et octets déployés

[links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv) est extrait des dépôts sources des sites à des commits épinglés ; `graph_snapshot_at` en donne la date pour chaque site. Ce sont des fichiers sources, pas les octets servis aux clients pendant la fenêtre. Une relation signifie « cette référence est écrite dans ce fichier de cet instantané », avec le fichier et la ligne comme pièce. Elle ne prouve pas qu’un client l’a suivie, et une relation absente signifie « non trouvée dans ce graphe », pas l’absence de toute référence ailleurs. Aucune URL trouvée dans un instantané n’est visitée. Les extraits des cas sont vérifiés mot pour mot (espaces normalisées) contre les mêmes fichiers d’instantané ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r1/case-checks.json)). Voir [découverte et maillage](decouverte-et-maillage.md).

## Comptes non revérifiés

`GET 200` est le statut enregistré par le collecteur. Le type de contenu et les octets servis ne sont pas revérifiés, et les compteurs sont des agrégats quotidiens écrits par le producteur pendant son fonctionnement. Les sommes de contrôle par jour de l’extraction conjointe (`acquire-readonly`), lues avant et après celle-ci, étaient identiques : les compteurs n’ont pas changé pendant la lecture. Elles ne font pas de cette extraction un instantané transactionnel.
