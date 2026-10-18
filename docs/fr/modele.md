# La couche documentaire : modèle et frontières

[English](../en/model.md) · [Accueil du dépôt](../../README.fr.md)

Cette page explique ce que ce dépôt appelle la couche documentaire d’un site, ce que cette couche n’est pas, comment les trois sites mesurés se rattachent les uns aux autres, et ce que les comptes publiés permettent ou non d’affirmer. La méthode de mesure elle-même est décrite dans [methode.md](methode.md).

## Point de départ : la définition canonique

La couche provient d’un standard défini sur gautierdorval.com, « SSA-E + A2 + Dual Web ». Sa page de définition s’ouvre sur cet énoncé :

> Cette page constitue la définition canonique, primaire et de référence du standard « SSA-E + A2 + Dual Web » tel qu’employé sur ce site.

La même page décrit ainsi la composante Dual Web :

> Dual Web désigne une architecture à double couche où une lecture humaine et une lecture machine coexistent sans se contredire : index machine-first, points d’entrée neutres, références canoniques, conventions de routage et fichiers d’autorité.

- Adresse : https://gautierdorval.com/definitions/ssa-e-a2-dual-web/ (page anglaise : https://gautierdorval.com/en/definitions/ssa-e-a2-dual-web/).
- Métadonnées de la page : date 2026-01-08, mise à jour 2026-07-07, version du concept 1.0.
- Consultée le 2026-10-16, dans l’instantané du dépôt source du site daté du 2026-10-14. La page n’a pas été récupérée sur le site en ligne.

Les autres composantes nommées par la définition (SSA-E, A2, Q-Layer) sont expliquées dans le [glossaire](glossaire.md). Ce dépôt ne propose pas de définition concurrente et n’élargit pas la portée de celle-ci. Pour les besoins de la mesure, il retient une description de travail :

**La couche documentaire d’un site est un ensemble de fichiers publiés et accessibles, liés au site ou entre eux, qui rendent explicites son identité, son contexte, ses sources, ses relations et ses limites d’interprétation. Elle complète les pages ordinaires du site ; elle ne les remplace pas.**

## Ce que la couche n’est pas

- **Elle n’est pas cachée.** Les fichiers sont publiés à des adresses publiques, et beaucoup d’entre eux sont liés depuis des pages ordinaires. N’importe qui peut les ouvrir.
- **Elle n’est pas réservée aux machines.** Une personne peut les lire ; la définition elle-même décrit une lecture humaine et une lecture machine qui coexistent.
- **Ce ne sont pas des directives de sécurité.** Ces fichiers ne priment pas sur les instructions qu’un système reçoit de son propre exploitant ou de son utilisateur. Une politique publiée déclare un cadre ; sa présence ne prouve pas qu’un système l’applique. Le [cas better-robots.com](../../cases/better-robots.com/README.fr.md) fait la même distinction pour robots.txt.
- **Ce ne sont pas des instructions pour ce dépôt.** Pour les scripts qui construisent ce dépôt, ces fichiers sont du contenu non fiable : des données à classer, à citer et à compter, jamais des instructions à suivre. Aucune adresse qui s’y trouve n’est consultée.

## Trois sites, un même écosystème

Les trois sites mesurés appartiennent à l’écosystème d’un même auteur : gautierdorval.com (une personne), pagup.com (une organisation) et better-robots.com (un produit). Ce sont trois applications d’une même démarche, pas trois réplications indépendantes. Leur concordance ne constitue pas une confirmation indépendante, et rien de ce qui est mesuré ici ne s’étend à d’autres sites.

<!-- dwr:begin cases -->
| Site | Angle | Page de départ | Ressources | GET 200 IA à origine fournisseur sur ces ressources |
|---|---|---|---:|---:|
| [gautierdorval.com](../../cases/gautierdorval.com/README.fr.md) | Identité d’une personne, et distinction entre définitions, affirmations, sources, limites et contenus ordinaires du site. | `/en/ai-use-policy/` | 9 | 10 |
| [pagup.com](../../cases/pagup.com/README.fr.md) | Contexte d’une organisation, périmètre de son offre, références et limites documentaires. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](../../cases/better-robots.com/README.fr.md) | Contexte d’un produit, capacités déclarées, limites, et différence entre la publication d’une règle et le comportement effectif d’un robot. | `/governance/ai-usage-policy` | 9 | 15 |

