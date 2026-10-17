# Études publiées sur llms.txt

[English](../en/llms-txt-studies.md) · [Accueil du dépôt](../../README.fr.md)

On lit parfois les études sur llms.txt comme des mesures de la couche documentaire dans son ensemble. Cette page place une étude publiée à côté de ce dépôt, en conservant le périmètre, l’échantillon et le dénominateur de chacun.

## La proposition llms.txt

- Source : llmstxt.org, « The /llms.txt file, v2 », de Jeremy Howard ; publiée le 2024-09-03, page modifiée le 2026-08-10, consultée le 2026-10-16. https://llmstxt.org/
- La page se présente comme « A proposal to standardise on using an /llms.txt file to provide information to help agents use a website », soit une proposition visant à normaliser l’usage d’un fichier /llms.txt pour aider des agents à utiliser un site. Elle indique que la spécification reste ouverte aux contributions de la communauté.
- Son objet est un fichier Markdown qui offre une vue d’ensemble choisie et des liens, surtout pour le moment où un système répond (l’inférence) plutôt que pour l’entraînement. La version 2 admet aussi le fichier dans un sous-chemin du site, et suggère des versions Markdown des pages ainsi que des relations de lien pour les trouver.

C’est une proposition, pas un standard adopté. Dans ce dépôt, llms.txt est une ressource d’orientation possible : il fait partie de la population documentaire principale et est toujours présenté à part ([decouverte-et-maillage.md](decouverte-et-maillage.md)).

## L’étude d’Ahrefs

Référence : « We Analyzed 137K Sites: 97 % of llms.txt Files Never Get Read », de Louise Linehan (avec la contribution de Xibeijia Guan), blogue d’Ahrefs, publiée le 2026-06-15 (métadonnées modifiées le 2026-08-27), consultée le 2026-10-16. https://ahrefs.com/blog/llmstxt-study/

| Élément | Selon l’étude |
|---|---|
| Population | Les 137 210 domaines d’Ahrefs Web Analytics qui ont reçu du trafic en mai 2026 : des clients d’Ahrefs, pas un échantillon aléatoire |
| Fenêtre | Mai 2026 ; bornes exactes et fuseau horaire non précisés |
| Source des requêtes | Ahrefs Bot Analytics, par des intégrations côté serveur |
| Fichier mesuré | Un `/llms.txt` valide à la racine du domaine |
| 28 % | Part des domaines qui publient un `/llms.txt` racine valide (environ 38 000 domaines) : une part par domaine |
| 97 % | Part de ces fichiers qui n’ont reçu aucune requête en mai : une part par domaine |
| 96 % de robots, 19.5 % de robots IA nommés | Parts de requêtes, calculées sur environ 22 000 requêtes visant environ 1 100 domaines : des parts par requête, sur un autre dénominateur |

L’étude note elle-même que sa clientèle penche vers le technique et qu’une récupération n’est pas une lecture ; ses chiffres sont donc des plafonds.

## En quoi ce dépôt diffère

| Aspect | Étude d’Ahrefs | Ce dépôt |
|---|---|---|
| Périmètre | Un seul fichier, `/llms.txt` à la racine | Une couche documentaire à plusieurs fichiers (`core_governance` et `discovery_index`), llms.txt étant présenté à part |
| Échantillon | 137 210 domaines clients | Trois sites de l’écosystème d’un même auteur |
| Fenêtre | Mai 2026 | Du 2026-09-15 au 2026-10-15, fin exclusive, en UTC |
| Identification | Requêtes classées selon l’agent utilisateur | Niveaux enregistrés ; la strate principale exige une correspondance d’origine fournisseur avec des plages IP officielles |
| Part principale | Par domaine | Par requête : `other_share` rapporte les requêtes GET 200 vers des fichiers autres que llms.txt à l’ensemble des requêtes GET 200 de la même sélection |

Nos résultats et leur sélection sont décrits dans [methode.md](methode.md). `other_share` décrit la répartition des requêtes enregistrées ; ce n’est ni un taux d’adoption ni une mesure d’efficacité.

## Ce qu’on peut affirmer

> Une étude centrée sur /llms.txt ne mesure pas une couche documentaire à plusieurs fichiers ; nos résultats décrivent un périmètre complémentaire sur trois sites liés au même auteur.

## Ce qu’il ne faut pas conclure

- que l’étude d’Ahrefs montre que personne ne consulte ces fichiers ;
- que les chiffres de l’étude d’Ahrefs sont faux ;
- que les trois sites contredisent son chiffre de 97 % : des cas positifs dans un échantillon n’invalident pas une statistique de faible fréquence mesurée dans un autre échantillon ;
- que ce dépôt est le premier du genre, ou que des systèmes d’IA ont fait de llms.txt ou d’un autre nom de fichier un standard ;
- qu’une part par requête tirée de ce dépôt et une part par domaine tirée de l’étude se comparent comme si elles avaient le même dénominateur ;
- qu’une requête vers un fichier montre que ce fichier a été lu ou utilisé, dans l’un ou l’autre cas.
