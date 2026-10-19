# Cas : better-robots.com

[English](README.md) · [Accueil du dépôt](../../README.fr.md)

> Édition `2026-09-15_2026-10-15-r2` · du 15 septembre au 14 octobre 2026 inclusivement, en UTC · instantané du graphe `2026-10-06` · candidate locale ; référence non approuvée

**90 URL documentaires ; 122 GET 200 IA à origine fournisseur sur ce site.** Couverture partielle ; un des trois cas du même écosystème d’auteur, pas une réplication indépendante.

## Question et portée

Contexte d’un produit, capacités déclarées, limites, et différence entre la publication d’une règle et le comportement effectif d’un robot.

## Question concrète

Selon les fichiers de gouvernance de better-robots.com, que permet de publier le plugin Better Robots.txt, et que ne peut-on pas conclure, à partir d’une règle publiée seule, sur le comportement effectif d’un robot donné ?

## Page de départ

`/governance/ai-usage-policy` (équivalent `/fr/governance/ai-usage-policy`). La page d’accueil y renvoie ; sa section de niveau 3 relie les fichiers de contexte produit et de limites.

## Parcours documentaire disponible

Chaque étape est une référence écrite dans un fichier de l’instantané source, vérifiée dans [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv). Elle montre ce qu’un lecteur peut suivre ; ce n’est pas un parcours de robot observé.

Chemins copiables seulement. Une ressource visitée manuellement en ligne peut différer de l’instantané daté ; les octets complets de l’instantané privé ne sont pas distribués.

## Lire par fonction

- `/plugin-context.md` : Contexte produit : ce à quoi sert le plugin et ce qu’il ne garantit pas.
- `/plugin-scope.md` : Capacités déclarées dans et hors du périmètre, et frontière entre le plugin et l’audit /check.
- `/limitations-context.md` : Limites publiques du produit comme outil de publication.
- `/robots-txt-context.md` : Définit robots.txt comme une déclaration d’intention, pas une preuve du comportement des robots.
- `/robots.txt` : Règle d’exploration publiée par le site lui-même, exemple de la couche de règles (ressource de contrôle, hors population principale).
- `/ai-usage-policy.md` : Texte de la politique en Markdown, dont la préférence d’usage déclarée sur l’entraînement de modèles.
- `/.well-known/anti-plausibility.json` : Complétions qu’un lecteur ne doit pas inventer au sujet du produit.

Ces sept repères de lecture introduisent les tables complètes de sources et de comptes ci-dessous ; aucune observation ni classe de périmètre n’est retirée.

- `/` → `/governance/ai-usage-policy`
- `/governance/ai-usage-policy` → `/plugin-context.md`
- `/governance/ai-usage-policy` → `/plugin-scope.md`
- `/governance/ai-usage-policy` → `/robots-txt-context.md`
- `/governance/ai-usage-policy` → `/limitations-context.md`
- `/governance/ai-usage-policy` → `/robots.txt`

## Parcours exécuté

Aucune trace d’exécution qualifiée ne fait partie de cette édition. Aucune n’est reconstituée à partir des comptes agrégés.

## Graphe documentaire

<picture><source media="(max-width: 640px)" srcset="../../figures/2026-09-15_2026-10-15-r2/G09-better-robots.com.fr.compact.svg"><img src="../../figures/2026-09-15_2026-10-15-r2/G09-better-robots.com.fr.svg" alt="Relations documentaires entre les ressources du cas better-robots.com dans l’instantané source" width="960"></picture>

## Ressources représentatives

