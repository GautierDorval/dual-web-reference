import tempfile
import unittest
from pathlib import Path

from tests import __init__  # noqa: F401
from dwr import metrics, project, verify
from dwr.common import csv_text

PROVIDER = "provider_origin_verified_actor"


def write(directory: Path, name: str, fields, rows):
    (directory / name).write_text(csv_text(fields, rows), encoding="utf-8", newline="\n")


def cell(rid, site, path, role, tier, n, method="GET", status="200", name="GPTBot"):
    return {"resource_id": rid, "site_id": site, "path": path, "http_method": method, "http_status": status,
            "actor_family": "openai", "actor_name": name, "actor_role": role, "stored_identity_tier": tier,
            "request_count": n}


def build_edition(directory: Path, *, resources, cells, days, scope_rows=()):
    (directory / "catalog.json").write_text('{"metrics_version":"dwr-metrics/1.0.0"}', encoding="utf-8")
    write(directory, "resources.csv", ["resource_id", "site_id", "path", "scope_class", "main_population", "llms_txt",
                                       "window_rows_status"],
          [{"resource_id": rid, "site_id": site, "path": path, "scope_class": scope, "main_population": main,
            "llms_txt": path == "/llms.txt", "window_rows_status": "rows_in_window"}
           for rid, site, path, scope, main in resources])
    write(directory, "consultations.csv", ["resource_id", "site_id", "path", "http_method", "http_status", "actor_family",
                                           "actor_name", "actor_role", "stored_identity_tier", "request_count"], cells)
    write(directory, "resource-summary.csv", ["resource_id", "provider_origin_ai_get200_days"],
          [{"resource_id": rid, "provider_origin_ai_get200_days": days.get(rid, 0)} for rid, *_ in resources])
    daily = [{"date_utc": "2026-10-01", "site_id": c["site_id"], "population": "main_documentary",
              "actor_role": c["actor_role"], "stored_identity_tier": c["stored_identity_tier"],
              "http_method": c["http_method"], "http_status": c["http_status"], "request_count": c["request_count"]}
             for c in cells if dict((r[0], r[4]) for r in resources)[c["resource_id"]]]
    write(directory, "daily-summary.csv", ["date_utc", "site_id", "population", "actor_role", "stored_identity_tier",
                                           "http_method", "http_status", "request_count"], daily)
    write(directory, "coverage.csv", ["date_utc", "observation_status", "coverage_status", "archive_reason_code",
                                      "aggregate_minus_v3", "aggregate_count", "v3_count", "joint_matches_archive"],
          [{"date_utc": "2026-10-01", "observation_status": "observed", "coverage_status": "partial_declared",
            "archive_reason_code": "COLLECTOR_WINDOW_ATTESTATION_MISSING", "aggregate_minus_v3": 0,
            "aggregate_count": 3, "v3_count": 3, "joint_matches_archive": True}])
    write(directory, "exclusions.csv", ["dimension", "exclusion_id", "excluded_value", "requests_all_actors",
                                        "provider_origin_ai_get200"], list(scope_rows))


