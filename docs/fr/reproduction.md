# Reproduction

[English](../en/reproduction.md) · [Accueil du dépôt](../../README.fr.md)

Cette page présente les commandes de la chaîne de calcul, ce que chacune lit et écrit, celles qui fonctionnent hors ligne, et ce qu’un lecteur public peut refaire ou non. Les étapes elles-mêmes sont décrites dans [méthode](methode.md).

## Reproduction corrigée et historique

Les commandes sélectionnent r2 par défaut. Pour reproduire les tables publiées et leur présentation, exécuter `analyze`, `render`, `build-site`, puis `verify`. Ces commandes ne font aucune acquisition.

`revise-public` est réservée à la préparation d’une révision locale distincte et non approuvée. Elle transforme les tables r1 inventoriées, change la clé d’édition, retient les lignes quotidiennes protégées et les compléments de couverture, puis régénère le catalogue candidat. Elle refuse une cible déjà déclarée accessible publiquement ou approuvée. Ne pas l’exécuter sur r2 publique. Avec des intrants locaux admissibles identiques, la transformation est déterministe. `prepare-edition` prépare le manifeste d’une candidate locale ; elle n’est pas nécessaire à la reproduction de r2 publiée.

Pour r1, `analyze` et `render` vérifient les empreintes du payload entier et des règles/schémas originaux au lieu d’appliquer le style courant. `verify --edition 2026-09-15_2026-10-15-r1` rejoue ses règles scellées. r1 ne peut être la cible de `project-public`, `prepare-edition` ou du rendu PNG.

`prepare-next --private-root <repertoire>` lit les intrants locaux normalisés et qualifiés existants et écrit exclusivement sous la racine privée. Sa répétition complète synthétique utilise les vraies fonctions de projection, mesure, métriques et figures. Elle n’acquiert aucune donnée D1, n’active aucune planification et ne promeut aucune référence. Voir [mises à jour](mises-a-jour.md).

La nouvelle clé primaire de consultation ajoute `measurement_epoch_id` pour conserver les versions réellement séparables. Les schémas historiques sont scellés sous `config/history/`. La structure des métriques reste compatible ; `metrics_version` identifie les définitions version 2. [metrics.schema.json](../../schemas/metrics.schema.json) décrit valeurs, états nuls, filtres, numérateur, dénominateur, provenance et libellés bilingues.

Chaque édition peut être citée avec son identifiant, l’empreinte de son catalogue et son statut courant, consigné dans `config/editions.json`. Seul un reçu externe valide autorise la qualification de référence approuvée. Aucune de ces citations n’implique une validation scientifique.


## Environnement

- Bibliothèque standard de Python seulement, aucun paquet à installer. Python 3.12 ou plus récent est requis ; la qualification locale couvre Python 3.13.15 et 3.14.6. `.python-version` sélectionne Python 3.14 ; la matrice CI vérifie Python 3.12, 3.13 et 3.14. Un résultat CI ne vaut que pour le commit indiqué dans son exécution.
- Point d’entrée : `python -I scripts/dwr.py <commande> [options]`. Le mode isolé (`-I`) ignore les variables d’environnement `PYTHON*` et le répertoire site de l’utilisateur.
- Windows : `pwsh .\scripts\dwr.ps1 <commande> [options]` lance le même point d’entrée avec le `python` trouvé dans le chemin d’exécution, en mode isolé, avec une sortie UTF-8, et renvoie son code de sortie.
- CI Linux : `.github/workflows/ci.yml` s’exécute sur `ubuntu-24.04` avec des permissions en lecture seule, des actions épinglées par identifiant de commit complet, aucun secret et aucun accès aux sources privées. Elle lance les tests unitaires (jeux de données synthétiques), `analyze`, `render`, `build-site` et `verify`, puis échoue si la régénération a modifié un fichier versionné (`git diff --exit-code`). Elle ne contacte jamais les sites mesurés.
- Tests unitaires seuls : `python -I -m unittest discover -s tests -t . -v`.

## Commandes

