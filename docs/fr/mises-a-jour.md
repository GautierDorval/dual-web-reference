# Éditions, revues et mises à jour

[English](../en/updates.md) · [Accueil du dépôt](../../README.fr.md)

<!-- dwr:begin edition-state -->
Édition r2 : accessible publiquement ; référence non approuvée ; aucune évaluation scientifique indépendante documentée. r1 reste accessible comme édition historique figée et non approuvée.
<!-- dwr:end edition-state -->

Un dépôt public, des tests réussis, une revue technique et une revue scientifique sont des faits distincts.

## Quatre états distincts

[config/editions.json](../../config/editions.json) décrit séparément la disponibilité, l’avancement de la revue, l’approbation de référence et la revue scientifique, hors du payload immuable. r1 est devenue publique dans l’intervalle de `public_availability_evidence`, borné par les reçus existants de mutation et de relecture anonyme. La création du dépôt et la date d’un commit ne donnent pas l’instant exact de disponibilité publique.

Le `catalog.json` r1 demeure identique octet par octet, y compris ses champs historiques `candidate_not_reviewed` et `published_at` nul. Ils décrivent la préparation originale et ne nient pas la disponibilité publique actuelle. `approved_release_at` est une date d’approbation distincte, consignée uniquement dans le registre externe des éditions. `revised_at` date une candidate de correction sans présumer sa publication.

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

## Approuver sans modifier le catalogue cité

Un reçu de revue dans la configuration externe des éditions identifie l’édition, le réviseur, la preuve, l’heure de revue et les décisions technique, éditoriale et de diffusion. Son `content_digest` est le SHA-256 déterministe du manifeste ordonné chemin-vers-SHA-256 de tous les fichiers des répertoires de données et figures de l’édition, PNG de repli compris, à l’exclusion du seul manifeste dérivé `SHA256SUMS.txt`. Reçus, pointeurs opérationnels et pages d’accueil sont hors de cette portée. Leur texte ne doit pas prétendre à une approbation plus large. Il n’y a aucun cycle d’empreinte ; toute modification du payload invalide le reçu.

La fonction partagée `latest_pointer` contrôle les octets réels, la complétude du reçu et la disponibilité publique, puis ordonne les éditions admissibles par fin de fenêtre et révision. Une candidate de remplacement non approuvée ne masque pas une référence approuvée valide. [latest.json](../../data/latest.json) reste nul faute de reçu d’approbation correspondant, bien que r1 soit publique.

## Observations immuables et révision de confidentialité

Les cinq causes de révision demeurent : observations tardives, correction du classificateur, changement de périmètre, correction de transformation et révision de confidentialité. r2 relève de la **révision de confidentialité** : les lignes quotidiennes protégées et les compléments de couverture sont retenus ensemble. Métadonnées, indicateurs dérivés et présentation accompagnent ce changement. Le [rapport de delta](../../data/editions/2026-09-15_2026-10-15-r2/delta-report.json) indique que les observations ne changent pas. Ce n’est pas une croissance temporelle. Liens de retour et états opérationnels restent hors du catalogue r1 figé.

[historical-editions.json](../../config/historical-editions.json) contrôle les octets historiques du payload, des figures, des schémas et des règles. `analyze` et `render --edition ...-r1` vérifient ces octets sans les réécrire ; la projection et la préparation vers r1 sont refusées. L’[inventaire public](../../config/publication-inventory.json) comprend les états remplacés encore accessibles. Une ancienne présentation du graphe diffère ; ses tables de comptes canoniques sont identiques. Voir le contrat limité de diffusion combinée dans [confidentialité](confidentialite.md).

## Préparation manuelle de la fenêtre suivante

Les fenêtres vont du 15 inclus au 15 suivant exclu, en UTC. La fenêtre historique compte 30 jours ; `[2026-10-15, 2026-11-15)` en compte 31. La préparation attend 48 heures après la fermeture. Les tests couvrent février à 28 et 29 jours, les mois de 30 et 31 jours, le changement d’année et la consolidation UTC. Les fenêtres glissantes ne s’additionnent pas.

