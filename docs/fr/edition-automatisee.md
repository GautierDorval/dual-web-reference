# Mois 2 : accès automatisés, profil B

Cette édition couvre le 15 octobre au 14 novembre 2026 inclus, UTC. Elle contient 223 accès sélectionnés sur 135 ressources distinctes site/chemin, réparties sur trois sites d’un même écosystème. Ces sites ne constituent pas des réplications indépendantes.

## Sélection et limites de mesure

La sélection retient la population documentaire principale, GET 200, le niveau d’origine fournisseur avec acteur vérifié enregistré, et les rôles enregistrés d’entraînement ou de recherche. Elle comprend 103 accès classés entraînement et 120 classés recherche. Ces étiquettes décrivent des classifications consignées : elles ne démontrent ni entraînement effectif, ni compréhension sémantique, ni adoption, ni citation, ni effet SEO.

L’archive contient 27 dates observées sur 31, toutes à couverture partielle déclarée. Les 17, 25, 26 et 27 octobre sont indisponibles, et non nuls. Le classificateur du producteur n’est pas attesté et la transition intrajournalière de mesure n’est pas résolue. La croissance M1/M2 n’est pas qualifiée et demeure null ; les populations et conditions de mesure diffèrent. Aucun graphe source M2 n’est qualifié. Les études de cas M1 restent des descriptions historiques de leur propre instantané.

## Ce que divulgue le profil B

Les sept tables contiennent des détails mensuels par ressource et acteur, des totaux mensuels par famille documentaire, des marges quotidiennes par site et rôle, ainsi qu’une couverture catégorielle minimale. Elles ne contiennent ni marges quotidiennes par famille ni partitions par époque. Les accès à la demande restent retenus selon U0, avec un compte null et une initiative inconnue. Les acteurs exclus et les diagnostics des sources ne sont pas publiés.

Les marges restantes peuvent encore contraindre des cellules automatisées individuelles, particulièrement dans les petits groupes. Les publications historiques et les informations auxiliaires restent accessibles. Ce profil n’est pas une anonymisation et ne garantit pas une non-reconstruction universelle.

## Statut et citation

Consulter le [registre des éditions](../../config/editions.json) pour la disponibilité et les décisions de revue courantes. `projection.json` conserve les métadonnées de préparation locale non approuvée ; ces champs immuables ne constituent pas le registre courant. Le catalogue public explicite cette distinction. Un audit technique ne vaut ni autorisation propriétaire ni évaluation scientifique indépendante.

Citer l’identifiant de l’édition, le SHA-256 de `catalog.json` et le manifeste de contenu. `data/latest.json` expose la dernière candidate séparément de la dernière référence approuvée. Un build réussi ne crée jamais une approbation.

## Reproduire sans acquérir de données

Avec Python 3.12 ou une version ultérieure, exécuter les commandes suivantes depuis ce dépôt :

```powershell
python -I scripts/dwr.py analyze
python -I scripts/dwr.py render
python -I scripts/dwr.py build-site
python -I scripts/dwr.py verify
```

L’adaptateur M2 valide le schéma fermé et recalcule tous les octets distribués depuis la projection canonique. Il ne contacte ni le producteur, ni les sites mesurés, ni un laboratoire. Cette reproduction publique vérifie les calculs et la présentation ; elle ne peut authentifier indépendamment l’acquisition privée ni établir une couverture complète.

## Fichiers canoniques

- [catalog.json](../../data/editions/2026-10-15_2026-11-15-r1/catalog.json)
- [manifest.json](../../data/editions/2026-10-15_2026-11-15-r1/manifest.json)
- [projection.json](../../data/editions/2026-10-15_2026-11-15-r1/projection.json)
- [schema.json](../../data/editions/2026-10-15_2026-11-15-r1/schema.json)
- [metrics.json](../../data/editions/2026-10-15_2026-11-15-r1/metrics.json)
- [on-demand.json](../../data/editions/2026-10-15_2026-11-15-r1/on-demand.json)
- [consultations.csv](../../data/editions/2026-10-15_2026-11-15-r1/consultations.csv)
- [resources.csv](../../data/editions/2026-10-15_2026-11-15-r1/resources.csv)
- [resource-summary.csv](../../data/editions/2026-10-15_2026-11-15-r1/resource-summary.csv)
- [actor-summary.csv](../../data/editions/2026-10-15_2026-11-15-r1/actor-summary.csv)
- [family-summary.csv](../../data/editions/2026-10-15_2026-11-15-r1/family-summary.csv)
- [daily-summary.csv](../../data/editions/2026-10-15_2026-11-15-r1/daily-summary.csv)
- [coverage.csv](../../data/editions/2026-10-15_2026-11-15-r1/coverage.csv)
- [figures.json](../../data/editions/2026-10-15_2026-11-15-r1/figures.json)