| Commande | Lit | Écrit | Réseau |
|---|---|---|---|
| `import-existing --package <dossier>` | paquet d’export : manifeste, archives, tables de marges, chiffres de référence | reçu d’import et marges privés ; rapport de rapprochement privé | aucun |
| `acquire-readonly` | fenêtre de l’édition | rien : affiche les requêtes prévues et leur SHA-256 (dry-run) | aucun |
| `acquire-readonly --execute --confirm-scope <début>..<fin>` | paramètres d’acquisition privés | résultats bruts et journal d’acquisition privés | lit la base du producteur au moyen de son client |
| `normalize` | l’unique import privé, l’archive privée à son commit épinglé, les acquisitions acceptées | `normalized.json` privé : lignes conjointes contrôlées contre les exports, chronologie des déploiements | aucun (lecture d’un dépôt local) |
| `qualify` | `normalized.json`, registre et règles de périmètre, règles d’attribution, instantanés privés des sources, `config/cases.json` | `qualified.json` privé | aucun |
| `project-public` | intrants conjoints privés validés ; cible locale non approuvée seulement | tables, catalogue, métriques, figures et manifeste préparés ensemble avant installation protégée | aucun |
| `analyze` | tables de l’édition | cible publique : comparaison seulement ; cible locale : métriques, figures et manifeste préparés avant installation | aucun |
| `render` | tables, métriques, configuration | figures publiques : comparaison séparée seulement ; figures locales : préparation avant installation ; régénération des pages, blocs, index et schémas actuels | aucun |
| `verify` | chaque fichier de l’arbre de travail ; les valeurs privées si `DWR_PRIVATE_ROOT` est défini | rien (rapport sur la sortie standard) | aucun |
| `publication-gate --ref <branche>` | chaque objet Git atteignable depuis la branche ; valeurs privées de la racine privée | rien (rapport sur la sortie standard, code de sortie 1 au moindre constat) | aucun (lecture du dépôt local) |
| `build-site` | fichiers publics | `site/dist/` (reconstruit de zéro, jamais déployé) | aucun |
| `prepare-edition` | fichiers et figures de l’édition | `delta-report.json`, `SHA256SUMS.txt` | aucun, ne publie rien |
| `png-fallback --edition <id>` | figures d’une candidate locale non approuvée | PNG facultatifs préparés avant installation ; refus public avant lancement du navigateur | rendu de fichiers locaux seulement |
| `png-fallback --edition <id> --preview <nouveau-dossier-externe>` | copie des figures hors des arbres canoniques | aperçu PNG hors du dépôt ; aucun remplacement historique | rendu de fichiers locaux seulement |
| `status` | `data/status.json`, calendrier | rien (sortie standard) | aucun |

`prepare-next` dérive sa fenêtre depuis l’état privé ; les autres commandes d’édition acceptent `--edition <id>` ; par défaut, c’est la candidate désignée dans `config/editions.json`. Les résultats s’affichent en JSON. Une erreur contrôlée `DwrError` affiche `FAIL <code>: <détail>` sur la sortie d’erreur et se termine avec le code 2 ; `verify` se termine avec le code 1 si un contrôle échoue, et un contrôle qui plante compte comme un échec. `acquire-readonly` refuse une fenêtre qui n’est pas close et toute valeur de `--confirm-scope` autre que la fenêtre exacte. Son mode par défaut reste le dry-run ; pour cette édition, il a été exécuté une seule fois, avec `--execute` et la valeur exacte `--confirm-scope 2026-09-15..2026-10-15`, dans l’environnement privé, jamais dans la CI.

Les étapes publiques (`analyze`, `render`, `verify`, `build-site`, `prepare-edition`, `status`) fonctionnent hors ligne et ne contactent jamais les sites mesurés. `verify` contrôle qu’aucun module de la chaîne autre que `acquire.py` n’importe de code réseau.

## La racine privée

