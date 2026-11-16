# Reçu local du mandat Common Crawl

Date : 16 novembre 2026. Statut : **correctif local consolidé après audit Codex, couverture d’archive partielle**. Résultat détaillé dans [le rapport](REPORT.fr.md) et [la matrice](matrix.csv).

## Travail livré

- Neuf URL exactes sélectionnées avant toute requête CDX, avec leurs motifs, observations et empreintes documentaires. Original privé immuable ; copie de revue expurgée du seul identifiant Git.
- Deux index publiés vérifiés ; 18 interrogations CDX, un catalogue et un WARC. 47 159 octets de corps téléchargés au total, dont 9 003 octets WARC compressés. Aucune pagination, relance, visite des sites ou requête D1.
- Une capture exploitable, dans M1 : le graphe JSON-LD de gautierdorval.com du 14 octobre à 07:54:39 UTC. Corps archivé de 50 179 octets identique à l’instantané détenu, trois empreintes source SHA-1 concordantes.
- Sept réponses d’absence explicite et dix erreurs CDX, trois HTTP 502 et sept HTTP 504. Aucune capture exploitable trouvée dans M2 ; aucune conclusion d’absence générale.
- Utilitaire ponctuel en bibliothèque standard, trente et un tests ciblés, matrice, sources, métadonnées, commandes et manifestes SHA-256. Les corps et métadonnées privées restent sur le stockage froid.

## Git, fichiers et autorisations

Dépôt cible : `GautierDorval/dual-web-reference`. Branche locale du lot : `codex/common-crawl-20261116`, depuis le `main` distant réellement relu. Le worktree public existant a été réutilisé ; aucun clone ou worktree de développement supplémentaire. Le checkout historique sans remote reste séparé. Les deux espaces ne portaient aucun changement suivi au démarrage. Les identités Git complètes initiales et finales, les chemins et le lease sont consignés dans `context.json` et `final-state.json` privés, conformément aux restrictions de diffusion du dépôt.

Sur les **388 fichiers suivis de la base publique**, seul `NOTICE.md` change, pour couvrir les nouvelles annexes par le mapping de licences existant. Les **214 fichiers suivis du checkout historique** restent identiques à leurs empreintes initiales. Les pointeurs locaux ignorés sont préservés. Les payloads, métriques, calendriers, protocoles, dénominateurs et résultats canoniques ne changent pas.

Fichiers du lot :

- `NOTICE.md` ;
- `scripts/common_crawl_annex.py` ;
- `tests/test_common_crawl_annex.py` ;
- les fichiers de cette annexe : `selection.json`, `matrix.csv`, `queries.json`, `captures.json`, `source-evidence.json`, `results.json`, `sources.json`, `REPORT.fr.md`, `REPRODUCTION.md`, `RECEIPT.md` et `manifest.json`.

Aucun push, PR, fusion, déploiement, publication, activation ou préparation de M2. L’audit Codex indépendant a été autorisé séparément par Gautier. Les éventuels commits de ce lot sont uniquement locaux. La livraison publique n’est pas autorisée par ce reçu.

## Vérifications exécutées

| Contrôle | Résultat observé |
|---|---|
| Tests ciblés de l’utilitaire | 31/31 réussis sur la version `1.0.3` |
| Suite complète après les corrections de l’audit | **208 exécutés : 206 réussis, 2 variantes de plateforme ignorées, aucun échec** |
| Suite complète lors de la passe initiale | 192 exécutés : 189 réussis, 2 variantes de plateforme ignorées, 1 échec de mapping de licences |
| Correction du mapping dans `NOTICE.md` | 4/4 tests de licences réussis après correction ; la suite complète n’a pas été répétée pour cette seule modification documentaire |
| Recalcul historique `analyze` | Réussite, mesures canoniques inchangées |
| `build-site` local | Réussite, 43 pages et 325 fichiers ; aucune annexe ajoutée au rendu |
| `verify` sur export exact du candidat, avec verrou privé | **69/69 contrôles réussis**, aucun échec ni contrôle ignoré |
| Intégrité des instantanés | 9/9 fichiers conformes aux métadonnées privées et aux empreintes publiques de la sélection |
| Matrice, CDX, WARC et manifestes | Références croisées et empreintes vérifiées ; matrice identique au recalcul privé |
| Préservation | Seul `NOTICE.md` change parmi les fichiers suivis initiaux ; 214/214 fichiers historiques préservés |

