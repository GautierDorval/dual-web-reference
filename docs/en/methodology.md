# Methodology

[Français](../fr/methode.md) · [Repository home](../../README.md)

This page describes how the numbers of an edition are produced, exactly as implemented in `analysis/dwr/`. The method is descriptive: it counts HTTP requests recorded to documentary files of three sites. It does not measure answers produced by any system, adoption, indexing, compliance or any effect of linking. See [model](model.md) for what the documentary layer is and [limits](limits.md) for what the results cannot support.

## A four-stage chain

| Stage | Commands | Runs on | Output |
|---|---|---|---|
| 1. Private acquisition | `import-existing`, `acquire-readonly` | private workspace | import receipt and typed export marginals; raw query results and acquisition log of the joint extraction |
| 2. Normalization and qualification | `normalize`, `qualify` | private workspace | private working files |
| 3. Minimized public projection | `project-public` | private inputs, public outputs | tables, `reconciliation.json`, `case-checks.json`, `catalog.json` under `data/editions/<edition>/` |
| 4. Presentation | `analyze`, `render`, `build-site` | public files only, offline | `metrics.json`, figures, generated blocks, static site |

Every published indicator is computed once, by `analyze` (`analysis/dwr/metrics.py`), from the public tables only. Figures, case pages and generated blocks read `metrics.json` and the same public tables. Inputs, outputs and network use of each command are listed in [reproduction](reproduction.md).

For this edition, stage 1 ran in two steps. First, `import-existing` checked the local export package of the internal report against its manifest (size and SHA-256 of every file, archive limits, inner checksums) and loaded its tables with closed column lists; a matching digest establishes the binary identity of the package, not the accuracy of the recorded events. Then, with the owner's approval, `acquire-readonly` was executed once in the private environment, with `--execute` and the exact window confirmation `--confirm-scope 2026-09-15..2026-10-15`. It ran only reviewed queries, each a single `SELECT` statement (`analysis/dwr/acquire.py`): the schema of the tables read, per-day checksums before and after, one query per UTC day of the window on the producer's daily aggregate table, the current artifact registry, the classifier versions and the producer deployment history. No row was written, the database was unchanged, and the checksums were identical before and after the read (interval in `extracted_at`).

## Populations

- **Collector perimeter**: every path recorded by the private collector on the three sites, all methods, statuses and actors (all rows of `daily-summary.csv`, whose populations are `main_documentary`, `other_documentary`, `robots_control` and `undeclared_bucket`; metric `collector.requests`).
- **Initial report scope** (`historical_report_scope`): every path except `/robots.txt`, `/.well-known/__undeclared__` and the producer category `well-known-probe`. It repeats the scope of the initial internal report and is used for reconciliation only.
- **Main documentary population**: site-path pairs of scope classes `core_governance` and `discovery_index` (see [scope](scope.md)).
- **Extended documentary layer**: the main population plus `supporting_documentation`. It is a secondary reading, never the headline.

The main result stratum is: main documentary population, `GET` with status `200`, stored tier `provider_origin_verified_actor`, roles `ai_training`, `ai_search` and `user_initiated_fetch`.

## Units

Distinct counts are counts of site-path pairs: one URL, identified by a `resource_id` such as `gd:/llms.txt`. A pair is not a consumer, a visitor or a session. Mirrors, language versions and formats are separate pairs. Distinct paths per actor group (`distinct_paths_in_group` in `actor-summary.csv`) are never added together, because two actors can request the same URL.

## Method and status

Only `GET` with status `200` counts as a request answered with a document body. `HEAD`, `304`, `301`, `404`, `405` and `5xx` stay in separate cells and are never added to `GET 200`. Under [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) (consulted 2026-10-16), a `HEAD` response and a `304` response carry no content (sections 9.3.2 and 15.4.5), and `405` means the method is not supported by the target resource (section 15.5.6). `GET 200` is the status recorded by the collector; the bytes served are not re-verified.

## Main indicators

Each entry of `metrics.json` carries `metric_id`, `value`, `unit`, `status`, `numerator`, `denominator`, `filters` and `source_files`, plus `label_en` and `label_fr`, and also `reason` and `attribution_quality` where they apply. `status` is `calculated`, or `not_calculable` when a denominator is zero.

