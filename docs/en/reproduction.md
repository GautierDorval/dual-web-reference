# Reproduction

[Français](../fr/reproduction.md) · [Repository home](../../README.md)

This page lists the commands of the calculation chain, what each one reads and writes, which ones work offline, and what a public reader can and cannot redo. The stages themselves are described in [methodology](methodology.md).

## Corrected and historical reproduction

Default commands select r2. To reproduce the published tables and their presentation, run `analyze`, `render`, `build-site`, then `verify`. These commands make no acquisition.

`revise-public` is reserved for preparing a distinct local, unapproved revision. It transforms the inventoried r1 tables, changes the edition key, withholds protected daily rows and coverage complements, and regenerates the candidate catalog. It refuses a target already marked publicly accessible or approved. Do not run it against public r2. With identical eligible local inputs, the transformation is deterministic. `prepare-edition` prepares a local candidate manifest; it is not needed to reproduce published r2.

Each edition can be cited with its identifier, catalog digest and current status from `config/editions.json`. Only a valid external receipt permits reference approval. None of these citations implies scientific validation.

For r1, `analyze` and `render` verify the complete frozen payload and original rule/schema hashes instead of applying current styles. `verify --edition 2026-09-15_2026-10-15-r1` replays its sealed rules. r1 is never a target of `project-public`, `prepare-edition` or PNG rendering.

`prepare-next --private-root <directory>` uses existing local normalized and qualified inputs and writes only under the private root. Its full synthetic rehearsal uses the actual projection, measurement, metrics and figure functions. It does not acquire D1 data, activate a schedule or promote a reference. See [updates](updates.md).

The new consultation primary key adds `measurement_epoch_id` so separately recorded versions are not merged. Historical schemas remain sealed under `config/history/`. The metric structure remains compatible; `metrics_version` identifies the version 2 definitions. [metrics.schema.json](../../schemas/metrics.schema.json) describes values, null states, filters, numerator, denominator, provenance and bilingual labels.


## Environment

- Python standard library only, no package to install. Python 3.12 or later is required; local qualification covers Python 3.13.15 and 3.14.6. `.python-version` selects Python 3.14; the CI matrix checks Python 3.12, 3.13 and 3.14. A CI result applies only to the commit shown in that run.
- Entry point: `python -I scripts/dwr.py <command> [options]`. Isolated mode (`-I`) ignores `PYTHON*` environment variables and the user site directory.
- Windows: `pwsh .\scripts\dwr.ps1 <command> [options]` runs the same entry point with the `python` found on the path, in isolated mode, with UTF-8 output, and returns its exit code.
- Linux CI: `.github/workflows/ci.yml` runs on `ubuntu-24.04` with read-only permissions, actions pinned to full commit identifiers, no secret and no access to private sources. It runs the unit tests (synthetic fixtures), `analyze`, `render`, `build-site` and `verify`, then fails if the regeneration changed any committed file (`git diff --exit-code`). It never contacts the measured sites.
- Unit tests alone: `python -I -m unittest discover -s tests -t . -v`.

## Commands

| Command | Reads | Writes | Network |
|---|---|---|---|
| `import-existing --package <dir>` | export package: manifest, archives, marginal tables, reference figures | private import receipt and marginals; private reconciliation report | none |
| `acquire-readonly` | edition window | nothing: prints the planned queries and their SHA-256 (dry run) | none |
| `acquire-readonly --execute --confirm-scope <start>..<end>` | private acquisition settings | private raw results and acquisition log | reads the producer database through its client |
| `normalize` | the single private import, the private archive at its pinned commit, accepted acquisitions | private `normalized.json`: joint rows checked against the exports, deployment timeline | none (local repository read) |
| `qualify` | `normalized.json`, scope registry and rules, attribution rules, private source snapshots, `config/cases.json` | private `qualified.json` | none |
| `project-public` | validated private joint inputs; local unapproved target only | staged tables, catalog, metrics, figures and checksum manifest; one guarded installation | none |
| `analyze` | edition tables | public target: comparison only; local target: staged metrics, figures and manifest | none |
| `render` | tables, metrics, configuration | public figures: separate comparison only; local figures: staged installation; current pages, blocks, indexes and schemas regenerated | none |
| `verify` | every file of the working tree; the private values if `DWR_PRIVATE_ROOT` is set | nothing (report on standard output) | none |
| `publication-gate --ref <branch>` | every Git object reachable from the branch; private values of the private root | nothing (report on standard output, exit code 1 on any finding) | none (local repository read) |
| `build-site` | public files | `site/dist/` (rebuilt from scratch, never deployed) | none |
| `prepare-edition` | edition files and figures | `delta-report.json`, `SHA256SUMS.txt` | none, publishes nothing |
| `png-fallback --edition <id>` | local unapproved edition figures | staged optional PNGs; public targets refused before browser launch | local file rendering only |
| `png-fallback --edition <id> --preview <new-external-directory>` | edition figures copied outside canonical trees | optional PNG preview outside the repository; no historical replacement | local file rendering only |
| `status` | `data/status.json`, calendar | nothing (standard output) | none |

