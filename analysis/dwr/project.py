"""project-public: the minimized public projection of an edition.

Built from the joint aggregate (day x site x path x method x status x actor x
tier), aggregated only to the grains allowed by config/small-cell-policy.json:
- edition grain: site x path x method x status x actor x tier (consultations.csv);
- daily grain: date x site x population x role x tier x method x status, never path
  or actor name (daily-summary.csv); protected strata (person-initiated or
  unattributable) are combined there into one group per date x site x population,
  because a finer daily row crossed with the edition grain could isolate one path;
- daily family grain for automated provider-origin roles of the main population
  only (daily-family-summary.csv).
Cells are exact sums of joint rows. A combination absent from a table had no
recorded request in the producer table; it is not a measured absence on the web.
"""

from __future__ import annotations

from collections import defaultdict

from . import SCHEMA_VERSION
from .common import REPO_ROOT, SITE_IDS, load_json
from .reconcile import AI_ROLES, PROVIDER, in_historical_scope

EPOCH = "classifier-2026-08-24.1"
AUTOMATED_MAIN_ROLES = ("ai_training", "ai_search")
PROTECTED_GROUP = "protected_strata"
ANY = "ANY"

CONSULTATION_FIELDS = (
    "edition_id", "schema_version", "measurement_epoch_id", "period_start_utc", "period_end_exclusive_utc",
    "time_grain", "date_utc", "site_id", "resource_id", "path", "scope_class", "http_method", "http_status",
    "actor_family", "actor_name", "actor_role", "stored_identity_tier", "attribution_assessment",
    "initiation_provenance", "initiation_evidence_status", "request_count", "observation_status",
    "coverage_status", "suppression_status", "cell_derivation", "source_snapshot_id",
)
RESOURCE_FIELDS = (
    "resource_id", "site_id", "path", "url", "format", "language", "scope_class", "main_population", "llms_txt",
    "family", "role_en", "role_fr", "declares_canonical_source", "mentions_runtime_or_mcp", "window_rows_status",
    "producer_category", "scope_rule_id", "review_status", "found_in_snapshot", "graph_snapshot_id",
    "outbound_relations", "inbound_relations", "historical_version_status", "snapshot_sha256", "justification",
)
LINK_FIELDS = (
    "graph_snapshot_id", "graph_snapshot_at", "source_site", "source_path", "source_resource_id", "target_site",
    "target_path", "target_resource_id", "relation_type", "evidence_line", "occurrences", "note",
)
RESOURCE_SUMMARY_FIELDS = (
    "edition_id", "resource_id", "site_id", "path", "scope_class", "main_population", "llms_txt",
    "requests_all_actors", "get200_all_actors", "head_all_actors", "status304_all_actors", "status4xx5xx_all_actors",
    "days_with_rows", "get200_days_all_actors", "provider_origin_ai_get200", "provider_origin_ai_get200_days",
    "coverage_status",
)
DAILY_FIELDS = ("edition_id", "date_utc", "site_id", "population", "actor_role", "stored_identity_tier",
                "http_method", "http_status", "request_count", "coverage_status", "archive_report_status")
ACTOR_FIELDS = ("edition_id", "population", "site_id", "actor_family", "actor_name", "actor_role",
                "stored_identity_tier", "attribution_assessment", "requests", "get200",
                "distinct_paths_in_group", "days_with_rows")
COVERAGE_FIELDS = ("edition_id", "date_utc", "observation_status", "coverage_status", "archive_status",
                   "archive_report_status", "archive_reason_code", "aggregate_count", "v3_count",
                   "aggregate_minus_v3", "export_matches_archive", "joint_matches_archive", "snapshots_for_date",
                   "classifier_version", "producer_deployment_label")
EXCLUSION_FIELDS = ("edition_id", "exclusion_id", "dimension", "excluded_value", "rule_id", "site_pairs",
                    "requests_all_actors", "get200_all_actors", "provider_origin_ai_get200", "published_status",
                    "reason_en", "reason_fr")
