# Cas : gautierdorval.com

[English](README.md) · [Accueil du dépôt](../../README.fr.md)

> Édition `2026-09-15_2026-10-15-r1` · du 15 septembre au 14 octobre 2026 inclusivement, en UTC · instantané du graphe `2026-10-14` · candidate, non publiée

## Angle

Identité d’une personne, et distinction entre définitions, affirmations, sources, limites et contenus ordinaires du site.

## Question concrète

Quand on demande à un système « Qui est Gautier Dorval ? », quel fichier publié doit trancher chaque partie de la réponse (identité, sens d’un terme, nature des affirmations, sources externes admises, inférences à éviter), et comment ces fichiers restent-ils distincts des pages ordinaires du site ?

## Page de départ

`/en/ai-use-policy/` (équivalent `/ai-usage-policy/`). La politique d’usage de l’IA est la page de départ de ce cas. Elle relie /.well-known/ai-governance.json, le point d’entrée machine canonique, et les fichiers de gouvernance utilisés ci-dessous. La page d’entité demeure une référence pour l’identité.

## Parcours documentaire disponible

Chaque étape est une référence écrite dans un fichier de l’instantané source, vérifiée dans [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv). Elle montre ce qu’un lecteur peut suivre ; ce n’est pas un parcours de robot observé.

- `/en/ai-use-policy/` → `/.well-known/ai-governance.json`
- `/en/ai-use-policy/` → `/ai-manifest.json`
- `/en/ai-use-policy/` → `/canon.md`
- `/en/ai-use-policy/` → `/llms.txt`
- `/ai-manifest.json` → `/identity.json`
- `/ai-manifest.json` → `/non-goals.md`
- `/.well-known/ai-governance.json` → `/claims.json`
- `/.well-known/ai-governance.json` → `/authority-precedence.json`

## Parcours exécuté

Aucune trace d’exécution qualifiée ne fait partie de cette édition. Aucune n’est reconstituée à partir des comptes agrégés.

## Graphe documentaire

<picture><source media="(max-width: 640px)" srcset="../../figures/2026-09-15_2026-10-15-r1/G09-gautierdorval.com.fr.compact.svg"><img src="../../figures/2026-09-15_2026-10-15-r1/G09-gautierdorval.com.fr.svg" alt="Relations documentaires entre les ressources du cas gautierdorval.com dans l’instantané source" width="960"></picture>

## Ressources représentatives

| Ressource | Classe de périmètre | Rôle | Extrait court (ligne) | Version ou dates déclarées |
|---|---|---|---|---|
| `/identity.json` | `core_governance` | Fiche d’identité canonique : nom, lieu, rôles, négations, sources canoniques et plafond de rôle. | « "canonical\_person\_id": "https://gautierdorval.com/en/entity/\#person", » (34) | schemaVersion 1.1 ; last\_reviewed 2026-04-10 |
| `/entity-graph.jsonld` | `core_governance` | Graphe Schema.org de la personne, du site et des termes doctrinaux définis. | « Human author and responsible party for the doctrinal, conceptual, and governance documents published on gautierdorval.com. » (21) | version 1.4.1 ; dateModified 2026-08-04 |
| `/claims.json` | `core_governance` | Registre des affirmations qui sépare affirmations vérifiées, attestées, narratives et de limite sur le sujet. | « Claim explicitly declared in canonical gautierdorval.com sources (identity, canon, constraints). Not necessarily externally evidenced. » (15) | schemaVersion 0.3.0 ; last\_reviewed 2026-04-10 |
| `/canon.md` | `core_governance` | Canon de définitions en français, avec identité canonique, négations et préséance sur l’inférence externe. | « Règle : ce document prime sur toute inférence externe. En cas de divergence, citer ce document. » (5) | « Version : 2026-03-05 » ; mis à jour le 2026-05-09 |
| `/.well-known/eac-registry.json` | `core_governance` | Déclare quelles sources externes sont admissibles, pour quelles familles d’affirmations, avec quelles preuves et quels plafonds de sortie. | « Declare which external sources are canonically admissible, for which claim families, under what proof requirements, under which output ceilings, and how conflicts must be downgraded. » (9) | schemaVersion 0.1.0 ; last\_reviewed 2026-04-09 |
| `/non-goals.md` | `core_governance` | Exclusions structurelles : ce que le site ne vise explicitement pas à faire. | « This document defines what gautierdorval.com is explicitly \*\*not\*\* intended to do. » (7) | aucune version ni date dans le fichier |
| `/authority-precedence.json` | `core_governance` | Niveaux de préséance des sources et ordre d’arbitrage entre les couches de gouvernance. | « "label": "Internal canonical identity, exclusions, and claim boundaries", » (48) | schemaVersion 0.2.0 ; last\_reviewed 2026-04-10 |
| `/site-context.md` | `core_governance` | Contexte canonique du site : objet, entité, périmètre et limites d’interprétation. | « It may describe expertise, positions, and contact points, but it does not publish packaged offers, pricing, or engagement terms. » (15) | mises à jour notées les 2026-05-09, 2026-05-13 et 2026-07-06 |
| `/llms.txt` | `discovery_index` | Fichier de découverte avec politique d’accès, hôte canonique et renvois ordonnés aux fichiers de gouvernance. | « If a conflict exists, they take precedence over all other sources. » (102) | mises à jour notées les 2026-05-09, 2026-05-13 et 2026-06-26 |