| Metric | Definition | Unit |
|---|---|---|
| `main.get200` | sum, over the pairs of the main population, of the `consultations.csv` cells with `GET`, `200`, stored tier `provider_origin_verified_actor` and one of the roles `ai_training`, `ai_search`, `user_initiated_fetch` | requests |
| `main.site_path_pairs` | pairs of the main population whose sum is at least 1 | site-path pairs |
| `main.llms_get200` | the same sum on `/llms.txt` only | requests |
| `main.other_get200`, `main.other_site_path_pairs` | the same sum and count on paths other than `/llms.txt` | requests, site-path pairs |
| `main.other_share` | `main.other_get200` divided by `main.get200` | ratio, 6 decimals |
| `main.site.<site>.*` | the same quantities for one site | as above |
| `main.role.<role>.get200`, `main.role.<role>.site.<site>.get200` | the same sum for one role, on all sites or on one site | requests |
| `main.sensitivity.without_user_fetch.get200`, `main.sensitivity.without_user_fetch.site_path_pairs` | the same sum and count without the role `user_initiated_fetch` | requests, site-path pairs |
| `main.recurrence.pairs_with_<n>_days`, `main.recurrence.max_days` | number of pairs of the main population, among those counted in `main.site_path_pairs`, whose `provider_origin_ai_get200_days` in `resource-summary.csv` falls in the bucket `<n>` (`1`, `2_to_3`, `4_to_7`, `8_or_more`); and the largest value | site-path pairs, days |
| `main.daily.sum_check`, `main.daily.days_with_requests`, `main.daily.site.<site>.days_with_requests` | from the `main_documentary` rows of `daily-summary.csv`, with the same filters restricted to the automated roles `ai_training` and `ai_search` (the small-cell policy keeps user-initiated fetches out of daily series): the sum of the daily series, which equals `main.get200` minus `main.role.user_initiated_fetch.get200`, and the UTC days with at least one such request, on any site or on one site | requests, days |
| `main_population.tier.<tier>.get200` | `GET 200` of the main population per stored tier, all roles | requests |
| `extended.get200`, `extended.site_path_pairs` | the same sum and count on the extended layer | requests, site-path pairs |
| `main.scope_delta.provider_ai_get200_excluded` | provider-origin AI `GET 200` of the initial report scope minus `main.get200` | requests |
| `historical.*` | the same quantities on the initial report scope, per role, and `GET 200` per stored tier, from `consultations.csv` | requests, pairs, ratio |
| `coverage.*` | day counts and archived sums from `coverage.csv`, including the days whose joint total equals the archived aggregate count | days, requests |
| `collector.requests` | sum of `request_count` over all rows of `daily-summary.csv` | requests |

```text
other_share = other_get200 / total_get200
```

Numerator and denominator share the window, sites, scope, method, status and identification level. If the denominator is zero, the value is null with status `not_calculable` and reason `denominator_zero_or_unavailable`, never 0%. The share describes how recorded requests are distributed in one selection; it is not an adoption rate or a measure of efficacy.

The split by role, the sensitivity without user-initiated fetches, the recurrence and the daily series are exact sums of cells of the joint aggregate. Nothing is estimated, and no daily or per-role value is spread from monthly totals. The reading without user-initiated fetches is a sensitivity analysis, not evidence of independence. Recurrence counts distinct UTC days per pair; it says nothing about sessions, order or the number of clients.

## The joint_acquisition mode

This edition has `source_mode = joint_acquisition`. It is built from the producer's joint daily aggregate: one row per UTC day, site, path, method, status, actor family, actor name, role and stored tier. `normalize` loads the rows of each day of the window and stops on any unknown method, role or tier, any status outside 100 to 599, any count that is not a non-negative integer, any duplicate key, or a total that differs from the per-day checksums of the extraction (`analysis/dwr/joint.py`).

The exports of the internal report, read earlier the same day (`exports_extracted_at` in `catalog.json`), are kept for reconciliation. `normalize` compares the joint rows with them and stops on any difference (`joint_acquisition_inconsistent_with_exports`): per-path monthly marginals, per-actor-group marginals of the initial report scope, daily totals per site, and method and status per site. The joint aggregate reproduces them exactly; each check and its result are in `reconciliation.json` (`joint_aggregate_vs_exports`). This is consistency between two readings of the same producer table, not an independent validation.

Before the joint acquisition, the split of each path by method and status had been deduced from the exports by zero mass: on the initial report scope, every request of each site fell in `GET 200`, `HEAD 200`, `GET 304` or `POST 405`, and the per-path columns added up, so the non-negativity of the counts fixed the split of every path. The joint aggregate confirms this deduction on every combination of path, method and status (check `deduced_method_status_split_confirmed`, and `method_status_split` in `catalog.json`). The deduction is now a reconciliation fact only: published cells come from the joint rows.

## Exact cells at the allowed grains

