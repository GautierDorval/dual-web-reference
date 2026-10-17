# Dual Web Reference

[Français](README.fr.md)

This repository documents a layer of **governance files** published on three websites of one ecosystem (gautierdorval.com, pagup.com, better-robots.com), explains the role of these files, and describes the HTTP accesses recorded to them. Its subject is documentary only.

The Dual Web, in the sense of its [canonical definition](https://gautierdorval.com/en/definitions/ssa-e-a2-dual-web/), presents a documentary layer that complements the pages of a site. Its files make explicit, among other things, identity, context, sources, relations and the limits of interpretation. They are published as accessible resources, linked to the site or to other documents. The layer is neither hidden nor reserved for machines, and a published policy declares a frame without proving that any system applies it. See [the model](docs/en/model.md).

This first edition describes the **existence and distribution of recorded accesses**, including beyond `llms.txt`. It does not measure better answers, adoption, search visibility, indexing, compliance or any causal effect of linking.

## Current edition: dates and status

<!-- dwr:begin dates -->
| Date or state | Value |
|---|---|
| Edition | `2026-09-15_2026-10-15-r1` |
| Status | candidate, not reviewed, not published |
| Measured period | September 15 to October 14, 2026 inclusive, UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-16` |
| published_at | `null` (not published) |
| revised_at | `null` |
| latest_available_data_date | `2026-10-14` |
| next_review_target | weekly review `2026-10-19T13:17:00Z`, not guaranteed |
| Updates | periodic update planned; manual preparation (automation not activated) |
<!-- dwr:end dates -->

## Main result, with its qualification

<!-- dwr:begin headline -->
In the main documentary population, the collector recorded **245 GET 200 requests** from AI roles whose provider origin was recorded as verified by an official IP-range match, on **174 distinct site-path pairs**.

Of these requests, **6** went to `/llms.txt` and **239** to other governance files, that is **97.6%** of the same selection (same period, sites, scope, method, status and identification level). This share describes how recorded requests are distributed; it is not an adoption rate.

By site: gautierdorval.com 62, pagup.com 61, better-robots.com 122. By recorded actor role: collection for training 200, AI search 30, user-initiated fetch 15; without user-initiated fetches, 230 requests remain (a sensitivity reading, not evidence of independence).

Qualification: provider-origin attribution does not use the Cloudflare predicate under review; the levels that do use it are kept apart. The initial internal report counted 372 such requests on a wider scope that included method, protocol and service-description files; the difference is itemized in [the scope delta](docs/en/scope.md).
<!-- dwr:end headline -->

## Two figures

<!-- dwr:begin figures-main -->
<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r1/G02.en.compact.svg"><img src="figures/2026-09-15_2026-10-15-r1/G02.en.svg" alt="Stacked horizontal bars, all sites and per site, splitting provider-origin AI-role GET 200 requests between /llms.txt and the other governance files; counts, totals and shares are written under each bar." width="960"></picture>

Data table: [G02.csv](figures/2026-09-15_2026-10-15-r1/G02.csv)

<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r1/G05.en.compact.svg"><img src="figures/2026-09-15_2026-10-15-r1/G05.en.svg" alt="Three ranked horizontal bar lists, one per site, of the ten main-population files with most provider-origin AI GET 200 requests." width="960"></picture>

Data table: [G05.csv](figures/2026-09-15_2026-10-15-r1/G05.csv)
<!-- dwr:end figures-main -->

All figures (G01 to G10), with their data tables and text alternatives, are listed in [figures.json](data/editions/2026-09-15_2026-10-15-r1/figures.json) and in the [figures folder](figures/2026-09-15_2026-10-15-r1/).

## Three cases

<!-- dwr:begin cases -->
| Site | Angle | Starting page | Resources | Provider-origin AI GET 200 on these resources |
|---|---|---|---:|---:|
| [gautierdorval.com](cases/gautierdorval.com/README.md) | Identity of a person, and the distinction between definitions, claims, sources, limits and ordinary site content. | `/en/entity/` | 9 | 10 |
| [pagup.com](cases/pagup.com/README.md) | Context of an organization, scope of its offer, references and documentary limits. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](cases/better-robots.com/README.md) | Context of a product, declared capabilities, limits, and the difference between publishing a rule and how a robot actually behaves. | `/governance/ai-usage-policy` | 9 | 15 |

The three sites belong to one author's ecosystem: three applications of one approach, not three independent replications. robots.txt is excluded from the last column.
<!-- dwr:end cases -->

## Files, data, method and reproduction

- Edition catalog with digests and dates: [catalog.json](data/editions/2026-09-15_2026-10-15-r1/catalog.json); named results: [metrics.json](data/editions/2026-09-15_2026-10-15-r1/metrics.json).
- Resources and their scope: [resources.csv](data/editions/2026-09-15_2026-10-15-r1/resources.csv), built from the versioned [scope registry](config/scope-registry.csv).
- Documentary relations found in the source snapshots: [links.csv](data/editions/2026-09-15_2026-10-15-r1/links.csv).
- Accesses: [consultations.csv](data/editions/2026-09-15_2026-10-15-r1/consultations.csv), [resource-summary.csv](data/editions/2026-09-15_2026-10-15-r1/resource-summary.csv), [daily-summary.csv](data/editions/2026-09-15_2026-10-15-r1/daily-summary.csv), [actor-summary.csv](data/editions/2026-09-15_2026-10-15-r1/actor-summary.csv); coverage and exclusions: [coverage.csv](data/editions/2026-09-15_2026-10-15-r1/coverage.csv), [exclusions.csv](data/editions/2026-09-15_2026-10-15-r1/exclusions.csv); table schemas in [schemas](schemas/).
- Method: [methodology](docs/en/methodology.md), [scope](docs/en/scope.md), [attribution](docs/en/attribution.md), [quality and coverage](docs/en/quality-and-coverage.md), [file roles](docs/en/file-roles.md), [discovery and linking](docs/en/discovery-and-linking.md), [privacy](docs/en/privacy.md), [glossary](docs/en/glossary.md).
- Reproduce every published number offline: [reproduction](docs/en/reproduction.md). The collection, the producer classification and the extraction rely on private sources and cannot be re-run from the public files.
- Static presentation (French and English), built locally with `python -I scripts/dwr.py build-site`.

## Essential limits

- **Attribution.** The main result keeps only requests whose provider origin was recorded from an official IP-range match. Two other recorded levels depend on a Cloudflare predicate that also accepts an empty category; they are labelled “recorded classification, reliability under review” and kept apart. Reproducing the defect does not show that it occurred in production. See [attribution](docs/en/attribution.md).
- **Who triggered a request is unknown.** A provider-origin request may have been triggered by anyone, including the site operator. Nothing here is independent external adoption.
- **Discovery routes.** `llms.txt` is one possible entry point, not a mandatory protocol. A URL can be known in other ways than an internal link. The relation graph shows what a reader can follow in a snapshot, not paths followed by robots. See [discovery and linking](docs/en/discovery-and-linking.md) and the [comparison with llms.txt studies](docs/en/llms-txt-studies.md).
- **Coverage.** All archived daily reports of the window are partial (declared). Rows on every day do not prove complete coverage. See [quality and coverage](docs/en/quality-and-coverage.md).
- **Data of this edition.** The counts come from one bounded, read-only extraction of the collector's daily aggregate table, cross-checked against the exports of the initial internal report: the two agree everywhere, but they come from the same producer chain, so this is consistency, not independent validation. See [limits](docs/en/limits.md).

## Updates, history and citation

The project is an operation followed over time, not a timeless report. Monthly reference editions use consecutive windows anchored on the 15th (UTC, exclusive end); the next one covers October 15 to November 14, 2026 inclusive (31 days). A weekly review is planned. **Periodic update planned; manual preparation**: no automation is active. Corrections create a new revision of an edition with its reason and delta. See [updates](docs/en/updates.md), [CHANGELOG.md](CHANGELOG.md), [data/index.json](data/index.json) and [data/status.json](data/status.json).

To cite an edition, give its identifier and the SHA-256 of its `catalog.json`; see [CITATION.cff](CITATION.cff). Licences: MIT for the code, CC BY 4.0 for the documentation and the data, quoted excerpts and third-party names excluded; see [NOTICE.md](NOTICE.md).