Les étapes privées exigent `DWR_PRIVATE_ROOT` (ou `--private-root`) : un dossier existant, situé hors de la racine du dépôt. Une valeur absente, un dossier inexistant ou un dossier à l’intérieur du dépôt arrête l’étape (`private_root_missing`, `private_root_unavailable`, `private_root_inside_public_repository`). Ce dossier contient le verrou interne, les imports, les acquisitions, les fichiers de travail et les instantanés des sources ; il n’est jamais versionné. Les étapes publiques n’en ont pas besoin. `verify` examine chaque fichier de l’arbre de travail, figures PNG et site construit compris, avec la même fonction que la porte de publication décrite plus bas ; lorsque la racine privée est définie, il cherche aussi les valeurs privées qui y sont conservées, et sans elle ce contrôle est signalé sous `skipped`, jamais comme réussi. Les exemples des tests sont synthétiques.

## Porte de publication

Avant toute publication, `python -I scripts/dwr.py publication-gate --ref <branch>` (une étape privée) lit les objets Git atteignables depuis la branche à publier : chaque commit (son en-tête sans les lignes structurelles `tree` et `parent`, et son message entier), le nom de chaque entrée de chaque arbre, arbres compris, et chaque fichier en octets bruts, fichiers binaires compris ; aucun chemin n’est exclu. Elle exige un historique qui part linéairement de la racine publiée nommée dans `config/publication-gate.json` (un seul commit avant la première publication, quand le fichier est absent du commit ou ne nomme aucune racine), sans commit de fusion, et des types de fichiers admis ; la racine est lue dans le commit à publier, et un fichier illisible arrête la porte. Un PNG doit se composer d’un IHDR unique de 13 octets, de blocs IDAT et d’un IEND unique et vide, sans rien après lui, avec des données d’image de la taille exacte annoncée. Les valeurs privées sont comparées sans égard à la casse, et les identifiants hexadécimaux sont détectés dans les deux casses ; un fichier JSON est aussi contrôlé après décodage de ses chaînes, et le texte après décodage des échappements en pourcentage. Les chemins locaux sont comparés aux racines locales réelles de la machine qui exécute la porte (dossier personnel en forme longue et courte, espace privé), après unification de la casse et des séparateurs ; les marqueurs génériques des chemins d’autres machines (dossiers utilisateur Windows, `/home/<nom>/`, `/Users/<nom>/`, dossier synchronisé, données d’application) sont une protection d’appoint, pas une garantie. Un identifiant de 40 caractères n’est admis que comme épinglage d’action ou comme racine publiée ou référence de diffusion listés dans `config/publication-gate.json` et écrits exactement `propriétaire/dépôt@<commit>` ; un test exige que chaque épinglage des workflows figure dans cette liste. Un constat nomme une catégorie et un chemin, et un chemin qui contient une valeur privée ou un identifiant est remplacé par sa position dans la liste. La porte protège contre l’inclusion par erreur de pièces privées ; elle n’est pas une preuve contre un contenu fabriqué pour la contourner. Une branche contenant un historique de travail privé n’est pas publiable. Une branche de correction issue de l’historique publié peut conserver plusieurs commits revus seulement si chaque commit atteignable franchit la porte et si ses états divulgués sont inventoriés. Une projection distincte peut aussi être créée comme un seul commit revu au-dessus de l’historique publié. Aucun commit publié n’est réécrit. La porte contrôle la racine, pas la tête publiée : deux historiques linéaires issus de la même racine la franchissent tous deux. La continuité avec l’édition précédente repose sur la vérification, juste avant le push, que la tête distante vérifiée de `main` est un ancêtre du candidat et qu’une éventuelle branche de correction distante peut avancer vers lui sans réécriture d’historique, et sur un push sans force, qu’impose la protection de `main`.

