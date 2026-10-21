# Confidentialité et diffusions combinées

[English](../en/privacy.md) · [Accueil du dépôt](../../README.fr.md)

La [politique actuelle](../../config/small-cell-policy.json) est la **version 2.0.0** ; sa revue de diffusion figure au registre externe des éditions. Elle décrit des protections d’agrégats testées, pas une anonymisation universelle ni l’impossibilité de toute inférence. r1 et ses [règles originales](../../config/history/2026-09-15_2026-10-15-r1/small-cell-policy.json) restent des pièces historiques immuables.

## Ce qui change

L’ancien seuil de dix chemins protégés sur l’édition ne prouvait pas la non-reconstruction de cellules quotidiennes. Deux tests fictifs exercent la vraie fonction historique : un seul jour actif peut dater dix cellules mensuelles ; la différence entre deux révisions peut situer une cellule chemin-jour ajoutée. La nouvelle porte refuse ces combinaisons. Ces tests démontrent des défauts du contrôle, pas une fuite réelle ni l’identification d’une personne dans r1. Ses groupes documentaires protégés couvrent toute la fenêtre, plutôt que le seul jour actif du premier exemple. Aucun retrait n’est engagé sur cette base.

L’ancienne prose exagérait aussi l’absence de récupérations à la demande des sorties quotidiennes. Dans r1, elles étaient **incluses dans le groupe quotidien protégé combiné**, sans rôle séparé, même si G01 et les mesures quotidiennes automatisées les excluaient. Les noms d’agents logiciels au grain de l’édition avaient déjà été autorisés par le propriétaire le 2026-10-17 ; cette même confirmation n’était plus attendue.

## Contrat actuel de diffusion

| Surface | Règle actuelle |
|---|---|
| Cellules ressource-acteur de l’édition et résumés de récurrence | r2 reprend les mêmes cellules historiques inventoriées. Toute observation protégée fine nouvelle ou modifiée est bloquée jusqu’à l’évaluation d’un contrat plus grossier distinct. |
| Lignes quotidiennes protégées | Retenues, y compris récupérations à la demande, strates non attribuées, non vérifiées, à vérification échouée et à nom déclaré sur signal réseau. Le libellé réseau dépendant du prédicat en revue ne permet pas d’exclure un navigateur. |
| Totaux et différences de couverture quotidiens | Retenus ensemble : soustraire le trafic non protégé pourrait retrouver un total protégé. Une cellule vide signifie retenue, jamais zéro mesuré. |
| Cellules quotidiennes et par famille automatisées à origine fournisseur | Conservées depuis les agrégats conjoints exacts ; aucune redistribution de comptes mensuels. |
| Éditions antérieures accessibles, révisions remplacées comprises | Incluses dans l’inventaire de publication. Un inventaire modifié ou absent bloque la diffusion fine avec l’état `not_assessed`. |
| Mesures dérivées, figures, alternatives, cas et téléchargements | Générés à partir des tables canoniques et vérifiés contre elles. Toute nouvelle surface indépendante exige une évaluation. |

Le [rapport de diffusion combinée](../../data/editions/2026-09-15_2026-10-15-r2/disclosure.json) consigne la décision et les limites. Le contrôle n’efface pas les marges r1 déjà publiques et ne couvre pas toute source auxiliaire tierce inconnue. Un acteur automatisé unique peut être déduit de son rôle ; une famille à ressource unique peut révéler le compte quotidien de cette ressource automatisée. Ces inférences sur un agent logiciel diffèrent de l’identification d’une personne. Les anciennes exceptions de `robots_control` et des compartiments de sondes étaient des décisions de diffusion, pas des propriétés anonymisantes des chemins.

## Minimisation et preuves

Les projections publiques ne comportent aucune IP de requête, chaîne d’agent utilisateur brute ou hachée, identifiant de témoin/session/appareil, secret, référent libre, chaîne de requête, transcription de conversation ou date du premier/dernier accès par chemin. Le trafic inconnu n’est pas requalifié en activité du propriétaire. Aucune nouvelle durée de conservation ni collecte rétroactive n’est autorisée.

La porte vérifie les termes et identifiants privés configurés ainsi que des représentations dangereuses connues. Les exports privés et instantanés sources demeurent hors du dépôt. Les empreintes établissent l’identité des octets, pas la vérité de la collecte ; les tests fictifs ne prouvent pas une divulgation personnelle réelle. Un problème se signale par [le canal privé autorisé](../../SECURITY.md).

<!-- dwr:begin history-inventory -->
L’inventaire décrit 8 états historiques nommés, pas 8 commits. Les octets déclarés sont vérifiés localement ; l’exhaustivité des références Git exige une preuve distincte. Les copies tierces inconnues et leurs données auxiliaires restent hors de cette preuve.
<!-- dwr:end history-inventory -->

La porte combinée rapproche les totaux de requêtes par ressource, mais ne peut pas reconstituer indépendamment ses jours actifs à partir des cellules de l’édition. Pour une sortie historique protégée répétée, ces comptes de jours doivent correspondre aux octets inventoriés. Pour une nouvelle préparation privée, validate_inputs compare tous les comptes par ressource, jours compris, à la source conjointe réelle. Une projection synthétique arbitraire isolée ne constitue pas cette préparation adossée à la source.

## Pièces de décision à la demande, sans nouvelle série publique

La proposition synthétique inactive distingue trois choix. U0 retourne les mêmes `withheld_not_zero` et compte null que les lignes protégées soient absentes, uniques ou nombreuses. U2 reporte le choix sans agrégat réel. U1 évalue un total **synthétique privé** de la fenêtre sur les trois sites, conserve les niveaux d’attribution et omet jours, chemins, sites et noms d’acteurs dans sa sortie. Son approbation publique est explicitement fausse. Aucun choix n’active une chaîne ni ne change la sélection historique de 245 accès ou le sous-ensemble automatisé distinct de 230.

Retirer le détail ne prouve pas l’impossibilité de reconstruction. Des contre-exemples exécutables couvrent le passage de zéro à un, les différences entre révisions, les fenêtres chevauchantes avec marge entrante connue, le retrait d’un site contributeur, la soustraction d’un total global, la récupération par le dénominateur d’une autre sortie et les divulgations publiques antérieures. Aucun seuil, arrondi ou intervalle de comptes n’est présenté comme garantie d’anonymat. U0 est la recommandation conservatrice en attente de décision explicite ; B1 détail automatisé, B2 couverture minimale et B3 traitement à la demande peuvent être décidés séparément.

Le rôle, le niveau d’attribution et la provenance de l’initiation sont distincts. `user_initiated_fetch` ne démontre ni une sollicitation par un utilisateur extérieur ni la restitution du résultat dans une réponse. Le prototype déclare la provenance d’initiation inconnue. Cette proposition n’efface pas les divulgations historiques ; la comparabilité qualifiée à la source reste nécessaire avant d’utiliser un sous-ensemble historique comme référence future.
