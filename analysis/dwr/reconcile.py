"""Offline reconciliation of the initial internal report.

This recomputes the historical figures from the same exports with this
repository's own code and compares them with the expected values. It is a
reproduction of arithmetic on the same inputs, not an independent audit: the
exports and the report come from the same producer chain.
"""

from __future__ import annotations

from collections import defaultdict

from .common import DwrError

AI_ROLES = ("ai_training", "ai_search", "user_initiated_fetch")
PROVIDER = "provider_origin_verified_actor"
NETWORK = "network_verified_claimed_actor"
UNATTRIBUTED = "cloudflare_verified_unattributed"


def in_historical_scope(record: dict) -> bool:
    return (record["path"] not in ("/robots.txt", "/.well-known/__undeclared__")
            and record["producer_category"] != "well-known-probe")


def historical_figures(marginals: dict) -> dict:
    files = marginals["files"]
    scope = [row for row in files if in_historical_scope(row)]
    actors = marginals["actors"]
    provider_ai_actors = [row for row in actors if row["stored_identity_tier"] == PROVIDER and row["actor_role"] in AI_ROLES]
    provider_paths = [row for row in scope if row["provider_ai_get200"] > 0]
    by_paths = sum(row["provider_ai_get200"] for row in scope)
    by_actors = sum(row["get200"] for row in provider_ai_actors)
    if by_paths != by_actors:
        raise DwrError("marginals_disagree", f"paths={by_paths} actors={by_actors}")
    llms = sum(row["provider_ai_get200"] for row in scope if row["path"] == "/llms.txt")
    governance_get200 = sum(row["get200"] for row in scope)
    unattributed = sum(row["get200"] for row in actors if row["stored_identity_tier"] == UNATTRIBUTED)
    network_ai = sum(row["get200"] for row in actors if row["stored_identity_tier"] == NETWORK and row["actor_role"] in AI_ROLES)
    role = defaultdict(int)
    for row in provider_ai_actors:
        role[row["actor_role"]] += row["get200"]
    by_site = defaultdict(int)
    for row in scope:
        by_site[row["site_id"]] += row["provider_ai_get200"]
    return {
        "all_collector_requests": sum(row["requests"] for row in files),
        "governance_requests": sum(row["requests"] for row in scope),
        "governance_get200": governance_get200,
        "governance_site_path_pairs": len({(row["site_id"], row["path"]) for row in scope}),
        "stored_cloudflare_unattributed_get200": unattributed,
        "stored_cloudflare_unattributed_percent_of_get200": round(unattributed * 100 / governance_get200, 2),
        "stored_provider_origin_ai_get200": by_paths,
        "stored_provider_origin_ai_site_path_pairs": len({(row["site_id"], row["path"]) for row in provider_paths}),
        "stored_provider_origin_ai_llms_get200": llms,
        "stored_provider_origin_ai_other_get200": by_paths - llms,
        "stored_provider_origin_ai_other_site_path_pairs": len({(row["site_id"], row["path"]) for row in provider_paths if row["path"] != "/llms.txt"}),
        "stored_provider_origin_ai_other_percent": round((by_paths - llms) * 100 / by_paths, 2),
        "stored_provider_origin_ai_training_get200": role["ai_training"],
        "stored_provider_origin_ai_search_get200": role["ai_search"],
        "stored_provider_origin_user_fetch_get200": role["user_initiated_fetch"],
        "stored_provider_origin_excluding_user_fetch_get200": by_paths - role["user_initiated_fetch"],
        "stored_network_claimed_ai_get200": network_ai,
        "heterogeneous_provider_plus_network_ai_get200": by_paths + network_ai,
        "_by_site_provider_origin_ai_get200": dict(sorted(by_site.items())),
    }


def daily_reconciliation(marginals: dict) -> list[dict]:
    totals = defaultdict(int)
    for row in marginals["daily"]:
        totals[row["date_utc"]] += row["all_requests"]
    rows = []
    for archive in marginals["archive_comparison"]:
        day = archive["date_utc"]
        rows.append({
            "date_utc": day,
            "daily_export_all_requests": totals.get(day),
            "archive_aggregate_count": archive["aggregate_count"],
            "archive_v3_count": archive["v3_count"],
            "report_d1_count": archive["d1_count"],
            "export_matches_archive_aggregate": totals.get(day) == archive["aggregate_count"],
            "aggregate_minus_v3": archive["aggregate_count"] - archive["v3_count"],
            "report_status": archive["report_status"],
            "reason_code": archive["reason_code"],
        })
    return rows


def compare(computed: dict, expected: dict) -> dict:
    lines = []
    for key in sorted(expected):
        value = computed.get(key)
        lines.append({"key": key, "expected": expected[key], "computed": value,
                      "status": "match" if value == expected[key] else "mismatch"})
    return {"all_match": all(line["status"] == "match" for line in lines), "lines": lines}