class MetricTests(unittest.TestCase):
    def test_share_pairs_roles_and_non_get200_never_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            build_edition(directory, resources=[
                ("pg:/llms.txt", "pagup.com", "/llms.txt", "discovery_index", True),
                ("pg:/a.json", "pagup.com", "/a.json", "core_governance", True),
                ("br:/a.json", "better-robots.com", "/a.json", "core_governance", True),
            ], cells=[
                cell("pg:/llms.txt", "pagup.com", "/llms.txt", "ai_training", PROVIDER, 1),
                cell("pg:/a.json", "pagup.com", "/a.json", "ai_search", PROVIDER, 2, name="OAI-SearchBot"),
                cell("pg:/a.json", "pagup.com", "/a.json", "ai_training", PROVIDER, 9, method="HEAD"),
                cell("pg:/a.json", "pagup.com", "/a.json", "ai_training", PROVIDER, 4, status="304"),
                cell("br:/a.json", "better-robots.com", "/a.json", "user_initiated_fetch", PROVIDER, 3, name="ChatGPT-User"),
                cell("br:/a.json", "better-robots.com", "/a.json", "unknown", "cloudflare_verified_unattributed", 50, name="unknown"),
                cell("br:/a.json", "better-robots.com", "/a.json", "ai_training", "network_verified_claimed_actor", 7, name="ClaudeBot"),
            ], days={"pg:/llms.txt": 1, "pg:/a.json": 2, "br:/a.json": 5})
            result = {m["metric_id"]: m for m in metrics.compute(directory)["metrics"]}
            self.assertEqual(result["main.get200"]["value"], 6)
            self.assertEqual(result["main.llms_get200"]["value"], 1)
            self.assertEqual(result["main.other_get200"]["value"], 5)
            self.assertAlmostEqual(result["main.other_share"]["value"], 5 / 6, places=6)
            self.assertEqual(result["main.site_path_pairs"]["value"], 3)
            self.assertEqual(result["main.role.ai_training.get200"]["value"], 1)
            self.assertEqual(result["main.role.ai_search.get200"]["value"], 2)
            self.assertEqual(result["main.role.user_initiated_fetch.get200"]["value"], 3)
            self.assertEqual(result["main.sensitivity.without_user_fetch.get200"]["value"], 3)
            self.assertEqual(result["main.sensitivity.without_user_fetch.site_path_pairs"]["value"], 2)
            self.assertEqual(result["main.recurrence.pairs_with_1_days"]["value"], 1)
            self.assertEqual(result["main.recurrence.pairs_with_2_to_3_days"]["value"], 1)
            self.assertEqual(result["main.recurrence.pairs_with_4_to_7_days"]["value"], 1)
            # Daily series carry automated roles only: the user-initiated fetch stays at edition level.
            self.assertEqual(result["main.daily.sum_check"]["value"], 3)
            # Unknown and network-claimed labels are counted in their own tiers, never as provider origin.
            self.assertEqual(result["main_population.tier.cloudflare_verified_unattributed.get200"]["value"], 50)
            self.assertEqual(result["main_population.tier.network_verified_claimed_actor.get200"]["value"], 7)

    def test_zero_denominator_is_not_calculable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            build_edition(directory, resources=[("pg:/llms.txt", "pagup.com", "/llms.txt", "discovery_index", True)],
                          cells=[cell("pg:/llms.txt", "pagup.com", "/llms.txt", "unknown", "unknown_automation", 4, name="unknown")],
                          days={})
            result = {m["metric_id"]: m for m in metrics.compute(directory)["metrics"]}
            self.assertEqual(result["main.get200"]["value"], 0)
            self.assertEqual(result["main.other_share"]["status"], "not_calculable")
            self.assertIsNone(result["main.other_share"]["value"])
            self.assertEqual(result["main.site.pagup.com.other_share"]["status"], "not_calculable")

    def test_scope_exclusion_is_itemized_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            build_edition(directory, resources=[
                ("pg:/a.json", "pagup.com", "/a.json", "core_governance", True),
                ("pg:/mcp.json", "pagup.com", "/mcp.json", "operational_descriptor", False),
            ], cells=[cell("pg:/a.json", "pagup.com", "/a.json", "ai_training", PROVIDER, 4),
                      cell("pg:/mcp.json", "pagup.com", "/mcp.json", "ai_training", PROVIDER, 2)],
                days={"pg:/a.json": 1, "pg:/mcp.json": 1},
                scope_rows=[{"dimension": "scope", "exclusion_id": "scope:operational_descriptor",
                             "excluded_value": "operational_descriptor", "requests_all_actors": 2, "provider_origin_ai_get200": 2}])
            result = {m["metric_id"]: m for m in metrics.compute(directory)["metrics"]}
            self.assertEqual(result["main.get200"]["value"], 4)
            self.assertEqual(result["historical.provider_ai.get200"]["value"], 6)
            self.assertEqual(result["main.scope_delta.provider_ai_get200_excluded"]["value"], 2)
            self.assertEqual(result["scope_delta.operational_descriptor.provider_ai_get200"]["value"], 2)