Exécuter `python -I scripts/dwr.py prepare-next --private-root <repertoire-prive-existant>` après que les étapes hors ligne de normalisation et de qualification ont produit les intrants locaux de la fenêtre. La commande choisit la **prochaine fenêtre manquante**, sans la sauter, valide les intrants, qualifie provenance et couverture, écrit une candidate privée, régénère les métriques et toutes les variantes de figures, prépare le delta et le rapport de diffusion combinée, puis consigne séparément préparation et diffusion. Un refus de diffusion demeure un refus ; une candidate privée n’est pas une projection publiable.

Le reçu permet de vérifier l’intégrité des intrants et sorties par leurs empreintes ; il n’authentifie pas leur auteur. Une reprise identique donne `unchanged` ; des intrants modifiés exigent une révision distincte, et une candidate interrompue exige une inspection. Une source manquante donne `source_unavailable` ; un intrant invalide, `validation_failed`. Aucun de ces états n’avance la fraîcheur des données ni la dernière référence approuvée. Le statut privé consigne l’heure UTC réelle. La répétition complète synthétique a réussi ; aucune nouvelle observation réelle n’a été acquise et la prochaine fenêtre réelle n’est pas encore disponible.

## Planification inactive

La revue hebdomadaire du lundi à 13 h 17 UTC et la préparation mensuelle sont des **gabarits inactifs**, sans garantie de service. La CI manuelle hors ligne valide les fichiers publics existants sans recueillir de données. [status.json](../../data/status.json) distingue code prêt, essai synthétique, disponibilité réelle, planification et approbation. Les événements publics dans [operations.json](../../config/operations.json) portent des dates ou bornes étayées ; leur annotation ne prouve aucune causalité.

Le catalogue de schéma 2 exclut disponibilité, approbation, état de revue scientifique, dates de publication, pointeur de remplacement et cibles de planification. Ces faits mutables viennent du registre des éditions et de la configuration opérationnelle. Les modifier puis régénérer la présentation ne change pas l’empreinte du contenu approuvé. Le catalogue historique r1 conserve son schéma et ses octets d’origine.

L’approbation exige des décisions technique, éditoriale et de diffusion concordantes dans review_status et dans le reçu lié au contenu. La page des éditions affiche l’approbation effective après validation du reçu, les décisions déclarées en texte lisible et approved_release_at seulement pendant la validité de cette approbation. data/status.json déduit l’état de la candidate de la même règle ; sa synthèse courante reprend la dernière revue d’approbation valide plutôt que la préparation antérieure.

L’index généré sépare declared_reference_release_status de reference_release_status, l’état effectif après validation du reçu.

## Limites actuelles d’écriture et de préparation

Chaque commande d’écriture canonique applique la même admission : les éditions historiques, accessibles publiquement, approuvées ou exposées selon l’inventaire sont immuables, même après déclassement de leur statut. Un registre inconnu ou invalide bloque l’écriture. Une nouvelle édition locale non approuvée peut être préparée sous verrou exclusif. La validation précède l’installation ; les erreurs interceptées déclenchent la restauration. Deux renommages de dossiers ne forment pas une transaction atomique du système de fichiers : une interruption laisse un verrou et un journal de reprise, et les lecteurs refusent l’édition jusqu’à inspection. Aucun contournement forcé n’existe. La reproduction publique des métriques et SVG compare dans un dossier temporaire distinct. La reproduction PNG exige `--preview` hors du dépôt et ne remplace jamais les figures publiques.

`prepare-next` sépare `preparation_status = complete_private` de `distribution_blocked_pending_contract` et `distribution_blocked_pending_policy_approval`. Aucun de ces états n’approuve une publication. Un verrou exclusif, un renommage du dossier préparé et le remplacement atomique de l’état empêchent les candidates concurrentes ou partielles. Le reçu détecte les intrants ou octets modifiés lors d’une reprise. Le curseur `last_processed_window_end_exclusive` est distinct de `latest_available_data_date` ; `pending_window_start` conserve la candidate en attente jusqu’à décision explicite. Une fenêtre entièrement indisponible reste en attente. Effacer cet état pour un test n’est pas une promotion réelle.