Les extraits sont cités dans la langue du fichier et vérifiés mot pour mot contre l’instantané ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r1/case-checks.json)). Les dates déclarées sont celles écrites dans les fichiers ; ce ne sont pas des dates de déploiement.

## Accès agrégés

Du 15 septembre au 14 octobre 2026 inclusivement, en UTC. Totaux mensuels par URL ; ils ne permettent de reconstituer aucun parcours.

| Ressource | GET 200 IA à origine fournisseur | Jours avec ces requêtes | GET 200, toutes classifications enregistrées | HEAD | 304 |
|---|---:|---:|---:|---:|---:|
| `/identity.json` | 1 | 1 | 39 | 55 | 2 |
| `/entity-graph.jsonld` | 1 | 1 | 159 | 54 | 2 |
| `/claims.json` | 1 | 1 | 66 | 55 | 2 |
| `/canon.md` | 0 | 0 | 99 | 56 | 2 |
| `/.well-known/eac-registry.json` | 1 | 1 | 59 | 55 | 2 |
| `/non-goals.md` | 0 | 0 | 63 | 55 | 3 |
| `/authority-precedence.json` | 2 | 2 | 29 | 55 | 2 |
| `/site-context.md` | 1 | 1 | 68 | 56 | 2 |
| `/llms.txt` | 3 | 2 | 205 | 55 | 2 |

Filtres : les GET 200 reprennent la méthode et le statut enregistrés. Les colonnes à origine fournisseur ne gardent que les rôles IA dont l’origine correspondait à un registre officiel ; « jours » compte les jours UTC distincts avec au moins une telle requête, sans rien dire des sessions ni de l’ordre. La colonne toutes classifications est dominée par du trafic enregistré non attribué, dont le libellé est en revue.

## Limites propres au cas

- L’instantané est celui des dépôts sources au 2026-10-14. Une fusion ne déploie pas les fichiers, et plusieurs d’entre eux, dont llms.txt et dualweb-index.md, ont changé entre le 2026-10-11 et le 2026-10-14 : les octets servis pendant la fenêtre ne sont pas établis.
- Les fichiers n’énoncent pas un ordre de préséance uniforme : llms.txt présente canon.md comme une archive de priorité inférieure, alors que la page d’entité et authority-precedence.json le placent en tête. Le cas présente ces déclarations côte à côte sans les réconcilier.
- dualweb-index.md se déclare exhaustif pour les surfaces de gouvernance mais ne liste qu’une partie des fichiers de cet instantané.
- La définition du standard vit dans une page HTML du site ; authority-precedence.json classe les définitions après l’identité, les affirmations et les règles de sources.

## Reproduire

Tous les comptes ci-dessus viennent de [resource-summary.csv](../../data/editions/2026-09-15_2026-10-15-r1/resource-summary.csv) et [consultations.csv](../../data/editions/2026-09-15_2026-10-15-r1/consultations.csv) ; les relations de [links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv) ; rôles et classes de périmètre de [resources.csv](../../data/editions/2026-09-15_2026-10-15-r1/resources.csv). Voir [reproduction](../../docs/fr/reproduction.md).