<!-- dwr:begin publication-gate -->
| Catégorie | Ce que la porte détecte | Contre-exemples testés |
|---|---|---|
| `history_not_from_published_root` | un historique qui ne part pas linéairement de la racine publiée nommée dans `config/publication-gate.json` (plus d’un commit tant qu’aucune racine n’est nommée, une autre racine, ou un commit de fusion, qu’exige toute seconde racine) | un second commit alors qu’aucune racine n’est nommée ; une racine autre que celle qui est nommée ; un commit de fusion après la racine nommée |
| `unsupported_entry` | un lien symbolique ou un sous-module dans un arbre | un lien symbolique ; une entrée de sous-module |
| `file_type_not_admitted` | un fichier dont le type n’est pas dans la liste admise | un fichier exécutable |
| `text_not_utf8` | un fichier texte qui n’est pas en UTF-8 valide | un octet Latin-1 dans un Markdown |
| `private_term` | un nom de dépôt privé, un nom de ressource privée ou un libellé privé, quelle que soit la casse | dans un fichier ; en majuscules dans un fichier ; dans un nom de fichier ; dans le nom d’un arbre vide ; dans le message du commit ; dans un bloc texte d’un PNG ; écrit en échappements Unicode JSON ; des échappements Unicode JSON dans un fichier qui commence par une marque d’ordre des octets ; encodé en pourcentage dans une URL |
| `private_identifier` | un identifiant de compte ou de base de données de la configuration d’acquisition, quelle que soit la casse | dans un fichier de test ; en majuscules ; dans un nom de fichier, jamais réaffiché dans le rapport |
| `private_commit` | un identifiant de commit complet du verrou interne, quelle que soit la casse | dans un fichier CSV ; en majuscules |
| `private_commit_prefix` | les sept premiers caractères (ou plus) d’un identifiant de commit du verrou interne | huit caractères dans un Markdown ; sept caractères en tête d’une ligne de journal ; sept caractères dans un lien `/commit/` |
| `local_root` | une racine locale de la machine qui exécute la porte (dossier personnel en forme longue ou courte, espace privé), quelle que soit la casse et quels que soient les séparateurs, y compris dans des chaînes JSON et des échappements en pourcentage | le dossier personnel en minuscules, comme l’écrit `ntpath.normcase` ; le dossier personnel en majuscules ; le dossier personnel avec des barres obliques ; le dossier personnel sérialisé par `common.canonical_json` ; la forme `/c/…` d’un shell de type Unix ; le nom court 8.3 du dossier personnel ; le chemin de l’espace privé sans le préfixe du dossier personnel ; le dossier personnel encodé en pourcentage dans une URL |
| `local_path` | un marqueur générique de chemin local sur n’importe quelle machine, protection d’appoint (dossier utilisateur Windows, `/home/<nom>/`, `/Users/<nom>/`, dossier utilisateur d’un shell de type Unix, dossier synchronisé, données d’application), quelle que soit la casse | un dossier utilisateur dans un Markdown ; un dossier utilisateur sérialisé en JSON (séparateurs doublés) ; un dossier utilisateur écrit avec des barres obliques ; un dossier utilisateur en minuscules ; un dossier `/home/<nom>/` ; un dossier `/Users/<nom>/` |
| `ip_address` | une adresse IPv4 | dans un Markdown ; dans un nom de fichier |
| `user_agent` | une chaîne d’agent utilisateur de navigateur | dans un Markdown |
| `identifier_32` | un identifiant hexadécimal de 32 caractères, dans l’une ou l’autre casse | en minuscules dans du code ; en majuscules dans du code ; dans un nom de fichier |
| `identifier_40` | un identifiant hexadécimal de 40 caractères, dans l’une ou l’autre casse, sauf un épinglage d’action ou la racine publiée/référence de diffusion listés dans `config/publication-gate.json` et écrits exactement `propriétaire/dépôt@<commit>` | dans un commentaire d’un modèle de workflow ; la valeur d’un épinglage admis répétée sans son préfixe `propriétaire/dépôt@` ; un épinglage absent de la liste, sur une étape `uses:` ; un épinglage absent de la liste, dans le bloc scalaire d’une étape `run:` ; une ligne `tree` dans le message du commit |
| `short_commit` | une référence courte de commit (`commit` suivi de 7 à 12 caractères hexadécimaux) | dans un Markdown |
| `png_chunk_not_admitted` | un bloc PNG autre que IHDR, IDAT et IEND | un bloc texte ; un bloc de palette |
| `png_malformed` | un PNG dont la structure diffère d’un IHDR unique de 13 octets, de blocs IDAT et d’un IEND unique et vide, ou dont les données d’image diffèrent de la taille annoncée | des données après IEND ; un IEND non vide ; un second IHDR ; des données d’image en trop ; un fichier tronqué ; une somme de contrôle fausse ; des dimensions au-delà de 16 384 pixels |