Les premiers échecs sont conservés dans les preuves, sans être renommés en réussites :

- invocation initiale de `unittest` par nom incompatible avec le mode isolé ; correction par le mode `discover` du dépôt ;
- parseur initial refusant les champs `WARC-Protocol` répétés ; corrigé et rejoué uniquement sur les octets déjà acquis ;
- mapping de licences manquant pour le nouveau dossier ; corrigé ;
- références internes et identifiants non admis dans les premières copies de revue ; retirés de ces copies, sans affaiblir le scanner ni changer l’échantillon original ;
- `verify` global du checkout incluant un identifiant dans le `CLAUDE.md` ignoré et préexistant. Ce pointeur n’a pas été modifié. La validation positive porte sur l’export exact des fichiers du candidat, sans les fichiers locaux ignorés ;
- le premier lancement de collecte rapporte un code shell 1 ; le code Python n’a pas été consigné séparément. Le code 2 est celui prévu par la source pour les dix erreurs CDX, pas une mesure ajoutée rétroactivement.

L’export temporaire sert uniquement à la validation, puis est retiré après vérification de son chemin et de l’absence de travail unique. Sa liste de fichiers et leurs empreintes demeurent dans les preuves privées. Ces contrôles du producteur ne constituent pas l’audit indépendant décrit ci-dessous.

## Relecture locale à la reprise

La reprise reste dans le mandat local. Les mêmes neuf URL, les requêtes acquises, leurs budgets et la sélection originale restent inchangés. Aucune nouvelle requête Common Crawl ni visite de site n’a été exécutée.

La version `1.0.2` corrige six défauts reproduits hors ligne :

| Défaut reproduit | Correction et contrôle |
|---|---|
| `collect` pouvait retourner `0` après un échec WARC | Retour `2` lorsque la récupération ou la qualification d’une capture reste incomplète ; un parcours valide conserve `0` |
| Les empreintes source étaient contrôlées seulement au recalcul | Vérification commune aux voies de collecte et de recalcul ; chacun des trois désaccords est refusé |
| Une limite de décompression réduite dans la sélection était ignorée | Application de la limite configurée aux enregistrements et aux corps HTTP gzip |
| Un flux DEFLATE corrompu interrompait le parseur | Conservation du résultat partiel et du diagnostic, sans qualification comme contenu exploitable |
| Les fichiers `manifest.json` imbriqués échappaient au manifeste parent | Exclusion du seul manifeste racine ; toute modification d’un manifeste imbriqué est détectée |
| La référence de l’archive supposait des dossiers de même parent | Calcul du chemin relatif réel ; reproduction dans un autre parent vérifiée |

Huit tests supplémentaires portent la suite ciblée à **23 tests réussis**. Les échecs avant correction sont conservés. Il s’agit d’une relecture du producteur, pas d’un audit indépendant.

Le recalcul final `analysis-04`, sur les mêmes octets, confirme une matrice strictement identique, les trois empreintes source concordantes et l’égalité du corps de C001 avec l’instantané. L’analyse historique `analysis-02` reste une preuve valide et immuable ; `results.json` distingue cette preuve du nouveau contrôle hors ligne. La couverture d’index demeure partielle, sans preuve nouvelle dans M2.

Les preuves de reprise sont dans `Preuves-Audits/dual-web-reference/common-crawl-20261116-review-01`, sous `PAGUP_COLD_STORAGE`. Le paquet initial scellé est préservé. Le reçu privé de cette reprise porte le candidat exact, les contrôles, le manifeste et l’état de clôture.

## Audit Codex et correctif consolidé

À la demande explicite de Gautier, un agent Codex indépendant a examiné le paquet Git exact. Son premier verdict est **NO_GO : un P1 et quatre P2**, avec des contre-exemples exécutés. Ce verdict et ses preuves restent immuables dans `Preuves-Audits/dual-web-reference/common-crawl-20261116-codex-audit-01`, sous `PAGUP_COLD_STORAGE`.

La version `1.0.3` traite ensemble les cinq constats :