`prepare-next` derives its next window from private status and ignores no missing window; the other edition commands accept `--edition <id>`; the default is the candidate named in `config/editions.json`. Results are printed as JSON. A controlled `DwrError` prints `FAIL <code>: <detail>` on standard error and exits with code 2; `verify` exits with code 1 when a check fails, and a check that crashes counts as failed. `acquire-readonly` refuses a window that is not closed and any `--confirm-scope` other than the exact window. Dry run remains its default; for this edition it was executed once, with `--execute` and the exact `--confirm-scope 2026-09-15..2026-10-15`, in the private environment, never in CI.

The public stages (`analyze`, `render`, `verify`, `build-site`, `prepare-edition`, `status`) are offline and never contact the measured sites. `verify` checks that no module of the chain other than `acquire.py` imports network code.

## The private root

Private stages need `DWR_PRIVATE_ROOT` (or `--private-root`): an existing directory outside the repository root. A missing value, a missing directory or a directory inside the repository stops the stage (`private_root_missing`, `private_root_unavailable`, `private_root_inside_public_repository`). It holds the internal lock, imports, acquisitions, working files and source snapshots, and is never committed. Public stages do not need it. `verify` examines every file of the working tree, PNG figures and the built site included, with the same function as the publication gate below; when the private root is set, it also looks for the private values kept there, and without it that check is reported under `skipped`, never as passed. Test samples are synthetic.

## Publication gate

Before any publication, `python -I scripts/dwr.py publication-gate --ref <branch>` (a private stage) reads the Git objects reachable from the branch to publish: each commit (its header without the structural `tree` and `parent` lines, and its whole message), the name of each entry of each tree, trees included, and each file as raw bytes, binary files included; no path is excluded. It requires a history that runs linearly from the published root named in `config/publication-gate.json` (a single commit before the first publication, when the file is absent from the commit or names no root), with no merge commit, and admitted file types only; the root is read from the commit to publish, and a file that cannot be read stops the gate. A PNG must consist of one IHDR of 13 bytes, IDAT chunks and one empty IEND, with nothing after it and image data of exactly the announced size. Private values are compared without regard to case, and hexadecimal identifiers are detected in both cases; a JSON file is also checked after decoding its strings, and text after decoding percent escapes. Local paths are compared with the actual local roots of the machine that runs the gate (home folder in long and short form, private workspace) after folding case and separators; generic markers of other machines' paths (Windows user folders, `/home/<name>/`, `/Users/<name>/`, synchronized folder, application data) are an additional best effort, not a guarantee. A 40-character identifier is admitted only as an action pin or as the published root or distribution baseline listed in `config/publication-gate.json` and written exactly `owner/repository@<commit>`; a test requires every pin of the workflows to be in that list. A finding names a category and a path, and a path that holds a private value or an identifier is replaced by its position in the listing. The gate guards against private material included by mistake; it is not a proof against content crafted to evade it. A branch containing private working history is not publishable. A correction branch based on the published history may retain several reviewed commits only when every reachable commit passes the gate and its disclosed states are inventoried. A separate projection can instead be created as one reviewed commit on top of the published history. Published commits are never rewritten. The gate checks the root, not the published head: two linear histories from the same root both pass it. Continuity with the previous edition rests on checking, just before the push, that the verified remote main is an ancestor of the candidate, and that an existing remote correction branch can advance to it without rewriting history, and on pushing without force, which the branch protection of `main` enforces.