Chacun des 59 contre-exemples ci-dessus est placé par un test par mutation dans `tests/test_publication_gate.py`, qui exige l’échec de la porte dans cette catégorie ; un autre test exige que ce tableau et les mutations se correspondent un à un. Une variante non listée n’est pas revendiquée. Non couvert : les pixels d’un PNG, qui rendent un SVG contrôlé comme texte mais ne sont pas lus eux-mêmes comme du texte, et un contenu fabriqué exprès pour contourner la porte.
<!-- dwr:end publication-gate -->

## Solution de repli en PNG

`node scripts/render_png.mjs <edition-id>` convertit les figures SVG en PNG avec Playwright (Chromium), en jeu de couleurs clair et à l’échelle 2, dans `figures/<edition>/png/`. `DWR_PLAYWRIGHT_DIR` peut désigner le dossier où Playwright est installé. Les octets PNG ne sont pas reproductibles à l’identique d’un moteur à l’autre : les fichiers SVG sont les figures de référence, et les PNG sont exclus de `SHA256SUMS.txt`.

## Déterminisme

Les mêmes intrants donnent des octets identiques pour chaque sortie CSV, JSON et SVG :

- le JSON est canonique : UTF-8, clés triées, indentation de deux espaces, saut de ligne final ;
- les CSV ont un ordre de colonnes fixe, un ordre de lignes fixe et des fins de ligne LF ; les décimales suivent un format fixe ;
- le générateur SVG n’utilise ni aléa, ni horodatage, ni script, ni référence externe, et seulement la pile de polices du système ;
- `generated_at` est fixé pour chaque candidate dans `config/editions.json`, de sorte qu’une reconstruction ne le modifie pas.

`verify` recalcule `metrics.json`, refait en mémoire le rendu d’une figure, de la table de données de chaque figure (à partir de sa variante large anglaise), des pages de cas et des blocs générés, et les compare octet par octet aux fichiers versionnés. Les fichiers de travail privés portent des horodatages et ne font pas partie de cette comparaison.

## Fichiers d’empreintes

- `catalog.json` liste la taille et le SHA-256 de chaque table, de `reconciliation.json` et de `case-checks.json`. Il ne se liste pas lui-même, pas plus que `metrics.json` et `figures.json`, dérivés après lui, ni `SHA256SUMS.txt`.
- `figures.json` liste le SHA-256 de chaque fichier SVG, de chaque table de données et de chaque table d’intrants de chaque figure.
- `SHA256SUMS.txt`, écrit par `prepare-edition` dans le dossier de l’édition, compte une ligne `<sha256>  <chemin depuis la racine du dépôt>` pour chaque fichier du dossier de l’édition et de `figures/<edition>/`. Il ne s’inclut jamais lui-même, et les fichiers PNG en sont exclus. Depuis la racine du dépôt, `sha256sum -c data/editions/<edition>/SHA256SUMS.txt` le vérifie sous Linux ; sous Windows, `Get-FileHash -Algorithm SHA256` donne les mêmes empreintes.

Une empreinte concordante montre que les fichiers sont ceux qui ont été revus ; elle ne montre pas que les observations sont vraies, et aucune signature n’intervient. Une revue approuve une empreinte ; toute modification ultérieure annule cette approbation.

## Conventions CSV

UTF-8 sans indicateur d’ordre des octets, fins de ligne LF, virgule comme séparateur, ligne d’en-tête, guillemets selon la RFC 4180 au besoin, point décimal, dates ISO 8601, booléens écrits `true` et `false`, et cellule vide signifiant null, jamais zéro. Les types de colonnes, les clés primaires et le minimum de 0 pour les comptes figurent dans les schémas JSON, dont le [schéma des consultations](../../schemas/consultations.schema.json).

