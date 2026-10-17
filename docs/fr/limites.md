# Limites

[English](../en/limits.md) · [Accueil du dépôt](../../README.fr.md)

Chaque limite ci-dessous nomme ce qu’elle restreint, puis précise ce qui est établi, ce qui ne l’est pas et ce que la limite ne permet à personne de nier. Ce dernier point applique une règle simple : l’absence de preuve dans ces tables n’est pas une preuve d’absence.

## 1. Attribution

Restreint : à qui les requêtes peuvent être attribuées.

- **Établi** : les niveaux et les rôles enregistrés par le classificateur 2026-08-24.1. La branche à origine fournisseur exige un acteur déclaré doté d’un registre officiel et une correspondance avec les plages IP officielles de ce fournisseur ; elle est évaluée avant le prédicat Cloudflare en revue.
- **Non établi** : la fiabilité des deux niveaux qui dépendent de ce prédicat (`network_verified_claimed_actor`, `cloudflare_verified_unattributed`). Les signaux bruts de Cloudflare n’ont pas été conservés ; ces niveaux ne peuvent donc pas être réévalués. Reproduire le défaut localement ne montre pas qu’une catégorie vide a été reçue en production. La qualification à origine fournisseur repose sur une séparation des chemins de code, pas sur un audit de la chaîne entière : l’exactitude des registres, la provenance de l’en-tête IP quand un Worker en appelle un autre et les métadonnées de déploiement ne sont pas auditées de bout en bout.
- **Ne permet pas de nier** : qu’une partie des requêtes enregistrées comme non attribuées provienne de systèmes d’IA, d’outils de surveillance, de navigateurs ou de faux positifs ; rien n’est redistribué entre ces catégories. Qu’aucune requête de la fenêtre ne porte `unknown_automation` ni `claimed_actor_unverified` est compatible avec le défaut ; cela ne le prouve pas. Détails : [attribution.md](attribution.md).

## 2. Voies de découverte

Restreint : la manière dont un fichier a été trouvé.

- **Établi** : les références écrites dans les fichiers de l’instantané, par type, fichier et ligne ([links.csv](../../data/editions/2026-09-15_2026-10-15-r1/links.csv)).
- **Non établi** : la voie empruntée par un client ; les relations de lien de la section `<head>` et les en-têtes HTTP `Link`, qui ne sont pas extraits ; les références situées sur d’autres sites ; les adresses connues d’avance.
- **Ne permet pas de nier** : qu’un fichier ait été trouvé par llms.txt, par une page externe ou par une URL déjà connue ; ni que llms.txt ait joué un rôle les jours sans requête vers lui. Voir [decouverte-et-maillage.md](decouverte-et-maillage.md).

## 3. Instantané et octets déployés

Restreint : le contenu qui a été servi.

- **Établi** : le contenu de chaque fichier dans l’instantané source (le 2026-10-14 pour gautierdorval.com, le 2026-10-06 pour pagup.com et better-robots.com), et les extraits de cas vérifiés contre lui.
- **Non établi** : les octets servis chaque jour de la fenêtre. Une fusion ne déploie pas, plusieurs fichiers de gautierdorval.com ont changé pendant la fenêtre, la version historique de chaque ressource est inconnue, et l’instantané de pagup.com est un build.
- **Ne permet pas de nier** : qu’un fichier demandé en septembre ait eu un autre contenu que celui qui a été examiné, ou qu’il aurait alors reçu une autre classe.

## 4. Couverture partielle

Restreint : l’intégralité des comptes.

<!-- dwr:begin coverage -->
30 jours sur 30 ont des lignes archivées ; les 30 rapports d’archive sont partiels (déclarés), 28 sans attestation de fenêtre du collecteur et 2 avec un écart agrégat/V3 d’une requête (2026-10-06, 2026-10-13). Somme agrégée archivée 24 815, somme V3 24 813. Des lignes sur 30 jours ne prouvent pas une couverture intégrale.
<!-- dwr:end coverage -->

- **Établi** : des lignes archivées pour les jours de la fenêtre, et la concordance des exports et de l’agrégat conjoint avec l’archive.
- **Non établi** : l’intégralité. La concordance avec l’archive n’est pas une validation indépendante, puisque les deux proviennent de la même chaîne.
- **Ne permet pas de nier** : que des requêtes aient eu lieu sans être enregistrées. Un zéro enregistré (`observed_zero`) n’est pas une preuve d’absence. Voir [qualite-et-couverture.md](qualite-et-couverture.md).

