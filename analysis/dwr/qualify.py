"""qualify: apply the versioned scope registry, attribution rules and coverage.

Inputs are the private normalized data, the public registry and rule files, and
the private source snapshots. Outputs stay private until project-public applies
the small-cell policy. Every collector path must have a registry entry; a missing
rule stops the stage.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from . import graph
from .common import REPO_ROOT, DwrError, SITE_IDS, load_json, read_csv, validate_path, validate_site

SCOPE_CLASSES = ("core_governance", "discovery_index", "supporting_documentation", "operational_descriptor",
                 "control_resource", "technical_resource", "undeclared_bucket", "unresolved_scope")
SITE_PREFIX = {"gautierdorval.com": "gd", "pagup.com": "pg", "better-robots.com": "br"}
REGISTRY_COLUMNS = ("site_id", "path", "scope_class", "scope_rule_id", "family", "format", "language",
                    "role_en", "role_fr", "declares_canonical_source", "mentions_runtime_or_mcp",
                    "found_in_snapshot", "review_status", "justification")


def resource_id(site_id: str, path: str) -> str:
    return f"{SITE_PREFIX[site_id]}:{path}"


def load_registry() -> dict[tuple[str, str], dict]:
    rows = read_csv(REPO_ROOT / "config" / "scope-registry.csv")
    if not rows or tuple(rows[0].keys()) != REGISTRY_COLUMNS:
        raise DwrError("schema_unknown", "scope-registry.csv")
    rules = load_json(REPO_ROOT / "config" / "scope-rules.json")
    known_rules = {rule["rule_id"] for rule in rules["rules"]}
    registry = {}
    for row in rows:
        key = (validate_site(row["site_id"]), validate_path(row["path"]))
        if key in registry:
            raise DwrError("registry_duplicate", f"{key}")
        if row["scope_class"] not in SCOPE_CLASSES:
            raise DwrError("scope_class_unknown", row["scope_class"])
        if row["scope_rule_id"] not in known_rules:
            raise DwrError("scope_rule_unknown", row["scope_rule_id"])
        if key[1] == "/robots.txt" and row["scope_class"] != "control_resource":
            raise DwrError("robots_txt_must_be_control_resource")
        if key[1] == "/.well-known/__undeclared__" and row["scope_class"] != "undeclared_bucket":
            raise DwrError("undeclared_bucket_must_stay_separate")
        registry[key] = dict(row)
    return registry


def main_population_classes() -> set[str]:
    rules = load_json(REPO_ROOT / "config" / "scope-rules.json")
    return {name for name, spec in rules["classes"].items() if spec["main_population"]}


def build_graphs(private: Path) -> dict[str, dict]:
    serving = load_json(private / "lock" / "sources-config.json").get("graph_serving_repositories", {})
    graphs = {}
    for site_id in SITE_IDS:
        site_dir = private / "sources" / site_id
        if not (site_dir / "snapshot.json").is_file() or site_id not in serving:
            graphs[site_id] = {"site_id": site_id, "status": "source_unavailable", "relations": [], "files": [],
                               "repositories": [], "snapshot_digest": ""}
            continue
        result = graph.extract_site(site_id, site_dir)
        # Only repositories that serve the site's files date the graph; evidence-only reads do not.
        result["repositories"] = serving[site_id]
        result["status"] = "extracted"
        graphs[site_id] = result
    return graphs


def qualify(normalized: dict, private: Path) -> dict:
    registry = load_registry()
    main_classes = main_population_classes()
    attribution = load_json(REPO_ROOT / "config" / "attribution-rules.json")
    marginals = normalized["marginals"]
    files = {(row["site_id"], row["path"]): row for row in marginals["files"]}
    if normalized.get("joint_rows"):
        from .joint import path_counts
        for key, counts in path_counts(normalized["joint_rows"]).items():
            files[key] = {**files.get(key, {}), **counts, "site_id": key[0], "path": key[1]}
    registered_only = {(row["site_id"], row["path"]): row for row in marginals["registered_without_window_rows"]}
    missing = sorted(set(files) - set(registry))
    if missing:
        raise DwrError("registry_entry_missing", f"{len(missing)} paths, first {missing[0]}")
    graphs = build_graphs(private)
    outbound, inbound = defaultdict(int), defaultdict(int)
    for site_graph in graphs.values():
        for relation in site_graph["relations"]:
            if relation["target_site"] == "external":
                continue
            outbound[(relation["source_site"], relation["source_path"])] += 1
            inbound[(relation["target_site"], relation["target_path"])] += 1
    digests = {(site, item["url_path"]): item["sha256"] for site, site_graph in graphs.items()
               for item in site_graph.get("files", [])}
    resources = []
    for key in sorted(registry, key=lambda k: (SITE_IDS.index(k[0]), k[1])):
        entry = registry[key]
        counts = files.get(key)
        status = ("rows_in_window" if counts else
                  "registered_now_no_row_in_window" if key in registered_only else "not_in_collector_window_export")
        resources.append({
            **entry,
            "resource_id": resource_id(*key),
            "url": f"https://{key[0]}{key[1]}",
            "main_population": entry["scope_class"] in main_classes,
            "llms_txt": key[1] == "/llms.txt",
            "window_rows_status": status,
            "producer_category": (counts or registered_only.get(key) or {}).get("producer_category", ""),
            "outbound_relations": outbound.get(key, 0),
            "inbound_relations": inbound.get(key, 0),
            "historical_version_status": "unknown",
            "snapshot_sha256": digests.get(key, ""),
            "counts": counts,
        })
    tiers = {name: spec for name, spec in attribution["assessments"].items()}
    for actor in marginals["actors"]:
        if actor["stored_identity_tier"] not in tiers:
            raise DwrError("attribution_rule_missing", actor["stored_identity_tier"])
    return {"edition_id": normalized["edition_id"], "source_mode": normalized["source_mode"],
            "resources": resources, "graphs": graphs, "attribution": attribution,
            "main_classes": sorted(main_classes), "case_checks": check_cases(private, graphs)}


def _squash(text: str) -> str:
    return " ".join(text.split())


def check_cases(private: Path, graphs: dict) -> list[dict]:
    """Verify each case excerpt verbatim (whitespace-normalized) in its snapshot file,
    and each documentary path step as a relation of the snapshot graph."""
    cases = load_json(REPO_ROOT / "config" / "cases.json")["cases"]
    checks = []
    for case in cases:
        site = case["site_id"]
        snapshot = load_json(private / "sources" / site / "snapshot.json")
        files = {item["url_path"]: item for item in snapshot.get("files", [])}
        relations = {(r["source_path"], r["target_path"]) for r in graphs[site]["relations"]
                     if r["target_site"] == site}
        for resource in case["resources"]:
            item = files.get(resource["path"])
            found = False
            digest = None
            if item:
                path = (private / "sources" / site / item["snapshot_file"]).resolve()
                text = path.read_text(encoding="utf-8-sig")
                found = _squash(resource["excerpt"]) in _squash(text)
                digest = item.get("sha256")
            checks.append({"site_id": site, "kind": "excerpt", "path": resource["path"], "verified": found,
                           "snapshot_file_sha256": digest})
        for source, target in case["path_steps"]:
            checks.append({"site_id": site, "kind": "path_step", "path": f"{source} -> {target}",
                           "verified": (source, target) in relations, "snapshot_file_sha256": None})
    return checks