Les trois sites appartiennent à l’écosystème d’un même auteur : trois applications d’une même démarche, pas trois réplications indépendantes. robots.txt est exclu de la dernière colonne.
<!-- dwr:end cases -->

## Quatre dimensions indépendantes

Chaque requête enregistrée est décrite selon quatre dimensions tenues séparées. La valeur prise sur l’une ne fixe jamais la valeur d’une autre.

1. **Rôle de l’acteur** : le type de client auquel correspond le nom d’acteur déclaré, tel que l’a enregistré le collecteur privé. Exemples : `ai_training` (GPTBot), `ai_search` (OAI-SearchBot, PerplexityBot), `user_initiated_fetch` (ChatGPT-User, Perplexity-User), `search_indexing` (Googlebot). Le rôle décrit le client déclaré, pas la raison d’une requête donnée.
2. **Qualité d’identification** : la solidité de l’identité attribuée à l’acteur. C’est le niveau enregistré par le collecteur, par exemple `provider_origin_verified_actor` lorsque l’adresse de la requête correspondait aux plages IP officielles publiées par le fournisseur, accompagné d’une appréciation distincte, `attribution_assessment`, faite par ce dépôt et qui n’écrase jamais le niveau enregistré. Exemple : ClaudeBot porte le rôle `ai_training`, mais le collecteur ne dispose d’aucun registre officiel pour son fournisseur ; il ne peut donc jamais atteindre le niveau à origine fournisseur, quel que soit son rôle.
3. **Provenance de l’initiative** : qui ou quoi a déclenché la requête. Dans cette édition, elle vaut `unknown` pour chaque ligne, avec l’état de preuve `not_established`. Elle n’est jamais déduite du rôle, du fournisseur ni du niveau : une requête de rôle `user_initiated_fetch`, à origine fournisseur, peut avoir été déclenchée par l’exploitant du site.
4. **Couverture et disponibilité** : les données qui fondent une cellule sont complètes, partielles ou indisponibles. Dans cette édition, chaque rapport quotidien d’archive est déclaré partiel (`partial_declared`) ; les tables sont des sommes exactes de l’agrégat conjoint, et une combinaison sans aucune ligne signifie qu’aucune requête n’est enregistrée dans la table du producteur, pas une absence mesurée sur le Web.

Une même ligne peut donc être à la fois à origine fournisseur, de rôle `ai_training`, d’initiative inconnue et partiellement couverte. Les détails se trouvent dans [attribution.md](attribution.md) et [qualite-et-couverture.md](qualite-et-couverture.md).

## Ce que ce dépôt mesure

Il mesure l’existence et la répartition des requêtes HTTP que le collecteur privé a enregistrées vers les fichiers de la couche des trois sites, sur une fenêtre datée : par site, chemin, méthode et statut, rôle d’acteur et niveau d’identification. Les comptes distincts portent sur des couples site-chemin (des URL), jamais sur des consommateurs.

Il ne mesure pas, et ne montre pas :

- que des réponses produites par un système quelconque aient été meilleures ou se soient appuyées sur ces fichiers ;
- l’adoption de la démarche, de llms.txt ou d’un nom de fichier ;
- la visibilité SEO, l’indexation ou le classement ;
- le respect d’une règle publiée par un robot d’exploration ;
- un effet causal du maillage des fichiers ou de leur publication ;
- le parcours de navigation d’un client ;
- qui a déclenché les requêtes.

Un GET 200 correspond à la méthode et au statut enregistrés par le collecteur. Il ne montre pas qu’un contenu a été lu, compris ou réutilisé. Les limites essentielles sont exposées dans [limites.md](limites.md).