| Ressource | Classe de périmètre | Rôle | Extrait court (ligne) | Version ou dates déclarées |
|---|---|---|---|---|
| `/plugin-context.md` | `core_governance` | Contexte produit : ce à quoi sert le plugin et ce qu’il ne garantit pas. | « It does not guarantee crawler compliance, technical enforcement, or live-site configuration state without inspection. » (11) | aucune déclarée |
| `/plugin-scope.md` | `core_governance` | Capacités déclarées dans et hors du périmètre, et frontière entre le plugin et l’audit /check. | « is not proof that the plugin was installed or configured on the audited site. » (27) | aucune déclarée |
| `/limitations-context.md` | `core_governance` | Limites publiques du produit comme outil de publication. | « It cannot, by itself, guarantee obedience, indexing outcomes, legal force, or security enforcement. » (11) | aucune déclarée |
| `/robots-txt-context.md` | `core_governance` | Définit robots.txt comme une déclaration d’intention, pas une preuve du comportement des robots. | « It is not proof of blocking, proof of compliance, or a security control. » (10) | aucune déclarée |
| `/robots.txt` | `control_resource` | Règle d’exploration publiée par le site lui-même, exemple de la couche de règles (ressource de contrôle, hors population principale). | « User-agent: GPTBot » (38) | « last updated 2026-05-16 » |
| `/ai-usage-policy.md` | `core_governance` | Texte de la politique en Markdown, dont la préférence d’usage déclarée sur l’entraînement de modèles. | « Not permitted without explicit written permission. » (233) | miroir de la page de politique datée du 2026-03-19 |
| `/.well-known/anti-plausibility.json` | `core_governance` | Complétions qu’un lecteur ne doit pas inventer au sujet du produit. | « claiming the plugin enforces or verifies compliance » (8) | schema\_version 1.1 |
| `/.well-known/ai-governance.json` | `core_governance` | Point d’entrée qui déclare l’intention d’usage et ne remplace aucun contrôle réel. | « They do not replace infrastructure controls, private contracts, or human verification. » (290) | schema\_version 2.4 |
| `/llms.txt` | `discovery_index` | Index de découverte qui oriente les questions sur le plugin vers les fichiers de contexte et de périmètre. | « is not the plugin runtime. » (266) | aucune déclarée |

Les extraits sont cités dans la langue du fichier et vérifiés mot pour mot contre l’instantané ([case-checks.json](../../data/editions/2026-09-15_2026-10-15-r2/case-checks.json)). Les dates déclarées sont celles écrites dans les fichiers ; ce ne sont pas des dates de déploiement.

## Accès agrégés

Du 15 septembre au 14 octobre 2026 inclusivement, en UTC. Totaux mensuels par URL ; ils n’établissent aucune session exécutée ni ordre de navigation.

| Ressource | GET 200 IA à origine fournisseur | Jours avec ces requêtes | GET 200, toutes classifications enregistrées | HEAD | 304 |
|---|---:|---:|---:|---:|---:|
| `/plugin-context.md` | 1 | 1 | 36 | 1 | 2 |
| `/plugin-scope.md` | 1 | 1 | 34 | 1 | 2 |
| `/limitations-context.md` | 1 | 1 | 35 | 1 | 3 |
| `/robots-txt-context.md` | 1 | 1 | 38 | 1 | 2 |
| `/robots.txt` | 419 | 30 | 4 146 | 17 | 4 |
| `/ai-usage-policy.md` | 3 | 3 | 76 | 1 | 2 |
| `/.well-known/anti-plausibility.json` | 2 | 2 | 16 | 0 | 1 |
| `/.well-known/ai-governance.json` | 3 | 3 | 61 | 0 | 1 |
| `/llms.txt` | 3 | 3 | 148 | 1 | 3 |

Filtres : les GET 200 reprennent la méthode et le statut enregistrés. Les colonnes à origine fournisseur ne gardent que les rôles IA dont l’origine correspondait à un registre officiel ; « jours » compte les jours UTC distincts avec au moins une telle requête, sans rien dire des sessions ni de l’ordre. La colonne toutes classifications est dominée par du trafic enregistré non attribué, dont le libellé est en revue.

## Limites propres au cas

- Les requêtes vers ces fichiers sont des accès à la documentation du produit. Ce ne sont ni des installations, ni des activations, ni des événements du plugin : le plugin fonctionne sur d’autres sites WordPress.
- Le robots.txt du site accorde l’accès d’exploration (Allow) aux robots listés, alors que la politique d’usage énonce une préférence distincte sur l’entraînement. Les deux sont des déclarations ; aucune ne montre ce qu’un robot fait du contenu.
- L’instantané est celui du dépôt source au 2026-10-06 ; le déploiement de ces octets exacts pendant la fenêtre est supposé, pas établi. Des fonctions de périphérie, comme un robots.txt géré par le CDN, ne peuvent pas être exclues à partir du dépôt.
- robots.txt est une ressource de contrôle : il est présenté dans sa propre section et n’est jamais ajouté à la population documentaire principale.

## Reproduire

Tous les comptes ci-dessus viennent de [resource-summary.csv](../../data/editions/2026-09-15_2026-10-15-r2/resource-summary.csv) et [consultations.csv](../../data/editions/2026-09-15_2026-10-15-r2/consultations.csv) ; les relations de [links.csv](../../data/editions/2026-09-15_2026-10-15-r2/links.csv) ; rôles et classes de périmètre de [resources.csv](../../data/editions/2026-09-15_2026-10-15-r2/resources.csv). Voir [reproduction](../../docs/fr/reproduction.md).
