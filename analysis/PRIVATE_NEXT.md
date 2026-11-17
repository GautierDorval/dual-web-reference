# Private next-window inputs / Sources privées de la fenêtre suivante

## English

This manual workflow prepares the calendar cursor's next edition outside the public repository. It does not register an edition, update public data, activate scheduling, approve distribution or publish anything. `prepare-next` remains offline. Only `acquire-next --execute` contacts the producer, using a closed list of SELECT statements for the three configured sites. It never requests the measured origins.

### Private workspace and inputs

Use a separate private root, outside every public checkout and separate from an earlier edition's workspace. The CLI never copies old inputs forward. Paths below are relative to that private root:

- `lock/acquisition-config.json`: `account_id`, `database_name`, `client_dir`; optionally `expected_client_version`, `wrangler_entrypoint`, its `wrangler_entrypoint_sha256`, and `log_path`. `client_dir` must contain the intended local Wrangler configuration. The default client is the already installed `npx --no-install wrangler`; an explicitly pinned entrypoint uses Node directly. Authentication comes from the existing environment. Do not put credentials in either JSON file.
- `lock/sources-config.json`: `archive.repository`, `archive.tables_directory`, `archive.commit` and `graph_serving_repositories`, plus any evidenced `measurement_provenance`. An empty graph mapping explicitly leaves the documentary graph unavailable. A current registry or an older snapshot does not establish the graph, classifier or deployment of a later window.
- The archive directory contains `manifest.json` and exactly the four tables `reports.csv`, `windows.csv`, `governance_daily.csv`, `site_counts.csv` under `tables/YYYY-MM/` for each month intersected by the window. The manifest binds `repository` to the canonical repository named in the private configuration, the full immutable `commit`, and each file's `path`, `byte_length` and `sha256`. Resolve and verify that pin from the canonical archive before creating the manifest; locally written hashes alone do not authenticate an upstream source. Keep the private repository identity out of shareable code and documentation. No Runtime table is consumed.

The next window comes from the private preparation cursor, falling back to the public cursor. A pending window is not skipped. The real UTC clock and `config/edition-calendar.json` enforce the consolidation delay before an executed acquisition or preparation. There is no CLI clock override.

### Commands (PowerShell)

