# Automated-only private qualification / Qualification privée automatisée

This page documents v1. The separate reduced release candidate is described in [Profile B](AUTOMATED_PROFILE_B.md).

Cette page décrit la v1. La candidate réduite distincte est documentée dans le [profil B](AUTOMATED_PROFILE_B.md).

## English

`prepare-automated` implements `dwr-automated/1.0.0` as a separate **private-only** contract. It is neither an activation of the synthetic `future_projection` prototype nor a change to the historical small-cell policy. It does not publish, register an edition, change `latest`, move the legacy cursor, acquire data, or activate scheduling.

The selection is fixed: qualified main-documentary resources, recorded GET 200, recorded `provider_origin_verified_actor` tier, and roles `ai_training` or `ai_search`. Filtering happens before all observation-derived inventory, counts, metrics, figures, metadata and file manifests. Recorded attribution remains under review; a role is not proof of actual training use or citation.

### Inputs and execution

Use a **new private workspace outside every Git checkout**, separate from any existing candidate. Preserve the accepted native acquisition and pinned sources, including their exact bytes and receipts. Do not reacquire merely to refresh a timestamp. Never edit an accepted candidate, a receipt or a cursor to satisfy admission.

Prepare and qualify this workspace using the source contract in [PRIVATE_NEXT.md](PRIVATE_NEXT.md). The new command reconstructs normalized and qualified inputs from those same native receipts and archive hashes. Missing/changed provenance markers, inconsistent sources, malformed counts or dates, non-consolidated windows and concurrent preparations fail closed. There is no diagnostic-file or synthetic-data override.