## 5. L’agrégat conjoint est une lecture de la table du producteur

Restreint : ce que les cellules exactes peuvent montrer.

- **Établi** : des cellules exactes jour × site × chemin × méthode × statut × acteur × niveau, lues une seule fois et en lecture seule dans la table du producteur, avec des sommes de contrôle identiques avant et après la lecture, et une concordance avec les exports pour chaque chemin, chaque groupe d’acteurs, chaque jour et chaque combinaison de méthode et de statut. La répartition par rôle de la population principale, sa série quotidienne, sa récurrence et la carte de chaleur G06 découlent de ces cellules.
- **Non établi** : une validation indépendante. L’agrégat conjoint et les exports sont deux lectures d’une même table du producteur ; des sommes de contrôle identiques montrent que les compteurs n’ont pas changé pendant la lecture, pas que celle-ci forme un instantané transactionnel. Un lecteur public ne peut pas relancer l’extraction.
- **Ne permet pas de nier** : des requêtes que le producteur n’a pas enregistrées. Une combinaison sans aucune ligne signifie qu’aucune requête n’est enregistrée dans la table du producteur, jamais une absence mesurée sur le Web. Voir [methode.md](methode.md).

## 6. L’écosystème d’un même auteur

Restreint : la généralisation.

- **Établi** : trois applications d’une même démarche, sur une personne, une organisation et un produit.
- **Non établi** : l’indépendance des trois sites, ou quoi que ce soit au sujet d’autres sites, d’autres auteurs ou du Web en général.
- **Ne permet pas de nier** : que d’autres sites présentent d’autres répartitions, plus élevées ou plus basses.

## 7. Requêtes possiblement déclenchées par l’exploitant

Restreint : l’interprétation de qui a déclenché une requête.

- **Établi** : la provenance de l’initiative vaut `unknown` pour chaque ligne (`not_established`).
- **Non établi** : qui a déclenché chaque requête. Une requête à origine fournisseur, même de rôle `user_initiated_fetch`, peut avoir été déclenchée par l’exploitant du site, par exemple pendant l’essai d’un assistant sur son propre site.
- **Ne permet ni de nier ni d’affirmer** qu’une partie des requêtes a été déclenchée par l’exploitant. Le trafic inconnu ne devient jamais du trafic de l’exploitant faute d’autre explication, et les coïncidences temporelles sont des indices, pas des correspondances avec des requêtes. La lecture sans les récupérations initiées par un utilisateur est une analyse de sensibilité, pas une preuve d’indépendance.

## 8. Aucun parcours exécuté

Restreint : ce qu’on peut dire de la navigation.

- **Établi** : des parcours disponibles (références écrites dans des fichiers) et des comptes agrégés par URL.
- **Non établi** : toute suite de requêtes faite par un client donné.
- **Ne permet pas de nier** : que des clients aient suivi les parcours disponibles, ou d’autres.

## 9. GET 200 est un statut enregistré

Restreint : ce que signifie un succès.

- **Établi** : le collecteur a enregistré la méthode GET et le statut 200.
- **Non établi** : les octets servis (non revérifiés) ; que le contenu ait été analysé, lu, conservé ou utilisé ; toute réponse produite à partir de lui.
- **Ne permet ni de nier ni d’affirmer** que le contenu a été utilisé.

## 10. Grains de confidentialité

Restreint : le niveau de détail publié.

- **Établi** : les tables suivent les grains fixés avant les résultats dans [small-cell-policy.json](../../config/small-cell-policy.json). Aucune adresse IP, aucun agent utilisateur, témoin (cookie), identifiant de session ou d’appareil, jeton, référent libre, chaîne de requête, transcription, ni date de premier ou de dernier accès par cellule ou par chemin. Les sorties quotidiennes ne portent jamais de chemin ni de nom d’acteur.
- **Non établi** : tout ce qui exigerait de croiser un jour avec un chemin, ou un jour avec un acteur ; le propriétaire a validé cette politique le 2026-10-17.
- **Ne permet pas de nier** : des régularités qui n’apparaîtraient qu’à un grain plus fin. Voir [confidentialite.md](confidentialite.md).
