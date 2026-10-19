# Changelog

Editions (data) and code are versioned separately. An edition identifier names its window and revision; a correction creates a new revision and never rewrites the previous one.

## Local correction candidate (2026-10-19)

- r1 remains byte-frozen at public commit `1b99aaad`; its original `SHA256SUMS.txt` SHA-256 is `afce61a2fcadb083ab6be516fc1b5dbea060c1be408432500f8fd5ebe78311fe`. r2 has a distinct manifest and a typed privacy-revision delta. Original observations, source graph and scope classes are preserved.
- Separate public availability, technical/editorial/distribution review, reference approval and scientific review. External approval receipts bind the deterministic payload manifest without changing the cited catalog. One shared chronological selector computes `latest`.
- Protect network-dependent strata; withhold protected daily margins and their coverage complements. Reproduce B1 and B2 on the actual historical function. The new combined-release gate inventories accessible history and blocks unassessed protected fine cells. No universal non-reconstruction claim.
- Add conditional 174/269 coverage, explicit 6/3 and 239/266 averages, named-agent and provider-family shares, 17/262 failed-origin context and 185/230 concentration. Definitions remain in the central metrics calculator; main 245/174/6/239 and scope 245/356/372 are unchanged.
- G01 to G10 retained. G03 now separates names, families and roles; its previous historical-role panel remains available in metrics. G08 reads actual coverage/version fields; G10 shows one observed window without treating r2 as growth. All SVG variants are checked. Compact figures use accessible horizontal regions when two-dimensional space is necessary.
- Add manual private `prepare-next`, synthetic two-epoch rehearsal, preserved mixed/unavailable states and idempotent receipts. Planning remains inactive. No new real acquisition or remote operation.
- Improve FR/EN entry pages, cases and navigation; measured resources remain copyable text by owner decision. Add the approved private security contact, concise public contribution templates and a schema-validated CFF.

## Historical preparation notes

### Candidate documentation correction (2026-10-18)

- Use `/en/ai-use-policy/` (French counterpart `/ai-usage-policy/`) as the gautierdorval.com case starting page. The replacement path steps already exist in the unchanged source snapshot graph; the entity page remains an identity reference. Regenerate the bilingual case pages, overview and documentary graph from the same edition data.
- Describe the existing manual offline CI accurately, and date the classifier-correction discussion to the historical preparation. No observation, count, historical label, source snapshot, edition window or publication status changes.

### Historical r1 preparation (now publicly accessible and frozen, not an approved reference)

- First monthly reference window: September 15 to October 14, 2026 inclusive, UTC (exclusive end 2026-10-15T00:00:00Z, 30 days).
- Built from a bounded read-only extraction of the producer's joint daily aggregate, read on 2026-10-16 (source mode `joint_acquisition`), cross-checked against the exports of the internal report with no mismatch.
- Scope reviewed path by path (`config/scope-registry.csv`, rules `scope-rules/1.0.0`; the wording of R03 was clarified after the registry build to name its content-review case, no class changed); attribution assessment `attribution-assessment/1.0.0`; small-cell policy `small-cell-policy/1.0.0`, fixed before results, then tightened once (next item).
- Small-cell policy tightened to `small-cell-policy/1.1.0` after a crossing check on the candidate: protected strata combined per day, site and population in `daily-summary.csv`, failed-verification tier protected, user-initiated fetches kept out of daily series (G01 and `main.daily` metrics). No edition-level count changed.
- Corrections after an independent read-only audit: the data table of each figure is the complete table of its wide variant (G06.csv had kept the twelve families of the compact view); every G09 variant carries the window, exclusive end, UTC, extraction and coverage, apart from the snapshot date; scope justifications keep public file names whole and carry no source-repository name or layout path; the list of private terms used by the checks moved to the private workspace, and a test sample that had reused a real account identifier is now synthetic. A publication gate (`publication-gate --ref <branch>`) checks the commits, entry names and files of the branch to publish, binary files included, with one mutation test per listed counterexample (see `docs/en/reproduction.md` for what is and is not covered); `verify` examines every file of the working tree with the same functions.
- Small-cell policy `small-cell-policy/1.1.0` validated by the owner on 2026-10-17, amendment and accepted residual cases included. Publishing named software-agent families (for example `GPTBot`) as actor names at edition level was approved by the owner on the same day; day-level outputs never carry an actor name.
- `catalog.json` now declares the small-cell policy actually applied (`small-cell-policy/1.1.0`; it had kept `1.0.0`). The versions of the scope rules, attribution rules and small-cell policy are read from their configuration files, and `verify` checks that the catalog matches them.
- Publication history: `config/publication-gate.json` names the published root, and the gate requires the history of the branch to publish to run linearly from it (a single commit before the first publication, when the file is absent or names no root; a file that cannot be read stops the gate). Each later edition is one new commit of the reviewed tree on top of the published history, so published commits are never rewritten. The gate checks the root, not the published head: continuity with the previous edition rests on checking the remote head before a push without force.
- Historical `published_at` remains null in the frozen catalog. Public availability is recorded separately in the edition configuration. No reference release has been approved.

### Licences

- Decided by the owner on 2026-10-17: MIT for the code, CC BY 4.0 for the documentation and the data. Full texts in `LICENSES/`, mapping in `NOTICE.md`; `CITATION.cff` and `pyproject.toml` declare them. A test checks that every tracked file maps to exactly one row of the `NOTICE.md` table and that the CC BY 4.0 legal code is the official text.
- `CITATION.cff` no longer carries `date-released: null`, which CFF 1.2.0 rejects: the field is omitted until a publication date exists. The file was validated with cffconvert 2.0.0 against schema 1.2.0 on 2026-10-17, and a test pins its SHA-256: any later change must be validated again before the digest is updated.

### Code 0.1.0

- Standard-library calculation chain: import, read-only acquisition (dry run by default), normalization, qualification, public projection, metrics, figures (SVG, two languages, two layouts), case pages, static presentation, offline verification, candidate preparation and status.
- Inactive workflow templates for weekly preparation and monthly editions; offline CI with read-only permissions.
- The temporary repositories of the publication gate tests are deleted after each test, read-only Git objects included (on Windows they were left in the temporary folder). Only a permission refusal on a file or folder that is not a symbolic link is retried; any other failure is raised.