FAMILY_DAILY_FIELDS = ("edition_id", "date_utc", "family", "actor_role", "request_count", "observation_status")
GRAPH_PREFIX = {"gautierdorval.com": "gd", "pagup.com": "pg", "better-robots.com": "br"}


def protected_strata() -> tuple[frozenset, frozenset]:
    spec = load_json(REPO_ROOT / "config" / "small-cell-policy.json")["protected_strata"]
    return frozenset(spec["actor_roles"]), frozenset(spec["stored_identity_tiers"])


def daily_key(day: str, site: str, population: str, role: str, tier: str, method: str, status,
              protected: tuple[frozenset, frozenset]) -> tuple:
    roles, tiers = protected
    if role in roles or tier in tiers:
        return (day, site, population, PROTECTED_GROUP, PROTECTED_GROUP, ANY, ANY)
    return (day, site, population, role, tier, method, str(status))


def deduce_method_status(marginals: dict) -> dict[str, bool]:
    """Per site, True when every historical-scope request falls in GET 200, HEAD 200,
    GET 304 or POST 405 and the per-path columns add up, so that the per-path split
    follows from the export by non-negativity. Kept as a reconciliation check: the
    joint acquisition confirms or refutes it (joint.cross_check)."""
    allowed = {("GET", 200), ("HEAD", 200), ("GET", 304), ("POST", 405)}
    result = {}
    for site in SITE_IDS:
        combos = {(row["http_method"], row["http_status"]): row["requests"]
                  for row in marginals["http"] if row["site_id"] == site and row["requests"] > 0}
        paths = [row for row in marginals["files"] if row["site_id"] == site and in_historical_scope(row)]
        sums = {("GET", 200): sum(r["get200"] for r in paths), ("HEAD", 200): sum(r["head"] for r in paths),
                ("GET", 304): sum(r["not_modified"] for r in paths), ("POST", 405): sum(r["errors"] for r in paths)}
        identity = all(r["requests"] == r["get200"] + r["head"] + r["not_modified"] + r["errors"] for r in paths)
        result[site] = (set(combos) <= allowed and identity
                        and all(combos.get(key, 0) == value for key, value in sums.items()))
    return result


def population_of(resource: dict) -> str:
    if resource["main_population"]:
        return "main_documentary"
    return {"control_resource": "robots_control", "undeclared_bucket": "undeclared_bucket"}.get(
        resource["scope_class"], "other_documentary")


def deployment_labels(timeline: dict | None) -> list[dict]:
    if not timeline or timeline.get("status") != "observed":
        return []
    return [{"label": f"pd{i:02d}", **deployment} for i, deployment in enumerate(timeline["deployments"], start=1)]


def label_for_day(labels: list[dict], day: str) -> str | None:
    """Labels of the deployments active at any time during the UTC day (joined by '+')."""
    start, end = f"{day}T00:00:00", f"{day}T23:59:59.999"
    active = []
    for index, deployment in enumerate(labels):
        begins = deployment["effective_at"]
        ends = labels[index + 1]["effective_at"] if index + 1 < len(labels) else None
        if begins <= end and (ends is None or ends > start):
            active.append(deployment["label"])
    return "+".join(active) or None