Une variante adaptée aux tableurs (`*.spreadsheet.csv`) est définie pour les copies destinées à être ouvertes dans un tableur : toute cellule commençant par `=`, `+`, `-`, `@`, une tabulation ou un retour chariot est précédée d’une apostrophe, afin de ne jamais être lue comme une formule. Les CSV canoniques conservent les valeurs exactes et sont ceux à utiliser pour tout calcul.

## Ce qu’un lecteur public peut refaire ou non

Avec ce seul dépôt, un lecteur peut recalculer chaque chiffre et chaque figure publiés à partir des tables publiques (`analyze`, `render`, `verify`, tous hors ligne, sans racine privée), vérifier les empreintes, retrouver le fichier et la ligne de chaque relation dans `links.csv`, et vérifier que les tables quotidiennes, la table par famille et les tables de l’édition concordent entre elles.

Il ne peut pas relancer la collecte, la classification du producteur, l’extraction depuis la base du producteur, la lecture de l’archive ni les instantanés du graphe : ils dépendent de dépôts privés et du collecteur privé. Vérifier une empreinte et refaire une agrégation, ce n’est pas refaire la collecte.

## Citer une édition

Citer l’identifiant de l’édition avec le SHA-256 de son `catalog.json` :

```text
Dual Web Reference, édition 2026-09-15_2026-10-15-r1 (du 15 septembre au 14 octobre 2026 inclusivement, en UTC),
catalog.json SHA-256 <64 caractères hexadécimaux>, consulté le <date>.
```

L’empreinte se calcule avec `sha256sum data/editions/<edition>/catalog.json` ou `Get-FileHash -Algorithm SHA256 data/editions/<edition>/catalog.json`, et elle figure aussi dans `SHA256SUMS.txt`. Citer l’identifiant et l’empreinte avec le statut courant dans `config/editions.json`. Seul un reçu externe valide autorise la qualification de référence approuvée. Une révision comme `r2` a son propre identifiant et sa propre empreinte ([mises à jour](mises-a-jour.md)).

## Codes de sortie de la préparation

| Résultat de `prepare-next` | Code | Interprétation |
|---|---|---|
| `validation_failed`, `source_unavailable` | 1 | Préparation non réussie, fraîcheur inchangée |
| `distribution_blocked_pending_contract`, `distribution_blocked_pending_policy_approval` | 0 | Préparation privée terminée, diffusion toujours bloquée |
| `unchanged`, fenêtre non prête ou état d’attente sans erreur | 0 | État consigné, aucune approbation implicite |
| `FAIL <code>` (`DwrError`, dont verrou occupé) | 2 | Erreur contrôlée sur la sortie d’erreur |

Un code 0 ne vaut donc jamais autorisation de diffusion. Les tableaux JSON et leurs champs d’état doivent être lus avec le code de sortie.

## Reprise après interruption

Pour un verrou `preparation/preparation.lock`, vérifier d’abord que le processus propriétaire est terminé. Conserver le verrou, l’état `preparation/status.json`, la candidate et son reçu avant intervention. Comparer les empreintes des intrants et sorties au reçu et inspecter les dossiers de préparation. Un reçu complet conforme permet à la prochaine exécution de récupérer la candidate et le curseur ; une candidate partielle ou des octets divergents exigent une résolution explicite, jamais un remplacement silencieux. Seulement après cette inspection, le propriétaire peut retirer le verrou périmé puis relancer `prepare-next`. Un second passage identique doit donner `unchanged`.

Le verrou d’édition `.dwr-work/<edition>.lock` est distinct : son dossier temporaire contient `recovery.json` pendant l’installation et les sauvegardes nécessaires à la restauration. Aucun verrou n’expire automatiquement. Les verrous coordonnent les producteurs qui respectent ce protocole ; ils ne confinent pas un autre processus doté des mêmes droits qui écrit arbitrairement dans les dossiers. Sous POSIX, un tel processus peut créer un dossier vide dans l’intervalle précédant `os.rename`, qui peut le remplacer. Cette course externe au verrou n’est pas qualifiée par les tests Windows.

## Ensembles de fichiers fermés et construction du site

