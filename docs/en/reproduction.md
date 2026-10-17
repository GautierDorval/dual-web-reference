# Reproduction

[Français](../fr/reproduction.md) · [Repository home](../../README.md)

This page lists the commands of the calculation chain, what each one reads and writes, which ones work offline, and what a public reader can and cannot redo. The stages themselves are described in [methodology](methodology.md).

## Environment

- Python standard library only, no package to install. Python 3.12 or later is required; the chain was developed and tested only with Python 3.14.6 (earlier versions are untested), and `.python-version` and the CI use Python 3.14.
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
| `project-public` | private working files; refuses to run without an accepted joint acquisition | `data/editions/<edition>/`: tables, `reconciliation.json`, `case-checks.json`, `catalog.json` | none |
| `analyze` | public edition tables | `metrics.json` | none |
| `render` | public tables, `metrics.json`, configuration | `figures/<edition>/` (SVG and CSV), `figures.json`, case pages, generated blocks of the README and docs, `data/index.json`, `data/latest.json`, `data/status.json`, `schemas/` | none |
| `verify` | every file of the working tree; the private values if `DWR_PRIVATE_ROOT` is set | nothing (report on standard output) | none |
| `publication-gate --ref <branch>` | every Git object reachable from the branch; private values of the private root | nothing (report on standard output, exit code 1 on any finding) | none (local repository read) |
| `build-site` | public files | `site/dist/` (rebuilt from scratch, never deployed) | none |
| `prepare-edition` | edition files and figures | `delta-report.json`, `SHA256SUMS.txt` | none, publishes nothing |
| `status` | `data/status.json`, calendar | nothing (standard output) | none |

Every command accepts `--edition <id>`; the default is the candidate named in `config/editions.json`. Results are printed as JSON. A failure prints `FAIL <code>: <detail>` on standard error and exits with code 2; `verify` exits with code 1 when a check fails, and a check that crashes counts as failed. `acquire-readonly` refuses a window that is not closed and any `--confirm-scope` other than the exact window. Dry run remains its default; for this edition it was executed once, with `--execute` and the exact `--confirm-scope 2026-09-15..2026-10-15`, in the private environment, never in CI.

The public stages (`analyze`, `render`, `verify`, `build-site`, `prepare-edition`, `status`) are offline and never contact the measured sites. `verify` checks that no module of the chain other than `acquire.py` imports network code.

## The private root

Private stages need `DWR_PRIVATE_ROOT` (or `--private-root`): an existing directory outside the repository root. A missing value, a missing directory or a directory inside the repository stops the stage (`private_root_missing`, `private_root_unavailable`, `private_root_inside_public_repository`). It holds the internal lock, imports, acquisitions, working files and source snapshots, and is never committed. Public stages do not need it. `verify` examines every file of the working tree, PNG figures and the built site included, with the same function as the publication gate below; when the private root is set, it also looks for the private values kept there, and without it that check is reported under `skipped`, never as passed. Test samples are synthetic.

## Publication gate

Before any publication, `python -I scripts/dwr.py publication-gate --ref public-candidate` (a private stage) reads the Git objects reachable from the branch to publish: each commit (its header without the structural `tree` and `parent` lines, and its whole message), the name of each entry of each tree, trees included, and each file as raw bytes, binary files included; no path is excluded. It requires a single root commit and admitted file types only. A PNG must consist of one IHDR of 13 bytes, IDAT chunks and one empty IEND, with nothing after it and image data of exactly the announced size. Private values are compared without regard to case, and hexadecimal identifiers are detected in both cases; a JSON file is also checked after decoding its strings, and text after decoding percent escapes. Local paths are compared with the actual local roots of the machine that runs the gate (home folder in long and short form, private workspace) after folding case and separators; generic markers of other machines' paths (Windows user folders, `/home/<name>/`, `/Users/<name>/`, synchronized folder, application data) are an additional best effort, not a guarantee. A 40-character identifier is admitted only as an action pin listed in `config/publication-gate.json` and written exactly `owner/repository@<commit>`; a test requires every pin of the workflows to be in that list. A finding names a category and a path, and a path that holds a private value or an identifier is replaced by its position in the listing. The gate guards against private material included by mistake; it is not a proof against content crafted to evade it. The history of the working branch is not publishable; only a branch that passes the gate is.

<!-- dwr:begin publication-gate -->
| Category | What the gate detects | Counterexamples tested |
|---|---|---|
| `history_not_single_root` | the branch has more than one commit, or a commit with a parent | a second commit |
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
| `identifier_40` | a 40-character hexadecimal identifier, in either case, except an action pin listed in `config/publication-gate.json` and written exactly `owner/repository@<commit>` | in a comment of a workflow template; an admitted pin value repeated without its `owner/repository@` prefix; a pin that is not in the list, on a `uses:` step; a pin that is not in the list, inside a `run:` block scalar; a `tree` line inside the commit message |
| `short_commit` | a short commit reference (`commit` followed by 7 to 12 hexadecimal characters) | in Markdown |
| `png_chunk_not_admitted` | a PNG chunk other than IHDR, IDAT and IEND | a text chunk; a palette chunk |
| `png_malformed` | a PNG whose structure differs from one IHDR of 13 bytes, IDAT chunks, one empty IEND, or whose image data differs from the announced size | data after IEND; a non-empty IEND; a second IHDR; extra image data; a truncated file; a wrong checksum; dimensions beyond 16 384 pixels |

Each of the 57 counterexamples above is planted by a mutation test in `tests/test_publication_gate.py`, which requires the gate to fail on it with that category; another test requires this table and the mutations to match one to one. A variant that is not listed is not claimed. Not covered: the pixels of a PNG, which render an SVG checked as text but are not read as text themselves, and content crafted on purpose to evade the gate.
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

UTF-8 without byte order mark, LF line endings, comma separator, header row, RFC 4180 quoting where needed, decimal point, ISO 8601 dates, booleans written `true` and `false`, and an empty cell meaning null, never zero. Column types, primary keys and the minimum of 0 for counts are in [schemas](../../schemas/).

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

The digest is computed with `sha256sum data/editions/<edition>/catalog.json` or `Get-FileHash -Algorithm SHA256 data/editions/<edition>/catalog.json`, and it also appears in `SHA256SUMS.txt`. The current edition is a candidate, not reviewed and not published: its digest can still change, and only a published edition should be cited. A revision such as `r2` has its own identifier and digest ([updates](updates.md)).
