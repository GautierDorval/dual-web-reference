# Dual Web Reference

[Français](README.fr.md)

This repository studies governance files, their documentary relations and recorded HTTP accesses.

<!-- dwr:begin edition-state -->
Edition r2: publicly accessible; reference not approved; no independent scientific review documented. r1 remains accessible as a byte-frozen, unapproved historical edition.
<!-- dwr:end edition-state -->

<!-- dwr:begin headline -->
**174 documentary URLs reached · 245 accesses · 3 sites in one ecosystem.** September 15 to October 14, 2026 inclusive, UTC.

[Explore the Gautier Dorval case](cases/gautierdorval.com/README.md): start at the AI policy, distinguish identity, sources and limits, then examine the snapshot relations.

Main selection: GET 200 requests from AI roles, with provider origin recorded as verified against official IP ranges. **Declared partial coverage.** A request does not prove understanding, adoption or a causal effect.

**6** accesses went to `llms.txt` and **239** to other files. The 97.6% share outside `llms.txt` describes this selection; it does not measure preference. Of 269 main resources with rows across all actors, methods and statuses, 174 were reached in the main selection. This denominator is not a complete historical documentary-web inventory.

Per resource with rows: 6/3 = 2 accesses for `llms.txt`, versus 239/266 = 0.90 elsewhere. Availability and exposure are not controlled.

GPTBot: 200; OAI-SearchBot: 14; PerplexityBot: 16; ChatGPT-User: 15. The OpenAI family accounts for 229/245 accesses; this is not market share across all agents.

Excluding user-initiated fetches: 230 automated accesses on 12 days; the three busiest days account for 185, or 80.4%. 133 of the 174 pairs received requests on only one day.

Explicit exclusion: 17 requests under those four names have **failed origin verification according to the producer**, among 262 requests in the selected provider-verified and failed-verification tiers only. Spoofing is not demonstrated. On PAGUP: no GET 200 of `llms.txt` in this selection and window; an earlier access remains possible.

Separate network-claimed stratum on the main documentary population: 412 AI-role GET 200, including 361 recorded as Meta-ExternalAgent. Its origin predicate remains under review; these requests are never added to the provider-origin selection.
<!-- dwr:end headline -->

## Read a documentary snapshot

The Gautier Dorval case starts at `/en/ai-use-policy/` (French: `/ai-usage-policy/`). Its declared machine entry point is `/.well-known/ai-governance.json`. The case sheet dates its snapshot; these documentary links are not an observed session. Paths remain copyable to avoid generating traffic from this presentation.

## Two complementary views

<!-- dwr:begin figures-main -->
<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r2/G02.en.compact.svg"><img src="figures/2026-09-15_2026-10-15-r2/G02.en.svg" alt="Stacked horizontal bars, all sites and per site, splitting provider-origin AI-role GET 200 requests between /llms.txt and the other governance files; counts, totals and shares are written under each bar." width="960"></picture>

Data table: [G02.csv](figures/2026-09-15_2026-10-15-r2/G02.csv)

<picture><source media="(max-width: 640px)" srcset="figures/2026-09-15_2026-10-15-r2/G05.en.compact.svg"><img src="figures/2026-09-15_2026-10-15-r2/G05.en.svg" alt="Three ranked horizontal bar lists, one per site, of the ten main-population files with most provider-origin AI GET 200 requests." width="960"></picture>

Data table: [G05.csv](figures/2026-09-15_2026-10-15-r2/G05.csv)
<!-- dwr:end figures-main -->

## Three cases, one ecosystem

<!-- dwr:begin cases -->
| Site | Angle | Starting page | Resources | Provider-origin AI GET 200 on these resources |
|---|---|---|---:|---:|
| [gautierdorval.com](cases/gautierdorval.com/README.md) | Identity of a person, and the distinction between definitions, claims, sources, limits and ordinary site content. | `/en/ai-use-policy/` | 9 | 10 |
| [pagup.com](cases/pagup.com/README.md) | Context of an organization, scope of its offer, references and documentary limits. | `/ai-usage-policy/` | 9 | 13 |
| [better-robots.com](cases/better-robots.com/README.md) | Context of a product, declared capabilities, limits, and the difference between publishing a rule and how a robot actually behaves. | `/governance/ai-usage-policy` | 9 | 15 |

The three sites belong to one author's ecosystem: three applications of one approach, not three independent replications. robots.txt is excluded from the last column.
<!-- dwr:end cases -->

## Method and data

1. Define the files and their functions in a dated registry.
2. Preserve recorded classifications, methods and statuses.
3. Apply the main scope and combined-release controls.
4. Recompute tables, metrics and figures from the same observations.

[Understand the files](docs/en/file-roles.md) · [Method](docs/en/methodology.md) · [Attribution](docs/en/attribution.md) · [Privacy](docs/en/privacy.md) · [Reproduction](docs/en/reproduction.md).

[r2 catalog](data/editions/2026-09-15_2026-10-15-r2/catalog.json) · [Metrics](data/editions/2026-09-15_2026-10-15-r2/metrics.json) · [Resources](data/editions/2026-09-15_2026-10-15-r2/resources.csv) · [Accesses](data/editions/2026-09-15_2026-10-15-r2/consultations.csv) · [Relations](data/editions/2026-09-15_2026-10-15-r2/links.csv).

## Editorial presentations in the ecosystem

- [Gautier Dorval: scope and interpretation of the observation](https://gautierdorval.com/en/blog/field-observations/dual-web-reference/).
- [Pagup: an operational reading of the evidence](https://pagup.com/en/proof/dual-web-reference-study/).

These presentations connect DWR with the Dual Web concept and the ecosystem. The repository remains the canonical data source. Their publication is neither reference approval nor independent scientific review.

## Essential limits

Three sites in one ecosystem are not three independent replications. Coverage is partial, discovery paths are not established, and provider origin remains a producer classification. A GET 200 does not prove semantic reading, adoption, better answers or SEO effects. Private collection evidence cannot be rerun from this repository. [Detailed limits](docs/en/limits.md).

## Dates, editions and maintenance

<!-- dwr:begin dates -->
| Date or state | Value |
|---|---|
| Edition | `2026-09-15_2026-10-15-r2` |
| Status | publicly accessible; reference not approved; no independent scientific review documented |
| Availability | `publicly_accessible` |
| Reference approval | `not_approved` |
| Measured period | September 15 to October 14, 2026 inclusive, UTC |
| period_start_inclusive | `2026-09-15` |
| period_end_exclusive | `2026-10-15` |
| last_included_date | `2026-10-14` |
| extracted_at | `2026-10-16T22:57:16.784712Z / 2026-10-16T22:58:54.949414Z` |
| source_snapshot_at | `2026-10-16T12:30:48Z` |
| graph_snapshot_at | better-robots.com `2026-10-06`, gautierdorval.com `2026-10-14`, pagup.com `2026-10-06` |
| generated_at | `2026-10-19` |
| approved_release_at | `null` |
| revised_at | `2026-10-19` |
| latest_available_data_date | `2026-10-14` |
| Updates | periodic update planned; manual preparation (automation not activated) |
<!-- dwr:end dates -->

[States and review](docs/en/updates.md) · [CHANGELOG](CHANGELOG.md) · [CITATION.cff](CITATION.cff) · [NOTICE](NOTICE.md) · [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md).

Local preview, without publication or an active schedule:

```powershell
python -I scripts/dwr.py analyze
python -I scripts/dwr.py render
python -I scripts/dwr.py build-site
python -m http.server 8000 --directory site/dist --bind localhost
```