<!-- dwr:begin publication-gate -->
| Category | What the gate detects | Counterexamples tested |
|---|---|---|
| `history_not_from_published_root` | a history that does not run linearly from the published root named in `config/publication-gate.json` (more than one commit while no root is named, another root, or a merge commit, which any second root requires) | a second commit while no root is named; a root other than the named one; a merge commit after the named root |
| `unsupported_entry` | a symbolic link or a submodule in a tree | a symbolic link; a submodule entry |
| `file_type_not_admitted` | a file whose type is not in the admitted list | an executable file |
| `text_not_utf8` | a text file that is not valid UTF-8 | a Latin-1 byte in Markdown |
| `private_term` | a private repository name, private resource name or private label, in any case | in a file; in capitals in a file; in a file name; in the name of an empty tree; in the commit message; in a PNG text chunk; written as JSON Unicode escapes; JSON Unicode escapes in a file that starts with a byte order mark; percent-encoded in a URL |
| `private_identifier` | an account or database identifier of the acquisition configuration, in any case | in a test file; in capitals; in a file name, never echoed in the report |
| `private_commit` | a full commit identifier of the internal lock, in any case | in a CSV file; in capitals |
| `private_commit_prefix` | the first seven characters (or more) of a commit identifier of the internal lock | eight characters in Markdown; seven characters at the start of a log line; seven characters in a `/commit/` link |
| `local_root` | a local root of the machine that runs the gate (home folder in long or short form, private workspace), in any case and with any separators, also inside JSON strings and percent escapes | the home folder in lower case, as `ntpath.normcase` writes it; the home folder in capitals; the home folder with forward slashes; the home folder serialized by `common.canonical_json`; the `/c/…` form of a Unix-style shell; the 8.3 short name of the home folder; the private workspace path without the home prefix; the home folder percent-encoded in a URL |
| `local_path` | a generic marker of a local path on any machine, best effort (Windows user folder, `/home/<name>/`, `/Users/<name>/`, Unix-style shell user folder, synchronized folder, application data), in any case | a user folder in Markdown; a user folder serialized in JSON (doubled separators); a user folder written with forward slashes; a user folder in lower case; a `/home/<name>/` folder; a `/Users/<name>/` folder |
| `ip_address` | an IPv4 address | in Markdown; in a file name |
| `user_agent` | a browser user-agent string | in Markdown |
| `identifier_32` | a 32-character hexadecimal identifier, in either case | in lower case in code; in upper case in code; in a file name |
| `identifier_40` | a 40-character hexadecimal identifier, in either case, except an action pin or the published root/distribution baseline listed in `config/publication-gate.json` and written exactly `owner/repository@<commit>` | in a comment of a workflow template; an admitted pin value repeated without its `owner/repository@` prefix; a pin that is not in the list, on a `uses:` step; a pin that is not in the list, inside a `run:` block scalar; a `tree` line inside the commit message |
| `short_commit` | a short commit reference (`commit` followed by 7 to 12 hexadecimal characters) | in Markdown |
| `png_chunk_not_admitted` | a PNG chunk other than IHDR, IDAT and IEND | a text chunk; a palette chunk |
| `png_malformed` | a PNG whose structure differs from one IHDR of 13 bytes, IDAT chunks, one empty IEND, or whose image data differs from the announced size | data after IEND; a non-empty IEND; a second IHDR; extra image data; a truncated file; a wrong checksum; dimensions beyond 16 384 pixels |

Each of the 59 counterexamples above is planted by a mutation test in `tests/test_publication_gate.py`, which requires the gate to fail on it with that category; another test requires this table and the mutations to match one to one. A variant that is not listed is not claimed. Not covered: the pixels of a PNG, which render an SVG checked as text but are not read as text themselves, and content crafted on purpose to evade the gate.
<!-- dwr:end publication-gate -->

## PNG fallback