def project(qualified: dict, normalized: dict, edition: dict, import_id: str) -> dict:
    if normalized.get("source_mode") != "joint_acquisition" or not normalized.get("joint_rows"):
        from .common import DwrError
        raise DwrError("joint_aggregate_required", "acquire-readonly then normalize before project-public")
    rows = normalized["joint_rows"]
    inventory = normalized["archive_inventory"]
    attribution = qualified["attribution"]["assessments"]
    window = edition["window"]
    edition_id = edition["edition_id"]
    snapshot_id = f"d1-joint-{normalized['joint_acquisition'].split('-', 1)[1].lower()}"
    resources = {(r["site_id"], r["path"]): r for r in qualified["resources"]}
    missing = sorted({(r["site_id"], r["path"]) for r in rows} - set(resources))
    if missing:
        from .common import DwrError
        raise DwrError("registry_entry_missing", f"{missing[0]}")
    common = {"edition_id": edition_id, "schema_version": SCHEMA_VERSION, "measurement_epoch_id": EPOCH,
              "period_start_utc": window.start_utc, "period_end_exclusive_utc": window.end_exclusive_utc,
              "time_grain": "edition", "date_utc": None, "initiation_provenance": "unknown",
              "initiation_evidence_status": "not_established", "coverage_status": "partial_declared",
              "suppression_status": "not_suppressed", "cell_derivation": "joint_exact", "source_snapshot_id": snapshot_id}

    graphs = qualified["graphs"]
    graph_ids = {}
    for site, site_graph in graphs.items():
        dates = sorted(str(repo.get("commit_date", ""))[:10] for repo in site_graph.get("repositories") or [] if repo.get("commit_date"))
        graph_ids[site] = {
            "graph_snapshot_id": (f"graph-{GRAPH_PREFIX[site]}-{dates[-1].replace('-', '')}-{site_graph['snapshot_digest'][:8]}"
                                  if site_graph["status"] == "extracted" and dates else None),
            "graph_snapshot_at": dates[-1] if dates else None,
            "status": site_graph["status"],
        }

    protected = protected_strata()
    edition_cells = defaultdict(int)
    daily_cells = defaultdict(int)
    family_cells = defaultdict(int)
    actor_cells = defaultdict(lambda: {"requests": 0, "get200": 0, "_paths": set(), "_days": set()})
    for r in rows:
        resource = resources[(r["site_id"], r["path"])]
        population = population_of(resource)
        n = r["request_count"]
        edition_cells[(r["site_id"], r["path"], r["http_method"], r["http_status"], r["actor_family"], r["actor_name"],
                       r["actor_role"], r["stored_identity_tier"])] += n
        daily_cells[daily_key(r["date_utc"], r["site_id"], population, r["actor_role"], r["stored_identity_tier"],
                              r["http_method"], r["http_status"], protected)] += n
        get200 = r["http_method"] == "GET" and r["http_status"] == 200
        if (population == "main_documentary" and get200 and r["stored_identity_tier"] == PROVIDER
                and r["actor_role"] in AUTOMATED_MAIN_ROLES):
            family_cells[(r["date_utc"], resource["family"], r["actor_role"])] += n
        actor = actor_cells[(population, r["site_id"], r["actor_family"], r["actor_name"], r["actor_role"],
                             r["stored_identity_tier"])]
        actor["requests"] += n
        actor["get200"] += n if get200 else 0
        actor["_paths"].add(r["path"])
        actor["_days"].add(r["date_utc"])

    consultations = []
    for (site, path, method, status, family, name, role, tier), n in edition_cells.items():
        resource = resources[(site, path)]
        consultations.append({**common, "site_id": site, "resource_id": resource["resource_id"], "path": path,
                              "scope_class": resource["scope_class"], "http_method": method, "http_status": status,
                              "actor_family": family, "actor_name": name, "actor_role": role,
                              "stored_identity_tier": tier, "attribution_assessment": attribution[tier]["attribution_assessment"],
                              "request_count": n, "observation_status": "observed"})
    consultations.sort(key=lambda c: (SITE_IDS.index(c["site_id"]), c["path"], c["http_method"], c["http_status"],
                                      c["actor_family"], c["actor_name"], c["stored_identity_tier"]))

    resources_out, summaries = [], []
    for resource in qualified["resources"]:
        site, path = resource["site_id"], resource["path"]
        resources_out.append({**{key: resource.get(key) for key in RESOURCE_FIELDS},
                              "graph_snapshot_id": graph_ids[site]["graph_snapshot_id"]})
        counts = resource["counts"]
        if not counts:
            continue
        summaries.append({
            "edition_id": edition_id, "resource_id": resource["resource_id"], "site_id": site, "path": path,
            "scope_class": resource["scope_class"], "main_population": resource["main_population"],
            "llms_txt": resource["llms_txt"], "requests_all_actors": counts["requests"],
            "get200_all_actors": counts["get200"], "head_all_actors": counts["head"],
            "status304_all_actors": counts["not_modified"], "status4xx5xx_all_actors": counts["errors"],
            "days_with_rows": counts["days"], "get200_days_all_actors": counts["get200_days"],
            "provider_origin_ai_get200": counts["provider_ai_get200"],
            "provider_origin_ai_get200_days": counts["provider_ai_get200_days"],
            "coverage_status": "partial_declared",
        })

    links = []
    by_key = {(r["site_id"], r["path"]): r["resource_id"] for r in qualified["resources"]}
    for site in SITE_IDS:
        info = graph_ids[site]
        for relation in graphs[site]["relations"]:
            if relation["target_site"] == "external":
                continue
            links.append({"graph_snapshot_id": info["graph_snapshot_id"], "graph_snapshot_at": info["graph_snapshot_at"],
                          "source_site": site, "source_path": relation["source_path"],
                          "source_resource_id": by_key.get((site, relation["source_path"]), ""),
                          "target_site": relation["target_site"], "target_path": relation["target_path"],
                          "target_resource_id": by_key.get((relation["target_site"], relation["target_path"]), ""),
                          "relation_type": relation["relation_type"], "evidence_line": relation["evidence_line"],
                          "occurrences": relation["occurrences"], "note": relation["note"]})
    links.sort(key=lambda r: (SITE_IDS.index(r["source_site"]), r["source_path"], r["target_site"],
                              r["target_path"] or "", r["relation_type"]))

    archive_by_day = {day["date_utc"]: day for day in inventory["days"]}
    daily = [{"edition_id": edition_id, "date_utc": day, "site_id": site, "population": population, "actor_role": role,
              "stored_identity_tier": tier, "http_method": method, "http_status": status, "request_count": n,
              "coverage_status": "partial_declared",
              "archive_report_status": archive_by_day.get(day, {}).get("report_status", "unavailable")}
             for (day, site, population, role, tier, method, status), n in daily_cells.items()]
    daily.sort(key=lambda r: (r["date_utc"], SITE_IDS.index(r["site_id"]), r["population"], r["actor_role"],
                              r["stored_identity_tier"], r["http_method"], r["http_status"]))

    families = sorted({family for (_, family, _) in family_cells})
    family_daily = []
    for day in window.dates():
        for family in families:
            for role in AUTOMATED_MAIN_ROLES:
                n = family_cells.get((day.isoformat(), family, role), 0)
                family_daily.append({"edition_id": edition_id, "date_utc": day.isoformat(), "family": family,
                                     "actor_role": role, "request_count": n,
                                     "observation_status": "observed" if n else "observed_zero"})

    actors = []
    for (population, site, family, name, role, tier), values in actor_cells.items():
        actors.append({"edition_id": edition_id, "population": population, "site_id": site, "actor_family": family,
                       "actor_name": name, "actor_role": role, "stored_identity_tier": tier,
                       "attribution_assessment": attribution[tier]["attribution_assessment"],
                       "requests": values["requests"], "get200": values["get200"],
                       "distinct_paths_in_group": len(values["_paths"]), "days_with_rows": len(values["_days"])})
    actors.sort(key=lambda r: (r["population"], SITE_IDS.index(r["site_id"]), r["stored_identity_tier"],
                               r["actor_role"], r["actor_name"]))

    labels = deployment_labels(normalized.get("deployment_timeline"))
    export_daily = defaultdict(int)
    for row in normalized["marginals"]["daily"]:
        export_daily[row["date_utc"]] += row["all_requests"]
    joint_daily = defaultdict(int)
    for r in rows:
        joint_daily[r["date_utc"]] += r["request_count"]
    coverage = []
    for day in inventory["days"]:
        aggregate, v3 = day.get("aggregate_count"), day.get("v3_count")
        coverage.append({"edition_id": edition_id, "date_utc": day["date_utc"],
                         "observation_status": "observed" if day["archive_status"] == "archived" else "observation_unavailable",
                         "coverage_status": "partial_declared" if day.get("report_status") == "partial" else day.get("report_status", "unknown"),
                         "archive_status": day["archive_status"], "archive_report_status": day.get("report_status"),
                         "archive_reason_code": day.get("governance_reason_code"), "aggregate_count": aggregate,
                         "v3_count": v3, "aggregate_minus_v3": (aggregate - v3) if aggregate is not None and v3 is not None else None,
                         "export_matches_archive": export_daily.get(day["date_utc"]) == aggregate,
                         "joint_matches_archive": joint_daily.get(day["date_utc"]) == aggregate,
                         "snapshots_for_date": day.get("snapshots"), "classifier_version": "2026-08-24.1",
                         "producer_deployment_label": label_for_day(labels, day["date_utc"])})

    exclusions = build_exclusions(qualified, rows, resources, edition_id, attribution)
    public_labels = [{"label": d["label"], "effective_at": d["effective_at"],
                      "versions": [{"percentage": v["percentage"]} for v in d["versions"]]} for d in labels]
    return {"resources": resources_out, "links": links, "consultations": consultations, "resource_summary": summaries,
            "daily": daily, "actors": actors, "coverage": coverage, "exclusions": exclusions,
            "family_daily": family_daily, "graph_snapshots": graph_ids, "deployments": public_labels,
            "source_snapshot_id": snapshot_id}


