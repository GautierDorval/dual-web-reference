# Éditions, revues et mises à jour

[English](../en/updates.md) · [Accueil du dépôt](../../README.fr.md)

<!-- dwr:begin edition-state -->
candidate locale; référence non approuvée; aucune évaluation scientifique indépendante documentée.
<!-- dwr:end edition-state -->

Un dépôt public, des tests réussis, une revue technique et une revue scientifique sont des faits distincts.

## Quatre états distincts

[config/editions.json](../../config/editions.json) décrit séparément la disponibilité, l’avancement de la revue, l’approbation de référence et la revue scientifique, hors du payload immuable. r1 est devenue publique dans l’intervalle de `public_availability_evidence`, borné par les reçus existants de mutation et de relecture anonyme. La création du dépôt et la date d’un commit ne donnent pas l’instant exact de disponibilité publique.

Le `catalog.json` r1 demeure identique octet par octet, y compris ses champs historiques `candidate_not_reviewed` et `published_at` nul. Ils décrivent la préparation originale et ne nient pas la disponibilité publique actuelle. `approved_release_at` est une date d’approbation distincte, consignée uniquement dans le registre externe des éditions. `revised_at` date une candidate de correction sans présumer sa publication.

<!-- dwr:begin dates -->
| Date ou état | Valeur |
|---|---|
| Édition | `2026-09-15_2026-10-15-r2` |
| Statut | candidate locale; référence non approuvée; aucune évaluation scientifique indépendante documentée |
| Disponibilité | `local_candidate` |
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

Exécuter `python -I scripts/dwr.py prepare-next --private-root <repertoire-prive-existant>` après que les étapes hors ligne de normalisation et de qualification ont produit les intrants locaux de la fenêtre. La commande choisit la **prochaine fenêtre manquante**, sans la sauter, valide les intrants, qualifie provenance et couverture, écrit une candidate privée, régénère les métriques et toutes les variantes de figures, prépare le delta et le rapport de diffusion combinée, puis s’arrête en `awaiting_review`. Un refus de diffusion demeure un refus ; une candidate privée n’est pas une projection publiable.

Le reçu authentifie les intrants et sorties. Une reprise identique donne `unchanged` ; des intrants modifiés exigent une révision distincte, et une candidate interrompue exige une inspection. Une source manquante donne `source_unavailable` ; un intrant invalide, `validation_failed`. Aucun de ces états n’avance la fraîcheur des données ni la dernière référence approuvée. Le statut privé consigne l’heure UTC réelle. La répétition complète synthétique a réussi ; aucune nouvelle observation réelle n’a été acquise et la prochaine fenêtre réelle n’est pas encore disponible.

## Planification inactive

La revue hebdomadaire du lundi à 13 h 17 UTC et la préparation mensuelle sont des **gabarits inactifs**, sans garantie de service. La CI manuelle hors ligne valide les fichiers publics existants sans recueillir de données. [status.json](../../data/status.json) distingue code prêt, essai synthétique, disponibilité réelle, planification et approbation. Les événements publics dans [operations.json](../../config/operations.json) portent des dates ou bornes étayées ; leur annotation ne prouve aucune causalité.

Le catalogue de schéma 2 exclut disponibilité, approbation, état de revue scientifique, dates de publication, pointeur de remplacement et cibles de planification. Ces faits mutables viennent du registre des éditions et de la configuration opérationnelle. Les modifier puis régénérer la présentation ne change pas l’empreinte du contenu approuvé. Le catalogue historique r1 conserve son schéma et ses octets d’origine.
