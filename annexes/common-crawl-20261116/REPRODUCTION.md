# Reproduire et vérifier l’annexe

Exécuter depuis la racine du worktree DWR portant `codex/common-crawl-20261116`. Python 3.12 ou plus, bibliothèque standard seulement. Le correctif n’est branché à aucune commande d’édition ni à un workflow.

## Vérification sans réseau

```powershell
$cold = $env:PAGUP_COLD_STORAGE
if (-not $cold) { $cold = [Environment]::GetEnvironmentVariable('PAGUP_COLD_STORAGE', 'User') }
if (-not $cold -or -not (Test-Path -LiteralPath $cold)) { throw 'Stockage froid indisponible' }
$evidence = Join-Path $cold 'Preuves-Audits\dual-web-reference\common-crawl-20261116'
python -I -B scripts/common_crawl_annex.py verify "$evidence\run-01"
python -I -B scripts/common_crawl_annex.py verify "$evidence\analysis-02"
python -I -B scripts/common_crawl_annex.py verify annexes/common-crawl-20261116
python -I -B -m unittest discover -s tests -t . -p test_common_crawl_annex.py -v
```

Le manifeste de l’annexe lie ses fichiers de revue. `sources.json` épingle en plus le script, ses tests et les sources canoniques consultées. Vérifier ces références, sans réécrire de manifeste :

```powershell
$sources = Get-Content -Raw -LiteralPath 'annexes\common-crawl-20261116\sources.json' | ConvertFrom-Json
foreach ($item in $sources.repository_files) {
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.path).Hash.ToLowerInvariant()
    if ($actual -ne $item.sha256) { throw "Empreinte différente : $($item.path)" }
}
```

`seal` crée une liste de fichiers et leurs empreintes ; il ne valide aucune observation. Ne pas le lancer pour faire disparaître un échec de `verify` sur une preuve existante. Le manifeste s’exclut lui-même ; les empreintes des manifestes privés sont épinglées dans `results.json` et le reçu privé `final-state.json` donne l’empreinte finale du manifeste de revue.

## Recalcul de la comparaison à partir des mêmes octets

Le dossier de preuves contient `context.json`, avec le chemin privé réellement utilisé. Il ne contient aucun secret d’accès. Les instantanés sources existants restent en lecture seule.

```powershell
$context = Get-Content -Raw -LiteralPath "$evidence\context.json" | ConvertFrom-Json
$snapshotRoot = $context.snapshot_root
$replay = Join-Path $evidence 'analysis-replay'
python -I -B scripts/common_crawl_annex.py analyze-cached `
    --run "$evidence\run-01" `
    --output $replay `
    --snapshot-root $snapshotRoot
if ($LASTEXITCODE -ne 0) { throw 'Recalcul incomplet ou invalide' }
python -I -B scripts/common_crawl_annex.py verify $replay
if ((Get-FileHash "$replay\matrix.csv").Hash -ne (Get-FileHash 'annexes\common-crawl-20261116\matrix.csv').Hash) {
    throw 'Matrice différente'
}
```

Cette commande n’instancie aucun client réseau. Elle refuse un dossier de sortie existant et vérifie d’abord les empreintes et l’ensemble exact des fichiers de `run-01`. Les horodatages d’analyse changent ; la matrice et les octets extraits demeurent reproductibles. Sans `--snapshot-root`, seule l’archive est relue et aucune égalité avec les octets d’un instantané local n’est revendiquée.

Les chemins `artifact_path` de `source-evidence.json` et `artifacts` de `captures.json` sont relatifs à `analysis-02`. `compressed_artifact` est relatif au même dossier. Les `private_raw_ref` des requêtes sont relatifs à `$evidence`. Les métadonnées intégrales et les corps restent sur le stockage froid, hors de Git.

## Reproduction réseau, distincte du recalcul

La commande suivante est fournie comme recette ; elle n’a pas été lancée une seconde fois. La sélection de neuf URL reste inchangée. Une nouvelle passe nécessite d’enregistrer son budget cumulé et ses tentatives avant exécution. Les plafonds sont appliqués **par invocation**, pas par un registre partagé entre plusieurs processus : ne pas lancer plusieurs copies, une boucle ou cette commande à répétition.

```powershell
$nextRun = Join-Path $evidence 'run-reproduction'
python -I -B scripts/common_crawl_annex.py collect `
    --selection annexes/common-crawl-20261116/selection.json `
    --output $nextRun
$collectExit = $LASTEXITCODE
Write-Output "COLLECT_EXIT=$collectExit"
```

Plafonds : dix URL, trois index, trente requêtes CDX, vingt WARC, 100 MiB pour l’ensemble des corps téléchargés, cinq secondes entre départs. Le fichier figé retient neuf URL et deux index. `limit=1001` sert de sentinelle ; atteindre cette limite ou une limite de taille rend la réponse incomplète, sans pagination implicite. Les limites de décompression sont de 16 MiB par enregistrement.

Aucune relance ni redirection. Un 403, 429 ou 503 arrête la passe et conserve `Retry-After` ; l’absence de réessai évite de raccourcir ce délai. Les erreurs de transport arrêtent aussi la passe. Un statut 200 qui ignorerait la plage WARC arrête le téléchargement avant lecture du corps. Les 502/504 sont enregistrés comme échecs sans relance. Un répertoire existant n’est jamais écrasé.

Code prévu : `0` pour une passe complète, `2` pour une passe incomplète. Le premier lancement n’a pas sauvegardé `$LASTEXITCODE` séparément ; le shell a rapporté `1`. Le reçu conserve cette limite de journalisation. L’analyse ne dépend pas de ce code : `requests.json`, `queries.json` et les corps bruts établissent les résultats.

## Contrôles du dépôt

La suite existante et les commandes suivantes sont hors ligne. `build-site` produit uniquement `site/dist`, sans déploiement. Aucune annexe n’est ajoutée au plan de sortie du site.

```powershell
python -I -B -m unittest discover -s tests -t . -v
python -I -B scripts/dwr.py analyze
python -I -B scripts/dwr.py build-site
python -I -B scripts/dwr.py verify
```

Ne pas utiliser `prepare-next`, `acquire-readonly --execute`, une publication ou un changement de registre pour reproduire cette annexe. Le [reçu](RECEIPT.md) indique les contrôles réellement exécutés et leurs limites.