def build_exclusions(qualified: dict, rows: list[dict], resources: dict, edition_id: str, attribution: dict) -> list[dict]:
    rules = load_json(REPO_ROOT / "config" / "scope-rules.json")
    out = []
    groups = defaultdict(list)
    for resource in qualified["resources"]:
        if resource["counts"] and not resource["main_population"]:
            groups[resource["scope_class"]].append(resource)
    for scope_class in sorted(groups):
        members = groups[scope_class]
        spec = rules["classes"][scope_class]
        out.append({"edition_id": edition_id, "exclusion_id": f"scope:{scope_class}", "dimension": "scope",
                    "excluded_value": scope_class, "rule_id": ";".join(sorted({m["scope_rule_id"] for m in members})),
                    "site_pairs": len(members),
                    "requests_all_actors": sum(m["counts"]["requests"] for m in members),
                    "get200_all_actors": sum(m["counts"]["get200"] for m in members),
                    "provider_origin_ai_get200": sum(m["counts"]["provider_ai_get200"] for m in members),
                    "published_status": "counts_published", "reason_en": spec["definition_en"],
                    "reason_fr": spec["definition_fr"]})
    tiers = defaultdict(lambda: {"requests": 0, "get200": 0, "ai_get200": 0})
    for r in rows:
        if not resources[(r["site_id"], r["path"])]["main_population"]:
            continue
        bucket = tiers[r["stored_identity_tier"]]
        bucket["requests"] += r["request_count"]
        if r["http_method"] == "GET" and r["http_status"] == 200:
            bucket["get200"] += r["request_count"]
            if r["actor_role"] in AI_ROLES:
                bucket["ai_get200"] += r["request_count"]
    for tier in sorted(tiers):
        if attribution[tier]["eligible_for_main_population"]:
            continue
        out.append({"edition_id": edition_id, "exclusion_id": f"attribution:{tier}", "dimension": "attribution",
                    "excluded_value": tier, "rule_id": attribution[tier]["attribution_assessment"], "site_pairs": None,
                    "requests_all_actors": tiers[tier]["requests"], "get200_all_actors": tiers[tier]["get200"],
                    "provider_origin_ai_get200": None, "published_status": "counts_published_main_population",
                    "reason_en": attribution[tier]["label_en"], "reason_fr": attribution[tier]["label_fr"]})
    return out
