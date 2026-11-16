# Annexe exploratoire Common Crawl du 16 novembre 2026

**Résultat établi :** une capture exploitable de `https://gautierdorval.com/entity-graph.jsonld`, datée du **14 octobre 2026 à 07:54:39 UTC**, conserve un corps de **50 179 octets identique octet pour octet** à l’instantané documentaire détenu pour DWR. Elle relève de **M1**, pas de M2. Les empreintes SHA-1 du payload WARC, du bloc HTTP et du CDX concordent avec les octets récupérés.

**Couverture partielle :** neuf URL figées avant interrogation, deux index, 18 requêtes d’index. Huit réponses sont exploitables : sept absences explicites et une capture. Dix interrogations échouent, trois en HTTP 502 et sept en HTTP 504. Une erreur n’est jamais comptée comme une absence. Une seule URL a ses deux interrogations complètes. Aucun taux d’adoption ou score n’est calculé.

Cette annexe locale n’est ni une édition canonique, ni une approbation scientifique, ni une publication. [Reproduction](REPRODUCTION.md), [matrice](matrix.csv), [résultats structurés](results.json), [reçu](RECEIPT.md).

## Question et portée

Une archive indépendante permet-elle de corroborer le contenu reçu par un collecteur à un instant donné ? Ici, elle corrobore le **corps de ressource conservé par Common Crawl** et son égalité avec un instantané documentaire DWR. Les agrégats d’accès DWR ne contiennent ni le corps reçu ni l’heure d’une transaction précise : le rapprochement avec une requête individuelle de ces agrégats reste **non établi**.

Le résultat ne démontre ni lecture ou utilisation par un modèle, ni compréhension, ni entraînement effectif, ni conformité à une politique, ni effet commercial. Il ne valide pas globalement le Dual Web. Ces limites ne démontrent pas davantage l’absence de ces usages ou effets.

## Sélection préalable et pièces disponibles

La sélection originale privée a été figée à `2026-11-16T15:37:16.557953Z`, avant la première requête CDX. SHA-256 : `6e10b5e00c7d9dc8c5e2d33052b5f984ddca0cd32c76885a70b0e0ed92eeedd5`. La collecte commence à `2026-11-16T15:41:06.990359Z`. La [copie de revue](selection.json) retire seulement l’identifiant Git, conformément au contrôle du dépôt ; son empreinte est donc distincte. Les neuf URL, leurs motifs, les index, les budgets et la date de sélection sont identiques. L’original et son reçu restent immuables dans les preuves privées.

Échantillon raisonné de neuf URL exactes, sans substitution : trois formats et rôles, croisés sur les trois cas déjà observés de DWR. `llms.txt` représente la découverte textuelle, `/.well-known/ai-governance.json` l’entrée JSON et `/entity-graph.jsonld` le graphe d’identité JSON-LD. Toutes appartiennent à la population documentaire principale et possèdent des lignes dans les observations historiques. Aucun site hors de ces trois cas, aucun hôte protégé de recherche et aucune URL non observée n’ont été ajoutés. Ce n’est pas un échantillon représentatif du Web.

Pour les neuf URL :

- population, format et empreinte documentaire viennent de `resources.csv` r2, dont l’empreinte est épinglée dans la sélection ;
- observations et niveaux d’attribution viennent de `consultations.csv` r2, au grain de l’édition M1, avec couverture déclarée partielle. La présence d’un accès n’implique pas qu’il appartient à la sélection principale des rôles IA ;
- les neuf fichiers d’instantané ont été retrouvés dans le dossier privé existant et leurs octets vérifiés contre leurs métadonnées et les empreintes publiques r2 ;
- instantanés de source du 14 octobre pour gautierdorval.com et du 6 octobre pour les deux autres sites, exports documentaires générés le 16 octobre. Ils proviennent de sources statiques ou, pour Pagup, d’une sortie de build déjà détenue ;
- aucune preuve de déploiement précisément applicable à la capture ni aucune transaction réseau DWR individuelle n’est établie dans cette annexe. Un commit, un build ou le nom `served` d’un dossier ne constituent pas cette preuve.

Les [pièces par URL](source-evidence.json) conservent ces limites. Les originaux privés, corps de ressources et métadonnées détaillées restent hors du dépôt.

## Index et calendrier