class ProjectionRuleTests(unittest.TestCase):
    def test_population_and_deployment_labels(self):
        self.assertEqual(project.population_of({"main_population": True, "scope_class": "core_governance"}), "main_documentary")
        self.assertEqual(project.population_of({"main_population": False, "scope_class": "control_resource"}), "robots_control")
        self.assertEqual(project.population_of({"main_population": False, "scope_class": "supporting_documentation"}), "other_documentary")
        labels = [{"label": "pd01", "effective_at": "2026-09-13T17:18:49Z"}, {"label": "pd02", "effective_at": "2026-10-02T10:00:00Z"}]
        self.assertEqual(project.label_for_day(labels, "2026-09-12"), None)
        self.assertEqual(project.label_for_day(labels, "2026-09-20"), "pd01")
        self.assertEqual(project.label_for_day(labels, "2026-10-02"), "pd01+pd02")
        self.assertEqual(project.label_for_day(labels, "2026-10-03"), "pd02")

    def test_protected_strata_are_combined_in_the_daily_grain(self):
        protected = project.protected_strata()
        combined = ("2026-10-01", "br", "main_documentary", project.PROTECTED_GROUP, project.PROTECTED_GROUP,
                    project.ANY, project.ANY)
        self.assertEqual(project.daily_key("2026-10-01", "br", "main_documentary", "user_initiated_fetch", PROVIDER,
                                           "GET", 200, protected), combined)
        self.assertEqual(project.daily_key("2026-10-01", "br", "main_documentary", "unknown",
                                           "cloudflare_verified_unattributed", "POST", 405, protected), combined)
        self.assertEqual(project.daily_key("2026-10-01", "br", "main_documentary", "ai_training", PROVIDER, "GET", 200,
                                           protected),
                         ("2026-10-01", "br", "main_documentary", "ai_training", PROVIDER, "GET", "200"))

    def test_crossing_check_flags_a_protected_daily_row_that_isolates_one_path(self):
        # Regression for the candidate r1 finding: one user-initiated fetch to one path, published per day,
        # gave away the day of that request once crossed with consultations.csv.
        policy = {"protected_strata": {"actor_roles": ["user_initiated_fetch"], "stored_identity_tiers": ["unknown_automation"]},
                  "daily_protected_group": {"label": "protected_strata", "any": "ANY", "minimum_paths": 3,
                                            "single_path_populations": ["robots_control"]}}
        resources = [{"site_id": "br", "path": f"/d{i}.md", "main_population": "true", "scope_class": "core_governance"}
                     for i in range(3)] + [{"site_id": "br", "path": "/robots.txt", "main_population": "false",
                                            "scope_class": "control_resource"}]
        fetch = cell("r0", "br", "/d0.md", "user_initiated_fetch", PROVIDER, "1")
        detailed = [{"site_id": "br", "population": "main_documentary", "actor_role": "user_initiated_fetch",
                     "stored_identity_tier": PROVIDER, "http_method": "GET", "http_status": "200", "request_count": "1"}]
        found = verify.isolated_protected_daily_groups([fetch], resources, detailed, policy)
        self.assertEqual(found["detailed_protected_rows"], 1)
        combined = [dict(detailed[0], actor_role="protected_strata", stored_identity_tier="protected_strata",
                         http_method="ANY", http_status="ANY")]
        found = verify.isolated_protected_daily_groups([fetch], resources, combined, policy)
        self.assertEqual(found, {"detailed_protected_rows": 0, "groups_below_minimum": [("br", "main_documentary", 1)]})
        spread = [cell(f"r{i}", "br", f"/d{i}.md", "unknown", "unknown_automation", "5") for i in range(3)] + [fetch]
        self.assertEqual(verify.isolated_protected_daily_groups(spread, resources, combined, policy),
                         {"detailed_protected_rows": 0, "groups_below_minimum": []})
        robots = [cell("rr", "br", "/robots.txt", "unknown", "unknown_automation", "9")]
        self.assertEqual(verify.isolated_protected_daily_groups(robots, resources, [dict(combined[0], population="robots_control")],
                                                                policy)["groups_below_minimum"], [])
        malformed = [dict(combined[0], http_method="GET")]
        self.assertEqual(verify.isolated_protected_daily_groups(spread, resources, malformed, policy)["detailed_protected_rows"], 1)


if __name__ == "__main__":
    unittest.main()