Set `$privateRoot` to the prepared private workspace. Run from this repository's intended checkout:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python scripts/dwr.py acquire-next --private-root $privateRoot
# Read the dry-run scope, then supply that exact start..exclusive-end value.
python scripts/dwr.py acquire-next --private-root $privateRoot --execute --confirm-scope $confirmedScope
python scripts/dwr.py normalize-next --private-root $privateRoot
python scripts/dwr.py qualify-next --private-root $privateRoot
python scripts/dwr.py prepare-next --private-root $privateRoot
```

The SQL plan reads schema metadata, per-day joint aggregates, registry and deployment evidence, independently grouped file/actor/day/HTTP/path-and-HTTP marginals, and before/after daily counts. Agreement checks consistency within one producer; it is not independent measurement validation or a database transaction snapshot. A changed total or inconsistent marginal stops normalization. A path whose recorded category changes during the window is rejected for explicit review.

Acquisition receipts retain the exact query, result hash, client version, source configuration identity and explicit `rows_written=0` / `changed_db=false` evidence. Exactly one accepted acquisition may match the cursor. Failed attempts remain separately recorded. Repeating an accepted acquisition creates ambiguity; reuse its receipts or prepare an explicit new revision instead. Normalization and qualification are deterministic and refuse changed existing outputs. Qualification and preparation recompute the normalized inputs against source receipts, archive hashes and source configuration, so edited provenance is not accepted merely because totals still match.

`prepare-next` always requires the `private-next-inputs/1.0.0` source contract and verifies it against the source files. Removing or changing the marker cannot select a legacy admission path. Earlier hand-built normalized inputs must be regenerated through `normalize-next` and `qualify-next` in a separate workspace using the preserved acquisition and pinned sources; adding a marker alone is insufficient. Historical editions and their projection commands are unchanged.

A site/day absent from the grouped SQL result can have an explicit zero in an available archive. Its archive count is checked against the absence of joint rows, while all existing SQL groups must match the joint groups exactly. Missing archive dates remain unavailable; no zero row is inserted into the producer export.

### Meaning of the private candidate

All producer rows remain in `working/<edition>/normalized.json`. Dates without an archive remain `observation_unavailable`. For candidate tables, **every count** excludes those dates, including per-resource summaries; `source-exclusions.private.json` records their private rows and totals. Missing dates are not zeros. Existing partial archive reports retain their declared status, even when their counts reconcile.

Unattested classifier versions remain unknown; a known intraday transition without separable row provenance remains `mixed_epoch_unresolved`. No proportional split or automatic M1 comparison is introduced. Missing documentary snapshots produce null resource evidence, unverified case checks, no graph edges and explicit unavailable G09 panels in both languages. Scope classification still follows the versioned registry and does not establish current file content.

The candidate receipt seals its input manifest and generated files. `complete_private` means the local package was built; distribution remains blocked pending the existing disclosure contract and policy. Review `measurement-report.json`, `delta-report.json`, `disclosure-report.json` and the unavailable states before drawing conclusions. Inspect rendered mobile figures before handoff. Neither these commands nor passing tests authorize a publication, a source repair, an origin crawl or a scheduled collection.

Temporary Windows sharing locks during installation, state replacement or staging cleanup receive a bounded retry (under four seconds of waiting). Other filesystem errors are not retried. A persistent cleanup lock is reported as `cleanup_status: pending` with the exact staging-directory name; it does not replace the original preparation failure or advance the cursor. Inspect that owned staging directory before removing it. Qualified inputs remain available for an offline retry without another acquisition.

## Français

Ce parcours manuel prépare la fenêtre désignée par le curseur dans un espace privé distinct. Il ne modifie ni les données publiques ni le registre des éditions. Il n’active aucune planification et n’autorise aucune diffusion. `prepare-next` fonctionne hors ligne. Seule l’exécution explicite de `acquire-next`, avec confirmation exacte de la période, lit la base du producteur au moyen de requêtes SELECT bornées aux trois sites. Aucun site mesuré n’est appelé.

Les fichiers privés, leurs champs et les commandes PowerShell sont décrits ci-dessus. Le manifeste des archives doit provenir d’un commit canonique vérifié et contenir les empreintes et tailles des quatre tables pour chacun des mois concernés. Les empreintes calculées localement ne suffisent pas à authentifier la provenance. Les anciennes sources ne sont jamais recopiées automatiquement dans la fenêtre suivante. Le délai de consolidation est vérifié avec l’heure UTC réelle.

Les extractions conjointes sont rapprochées de regroupements SQL distincts sur les fichiers, acteurs, journées et dimensions HTTP. Cette concordance démontre une cohérence interne au producteur, sans constituer une mesure indépendante ni un instantané transactionnel. Les reçus lient requêtes, résultats, configuration de la source et version du client. La qualification et la préparation recalculent les données attendues pour refuser toute provenance modifiée. Un échec conserve son reçu ; plusieurs extractions acceptées pour la même fenêtre sont considérées comme ambiguës.

`prepare-next` exige toujours le contrat `private-next-inputs/1.0.0` et le vérifie avec les sources. Un marqueur supprimé ou inconnu ne permet aucun chemin de compatibilité implicite. Les anciennes entrées construites manuellement doivent être régénérées par `normalize-next` et `qualify-next` dans un espace distinct, avec l’acquisition conservée et les sources épinglées ; ajouter le marqueur ne suffit pas. Les éditions historiques et leurs commandes de projection sont inchangées.

Un couple site/jour absent du regroupement SQL peut correspondre à un zéro explicite dans une archive disponible. Ce compteur est rapproché de l’absence de lignes conjointes ; tous les groupes SQL présents doivent correspondre exactement aux groupes conjoints. Une archive manquante reste indisponible et aucune ligne zéro n’est ajoutée à l’export du producteur.

Toutes les lignes du producteur restent privées. Une journée sans archive reste indisponible et ses lignes sont exclues de tous les comptes de la candidate, avec un relevé privé des exclusions. Elle n’est jamais convertie en zéro. Les archives partielles conservent leur statut déclaré. Les versions de classificateur non attestées restent inconnues et une transition intrajournalière non séparable reste non résolue. Aucune croissance par rapport à M1 n’est déduite automatiquement.

Sans instantané documentaire qualifié, les preuves de présence et les relations restent nulles, les cas ne sont pas déclarés vérifiés et les figures G09 affichent leur indisponibilité en français et en anglais. La classification du périmètre repose toujours sur le registre versionné ; elle ne prouve pas le contenu actuel des fichiers.

Le statut `complete_private` atteste uniquement la construction locale du paquet. Les rapports de mesure, de comparaison et de divulgation, les états indisponibles et les captures mobiles doivent être examinés avant remise. La publication, la réparation des sources, les appels aux origines et les collectes planifiées nécessitent leurs autorisations propres.

Un verrou de partage Windows temporaire reçoit une reprise bornée à moins de quatre secondes d’attente. Les autres erreurs ne sont pas réessayées. Si le nettoyage reste bloqué, le résultat indique `cleanup_status: pending` et le nom du dossier temporaire concerné, sans masquer l’échec initial ni avancer le curseur. Les entrées qualifiées sont conservées pour une reprise hors ligne.
