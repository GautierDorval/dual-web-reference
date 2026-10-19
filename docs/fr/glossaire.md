# Glossaire

[English](../en/glossary.md) · [Accueil du dépôt](../../README.fr.md)

Définitions en langage courant des libellés, codes et sigles qui figurent dans les tables et les pages. Les libellés en format `code` sont conservés tels qu’enregistrés : ce sont des identifiants, pas des traductions.

## Unités et temps

- **Couple site-chemin** : un chemin sur un site, par exemple pagup.com avec `/llms.txt`. C’est l’unité de tout compte distinct. Il compte des URL, jamais des consommateurs, et les comptes distincts par acteur ne sont jamais additionnés.
- **Édition** : un ensemble figé de tables publiques pour une fenêtre, identifié sous la forme `<début>_<fin>-r<n>`, par exemple `2026-09-15_2026-10-15-r1`. Le statut de candidate indique une approbation de référence en attente, pas sa disponibilité. r1 est accessible publiquement sans être approuvée ; r2 reste locale.
- **Révision** : le suffixe `r<n>`. Une correction crée une nouvelle révision (`r2`) avec son motif, l’écart chiffré, son auteur, la personne qui l’a revue et un lien vers la révision précédente ; la révision antérieure n’est jamais modifiée ([mises-a-jour.md](mises-a-jour.md)).
- **Fenêtre** : la période mesurée d’une édition. Les fenêtres mensuelles de référence commencent le 15, en UTC.
- **Fin exclusive** : la date de fin n’est pas incluse. La fenêtre `[2026-09-15, 2026-10-15)` couvre du 15 septembre au 14 octobre inclusivement, soit 30 jours ; la suivante, `[2026-10-15, 2026-11-15)`, compte 31 jours.

## Méthodes et statuts HTTP

- **GET 200** : une requête GET qui a reçu le statut 200 (succès), tel qu’enregistré par le collecteur. Les octets servis ne sont pas revérifiés. C’est le statut de comptage du résultat principal.
- **HEAD** : une requête identique à GET, sauf que la réponse ne porte aucun contenu (RFC 9110). Ce n’est pas une lecture de document.
- **304 (Not Modified)** : la réponse à une requête conditionnelle quand la copie que détient le client est encore à jour ; elle ne porte aucun contenu.
- **405 (Method Not Allowed)** : la méthode est connue, mais n’est pas prise en charge pour cette ressource. Dans le périmètre du relevé initial de cette édition, l’agrégat conjoint consigne chaque erreur comme une requête POST qui a reçu le statut 405.
- **301, 404, 5xx** : redirection, ressource introuvable, erreur du serveur. Aucun de ces statuts ne correspond à un contenu de document servi avec succès.

## Niveaux d’identification enregistrés

Le collecteur privé enregistre un niveau par requête (version de classificateur 2026-08-24.1). Ce dépôt le conserve tel qu’enregistré ; voir [attribution.md](attribution.md).

- `provider_origin_verified_actor` : un acteur déclaré dont le fournisseur publie un registre officiel (GPTBot, OAI-SearchBot, ChatGPT-User, PerplexityBot, Perplexity-User, Googlebot, Applebot), et dont l’adresse de requête correspondait aux plages IP officielles de ce fournisseur. Cette branche n’utilise pas le prédicat Cloudflare en revue. Elle qualifie l’origine de la requête, pas la chaîne entière. Les acteurs d’Anthropic n’ont pas de registre de ce type dans le collecteur et ne peuvent pas atteindre ce niveau.
- `network_verified_claimed_actor` : un nom d’acteur déclaré (par exemple ClaudeBot), sans correspondance avec un registre officiel, accepté par le prédicat de vérification réseau en revue.
- `cloudflare_verified_unattributed` : aucune identité de fournisseur ; le libellé dépend lui aussi du prédicat en revue, qui peut laisser passer des clients qui ne sont pas du tout des robots.
- `spoofed_or_failed_verification` : un nom de fournisseur déclaré dont l’origine ne correspondait pas au registre officiel.
- `claimed_actor_unverified` : un nom déclaré seulement, sans vérification.
- `unknown_automation` : aucune identification.
- `synthetic_probe` : une requête de contrôle synthétique signée, envoyée par le collecteur lui-même.
- `cryptographically_verified_actor` : niveau défini par le contrat du producteur ; non produit par le classificateur 2026-08-24.1.

**Prédicat en revue** : le test qu’utilise le collecteur pour tenir une requête pour vérifiée par Cloudflare. Il est satisfait quand l’indicateur de robot vérifié vaut vrai, ou quand le champ de catégorie de robot vérifié contient autre chose qu’une valeur nulle ou absente ; une chaîne vide le satisfait aussi.

## attribution_assessment

Une interprétation distincte faite par ce dépôt ([attribution-rules.json](../../config/attribution-rules.json)) ; elle n’écrase jamais le niveau enregistré.

- `registry_match_not_affected_by_predicate` : l’origine correspondait à un registre officiel ; le prédicat en revue n’est pas utilisé.
- `registry_mismatch_not_affected_by_predicate` : l’origine ne correspondait pas au registre du fournisseur déclaré.
- `recorded_classification_reliability_under_review` : « Classification enregistrée, fiabilité en cours de revue ». Le libellé dépend du prédicat en revue ; il est conservé et jamais redistribué.
- `unverified_claim` : un nom déclaré sans vérification.
- `unverified_unknown` : aucune identification.
- `synthetic_marker` : une requête de contrôle du collecteur.
- `not_observed_in_covered_versions` : un niveau que les versions de classificateur couvertes ne produisent pas.

## Rôles d’acteur