Le contrat inactif `future_projection.prepare_synthetic` accepte seulement des exemples synthétiques : ressources documentaires principales, GET 200, rôles `ai_training` ou `ai_search` et niveau `provider_origin_verified_actor`. Toutes les sorties sont dérivées après ce filtre, inventaires, métriques et données des figures compris. Les totaux, empreintes et marges de couverture des lignes rejetées sont exclus. Aucun commutateur CLI ne l’active. Deux décisions propriétaires restent distinctes : le traitement du contrat historique r2 et l’adoption d’un futur contrat de diffusion. La sélection historique de 245 requêtes n’est pas renommée en sous-ensemble automatisé de 230 requêtes.

## Errata des métadonnées historiques et confiance

r1 reste historique, non approuvée et accessible. r2 propose son remplacement par `supersedes` ; `superseded_by` décrit seulement un remplacement approuvé et reste donc null. `latest` reste null. Une préparation ou une correction logicielle ne change pas ces décisions.

Le catalogue r2 conserve exactement ses octets. Sa liste omet `disclosure.json` et `delta-report.json` : son fichier `SHA256SUMS.txt` existant fournit la liste d’intégrité des fichiers de l’édition. Les nouveaux catalogues listent leurs fichiers directs et classent explicitement les dérivés et les exclusions d’autoréférence. Un catalogue déjà exposé n’est pas corrigé silencieusement.

Un reçu SHA-256 lie les décisions au contenu et valide leur structure ; il n’authentifie pas cryptographiquement la personne nommée comme réviseur. L’autorité repose sur les écritures autorisées du dépôt et les preuves de revue. La version logicielle 0.1.0, la politique 2.0.0, les schémas de catalogue et de métriques, et les schémas des tables publiques sont des espaces de version distincts.

L’écart historique V3 ne dispose toujours pas d’une résolution qualifiée par sa source. Des tests d’époques synthétiques ne peuvent pas le clore. Les métadonnées r2 existantes n’attestent ni l’époque de classificateur ni une couverture complète ; aucune provenance manquante n’est déduite du logiciel actuel, des étiquettes ou des dates. Le registre de disponibilité précise la portée de sa preuve, sans inventer un premier instant de publication.

Avant toute adoption du contrat futur, la qualification de diffusion doit traiter aussi les métadonnées issues de toutes les lignes : `catalog.measurement.days`, `catalog.measurement.epoch_definitions`, les champs d’époque de couverture et `catalog.input_digest` (empreinte des intrants privés). Ces surfaces sont explicitement exclues du prototype synthétique inactif. Le catalogue complet de la préparation privée n’est pas une preuve de non-divulgation ni une projection autorisée.

## Revue historique close et portée de la préparation

Le registre modifiable de r1 indique désormais `not_approved` pour ses trois dimensions de revue et `historical_frozen_no_approval_recorded` pour son cycle de vie. Cela clôt le libellé trompeur de corrections en cours ; aucune revue, identité de réviseur ou approbation n’est consignée. La liste de preuves et le reçu d’approbation restent vides. Les corrections appartiennent à des candidates distinctes ; les octets de r1 restent gelés. r2 demeure accessible publiquement et non approuvée, sans nouvelle évaluation scientifique. Latest reste null.

`preparation.code_ready` signifie uniquement que `prepare-next` privé a été qualifié sur des entrées synthétiques, selon `code_ready_scope`. Cela ne certifie pas une future projection publique. `future_distribution` reste bloquée en attente d’approbation du contrat et de la politique, les sources de la prochaine fenêtre réelle restent indisponibles et `planning_activated` reste faux. L’intégration de PR 2 est consignée séparément dans le changelog ; sa date n’est pas la première disponibilité d’une édition. La fermeture de diffusion n’introduit aucune nouvelle date d’observation.
