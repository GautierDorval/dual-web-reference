# Mises à jour

[English](../en/updates.md) · [Accueil du dépôt](../../README.fr.md)

Ce dépôt suit une opération continue, pas un rapport intemporel. Chaque édition indique quand ses données ont été mesurées, lues, générées, publiées et révisées, et ces dates restent distinctes. Le calendrier est [config/edition-calendar.json](../../config/edition-calendar.json), les éditions sont listées dans [config/editions.json](../../config/editions.json) et les revues réellement effectuées dans [config/operations.json](../../config/operations.json).

État actuel : **Actualisation périodique prévue ; préparation manuelle.** Aucune automatisation n’est activée.

## Dates de l’édition courante

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

| Champ | Sens |
|---|---|
| `period_start_inclusive` | premier jour UTC de la fenêtre mesurée, inclus |
| `period_end_exclusive` | fin exclusive de la fenêtre : le premier jour non inclus, qui n’est pas le dernier jour compté |
| `last_included_date` | dernier jour UTC effectivement inclus dans les comptes |
| `extracted_at` | intervalle (début et fin, UTC) pendant lequel l’agrégat conjoint a été lu chez le producteur ; la lecture antérieure des exports figure dans `exports_extracted_at` de `catalog.json` |
| `source_snapshot_at` | date du commit épinglé de l’archive privée utilisée pour la couverture |
| `graph_snapshot_at` | pour chaque site, date de l’instantané des sources dont sont tirés `links.csv` et le registre |
| `generated_at` | date de préparation de cette candidate ; fixée dans `config/editions.json` pour qu’une reconstruction des mêmes intrants donne les mêmes octets |
| `published_at` | première publication publique réelle de l’édition ; `null` jusque-là et jamais modifiée par une reconstruction |
| `revised_at` | date d’une correction publiée ; `null` s’il n’y en a pas |
| `latest_available_data_date` | dernier jour disponible et interprétable, pas la date de la dernière exécution réussie |
| `next_review_target` | prochaine revue hebdomadaire prévue et prochaine fenêtre mensuelle, explicitement sans garantie |

Un rendu régénéré aujourd’hui à partir de données de septembre ne devient pas une observation d’aujourd’hui. Une figure historique conserve sa propre période, même lorsque l’accueil renvoie vers une édition plus récente.

## Fenêtres mensuelles ancrées le 15

Les éditions de référence utilisent des fenêtres mensuelles consécutives en UTC, du 15 (inclus) au 15 du mois suivant (exclu) (`analysis/dwr/dates.py`). La première fenêtre est `[2026-09-15, 2026-10-15)` : 30 jours, du 15 septembre au 14 octobre inclusivement. La suivante est `[2026-10-15, 2026-11-15)` : 31 jours, du 15 octobre au 14 novembre inclusivement. Les éditions ne font donc pas toutes « 30 jours ». Le jour UTC en cours n’est jamais inclus, et une acquisition refuse une fenêtre qui n’est pas close.

## Préparation hebdomadaire et déclenchement manuel

Le calendrier prévoit une revue hebdomadaire le lundi à 13 h 17 UTC et une édition mensuelle. Les deux sont des modèles marqués `activation_status = template_not_activated`, conservés hors du dossier des workflows automatiques. Le workflow de CI hors ligne accepte aussi les exécutions manuelles `workflow_dispatch`. Il vérifie la projection publique existante ; il ne collecte aucune nouvelle donnée et ne publie aucune édition.

Ce que fait la préparation : vérifier la disponibilité des sources, préparer une édition candidate et un rapport de différences, et consigner l’état de l’opération. Ce qu’elle ne fait jamais : publier automatiquement, publier des données privées ou une candidate non revue, ou exécuter l’acquisition privée authentifiée. Celle-ci ne s’exécute que dans l’environnement privé, jamais dans une CI publique ; les jobs publics n’ont accès ni à la base du producteur ni aux sources privées.

La documentation de GitHub ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), consultée le 2026-10-16) indique que les exécutions planifiées peuvent être retardées en période de forte charge et que certains jobs en file d’attente peuvent être abandonnés ; les planifications ne s’exécutent que depuis la branche par défaut et, dans un dépôt public, elles sont désactivées après 60 jours sans activité. Aucune heure de mise à jour n’est donc promise ici.

## Délai de consolidation

Une édition mensuelle n’est préparée qu’au moins 48 heures après la clôture de la fenêtre (`consolidation_delay_hours`). Ce délai laisse aux comptes tardifs le temps d’arriver ; il ne garantit rien. Si la source reste partielle, l’édition l’indique. Les seuils de fraîcheur (revue hebdomadaire en retard après 10 jours, édition mensuelle en retard 21 jours après la consolidation) sont des règles d’exploitation, pas des engagements.

## États d’opération et relances

Chaque exécution se termine dans l’un de six états : `new_data`, `unchanged`, `source_unavailable`, `validation_failed`, `awaiting_review` et `published`. Une exécution réussie ne prouve pas l’arrivée de données nouvelles : une exécution qui ne trouve rien de nouveau est `unchanged` et ne fait jamais avancer la date des données. Les relances sont bornées (3 tentatives au plus) et idempotentes. Une exécution tardive ou relancée ne déplace jamais la fenêtre vers une période plus favorable, et une fenêtre incomplète ou manquée reste visible.

## Éditions figées et révisions

Une édition est identifiée sous la forme `<début>_<fin>-r<n>`, par exemple `2026-09-15_2026-10-15-r1`. Version du code, version du schéma, versions des règles et identifiant d’édition sont distincts (voir `versions` dans `catalog.json`). Une fois publiée, une édition est figée. Une correction crée `r2`, avec son motif, le delta chiffré, l’auteur et le relecteur de la correction, et des liens dans les deux sens (`supersedes`, `superseded_by`). La cause est l’une des suivantes : observations tardives, correction du classificateur, changement de périmètre, correction de transformation, révision de confidentialité. Aucune de ces causes n’est une croissance. Un retrait exigé pour la confidentialité ou les droits est traité comme une exception documentée, sans réécrire l’historique pour le masquer. Une correction du classificateur ouvre aussi une nouvelle époque de mesure (`measurement_epoch_id`) ; les libellés enregistrés sous une version antérieure ne sont pas réétiquetés.

## latest.json et status.json

[data/latest.json](../../data/latest.json) ne pointe que vers une édition publique revue, jamais vers un brouillon ni vers la dernière exécution réussie. Il vaut `null` aujourd’hui, avec son motif, parce qu’aucune édition n’a encore été revue et publiée.

[data/status.json](../../data/status.json) rend compte de l’état réel avec des données non sensibles seulement : `realtime = false`, les états d’automatisation, l’édition candidate et son état, la dernière revue, `latest_available_data_date` et `next_review_target`. Ce n’est pas un indicateur en temps réel. Lorsqu’une source fait défaut, la dernière édition valide est conservée et l’indisponibilité est affichée ; les séries ne sont jamais remplacées par des zéros et la date des données n’avance pas.

## Fenêtres glissantes

Une vue `rolling_30d` (les 30 derniers jours clos) pourra s’ajouter plus tard comme produit secondaire, à partir de l’agrégat quotidien conjoint qualifié ; elle n’est pas produite dans cette édition. Les fenêtres glissantes se chevauchent : leurs totaux ne sont jamais additionnés pour construire une tendance. Les comparaisons principales utilisent les éditions mensuelles, qui ne se chevauchent pas.