| Index | Publication annoncée | Collecte annoncée | Pertinence |
|---|---|---|---|
| `CC-MAIN-2026-43` | 21 octobre 2026 | 5 au 18 octobre 2026 | M1 et recoupement potentiel de M2 du 15 au 18 octobre |
| `CC-MAIN-2026-39` | 19 septembre 2026 | 4 au 17 septembre 2026 | Début de M1 du 15 au 17 septembre et captures antérieures |

Ces périodes sont vérifiées dans les annonces officielles [d’octobre](https://www.commoncrawl.org/blog/october-2026-crawl-archive-now-available) et [de septembre](https://www.commoncrawl.org/blog/september-2026-crawl-archive-now-available). Les dates de publication ne servent jamais d’horodatage de capture. Le catalogue téléchargé commence par octobre, septembre et août ; aucun lot de novembre n’y est annoncé.

La fenêtre M2 demeure `[2026-10-15T00:00:00Z, 2026-11-15T00:00:00Z)`. `config/edition-calendar.json`, `data/status.json` et la documentation locale concordent avec le brief : consolidation de 48 heures, première préparation admissible le **17 novembre à 00:00 UTC**, soit le **16 novembre à 19:00 à Toronto**. C’est une borne d’admissibilité, pas un lancement programmé. Aucun `prepare-next`, acquisition D1, rattrapage ou changement de calendrier n’a été exécuté.

## Méthode et budget réel

Utilitaire ponctuel [common_crawl_annex.py](../../scripts/common_crawl_annex.py), bibliothèque standard Python seulement, indépendant de la chaîne DWR. `cdx_toolkit` a été consulté ; son installation n’était pas nécessaire pour ce périmètre exact. Aucun service, dépendance du produit ou traitement récurrent n’est ajouté.

Les requêtes utilisent `matchType=exact`, puis vérifient l’URL originale caractère par caractère : les variantes HTTP, hôte ou chemin ne sont pas assimilées silencieusement. Les deux index sont interrogés sans filtre temporel, puis les captures sont classées selon les bornes UTC inclusives et exclusives. Aucun domaine entier, lien découvert ou fichier de gouvernance lié n’est exploré. Les requêtes et leurs erreurs sont conservées dans [queries.json](queries.json).

Appels séquentiels, intervalle minimal de cinq secondes entre départs, délai réseau de 30 secondes. Aucune relance des erreurs, aucun mandataire ajouté, aucune rotation d’adresse, aucune redirection réseau suivie. L’utilitaire s’arrête dès le premier 403, 429 ou 503 et conserve `Retry-After`. Aucun de ces statuts n’a été observé. Les 502/504 restent des échecs bornés, conservés sans réessai. La passe s’arrête après les 18 interrogations prévues, sans consommer le reste du plafond pour multiplier les tentatives.

| Budget | Consommé | Maximum du mandat |
|---|---:|---:|
| URL exactes | 9 | 10 |
| Index | 2 | 3 |
| Requêtes d’index, pagination comprise | 18, aucune pagination | 30 |
| Enregistrements WARC téléchargés | 1 | 20 |
| Octets WARC compressés téléchargés | 9 003 | 100 MiB |
| Corps téléchargés par l’utilitaire, catalogue et erreurs compris | 47 159 | 100 MiB appliqués conservativement à leur ensemble |

Une requête supplémentaire lit le catalogue `collinfo.json`. Les consultations documentaires via l’outil Web sont distinctes des requêtes CDX et WARC ; leur volume réseau n’est pas instrumenté par l’utilitaire. Une première tentative de lecture du catalogue par cet outil a retourné `UnexpectedStatusCode`, sans statut HTTP exposé. La récupération directe conservée ensuite réussit en HTTP 200.

## Résultats par URL

Les identifiants renvoient à la sélection et à la matrice complète. « Partiel » décrit la couverture des interrogations, indépendamment de l’existence d’une capture exploitable.

| ID | Site | Ressource | Interrogations complètes | Résultat |
|---|---|---|---:|---|
| U01 | gautierdorval.com | `/llms.txt` | 2/2 | Aucune capture dans les deux index interrogés |
| U02 | gautierdorval.com | `/.well-known/ai-governance.json` | 1/2 | Interrogation incomplète |
| U03 | gautierdorval.com | `/entity-graph.jsonld` | 1/2 | C001 exploitable dans M1, hors M2 ; couverture partielle |
| U04 | pagup.com | `/llms.txt` | 1/2 | Interrogation incomplète |
| U05 | pagup.com | `/.well-known/ai-governance.json` | 0/2 | Interrogation échouée |
| U06 | pagup.com | `/entity-graph.jsonld` | 1/2 | Interrogation incomplète |
| U07 | better-robots.com | `/llms.txt` | 1/2 | Interrogation incomplète |
| U08 | better-robots.com | `/.well-known/ai-governance.json` | 0/2 | Interrogation échouée |
| U09 | better-robots.com | `/entity-graph.jsonld` | 1/2 | Interrogation incomplète |

La matrice distingue six états : `no_capture_in_queried_indexes`, `capture_only_outside_window`, `query_failed_or_incomplete`, `capture_content_not_retrieved`, `content_partial_redirect_or_revisit`, `content_retrieved_comparable`. La couverture est un champ distinct. Les deux états concernant un contenu manquant ou partiel ne subsistent pas dans le résultat final ; ils sont exercés par les tests et ne sont pas inventés comme observations réelles.

## Capture C001 et comparaison

[C001](captures.json) : `https://gautierdorval.com/entity-graph.jsonld`, `2026-10-14T07:54:39Z`, WARC `response`, HTTP 200, `application/ld+json; charset=utf-8`, aucun en-tête `WARC-Truncated`, aucune redirection et aucune revisite déclarées. Le corps est disponible.

- Fichier : `crawl-data/CC-MAIN-2026-43/segments/1791170055063.80/warc/CC-MAIN-20261014063221-20261014093221-00165.warc.gz`.
- Plage : offset `249413868`, longueur `9003`, requête `Range: bytes=249413868-249422870`. HTTP 206, plage et taille retournées contrôlées.
- Corps archivé et instantané : `50179` octets, SHA-256 `b200673a3db19917f7177be499f909495b06f12a07e90ab28c26c64a93c264e0`.
- SHA-1 du payload et du CDX : `4KV2BHVMJ7JU2SZOVD3EMVNV5RAYLCHO` ; SHA-1 du bloc : `64DFPE5SMDADF7KBCVG7GWU2LY4ELDZT`. Les trois sont recalculés avec succès.

Le conteneur gzip WARC est décompressé séparément. Le bloc HTTP, le payload conservé, les octets décodés et le texte normalisé sont des artefacts distincts. **`x-crawler-content-encoding: br` signale un décodage Brotli effectué par le collecteur avant conservation** ; aucun `Content-Encoding` ne reste à décoder dans le corps archivé. L’égalité concerne ce corps conservé, pas les octets compressés ayant transité sur le réseau. La normalisation locale applique le charset UTF-8 et les seules conversions CRLF/CR vers LF ; elle ne change pas les octets de ce fichier.

Le premier parseur refusait à tort les deux champs `WARC-Protocol`, pourtant illustrés dans la [documentation Common Crawl](https://www.commoncrawl.org/cdxj-index). Ce défaut local a été corrigé avec un test discriminant. `run-01` conserve le diagnostic initial ; `analysis-02` contient l’analyse finale obtenue **sans nouvelle requête réseau**. Les anciens artefacts ne sont pas réécrits.

Common Crawl n’exécute pas JavaScript. Aucun rendu navigateur n’entre dans cette comparaison et aucune capture HTML n’est utilisée pour inférer la collecte d’un fichier lié. [FAQ officielle](https://www.commoncrawl.org/faq)

La relecture locale a ensuite corrigé les voies d’erreur et de preuve de l’utilitaire (`1.0.2`) ; le [reçu](RECEIPT.md) donne les six défauts et les tests avant/après. Un nouveau recalcul hors ligne des mêmes octets confirme une matrice et une conclusion inchangées. Les erreurs HTTP initiales ne sont ni rejouées ni transformées en absences.

## Limites et prochaine action utile

Une capture établit ici une concordance de contenu bornée. Aucune capture exploitable dans M2 n’a été retrouvée dans cette passe ; les erreurs d’index empêchent toute conclusion d’absence générale. Aucun utilisateur ou modèle n’est identifié à partir d’un `User-Agent`. L’égalité du fichier ne restitue ni le déclencheur ni le parcours de découverte.

La prochaine action utile est de revoir ce paquet local. Une éventuelle nouvelle passe devra conserver le même échantillon et définir explicitement son budget cumulé et ses tentatives, après examen des erreurs 502/504. Pour rattacher une capture à une transaction DWR, il faudrait en plus une preuve réseau historique au grain pertinent et sa portée d’attribution ; elle ne sera pas fabriquée à partir des agrégats. Aucune nouvelle collecte ni livraison externe n’est déclenchée par cette recommandation.