From the intended code checkout, in PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python scripts/dwr.py normalize-next --private-root $privateRoot
python scripts/dwr.py qualify-next --private-root $privateRoot
python scripts/dwr.py prepare-automated --private-root $privateRoot
```

If the exact normalized and qualified files were already copied and verified with the accepted sources, only the last command is necessary. It independently repeats source admission. No `--execute`, public destination, edition override or CLI clock override exists on this command.

Outputs are installed atomically under `automated/candidates/<window-r1>/`. The contract identifier plus the window identify this separate candidate. An existing candidate is immutable: unchanged inputs and exact regenerated output bytes permit an idempotent readback; changed inputs require a distinct workspace/revision. Recovery may restore only `automated/status.json`. `preparation/status.json` and its legacy cursor are not written.

Readback reconstructs all four private diagnostics as well as the projection, enforces the exact file/directory set and the receipt's invariant fields, and rejects a coherently edited diagnostic/receipt before restoring status. The historical preparation timestamp must be canonical UTC and after consolidation; it is not replaced by the current time. Its original value is authenticated only by the independently retained receipt/archive fingerprint, not reconstructed from source observations.

### Output boundaries

| Surface | Contract |
|---|---|
| Monthly consultations | Site, path, documentary family, software actor family/name, role, selected count. Whole window; no day, active-day count, timestamp or epoch partition. |
| Monthly inventory and summaries | Selected resources only; resource, actor and family marginals from those consultations. |
| Daily tables | Full UTC calendar by site and role, plus a separate family-and-role table. No path, named actor or extra site-and-family crossing. |
| Coverage | Minimal categorical archive presence, observation availability, source qualification and declared coverage. Counts describe only the selected observations. Missing dates are null. |
| On-demand | Constant U0: `withheld_not_zero`, null count and unknown initiation provenance, independent of whether rejected rows exist. |
| Metrics and figures | Recalculated solely from these closed outputs. No total of all actors, excluded count, complementary ratio, full registry or private-input digest. |
| Provenance | Categorical window-level limitations from admitted provenance, independently of observation rows. No daily epoch partitions or private identifiers. Unknown stays unknown. |
| Comparison and documentary graph | Growth remains null until a separate baseline/comparability qualification. Graphs and case evidence are not qualified by this contract; G09 panels remain explicitly unavailable. |

`projection/projection.json` is canonical; `schema.json` is its generated closed JSON Schema. CSV, metrics, figure data, FR/EN reports and manifests are deterministic derivatives. The verifier regenerates every allowed filename and byte. Unknown fields, extra files/directories, malformed types, missing calendar cells and inconsistent marginals are rejected.

Figures G01 (daily selected total), G02 (recorded roles), G03 (sites), G06 (documentary families), G08 (coverage) and per-site G09 (unavailable graph) have English/French, wide/compact SVG variants and their data CSV. Other historical figure identifiers and cases are not silently reused under the new selection. The reports request no measured origin, external asset, font or analytics.

The complete candidate is private. `diagnostics/` and `preparation-receipt.json` contain source fingerprints, source-wide exclusions and operational evidence that are **not** part of the projection's allowlist or manifest. Copying the whole candidate into a public repository would violate this boundary. A valid projection manifest still does not authorize publication.

### Scope of qualification

The coverage adapter minimizes **admitted** archive evidence; it does not independently authenticate an archive or infer completeness from counts. A qualified source here means the private input contract was checked, not that classifier attribution or coverage is scientifically established. A missing archive does not establish producer downtime. A zero under partial coverage only means no selected row recorded within that partial observation.

The tests vary rejected rows, counts, identities, epochs and private diagnostics while fixing the selected observations and categorical evidence, and compare all output bytes. They also exercise the real offline source-admission path with native-format synthetic SQL receipts and changed rejected counts. This proves the stated conditional independence, not that all possible future evidence producers are independent of protected activity.

Small automated groups can still reveal an actor or resource; historical releases and auxiliary data remain available. There is no universal anonymity/non-reconstruction claim. `complete_private` and `private_contract_qualified_pending_release_review` are distinct from publication approval, reference approval or independent scientific review. Distribution remains `distribution_blocked_pending_release_review`.

Run the targeted checks with:

```powershell
python -I -B -m unittest discover -s tests -t . -p test_automated_contract.py -v
```

Inspect actual FR/EN mobile and desktop captures of the new private reports and figures before handoff, then obtain the independent review of the stable code and candidate. Any future public release requires its own authorization, complete disclosure-history review and qualification of all proposed release surfaces.

## Français

`prepare-automated` met en œuvre `dwr-automated/1.0.0` dans une voie **exclusivement privée**, distincte du prototype synthétique et de la politique historique. La sélection retient la population documentaire principale, GET 200, le niveau enregistré `provider_origin_verified_actor` et les rôles `ai_training` ou `ai_search`. Ces classifications restent sous examen ; elles ne prouvent ni entraînement effectif ni citation.

Utiliser un nouvel espace privé extérieur aux dépôts Git, distinct de toute candidate existante. Réutiliser l'acquisition native acceptée et les sources épinglées, sans en modifier les octets. Les commandes PowerShell ci-dessus normalisent et qualifient ces sources selon [PRIVATE_NEXT.md](PRIVATE_NEXT.md). Si ces entrées sont déjà présentes et vérifiées, seule `prepare-automated` est nécessaire ; elle reconstruit quand même les données attendues depuis les reçus. Aucune collecte, destination publique, substitution diagnostique ou simulation synthétique n'est offerte.

La candidate est installée sous `automated/candidates/<fenêtre-r1>/`, identifiée conjointement par son contrat et sa fenêtre. Le curseur historique, `latest`, les éditions et la politique antérieure restent inchangés. Une candidate existante doit reproduire exactement les sources et sorties attendues ; sinon, une révision distincte est nécessaire. Seul l'état séparé `automated/status.json` peut être rétabli après interruption.

La reprise reconstruit aussi les quatre diagnostics privés, impose l'ensemble exact des fichiers et dossiers ainsi que les champs invariants du reçu, puis refuse toute falsification cohérente avant de rétablir l'état. La date historique de préparation doit être canonique en UTC et postérieure à la consolidation ; elle n'est jamais remplacée par l'heure courante. Sa valeur d'origine est authentifiée seulement par l'empreinte indépendante conservée du reçu ou de l'archive, sans être reconstruite depuis les observations.

Les détails de chemins et d'acteurs sont mensuels, sans jour, compte de jours actifs, première/dernière date ou partition d'époque. Les séries quotidiennes croisent séparément jour/site/rôle et jour/famille/rôle. Tous les comptes, inventaires et dérivés sont calculés après sélection. Les accès à la demande suivent U0 : un bloc constant `withheld_not_zero`, compte null et provenance d'initiation inconnue, quelle que soit leur présence réelle.

Le calendrier de couverture reste complet. Les dates indisponibles sont nulles ; un zéro sous couverture partielle signifie uniquement qu'aucune ligne sélectionnée n'a été enregistrée dans l'observation disponible. La présence d'une archive et la cohérence de ses comptes ne prouvent pas une couverture complète. Une archive absente ne démontre pas une panne du producteur. La qualification des sources n'est pas une validation scientifique de l'attribution.

`projection/projection.json` est la source canonique du paquet sélectionné, avec son schéma fermé et ses dérivés déterministes : CSV, métriques, figures, rapports FR/EN et manifeste. Les figures G01, G02, G03, G06, G08 et G09 par site ont des variantes larges et compactes ; les autres figures historiques et les cas ne sont pas repris implicitement. Les graphes G09 restent indisponibles dans ce contrat et la croissance reste null. Les rapports ne contactent aucun site mesuré et n'utilisent aucun actif externe.

Les diagnostics privés et le reçu de préparation sont séparés de `projection/`. Ils peuvent contenir des empreintes de sources, des comptes exclus et leurs compléments. Ils ne doivent jamais être copiés dans une diffusion. Le vérificateur refuse tout champ, fichier ou dossier inattendu dans la projection et rapproche les marges de la sélection.

Les tests vérifient l'indépendance de tous les octets diffusibles vis-à-vis des lignes rejetées, à sélection et preuves catégorielles fixes. Le parcours réel d'admission est aussi exercé avec des reçus SQL synthétiques natifs. Cette preuve reste conditionnelle : de petits groupes automatisés peuvent révéler un acteur ou une ressource ; les divulgations historiques et les données auxiliaires demeurent accessibles. Aucune garantie générale d'anonymat ou de non-reconstruction n'est affirmée.

`complete_private` atteste une construction privée. La diffusion reste `distribution_blocked_pending_release_review`. Examiner les captures FR/EN mobiles et bureau réelles, puis faire revoir indépendamment le code et la candidate stables. Une diffusion ultérieure exige son autorisation propre et la qualification de toutes ses surfaces et de l'historique public pertinent.