`node scripts/render_png.mjs <edition-id>` converts the SVG figures to PNG with Playwright (Chromium), in the light colour scheme at device scale 2, into `figures/<edition>/png/`. `DWR_PLAYWRIGHT_DIR` may point to the directory where Playwright is installed. PNG bytes are not bit-reproducible across engines: the SVG files are the canonical figures, and the PNG files are excluded from `SHA256SUMS.txt`.

## Determinism

The same inputs give identical bytes for every CSV, JSON and SVG output:

- JSON is canonical: UTF-8, sorted keys, two-space indentation, final line feed;
- CSV files have a fixed column order, a fixed row order and LF line endings; decimals are formatted in a fixed way;
- the SVG writer uses no randomness, no timestamp, no script and no external reference, and only the system font stack;
- `generated_at` is fixed for each candidate in `config/editions.json`, so a rebuild does not change it.

`verify` recomputes `metrics.json`, re-renders a figure, the data table of every figure (from its wide English variant), the case pages and the generated blocks in memory, and compares them byte for byte with the committed files. Private working files carry timestamps and are not part of this comparison.

## Digest files

- `catalog.json` lists the bytes and SHA-256 of each table, `reconciliation.json` and `case-checks.json`. It does not list itself, nor `metrics.json` and `figures.json`, which are derived after it, nor `SHA256SUMS.txt`.
- `figures.json` lists the SHA-256 of every SVG file, data table and input table of each figure.
- `SHA256SUMS.txt`, written by `prepare-edition` in the edition folder, has one line `<sha256>  <path from the repository root>` for every file of the edition folder and of `figures/<edition>/`. It never includes itself, and PNG files are left out. From the repository root, `sha256sum -c data/editions/<edition>/SHA256SUMS.txt` checks it on Linux; on Windows, `Get-FileHash -Algorithm SHA256` gives the same digests.

A matching digest shows that the files are those that were reviewed; it does not show that the observations are true, and no signature is involved. A review approves a digest; any later change invalidates that approval.

## CSV conventions

UTF-8 without byte order mark, LF line endings, comma separator, header row, RFC 4180 quoting where needed, decimal point, ISO 8601 dates, booleans written `true` and `false`, and an empty cell meaning null, never zero. Column types, primary keys and the minimum of 0 for counts are in the JSON schemas, including the [consultation schema](../../schemas/consultations.schema.json).

A spreadsheet-safe variant (`*.spreadsheet.csv`) is defined for copies meant to be opened in a spreadsheet: any cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return is prefixed with an apostrophe, so that it is never read as a formula. The canonical CSV files keep the exact values and are the ones to use for any calculation.

## What a public reader can and cannot redo

A reader with this repository alone can recompute every published number and figure from the public tables (`analyze`, `render`, `verify`, all offline, without a private root), check the digests, find the file and line of each relation in `links.csv`, and check that the daily tables, the family table and the edition tables agree with each other.

A reader cannot re-run the collection, the producer classification, the extraction from the producer database, the archive read or the graph snapshots: these depend on private repositories and on the private collector. Checking a digest and redoing an aggregation is not redoing the collection.

## How to cite an edition

Cite the edition identifier together with the SHA-256 of its `catalog.json`:

```text
Dual Web Reference, edition 2026-09-15_2026-10-15-r1 (September 15 to October 14, 2026 inclusive, UTC),
catalog.json SHA-256 <64 hexadecimal characters>, consulted <date>.
```

The digest is computed with `sha256sum data/editions/<edition>/catalog.json` or `Get-FileHash -Algorithm SHA256 data/editions/<edition>/catalog.json`, and it also appears in `SHA256SUMS.txt`. Cite the edition and catalog digest together with the current availability and review state in `config/editions.json`. A reference is approved only when its external receipt validates against the payload digest. A revision such as `r2` has its own identifier and digest ([updates](updates.md)).

## Preparation exit codes

| `prepare-next` result | Code | Meaning |
|---|---|---|
| `validation_failed`, `source_unavailable` | 1 | Preparation unsuccessful, freshness unchanged |
| `distribution_blocked_pending_contract`, `distribution_blocked_pending_policy_approval` | 0 | Private preparation complete, distribution still blocked |
| `unchanged`, window not ready or pending state without error | 0 | State recorded, no implicit approval |
| `FAIL <code>` (`DwrError`, including busy lock) | 2 | Controlled error on standard error |