| Constat | Correction vérifiée hors réseau |
|---|---|
| F01, P1 : CDX tronqué admis comme complet, voire comme absence | Vérification indépendante de `Content-Length` après lecture bornée ; les réponses tronquées restent incomplètes |
| F02, P2 : tentative perdue après exception HTTP ou interruption | Reçu écrit avant l’appel, finalisé même en cas d’échec ; octets partiels exposés conservés ; interruption propagée et arrêt explicite |
| F03, P2 : recalcul imbriqué modifiant la preuve source | Refus d’une sortie égale ou descendante d’un dossier d’entrée, avant toute écriture |
| F04, P2 : répétitions HTTP valides refusées | Conservation des champs de liste répétés, avec refus maintenu des ambiguïtés de cadrage et de décodage |
| F05, P2 : taille totale `Content-Range` incohérente admise | Validation numérique commune à la collecte et au recalcul : `0 ≤ début ≤ fin < total`, plage et longueur conformes au CDX |

Huit nouveaux tests portent la suite ciblée à **31 tests réussis**. Les échecs avant correction sont conservés, ainsi que le parcours valide. Le recalcul `analysis-05`, avec réseau désactivé, conserve exactement la matrice, C001 exploitable dans M1, les trois empreintes source concordantes et l’égalité avec l’instantané. Les neuf instantanés sont vérifiés. Parmi les vingt réponses historiques, les douze longueurs HTTP déclarées concordent avec les corps conservés ; ce contrôle ne fournit aucune longueur absente pour les huit autres.

Les preuves de correction sont dans `Preuves-Audits/dual-web-reference/common-crawl-20261116-codex-fixes-01`. Le paquet consolidé destiné à la révision finale du même auditeur est immuable. Son verdict doit être lu dans `Preuves-Audits/dual-web-reference/common-crawl-20261116-codex-audit-02`, avec l’identité exacte du candidat. Les contrôles du producteur ci-dessus ne préjugent pas de ce verdict.

L’auditeur dispose du code et des métadonnées de l’annexe, pas des corps historiques privés. L’égalité réelle de C001 avec l’instantané reste une vérification du producteur, distincte de l’audit indépendant du comportement du code. Aucun nouveau résultat scientifique ou opérationnel n’est déduit de la correction.

## Procédures, stockage et limites

Démarrage Pagup, readiness, frontière de navigation, cycle des dépôts, protocole Codex/Claude, confidentialité DWR, calendrier, stockage et applicabilité visuelle ont été consultés. `context.json` privé consigne les documents réellement lus, les portions lues, la révision disponible et les limites, dont les sorties initialement tronquées. Le doctor est rouge pour des configurations hors de ce mandat ; Python et les commandes réellement nécessaires fonctionnent. La revue mensuelle des outils n’est pas due. Aucun outil n’a été mis à jour.

Preuves : sous `PAGUP_COLD_STORAGE`, dossier `Preuves-Audits/dual-web-reference/common-crawl-20261116`. `LISEZMOI-RESTAURATION.md` décrit la reprise. `run-01` conserve les réponses et le premier diagnostic ; `analysis-01` reste historique ; `analysis-02` est l’analyse finale. Le manifeste de l’annexe couvre les fichiers de revue ; les manifestes privés couvrent les octets d’analyse. Une empreinte établit leur intégrité, pas l’identité d’un modèle ni toutes les circonstances de collecte.

`visual_applicability: not-applicable` : documentation locale brute et utilitaire sans changement de surface rendue. Aucune capture mobile n’est revendiquée.

Aucun producteur, consommateur, schéma, épinglage, liaison, cron ou interface de gouvernance n’est modifié. L’état DWR pertinent reste inactif dans les fichiers consultés. L’Observatoire n’a pas été revalidé live dans cette annexe ; aucune réussite opérationnelle globale n’est annoncée. Aucun appel supplémentaire aux sites ou producteurs n’est autorisé par cette limite.

La date M2 est une borne d’admissibilité déjà documentée, pas une nouvelle obligation imposant une présence à heure fixe. Aucun événement Outlook n’a été créé ou modifié.

## Prochaine action

Lire le verdict final indépendant lié au candidat exact avant toute décision de livraison. Les dix interrogations échouées et l’absence de rapprochement transactionnel restent des limites explicites. Toute nouvelle passe réseau doit conserver l’échantillon et comptabiliser ses budgets ; toute publication ou livraison externe exige son autorisation propre. Le résultat actuel reste une corroboration documentaire ponctuelle dans M1.