`analysis/dwr/distribution.py` fournit un contrôle commun de l’ensemble exact et des octets à `verify`, `build-site`, la préparation de candidate et la porte Git. Les inventaires existants `publication-inventory.json` et `historical-editions.json` sont identifiés par leurs octets SHA-256 de référence ; les recalculer depuis le dossier courant ne peut pas autoriser un ajout. Leurs entrées revues couvrent les fichiers historiques des éditions et figures, PNG compris. Une liste source fixe couvre les autres configurations, schémas et pointeurs opérationnels. Les deux gabarits de workflow explicitement nommés restent réservés au dépôt. Aucune extension ni copie de dossier entier ne vaut autorisation.

Les racines contrôlées sont `data`, `figures`, `config` et `schemas`, fichiers non suivis et dossiers vides compris. Une édition inconnue ou privée y est refusée. Une entrée privée au registre ne donne aucun droit de diffusion ; rétrograder une édition publique en privée ne libère pas ses octets historiques du contrat. Le code et la documentation hors de ces racines restent soumis aux contrôles Git et de confidentialité existants ; tous les noms du dépôt ne sont pas déclarés immuables. Les fichiers opérationnels et configurations modifiables nécessitent encore les contrôles sémantiques et de confidentialité.

Avant toute copie, le constructeur déclare chaque page et chaque fichier source/destination. Il lit les octets admis, produit les pages en mémoire, compare à nouveau les sources, écrit un dossier temporaire neuf, contrôle chaque nom et chaque octet, puis revérifie la stabilité des sources. `site/dist` reste intact jusque-là. Une construction neuve remplace un ancien dist contenant des fichiers parasites sans les recopier. `verify` recalcule indépendamment le plan attendu et compare le dist réel : un ajout ou une modification après construction est refusé. Un archivage extérieur à cette CLI doit exécuter ce contrôle immédiatement avant l’empaquetage ; le code n’intercepte pas les utilitaires arbitraires de copie ou d’archive.

Les octets des manifestes historiques sont eux-mêmes épinglés, jamais régénérés pour légitimer une modification. Le plan de sortie précède l’observation du dossier construit, sans manifeste auto-approbateur. La préparation privée applique son propre ensemble explicite de fichiers et de figures avant de sceller de nouveaux octets ; elle n’accorde aucune admission publique.

La porte Git contrôle l’arbre réel à `distribution_baseline` et chaque arbre successeur accessible. Les ancêtres stricts de cette référence publique fixe conservent le contrôle de confidentialité de tous leurs objets et leur identité Git immuable ; ils ne sont pas rétroactivement soumis à l’ensemble actuel des éditions. Un fichier ajouté puis supprimé dans des commits ultérieurs reste refusé. Une référence falsifiée ne peut pas l’exempter. Le dossier de travail et Git sont deux contrôles distincts : les fichiers non suivis n’existent pas dans les objets Git. Les diagnostics des entrées contrôlées utilisent des positions plutôt que les noms détectés.

Les chemins doivent être relatifs, normalisés NFC et non ambigus sur un système insensible à la casse. Liens symboliques, jonctions, points de réanalyse, fichiers spéciaux et sous-modules sont refusés. Les tests de jonction Windows et de collision sur entrées Git synthétiques se distinguent des variantes propres à POSIX ; une variante ignorée n’est pas réussie. Les accès et verrous supposent des processus coopératifs. Ils ne confinent pas un processus malveillant disposant des mêmes permissions.

### Reprise du site

Le verrou exclusif `site/.build.lock` empêche les constructions coopératives de partager un dossier temporaire. Un échec d’installation intercepté restaure l’ancien dist. Si la restauration ou le nettoyage de sauvegarde échoue, conserver le verrou, `site/.dist-backup` et les dossiers `.build-*` pour inspection. Un arrêt brutal peut survenir entre les renommages : arrêter d’abord le propriétaire, comparer la candidate à un plan recalculé et préserver l’ancienne sortie, puis résoudre explicitement les dossiers et le verrou. Aucun nettoyage automatique d’un verrou ancien ni transaction atomique de deux dossiers face à un arrêt brutal n’est promis. Une construction réussie n’est ni une approbation, ni une publication, ni une validation de collecte, ni une garantie de confidentialité.
