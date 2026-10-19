# Découverte et maillage

[English](../en/discovery-and-linking.md) · [Accueil du dépôt](../../README.fr.md)

Un fichier de la couche peut être atteint de plusieurs façons. Cette page recense ces voies, précise ce que [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv) en consigne, et distingue trois notions faciles à confondre : un parcours disponible, un parcours exécuté et des accès comptés en agrégat.

## Voies d’accès à un fichier

- **Ancres HTML** : liens `<a href>` des pages ordinaires du site.
- **Relations de lien et en-têtes** : éléments `<link rel>` de la section `<head>` d’une page HTML, ou en-têtes de réponse HTTP `Link`, lorsqu’un site les emploie. La proposition llms.txt suggère elle-même de telles relations pour pointer vers les versions Markdown des pages et vers le fichier llms.txt qui les couvre.
- **Liens Markdown et adresses en clair** : liens et URL écrits dans des fichiers Markdown, texte ou YAML, y compris llms.txt.
- **Références JSON** : adresses inscrites comme valeurs dans des fichiers JSON ou JSON-LD, telles quelles ou sous une clé qui déclare une relation (`sameAs`, `canonical`, `source`, `related`, `index`, `manifest` et clés semblables).
- **Sitemaps** : entrées `<loc>` des sitemaps XML.
- **Connaissance directe d’une URL** : un client peut demander une adresse qu’il connaît déjà (visite antérieure, liste, emplacement conventionnel comme `/llms.txt` ou `/.well-known/`, page externe, personne qui l’a collée) sans suivre aucun lien du site.

## llms.txt, une porte d’entrée parmi d’autres

llms.txt est une ressource d’orientation possible. C’est une proposition (voir [etudes-llms-txt.md](etudes-llms-txt.md)), pas un protocole qu’un client devrait lire en premier. Sur les trois sites, il renvoie à d’autres fichiers de gouvernance, mais ces fichiers peuvent aussi être atteints depuis des pages HTML, des manifestes et des index, des références JSON et des sitemaps. Les noms de fichiers sont des choix d’implémentation propres à chaque site.

Deux inférences ne sont donc pas permises. Une requête vers un autre fichier ne montre pas que celui-ci a été trouvé par llms.txt. Et l’absence de requête vers llms.txt un jour donné ne prouve pas qu’il n’a joué aucun rôle auparavant.

## Ce que consigne links.csv

Chaque ligne de links.csv est une référence écrite dans un fichier de l’instantané source d’un site. Elle donne :

- la source et la cible (site, chemin et identifiant de ressource) ;
- le type de relation : `html_anchor`, `markdown_link`, `plain_url_mention`, `json_reference`, `declared_relation` ou `sitemap_entry` ;
- l’identifiant et la date de l’instantané du graphe ;
- la ligne de preuve (première occurrence dans le fichier) et le nombre d’occurrences ;
- une note, par exemple la clé JSON qui porte l’adresse.

L’extraction est déterministe et ne lit que des fichiers. En HTML, elle relève les ancres `<a href>` ; les éléments `<link>` de la section `<head>` ne sont pas extraits dans cette édition, et les en-têtes HTTP ne font pas partie d’un instantané source. Les références vers des sites extérieurs aux trois ne sont pas conservées. Les références répétées qui partagent la même source, la même cible et le même type sont fusionnées en une seule ligne, avec leur nombre d’occurrences.

Ce que links.csv ne consigne pas :

- **Pas un parcours suivi.** Une ligne signifie « cette référence est écrite dans ce fichier de cet instantané ». Ce n’est pas la preuve qu’un client l’a suivie.
- **Une absence signifie « introuvable dans ce graphe ».** Une ligne manquante ne veut pas dire qu’aucune référence n’existe ailleurs : dans une autre page, sur un site externe, dans un en-tête ou dans une version antérieure du fichier.
- **Aucune pondération.** La table ne hiérarchise pas les liens et ne dit pas lequel un client préférerait.

## Parcours disponible, parcours exécuté, accès agrégés

- **Parcours disponible** : une chaîne de références écrites dans des fichiers, telle que la consigne links.csv. Il montre ce qu’un lecteur peut suivre. Les pages de cas énumèrent de tels parcours, chaque étape étant vérifiée dans l’instantané.
- **Parcours exécuté** : la suite de requêtes qu’un client donné a réellement faites. L’établir exige une trace d’exécution qualifiée pour ce client. Aucune ne fait partie de cette édition, et aucune n’est reconstituée à partir des comptes.
- **Accès agrégés** : des totaux par URL sur la fenêtre, des totaux quotidiens par site et par population, et des totaux quotidiens par famille documentaire pour les rôles automatisés à origine fournisseur. On ne peut pas les enchaîner en parcours : que deux fichiers liés aient tous deux été demandés au cours du même mois ne montre pas que l’un a mené à l’autre.

## Un parcours qui part du HTML : pagup.com

Le [cas pagup.com](../../cases/pagup.com/README.fr.md) part de la page de politique IA, une page HTML ordinaire liée depuis la page d’accueil. De là, des références écrites mènent à l’index canonique, au fichier d’identité, au contexte du site, aux déclarations de périmètre et au fichier de préséance des sources, sans passer par llms.txt. Le cas montre qu’on peut entrer dans la couche depuis des pages ordinaires. Il ne montre pas qu’un client a emprunté ce chemin.

## Les instantanés ne sont pas l’état de septembre

Le graphe est extrait des dépôts sources des sites à une date d’instantané : le 2026-10-14 pour gautierdorval.com, le 2026-10-06 pour pagup.com et better-robots.com. Plusieurs fichiers de gautierdorval.com ont changé pendant la fenêtre, et une fusion ne déploie rien. Les sitemaps d’aujourd’hui ne sont pas ceux de septembre : une ligne `sitemap_entry` montre ce que l’instantané énumère, pas ce qu’un robot pouvait lire un jour donné de la fenêtre. Pour pagup.com, l’instantané est un build ; les valeurs `lastmod` de ses sitemaps proviennent donc du build. La version historique de chaque ressource est consignée comme inconnue.

## Pourquoi aucun taux de couverture rapporté à l’inventaire actuel

On pourrait diviser le nombre de fichiers demandés par le nombre de fichiers de l’inventaire et appeler le résultat la part de la couche qui a été atteinte. Ce ratio portant sur l’inventaire complet n’est pas calculé. Le ratio distinct 174/269 utilise seulement les couples site-chemin principaux ayant des lignes enregistrées, tous acteurs, méthodes et statuts confondus. Il est conditionnel à ces lignes, pas à l’inventaire historique complet. L’inventaire (le registre de périmètre et resources.csv) reflète l’état au moment de l’enregistrement et de l’instantané, après la fenêtre. Certaines ressources sont enregistrées aujourd’hui sans aucune ligne dans la fenêtre (colonne `window_rows_status`), d’autres ont pu exister alors et changer depuis, et la couverture quotidienne est déclarée partielle. Le numérateur et le dénominateur ne décriraient pas le même ensemble de fichiers au même moment. Le dépôt publie plutôt des comptes par couple site-chemin.
