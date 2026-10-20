"""analyze: every published number, computed once, from the public files only.

Each metric names its numerator, denominator, filters, unit and status. A share
whose denominator is zero or unavailable is `not_calculable`, never 0 %.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .common import SITE_IDS, read_csv, load_json

PROVIDER = "provider_origin_verified_actor"
UNATTRIBUTED = "cloudflare_verified_unattributed"
NETWORK = "network_verified_claimed_actor"
AI_ROLES = ("ai_training", "ai_search", "user_initiated_fetch")
MAIN_FILTER = ("site-path pairs of the main documentary population (scope classes core_governance and "
               "discovery_index); GET with status 200; stored tier provider_origin_verified_actor; roles "
               "ai_training, ai_search, user_initiated_fetch")
QUALITY = "provider_origin_registry_match"
AUTOMATED_ROLES = ("ai_training", "ai_search")
DAILY_FILTER = MAIN_FILTER.replace("roles ai_training, ai_search, user_initiated_fetch",
                                   "automated roles ai_training and ai_search only (the small-cell policy keeps "
                                   "user-initiated fetches out of daily series)")


def _bool(value: str) -> bool:
    return value == "true"


def metric(metric_id, value, unit, *, numerator=None, denominator=None, filters="", status="calculated",
           sources=(), reason=None, label_en="", label_fr="", quality=None):
    entry = {"metric_id": metric_id, "value": value, "unit": unit, "status": status, "numerator": numerator,
             "denominator": denominator, "filters": filters, "source_files": list(sources),
             "label_en": label_en, "label_fr": label_fr}
    if reason:
        entry["reason"] = reason
    if quality:
        entry["attribution_quality"] = quality
    return entry


def share(metric_id, numerator, denominator, **kwargs):
    if numerator is None or denominator in (None, 0):
        return metric(metric_id, None, "ratio", numerator=numerator, denominator=denominator,
                      status="not_calculable", reason=("source_unavailable" if numerator is None or denominator is None else "denominator_zero"), **kwargs)
    return metric(metric_id, round(numerator / denominator, 6), "ratio", numerator=numerator,
                  denominator=denominator, **kwargs)


def is_get200(row) -> bool:
    return row["http_method"] == "GET" and row["http_status"] == "200"


def compute(edition_dir: Path) -> dict:
    catalog = load_json(edition_dir / "catalog.json")
    modern = catalog.get("metrics_version") == "dwr-metrics/2.0.0"
    resources = {row["resource_id"]: row for row in read_csv(edition_dir / "resources.csv")}
    consultations = read_csv(edition_dir / "consultations.csv")
    summary = {row["resource_id"]: row for row in read_csv(edition_dir / "resource-summary.csv")}
    daily = read_csv(edition_dir / "daily-summary.csv")
    coverage = read_csv(edition_dir / "coverage.csv")
    exclusions = read_csv(edition_dir / "exclusions.csv")
    files_c = ("consultations.csv", "resources.csv")
    out = []

    provider = defaultdict(int)
    role_of = defaultdict(lambda: defaultdict(int))
    tier_main = defaultdict(int)
    tier_historical = defaultdict(int)
    network_ai_historical = 0
    get200_all = defaultdict(int)
    for row in consultations:
        resource = resources[row["resource_id"]]
        n = int(row["request_count"])
        historical = resource["scope_class"] not in ("control_resource", "undeclared_bucket")
        if not is_get200(row):
            continue
        get200_all[row["resource_id"]] += n
        if _bool(resource["main_population"]):
            tier_main[row["stored_identity_tier"]] += n
        if historical:
            tier_historical[row["stored_identity_tier"]] += n
            if row["stored_identity_tier"] == NETWORK and row["actor_role"] in AI_ROLES:
                network_ai_historical += n
        if row["stored_identity_tier"] == PROVIDER and row["actor_role"] in AI_ROLES:
            provider[row["resource_id"]] += n
            role_of[row["resource_id"]][row["actor_role"]] += n
    main_ids = [rid for rid, row in resources.items() if _bool(row["main_population"]) and provider.get(rid)]

    def subset(ids, site=None, llms=None):
        chosen = [rid for rid in ids if (site is None or resources[rid]["site_id"] == site)
                  and (llms is None or _bool(resources[rid]["llms_txt"]) == llms)]
        return sum(provider[rid] for rid in chosen), sum(1 for rid in chosen if provider[rid] > 0)

    total, pairs = subset(main_ids)
    llms, _ = subset(main_ids, llms=True)
    other, other_pairs = subset(main_ids, llms=False)
    out += [
        metric("main.get200", total, "requests", filters=MAIN_FILTER, sources=files_c, quality=QUALITY,
               label_en="GET 200 requests, main documentary population, provider-origin AI roles",
               label_fr="Requêtes GET 200, population documentaire principale, rôles IA à origine fournisseur"),
        metric("main.site_path_pairs", pairs, "site-path pairs", filters=MAIN_FILTER + "; pairs with at least one request",
               sources=files_c, quality=QUALITY, label_en="Distinct site-path pairs receiving these requests",
               label_fr="Couples site-chemin distincts recevant ces requêtes"),
        metric("main.llms_get200", llms, "requests", filters=MAIN_FILTER + "; path /llms.txt", sources=files_c,
               quality=QUALITY, label_en="Of which /llms.txt", label_fr="Dont /llms.txt"),
        metric("main.other_get200", other, "requests", filters=MAIN_FILTER + "; path other than /llms.txt",
               sources=files_c, quality=QUALITY, label_en="Of which other resources", label_fr="Dont autres ressources"),
        metric("main.other_site_path_pairs", other_pairs, "site-path pairs", filters=MAIN_FILTER + "; other than /llms.txt",
               sources=files_c, quality=QUALITY, label_en="Site-path pairs other than /llms.txt",
               label_fr="Couples site-chemin autres que /llms.txt"),
        share("main.other_share", other, total, filters=MAIN_FILTER, sources=files_c, quality=QUALITY,
              label_en="Share of these requests going to resources other than /llms.txt",
              label_fr="Part de ces requêtes vers des ressources autres que /llms.txt"),
    ]
    for site in SITE_IDS:
        site_total, site_pairs = subset(main_ids, site=site)
        site_llms, _ = subset(main_ids, site=site, llms=True)
        out += [
            metric(f"main.site.{site}.get200", site_total, "requests", filters=MAIN_FILTER + f"; site {site}",
                   sources=files_c, quality=QUALITY, label_en=site, label_fr=site),
            metric(f"main.site.{site}.site_path_pairs", site_pairs, "site-path pairs", filters=MAIN_FILTER + f"; site {site}",
                   sources=files_c, quality=QUALITY, label_en=f"{site} pairs", label_fr=f"Couples {site}"),
            metric(f"main.site.{site}.llms_get200", site_llms, "requests", filters=MAIN_FILTER + f"; site {site}; /llms.txt",
                   sources=files_c, quality=QUALITY, label_en=f"{site} /llms.txt", label_fr=f"{site} /llms.txt"),
            share(f"main.site.{site}.other_share", site_total - site_llms, site_total,
                  filters=MAIN_FILTER + f"; site {site}", sources=files_c, quality=QUALITY,
                  label_en=f"{site} share other than /llms.txt", label_fr=f"{site}, part hors /llms.txt"),
        ]
    for role in AI_ROLES:
        value = sum(role_of[rid][role] for rid in main_ids)
        out.append(metric(f"main.role.{role}.get200", value, "requests", filters=MAIN_FILTER + f"; role {role}",
                          sources=files_c, quality=QUALITY, label_en=f"Role {role}", label_fr=f"Rôle {role}"))
        for site in SITE_IDS:
            out.append(metric(f"main.role.{role}.site.{site}.get200",
                              sum(role_of[rid][role] for rid in main_ids if resources[rid]["site_id"] == site), "requests",
                              filters=MAIN_FILTER + f"; role {role}; site {site}", sources=files_c, quality=QUALITY,
                              label_en=f"{role} on {site}", label_fr=f"{role} sur {site}"))
    user = sum(role_of[rid]["user_initiated_fetch"] for rid in main_ids)
    without = sum(1 for rid in main_ids if provider[rid] - role_of[rid]["user_initiated_fetch"] > 0)
    out += [
        metric("main.sensitivity.without_user_fetch.get200", total - user, "requests",
               filters=MAIN_FILTER + "; excluding role user_initiated_fetch (sensitivity analysis, not evidence of independence)",
               sources=files_c, quality=QUALITY, label_en="Sensitivity: without user-initiated fetches",
               label_fr="Sensibilité : sans récupérations à la demande"),
        metric("main.sensitivity.without_user_fetch.site_path_pairs", without, "site-path pairs",
               filters=MAIN_FILTER + "; excluding role user_initiated_fetch", sources=files_c, quality=QUALITY,
               label_en="Pairs without user-initiated fetches", label_fr="Couples sans récupérations à la demande"),
    ]

    # Recurrence: distinct UTC days with at least one provider-origin AI GET 200, per main-population pair.
    days = [int(summary[rid]["provider_origin_ai_get200_days"]) for rid in main_ids]
    buckets = {"1": sum(1 for d in days if d == 1), "2-3": sum(1 for d in days if 2 <= d <= 3),
               "4-7": sum(1 for d in days if 4 <= d <= 7), "8+": sum(1 for d in days if d >= 8)}
    for name, value in buckets.items():
        out.append(metric(f"main.recurrence.pairs_with_{name.replace('+', '_or_more').replace('-', '_to_')}_days", value,
                          "site-path pairs", filters=MAIN_FILTER + f"; days with requests: {name}",
                          sources=("resource-summary.csv",), quality=QUALITY,
                          label_en=f"Pairs requested on {name} days", label_fr=f"Couples demandés {name} jours"))
    out.append(metric("main.recurrence.max_days", max(days) if days else None, "days", filters=MAIN_FILTER,
                      sources=("resource-summary.csv",), quality=QUALITY, label_en="Most days for one pair",
                      label_fr="Nombre maximal de jours pour un couple"))
    daily_main = defaultdict(int)
    for row in daily:
        if (row["population"] == "main_documentary" and row["stored_identity_tier"] == PROVIDER
                and row["actor_role"] in AUTOMATED_ROLES and is_get200(row)):
            daily_main[(row["date_utc"], row["site_id"])] += int(row["request_count"])
    out.append(metric("main.daily.sum_check", sum(daily_main.values()), "requests",
                      filters=DAILY_FILTER + "; sum of the daily series (equals main.get200 minus user-initiated fetches)",
                      sources=("daily-summary.csv",), quality=QUALITY, label_en="Sum of the daily series",
                      label_fr="Somme de la série quotidienne"))
    for site in SITE_IDS:
        out.append(metric(f"main.daily.site.{site}.days_with_requests",
                          sum(1 for (day, s), v in daily_main.items() if s == site and v > 0), "days",
                          filters=DAILY_FILTER + f"; site {site}", sources=("daily-summary.csv",), quality=QUALITY,
                          label_en=f"Days with requests on {site}", label_fr=f"Jours avec requêtes sur {site}"))
    out.append(metric("main.daily.days_with_requests", len({day for (day, _), v in daily_main.items() if v > 0}), "days",
                      filters=DAILY_FILTER + "; any site", sources=("daily-summary.csv",), quality=QUALITY,
                      label_en="Days with requests, any site", label_fr="Jours avec requêtes, tous sites"))
    for tier, value in sorted(tier_main.items()):
        out.append(metric(f"main_population.tier.{tier}.get200", value, "requests",
                          filters=f"main documentary population; GET 200; stored tier {tier}; all roles",
                          sources=files_c, label_en=tier, label_fr=tier))

    extended_ids = [rid for rid, row in resources.items() if provider.get(rid) and row["scope_class"] in (
        "core_governance", "discovery_index", "supporting_documentation")]
    out += [
        metric("extended.get200", sum(provider[rid] for rid in extended_ids), "requests",
               filters=MAIN_FILTER.replace("(scope classes core_governance and discovery_index)",
                                           "plus supporting_documentation (extended documentary layer)"),
               sources=files_c, quality=QUALITY, label_en="Extended documentary layer (secondary reading)",
               label_fr="Couche documentaire élargie (lecture secondaire)"),
        metric("extended.site_path_pairs", len(extended_ids), "site-path pairs",
               filters="extended documentary layer; pairs with at least one provider-origin AI GET 200",
               sources=files_c, quality=QUALITY, label_en="Extended layer pairs", label_fr="Couples de la couche élargie"),
    ]
    for scope_row in exclusions:
        if scope_row["dimension"] == "scope":
            out.append(metric(f"scope_delta.{scope_row['excluded_value']}.provider_ai_get200",
                              int(scope_row["provider_origin_ai_get200"]), "requests",
                              filters=f"provider-origin AI-role GET 200 on pairs of scope class {scope_row['excluded_value']}",
                              sources=("exclusions.csv",), quality=QUALITY, label_en=scope_row["excluded_value"],
                              label_fr=scope_row["excluded_value"]))
            out.append(metric(f"exclusion.{scope_row['exclusion_id']}.requests", int(scope_row["requests_all_actors"]),
                              "requests", filters=f"scope class {scope_row['excluded_value']}",
                              sources=("exclusions.csv",), label_en=scope_row["excluded_value"],
                              label_fr=scope_row["excluded_value"]))

    historical_ids = [rid for rid, row in resources.items() if row["window_rows_status"] == "rows_in_window"
                      and row["scope_class"] not in ("control_resource", "undeclared_bucket")]
    hist_provider = sum(provider.get(rid, 0) for rid in historical_ids)
    hist_get200 = sum(get200_all.get(rid, 0) for rid in historical_ids)
    out += [
        metric("main.scope_delta.provider_ai_get200_excluded", hist_provider - total, "requests", numerator=hist_provider,
               filters="provider-origin AI-role GET 200 on historical-scope pairs outside the main documentary population",
               sources=files_c, label_en="Removed by the editorial scope review",
               label_fr="Retirées par la revue éditoriale du périmètre"),
        metric("historical.site_path_pairs", len(historical_ids), "site-path pairs", filters="historical report scope",
               sources=files_c, label_en="Historical scope pairs", label_fr="Couples du périmètre historique"),
        metric("historical.get200", hist_get200, "requests", filters="historical report scope; GET 200; all stored tiers",
               sources=files_c, label_en="Historical scope GET 200, all classifications",
               label_fr="GET 200 du périmètre historique, toutes classifications"),
        metric("historical.provider_ai.get200", hist_provider, "requests",
               filters="historical report scope; provider-origin AI roles; GET 200", sources=files_c, quality=QUALITY,
               label_en="Historical provider-origin AI GET 200", label_fr="GET 200 IA à origine fournisseur, périmètre historique"),
        metric("historical.provider_ai.site_path_pairs", sum(1 for rid in historical_ids if provider.get(rid, 0) > 0),
               "site-path pairs", filters="historical report scope; provider-origin AI roles; GET 200", sources=files_c,
               label_en="Historical provider-origin AI pairs", label_fr="Couples IA à origine fournisseur, périmètre historique"),
        metric("historical.unattributed.get200", tier_historical[UNATTRIBUTED], "requests",
               filters="historical report scope; stored tier cloudflare_verified_unattributed; GET 200", sources=files_c,
               quality="recorded_classification_reliability_under_review",
               label_en="Recorded as Cloudflare-verified, unattributed (under review)",
               label_fr="Enregistrées comme vérifiées par Cloudflare, non attribuées (en revue)"),
        share("historical.unattributed.share_of_get200", tier_historical[UNATTRIBUTED], hist_get200,
              filters="historical report scope; GET 200", sources=files_c,
              quality="recorded_classification_reliability_under_review",
              label_en="Share of historical GET 200 recorded as unattributed",
              label_fr="Part des GET 200 historiques enregistrée non attribuée"),
        metric("historical.network_claimed_ai.get200", network_ai_historical, "requests",
               filters="historical report scope; stored tier network_verified_claimed_actor; AI roles; GET 200",
               sources=files_c, quality="recorded_classification_reliability_under_review",
               label_en="Declared AI names with a network signal under review (never added to the provider tier)",
               label_fr="Noms IA déclarés avec signal réseau en revue (jamais ajoutés au niveau fournisseur)"),
    ]
    for role in AI_ROLES:
        out.append(metric(f"historical.provider_ai.role.{role}.get200",
                          sum(role_of[rid][role] for rid in historical_ids), "requests",
                          filters=f"historical report scope; provider-origin; role {role}; GET 200",
                          sources=files_c, quality=QUALITY, label_en=role, label_fr=role))
    for tier, value in sorted(tier_historical.items()):
        out.append(metric(f"historical.tier.{tier}.get200", value, "requests",
                          filters=f"historical report scope; stored tier {tier}; GET 200; all roles",
                          sources=files_c, label_en=tier, label_fr=tier))

    out.append(metric("collector.requests", sum(int(r["request_count"]) for r in (consultations if modern else daily)), "requests",
                      filters="all paths recorded by the collector on the three sites, all methods, statuses and actors",
                      sources=(("consultations.csv",) if modern else ("daily-summary.csv",)), label_en="All requests recorded by the collector",
                      label_fr="Toutes les requêtes enregistrées par le collecteur"))
    partial = sum(1 for r in coverage if r["coverage_status"] == "partial_declared")
    attestation = sum(1 for r in coverage if r["archive_reason_code"] == "COLLECTOR_WINDOW_ATTESTATION_MISSING")
    mismatch_days = sorted(r["date_utc"] for r in coverage if r["aggregate_minus_v3"] not in ("", "0"))
    out += [
        metric("coverage.days_in_window", len(coverage), "days", sources=("coverage.csv",),
               label_en="Days in the window", label_fr="Jours de la fenêtre"),
        metric("coverage.days_observed", sum(1 for r in coverage if r["observation_status"] == "observed"), "days",
               sources=("coverage.csv",), label_en="Days with archived rows", label_fr="Jours avec lignes archivées"),
        metric("coverage.days_partial_declared", partial, "days", sources=("coverage.csv",),
               label_en="Days whose archive report is partial", label_fr="Jours dont le rapport d’archive est partiel"),
        metric("coverage.days_attestation_missing", attestation, "days", sources=("coverage.csv",),
               label_en="Days with missing collector window attestation",
               label_fr="Jours sans attestation de fenêtre du collecteur"),
        metric("coverage.aggregate_v3_mismatch_days", (None if modern and any(r["aggregate_minus_v3"] == "" for r in coverage) else len(mismatch_days)), "days", sources=("coverage.csv",),
               filters=";".join(mismatch_days), label_en="Days with an aggregate/V3 count gap",
               label_fr="Jours avec écart entre agrégats et V3"),
        metric("coverage.aggregate_sum", sum(int(r["aggregate_count"]) for r in coverage) if all(r["aggregate_count"] != "" for r in coverage) else None, "requests",
               sources=("coverage.csv",), label_en="Sum of archived aggregate counts",
               label_fr="Somme des comptes agrégés archivés"),
        metric("coverage.v3_sum", sum(int(r["v3_count"]) for r in coverage) if all(r["v3_count"] != "" for r in coverage) else None, "requests", sources=("coverage.csv",),
               label_en="Sum of archived V3 counts", label_fr="Somme des comptes V3 archivés"),
        metric("coverage.joint_matches_archive_days", sum(1 for r in coverage if r["joint_matches_archive"] == "true"),
               "days", sources=("coverage.csv",), label_en="Days whose joint total equals the archived aggregate",
               label_fr="Jours dont le total conjoint égale l’agrégat archivé"),
    ]
    if modern:
        out += expanded_metrics(resources, consultations, daily_main, total, pairs, llms, other)
        for item in out:
            if item["value"] is None and item["metric_id"] in ("coverage.aggregate_v3_mismatch_days", "coverage.aggregate_sum", "coverage.v3_sum"):
                item.update(status="withheld", reason="daily_coverage_complement_withheld_by_disclosure_policy")
    out.sort(key=lambda m: m["metric_id"])
    document = {"metrics": out}
    if catalog.get("versions", {}).get("public_schema") == "dwr-public/2.0.0":
        document["measurement"] = {"epochs": catalog.get("measurement", {}).get("epochs", []),
                                   "classifier_versions": catalog["versions"].get("classifier_recorded", []),
                                   "epoch_resolution": catalog.get("measurement", {}).get("epoch_resolution", "unknown"),
                                   "aggregation": "request sums across epochs; distinct resources and days use unions"}
    return document


def expanded_metrics(resources, consultations, daily_main, total, pairs, llms, other):
    """Version 2 additions, computed only here; frozen v1 metrics retain their contract."""
    observed = {rid for rid, r in resources.items() if _bool(r["main_population"]) and r["window_rows_status"] == "rows_in_window"}
    llms_pairs = sum(resources[rid]["path"] == "/llms.txt" for rid in observed)
    sources = ("consultations.csv", "resources.csv")
    selection = [r for r in consultations if r["resource_id"] in observed and is_get200(r)
                 and r["stored_identity_tier"] == PROVIDER and r["actor_role"] in AI_ROLES]
    definition = "main population site-path pairs with recorded rows across all actors, methods and HTTP statuses; not a complete historical inventory"
    out = [metric("main.recorded_pairs", len(observed), "site-path pairs", filters=definition, sources=sources,
                  label_en="Main resources with recorded rows", label_fr="Ressources principales avec lignes enregistrées"),
           share("main.conditional_pair_share", pairs, len(observed), filters=MAIN_FILTER + "; denominator: " + definition,
                 sources=sources, label_en="Conditional share of resources with recorded rows", label_fr="Part conditionnelle des ressources avec lignes"),
           metric("main.llms_recorded_pairs", llms_pairs, "site-path pairs", filters=definition + "; /llms.txt", sources=sources),
           metric("main.other_recorded_pairs", len(observed)-llms_pairs, "site-path pairs", filters=definition + "; other resources", sources=sources)]
    for label, numerator, denominator in (("llms", llms, llms_pairs), ("other", other, len(observed)-llms_pairs)):
        item = share(f"main.{label}_requests_per_recorded_url", numerator, denominator, filters=MAIN_FILTER + "; denominator: " + definition + "; no exposure adjustment", sources=sources)
        item["unit"] = "requests per resource with recorded rows"
        out.append(item)
    for site in SITE_IDS:
        out.append(metric(f"main.site.{site}.recorded_pairs", sum(resources[rid]["site_id"] == site for rid in observed), "site-path pairs", filters=definition + "; " + site, sources=sources))
    for dimension in ("actor_name", "actor_family"):
        counts = defaultdict(int)
        for row in selection:
            counts[row[dimension]] += int(row["request_count"])
        for name, count in sorted(counts.items()):
            prefix = f"main.{dimension}.{name}"
            out.extend([metric(prefix + ".get200", count, "requests", filters=MAIN_FILTER + f"; {dimension}={name}", sources=sources, quality=QUALITY),
                        share(prefix + ".share", count, total, filters=MAIN_FILTER + f"; {dimension}={name}", sources=sources, quality=QUALITY)])
    names = {"GPTBot", "OAI-SearchBot", "PerplexityBot", "ChatGPT-User"}
    failed = sum(int(r["request_count"]) for r in consultations if r["resource_id"] in observed and is_get200(r)
                 and r["actor_name"] in names and r["stored_identity_tier"] == "spoofed_or_failed_verification" and r["actor_role"] in AI_ROLES)
    matched = sum(int(r["request_count"]) for r in selection if r["actor_name"] in names)
    filter_failed = "main population; GET 200; AI roles; exact names GPTBot, OAI-SearchBot, PerplexityBot, ChatGPT-User; failed tier spoofed_or_failed_verification; denominator matched provider-origin plus failed tier only; not proven spoofing"
    out.extend([metric("main.failed_origin_selected.get200", failed, "requests", filters=filter_failed, sources=sources),
                share("main.failed_origin_selected.share", failed, matched + failed, filters=filter_failed, sources=sources)])
    by_day = defaultdict(int)
    for (day, site), count in daily_main.items():
        by_day[day] += count
    top = sorted(by_day.items(), key=lambda item: (-item[1], item[0]))[:3]
    numerator = sum(count for _, count in top)
    out.extend([metric("main.automated.top3_days_get200", numerator, "requests", filters=DAILY_FILTER, sources=("daily-summary.csv",)),
                share("main.automated.top3_days_share", numerator, sum(by_day.values()), filters=DAILY_FILTER, sources=("daily-summary.csv",))])
    for index, (day, count) in enumerate(top, 1):
        out.append(metric(f"main.automated.top_day_{index}.get200", count, "requests", filters=DAILY_FILTER + "; date=" + day, sources=("daily-summary.csv",)))
    labels = {
        "main.llms_recorded_pairs": ("llms.txt resources with recorded rows", "Ressources llms.txt avec lignes enregistrées"),
        "main.other_recorded_pairs": ("Other resources with recorded rows", "Autres ressources avec lignes enregistrées"),
        "main.llms_requests_per_recorded_url": ("llms.txt requests per resource with rows, unadjusted exposure", "Requêtes llms.txt par ressource avec lignes, exposition non ajustée"),
        "main.other_requests_per_recorded_url": ("Other requests per resource with rows, unadjusted exposure", "Autres requêtes par ressource avec lignes, exposition non ajustée"),
        "main.failed_origin_selected.get200": ("Failed origin verification for four selected names", "Vérification d’origine échouée pour quatre noms retenus"),
        "main.failed_origin_selected.share": ("Failed-origin share among selected verified and failed tiers", "Part à origine non vérifiée parmi les niveaux vérifiés et échoués retenus"),
        "main.automated.top3_days_get200": ("Automated requests on the three busiest days", "Requêtes automatisées des trois journées les plus actives"),
        "main.automated.top3_days_share": ("Share of automated requests on the three busiest days", "Part des requêtes automatisées sur les trois journées les plus actives"),
    }
    for item in out:
        key = item["metric_id"]
        if item["label_en"] and item["label_fr"]:
            continue
        if key in labels:
            en, fr = labels[key]
        elif key.startswith(("main.actor_name.", "main.actor_family.")):
            dimension, name, kind = key.split(".")[1:]
            en = ("Recorded agent " if dimension == "actor_name" else "Provider family ") + name + (": requests" if kind == "get200" else ": share of main selection")
            fr = ("Agent enregistré " if dimension == "actor_name" else "Famille de fournisseur ") + name + (" : requêtes" if kind == "get200" else " : part de la sélection principale")
        elif key.startswith("main.site."):
            site = key[len("main.site."):-len(".recorded_pairs")]
            en, fr = site + ": resources with recorded rows", site + " : ressources avec lignes enregistrées"
        else:
            rank = key.split("top_day_")[1].split(".")[0]
            en, fr = "Automated requests on ranked day " + rank, "Requêtes automatisées de la journée au rang " + rank
        item.update(label_en=en, label_fr=fr)
    return out