Exit code 0 never authorizes distribution. Read the JSON state fields together with the exit code.

## Recovery after interruption

For `preparation/preparation.lock`, first verify that the owning process has stopped. Preserve the lock, `preparation/status.json`, candidate and receipt before intervention. Compare input and output digests against the receipt and inspect staging directories. A complete matching receipt allows the next run to recover the candidate and cursor; partial candidates or divergent bytes require explicit resolution, never silent replacement. Only after this inspection may the owner remove the stale lock and rerun `prepare-next`. An identical second replay must return `unchanged`.

The edition lock `.dwr-work/<edition>.lock` is separate: its staging directory contains `recovery.json` during installation and the backups required for restoration. Neither lock expires automatically. Locks coordinate producers following this protocol; they do not confine another process with the same permissions that writes arbitrarily into the directories. On POSIX, such a process can create an empty directory in the gap preceding `os.rename`, which may replace it. This race outside the cooperative lock is not qualified by Windows tests.

## Closed file sets and staged site output

`analysis/dwr/distribution.py` supplies one exact-set and byte-integrity check to `verify`, `build-site`, candidate preparation and the Git publication gate. The existing `publication-inventory.json` and `historical-editions.json` are identified by their baseline SHA-256 bytes; rebuilding them from the current directory cannot admit a new file. Their reviewed entries cover all historical edition and figure files, including PNGs. A fixed source list covers the remaining configuration, schemas and operational pointers. The two explicitly named workflow templates are source-only. No extension or whole-directory copy rule admits files.

The controlled repository roots are `data`, `figures`, `config` and `schemas`, including untracked files and empty directories. Unknown or private edition directories are rejected on these shareable surfaces. A private registry entry does not grant distribution authority; changing a public entry to private does not release its historical bytes from the contract. Root source-code and documentation files remain subject to the existing Git/privacy controls, not a claim that every repository filename is frozen. Mutable operational/configuration files still need semantic and privacy checks.

Before copying, the site builder declares each generated page and exact source/destination file. It reads accepted bytes, renders in memory, compares the sources again, writes a fresh staging directory, checks every staged filename and byte, and checks source stability once more. Existing `site/dist` is untouched until these checks pass. A fresh build replaces an old dist containing extra files without copying those extras. `verify` independently reconstructs the expected output plan and compares the actual dist, so an extra or modified file added after a successful build is refused. An archive made outside this CLI must run this check immediately before packaging; the code does not intercept arbitrary filesystem/archive utilities.

Historical manifest bytes are themselves pinned; they are not regenerated to authorize changes. The output plan is computed before observing staged files, with no self-approving output manifest. The private preparation manifest uses its own explicit payload and figure-generator set before sealing new bytes; this grants no public admission.

The Git gate checks the real tree at `distribution_baseline` and every reachable successor tree. Strict ancestors of that fixed public baseline retain the prior full-object privacy scan and their immutable Git identity; they are not retroactively required to match today's edition set. A file added and removed in later commits is still rejected. A fabricated baseline pin cannot exempt it. Worktree checks and Git checks are separate: untracked files do not occur in Git objects. Gate diagnostics for controlled entries use positions instead of detected filenames.

Paths must be relative, NFC-normalized and unambiguous across case-insensitive filesystems. Symlinks, junctions/reparse points, special files and submodules are refused. Windows junction tests and synthetic Git-entry collision tests are distinct from POSIX-only tests; a skipped platform branch is not a pass. Filesystem access and locks assume cooperating processes. These checks do not confine a malicious process with the same permissions.

### Site recovery

The exclusive `site/.build.lock` prevents cooperating builds from sharing a stage. A caught installation failure restores the former dist. If rollback or backup cleanup fails, retain the lock, `site/.dist-backup` and `.build-*` evidence for inspection. An abrupt process stop can occur between directory renames: stop the owner first, compare the candidate against a freshly computed plan and preserve the previous output, then resolve the retained directories and lock explicitly. No automatic stale-lock removal or crash-atomic two-directory transaction is claimed. A successful build alone is not approval, publication, collection validation or a confidentiality guarantee.