Enregistrés par le producteur d’après le nom d’acteur déclaré. Un rôle décrit le client déclaré, jamais qui a déclenché une requête.

- `ai_training` : robot déclaré comme collectant du contenu pour l’entraînement de modèles (par exemple GPTBot).
- `ai_search` : robot d’un service de recherche ou de réponse par IA (par exemple OAI-SearchBot, PerplexityBot).
- `user_initiated_fetch` : récupération faite par un assistant pour répondre à la demande d’un utilisateur (par exemple ChatGPT-User, Perplexity-User).
- `search_indexing` : robot d’un moteur de recherche (par exemple Googlebot, Bingbot, Applebot).
- `seo_tool` : robot d’un outil SEO (par exemple AhrefsBot, SemrushBot).
- `generic_automation` : autre automatisation déclarée.
- `unknown` : aucun rôle enregistré.

Le résultat principal retient les trois premiers rôles.

## Classes de périmètre

`core_governance`, `discovery_index`, `supporting_documentation`, `operational_descriptor`, `control_resource`, `technical_resource`, `undeclared_bucket` et `unresolved_scope` sont définies, avec des exemples, dans [roles-des-fichiers.md](roles-des-fichiers.md) et [perimetre.md](perimetre.md).

## Conventions des tables

- `coverage_status` = `partial_declared` : l’archive du producteur déclare partiel le rapport du jour ; des lignes existent, mais l’intégralité n’est pas attestée ([qualite-et-couverture.md](qualite-et-couverture.md)).
- `observed` : la cellule est enregistrée avec un compte supérieur à zéro. `observed_zero` : un zéro explicite, écrit seulement dans `daily-family-summary.csv`, pour un jour, une famille et un rôle sans aucune requête de ce type dans la table du producteur ; sous une couverture partielle, ce n’est pas une preuve d’absence. Une cellule vide (null) signifie non disponible ou non calculable, jamais zéro.
- Ligne absente : dans les tables r1 figées, aucune ligne signifie aucune requête enregistrée au grain indiqué. Dans les tables quotidiennes r2, les lignes protégées sont retenues : leur absence ne signifie jamais zéro.
- `protected_strata`, avec `http_method` et `http_status` = `ANY` : dans `daily-summary.csv` de r1 figée, la ligne quotidienne unique par site et par population qui regroupe toutes les requêtes des strates protégées, quels que soient leur rôle, leur niveau enregistré, leur méthode ou leur statut ([confidentialite.md](confidentialite.md)).
- `cell_derivation` = `joint_exact` : la cellule est une somme exacte de lignes de l’agrégat conjoint ([methode.md](methode.md)).
- `initiation_provenance` = `unknown`, `initiation_evidence_status` = `not_established` : qui a déclenché la requête n’est pas établi.
- `source_mode` = `joint_acquisition` : l’édition a été construite à partir d’une extraction bornée, en lecture seule, de l’agrégat conjoint du producteur (jour, site, chemin, méthode, statut, acteur et niveau croisés ensemble), contrôlée contre les exports du relevé interne.
- `other_share` : les requêtes GET 200 vers des fichiers autres que llms.txt, rapportées à l’ensemble des requêtes GET 200 de la même sélection ; ce n’est pas un taux d’adoption.

## Couches nommées par les sites

Plusieurs noms de fichiers et rôles des cas emploient le vocabulaire de la démarche de l’auteur. Ce dépôt n’a pas besoin de ces termes pour compter des accès. Ils sont expliqués par leur fonction, telle que l’énoncent la définition canonique, les fichiers des sites et les rôles du registre ; lorsque les lettres d’un sigle n’y sont pas développées, on le précise.

- **SSA-E** : selon la définition canonique, la couche de stabilisation sémantique des entités et des relations (définitions, périmètres, hiérarchies, cohérence).
- **A2** : selon la même définition, une sous-couche de contraintes interprétatives ciblées, pour les pages ou les zones à haut risque de dérive.
- **Dual Web** : la double couche de lecture décrite dans [modele.md](modele.md).
- **Q-Layer** : selon la même définition, une couche de légitimité de réponse : elle précise quand une réponse est autorisée, doit être clarifiée, suspendue ou ne pas être produite (`response-legitimacy.md`). Le sens de la lettre Q n’y est pas précisé.
- **EAC** : nommée External Authority Control dans les fichiers des sites ; déclare quelles sources externes sont admissibles, pour quelles familles d’affirmations, selon quelles exigences de preuve et sous quels plafonds de sortie (`eac-registry.json`, `eac-claims.json`).
- **CCL** : nommée Causal Context Layer dans les fichiers des sites ; décrit les situations qui déclenchent un besoin, le besoin latent, les résultats visés et les dérivations à éviter (`causal-context-map.json`).
- **SAL** : nommée Situational Applicability Layer dans les fichiers des sites ; énonce quand une capacité s’applique et quand elle ne s’applique pas, avec les preuves requises (`situational-applicability-map.json`).
- **CPI** : décrite dans les fichiers des sites comme une couche de pondération interprétative : des sources pondérées selon la classe d’affirmation et le champ d’autorité (`interpretive-weighting-policy.json`). Le développement des lettres n’est pas établi ici.
- **CAI** : décrite dans les fichiers des sites comme une couche d’intégrité attestée : des empreintes d’énoncés canoniques choisis, et ce que ces empreintes ne prouvent pas (`attested-interpretive-units.json`, `content-digests.json`). Le développement des lettres n’est pas établi ici.
- **MCP** : le Model Context Protocol, par lequel un serveur expose des outils ou du contexte ; un fichier qui décrit un tel serveur est un descripteur opérationnel.
- **`/.well-known/`** : préfixe de chemin réservé aux fichiers de métadonnées qui valent pour tout le site (RFC 8615).
