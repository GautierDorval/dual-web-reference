# Confidentialité

[English](../en/privacy.md) · [Accueil du dépôt](../../README.fr.md)

Cette page précise ce que les fichiers publics ne contiennent jamais, à quels grains les comptes sont publiés et pourquoi aucune valeur publiée n’a besoin d’être supprimée. La politique est [config/small-cell-policy.json](../../config/small-cell-policy.json). Elle a été fixée avant le calcul de tout résultat (`fixed_before_results = true`) et s’applique à chaque table d’édition, figure, README, document, page de cas, au site statique et aux éditions futures avec leurs deltas. Elle a été modifiée une fois par la suite, uniquement pour la resserrer (`small-cell-policy/1.1.0`, voir la [modification](#modification-du-2026-10-16)). Le propriétaire l’a validée le 2026-10-17, modification comprise (`status: validated_by_owner`).

## Exclusions structurelles

Le dépôt public ne contient jamais :

- d’adresse IP de requête ;
- de chaîne user agent, brute ou hachée ;
- d’identifiant de cookie, de session ou d’appareil ;
- de jeton ni d’identifiant d’accès ;
- de référent en texte libre ;
- de chaîne de paramètres d’URL ;
- de transcription de conversation ;
- d’horodatage de première ou de dernière apparition par cellule ;
- de date de premier ou de dernier accès par chemin.

Ces champs sont exclus par construction : la projection publique n’a aucune colonne pour eux. Par exemple, les dates de premier et de dernier accès par chemin fournies par les exports servent seulement à vérifier qu’elles tombent dans la fenêtre, puis elles sont écartées.

## Grains autorisés

| Grain | Temps | Dimensions | Strates | Fichiers |
|---|---|---|---|---|
| `edition_resource_actor` | édition | site, chemin, méthode, statut, famille d’acteur, nom d’acteur, rôle, niveau enregistré, appréciation | toutes | `consultations.csv`, `resource-summary.csv`, `actor-summary.csv` |
| `daily_site_population` | jour | site, population, rôle, niveau enregistré, méthode, statut | strates non protégées en détail ; strates protégées regroupées en un seul groupe par jour, site et population | `daily-summary.csv` |
| `daily_family_automated_main` | jour | famille, rôle | population principale, niveau à origine fournisseur, rôles `ai_training` et `ai_search` seulement | `daily-family-summary.csv` |

Combinaisons interdites : jour × chemin, jour × nom d’acteur, jour × rôle, niveau enregistré, méthode ou statut pour toute strate protégée, jour × famille pour toute strate protégée, et `user_initiated_fetch` dans toute série, figure ou mesure quotidienne. Les sorties quotidiennes ne portent donc jamais de chemin ni de nom d’acteur : ceux-ci n’apparaissent qu’au niveau de l’édition. Une carte de chaleur par jour et par famille n’est permise que pour les rôles automatisés à origine fournisseur ; dans cette édition, c’est la figure G06, tracée à partir de `daily-family-summary.csv` ([méthode](methode.md)).

## Strates protégées

Certaines strates peuvent contenir des requêtes provoquées par une personne : les récupérations à la demande (`user_initiated_fetch`), et les clients non attribués, non vérifiés ou dont la vérification a échoué, dont le libellé enregistré ne permet pas d’exclure un navigateur (`cloudflare_verified_unattributed`, `unknown_automation`, `claimed_actor_unverified`, `spoofed_or_failed_verification`). Au grain quotidien, toutes leurs requêtes sont comptées dans une seule ligne par jour, site et population, dont `actor_role` et `stored_identity_tier` valent `protected_strata` et dont `http_method` et `http_status` valent `ANY`. Elles n’apparaissent jamais dans une vue quotidienne par famille, et les récupérations à la demande n’apparaissent dans aucune série, figure ou mesure quotidienne : elles sont comptées pour l’édition seulement. Nommer une famille d’agents logiciels, comme un robot d’exploration, n’identifie pas un visiteur individuel ; la publication de tels noms au niveau de l’édition attend encore la confirmation du propriétaire (voir plus bas).

## Pourquoi aucune suppression n’est nécessaire

Aux grains autorisés, aucune cellule ne peut isoler une personne : les tables quotidiennes ne portent ni chemin ni nom d’acteur, les strates protégées y sont regroupées par jour en groupes qui couvrent de nombreux chemins, et les tables d’édition couvrent une fenêtre entière. La politique fixe donc `numeric_suppression = none_required_at_the_allowed_grains`, avec un compte publié minimal de 1. Comme aucune valeur n’est supprimée, la suppression complémentaire ne s’applique pas (`not_applicable_because_no_value_is_suppressed`), et chaque cellule publiée porte `suppression_status = not_suppressed`.

## Croisements et différences

Chaque table publiée est une marge de l’un des trois grains ci-dessus, mais une marge peut encore isoler une cellule lorsqu’on la croise avec une autre. Si une strate quotidienne ne couvre qu’un chemin au grain de l’édition, sa série quotidienne équivaut à ce chemin : lire `daily-summary.csv` à côté de `consultations.csv` donne alors le jour de chaque requête vers ce chemin. C’est pourquoi les strates protégées ne sont publiées par jour que sous la forme du groupe décrit plus haut, et pourquoi les récupérations à la demande restent hors de toute sortie quotidienne, y compris la figure G01 et les mesures `main.daily`.

Deux contrôles de `verify` maintiennent cette règle : `protected_strata_combined_in_daily_outputs` (aucune ligne quotidienne ne porte un rôle ou un niveau protégé hors du groupe) et `no_daily_group_isolates_a_protected_path` (hors des populations à chemin unique acceptées, chaque groupe couvre au moins `minimum_paths` chemins avec des requêtes protégées au grain de l’édition ; la politique fixe 10). Si une édition future échoue au second contrôle, verify échoue et un regroupement plus grossier doit être choisi avant toute publication. Soustraire des tables, combiner des filtres ou comparer deux éditions ou révisions ne donne alors, pour les strates protégées, rien de plus fin que jour × site × population. Il n’y a pas non plus de valeur supprimée à retrouver.

## Cas résiduels acceptés

La politique énumère quatre cas acceptés tels quels :

- la population `robots_control` est formée du seul `/robots.txt`, de sorte que ses comptes quotidiens, groupe protégé compris, équivalent à ce chemin. Il s’agit d’un fichier public de contrôle des robots, hors de la population principale ;
- la population `undeclared_bucket` est un compartiment du collecteur par site (`/.well-known/__undeclared__`), de sorte que ses comptes quotidiens équivalent à ce compartiment. Ce n’est pas un document : il regroupe des requêtes vers de nombreux noms non déclarés ;
- une strate automatisée non protégée (un agent logiciel nommé, de niveau enregistré à origine fournisseur ou vérifié par le réseau, dans un rôle autre que `user_initiated_fetch`) dont les cellules d’édition ne couvrent qu’un chemin rend sa ligne quotidienne équivalente à ce chemin pour cet agent logiciel. Aucune strate protégée n’est en jeu ;
- une famille documentaire qui ne contient qu’un chemin sur tous les sites rend une cellule de `daily-family-summary.csv` équivalente à un chemin, pour les seuls robots automatisés à origine fournisseur. Aucune strate protégée n’est en jeu.

## Modification du 2026-10-16

Un contrôle de croisement exécuté sur l’édition candidate, avant toute publication, a trouvé trois strates quotidiennes protégées dont les cellules d’édition ne couvraient qu’un chemin : le jour de ces requêtes vers ce chemin pouvait donc être retrouvé en croisant `daily-summary.csv` avec `consultations.csv`. L’une d’elles était une seule récupération à la demande. La politique a été resserrée dans la version `small-cell-policy/1.1.0` : strates protégées regroupées au grain quotidien, `spoofed_or_failed_verification` ajouté aux niveaux protégés comme leur définition l’exige, récupérations à la demande retirées des séries quotidiennes, compartiment non déclaré et strates non protégées à chemin unique énumérés comme cas résiduels acceptés, et argument des différences corrigé. Aucun compte d’édition n’a changé : le résultat principal, la répartition par rôle et l’écart de périmètre sont les mêmes. Les vues quotidiennes ne comptent plus que les rôles automatisés. La modification est consignée dans le fichier de la politique (`amendments`) ; le propriétaire a validé la politique, modification comprise, le 2026-10-17.

## Décisions du propriétaire

- Validée le 2026-10-17 : cette politique, modification et cas résiduels acceptés compris.
- En attente : confirmer que des familles nommées d’agents logiciels (par exemple `GPTBot`) peuvent être publiées comme noms d’acteurs au niveau de l’édition.

Tant que ce point n’est pas confirmé, l’édition reste une candidate non publiée ([mises à jour](mises-a-jour.md)).

## Le trafic inconnu n’est jamais imputé

Le trafic enregistré comme inconnu ou non attribué ne devient jamais du trafic de l’exploitant faute d’autre explication. Une coïncidence entre une heure et une activité connue est un indice, pas un appariement de requêtes, et aucun historique de conversation n’est exporté pour trancher une telle question. Voir [attribution](attribution.md).

## Conservation et pièces privées

- Aucune durée de conservation n’est prolongée et aucune donnée destinée à être purgée n’est sauvegardée. L’édition réutilise les exports et les agrégats quotidiens déjà conservés par le producteur, selon les durées de conservation déjà autorisées ; tout changement relèverait d’une décision distincte.
- Les pièces privées (exports, résultats bruts de l’extraction conjointe, lectures de l’archive, instantanés des sources, verrou interne) se trouvent dans un espace de travail privé situé hors de la racine du dépôt. Les étapes privées refusent un espace situé à l’intérieur du dépôt (`private_root_inside_public_repository`), et les motifs de `.gitignore` ne sont qu’une seconde ligne de défense.
- Les fichiers publics portent des étiquettes à la place des identifiants privés : des étiquettes de déploiement du producteur au lieu des identifiants de déploiement, de version et de commit, et une empreinte du verrou interne (`private_lock_sha256` dans `catalog.json`) au lieu de son contenu.