`project-public` refuses to run without an accepted joint acquisition (`joint_aggregate_required`). It sums the joint rows only to the grains allowed by the [small-cell policy](privacy.md) (`analysis/dwr/project.py`):

- `consultations.csv`: edition grain, site × path × method × status × actor family × actor name × role × stored tier;
- `daily-summary.csv`: day × site × population × role × stored tier × method × status, never path or actor name; protected strata are combined into one row per day, site and population (`protected_strata`, method and status `ANY`, see [privacy](privacy.md)); columns `edition_id`, `date_utc`, `site_id`, `population`, `actor_role`, `stored_identity_tier`, `http_method`, `http_status`, `request_count`, `coverage_status` and `archive_report_status`; populations `main_documentary`, `other_documentary` (every other scope class except the two below), `robots_control` (`/robots.txt`) and `undeclared_bucket`;
- `actor-summary.csv`: population × site × actor family × actor name × role × stored tier, with `requests`, `get200`, `distinct_paths_in_group` and `days_with_rows`, for every population;
- `resource-summary.csv`: one row per pair with rows in the window, including the number of UTC days with at least one provider-origin AI `GET 200` (`provider_origin_ai_get200_days`);
- `daily-family-summary.csv`: day × documentary family × role, for the main population, the provider-origin tier, `GET 200` and the roles `ai_training` and `ai_search` only; the small-cell policy leaves user-initiated fetches out.

Every cell is an exact sum of joint rows (`cell_derivation = joint_exact`); nothing is allocated in proportion to anything. A combination absent from a table had no recorded request in the producer table; it is not a measured absence on the web. Explicit zeros appear only in `daily-family-summary.csv` (`observation_status = observed_zero`). The heat map G06 is drawn from that table, never from marginals.

## Reconciliation

<!-- dwr:begin reconciliation -->
| Historical figure | Expected | Recomputed | Status |
|---|---:|---:|---|
| `all_collector_requests` | 24,815 | 24,815 | match |
| `governance_get200` | 14,126 | 14,126 | match |
| `governance_requests` | 19,587 | 19,587 | match |
| `governance_site_path_pairs` | 386 | 386 | match |
| `heterogeneous_provider_plus_network_ai_get200` | 933 | 933 | match |
| `stored_cloudflare_unattributed_get200` | 12,476 | 12,476 | match |
| `stored_cloudflare_unattributed_percent_of_get200` | 88.32 | 88.32 | match |
| `stored_network_claimed_ai_get200` | 561 | 561 | match |
| `stored_provider_origin_ai_get200` | 372 | 372 | match |
| `stored_provider_origin_ai_llms_get200` | 6 | 6 | match |
| `stored_provider_origin_ai_other_get200` | 366 | 366 | match |
| `stored_provider_origin_ai_other_percent` | 98.39 | 98.39 | match |
| `stored_provider_origin_ai_other_site_path_pairs` | 257 | 257 | match |
| `stored_provider_origin_ai_search_get200` | 44 | 44 | match |
| `stored_provider_origin_ai_site_path_pairs` | 259 | 259 | match |
| `stored_provider_origin_ai_training_get200` | 302 | 302 | match |
| `stored_provider_origin_excluding_user_fetch_get200` | 346 | 346 | match |
| `stored_provider_origin_user_fetch_get200` | 26 | 26 | match |

Same exports, same filters, this repository's own code. This is a reproduction of arithmetic, not an independent audit: the exports and the initial report come from the same producer chain. The combined figure of 933 mixes two identification levels and is never presented as a homogeneous total.
<!-- dwr:end reconciliation -->

`import-existing` recomputes the figures of the initial internal report with this repository's own code (`analysis/dwr/reconcile.py`) and compares them with the reference values; any difference stops the import. It also compares daily export totals with the archived aggregate counts, and `project-public` does the same for the daily totals of the joint aggregate (`export_matches_archive` and `joint_matches_archive` in `coverage.csv`). All these comparisons use inputs from the same producer chain, so agreement shows that the arithmetic is reproduced, not that the collection is right. Reconciliation applies to the initial report scope only: the main result uses the reviewed scope and is not forced to equal any historical figure. The difference is itemized in [scope](scope.md).

## What was not done

- No new collection: the edition uses the requests already recorded by the private collector.
- No live fetch of the three sites: relations come from source snapshots, and no URL found in them is fetched.
- No write to the producer database: the single bounded extraction ran read-only `SELECT` queries, wrote no row and left the database unchanged.
- No stored label was rewritten (see [attribution](attribution.md)).
