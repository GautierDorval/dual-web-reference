import unittest

from tests import __init__  # noqa: F401
from dwr import project, reconcile
from dwr.common import DwrError, load_json, REPO_ROOT

PROVIDER = "provider_origin_verified_actor"


def file_row(site, path, requests, get200, head=0, n304=0, errors=0, provider=0, category="x"):
    return {"site_id": site, "path": path, "producer_category": category, "requests": requests, "get200": get200,
            "head": head, "not_modified": n304, "errors": errors, "days": 1, "get200_days": 1, "provider_ai_get200": provider}


def actor(site, name, role, tier, get200, requests=None):
    return {"site_id": site, "actor_name": name, "actor_role": role, "stored_identity_tier": tier,
            "requests": requests if requests is not None else get200, "get200": get200, "paths": 1, "days": 1}


def marginals():
    files = [
        file_row("pagup.com", "/llms.txt", 4, 3, head=1, provider=1),
        file_row("pagup.com", "/identity.json", 5, 4, n304=1, provider=2),
        file_row("pagup.com", "/robots.txt", 9, 9, provider=7),
        file_row("pagup.com", "/.well-known/__undeclared__", 3, 0, errors=3, category="well-known-probe"),
        file_row("better-robots.com", "/identity.json", 2, 1, errors=1, provider=1),
    ]
    actors = [actor("pagup.com", "GPTBot", "ai_training", PROVIDER, 2), actor("pagup.com", "ChatGPT-User", "user_initiated_fetch", PROVIDER, 1),
              actor("better-robots.com", "PerplexityBot", "ai_search", PROVIDER, 1),
              actor("pagup.com", "unknown", "unknown", "cloudflare_verified_unattributed", 4),
              actor("pagup.com", "ClaudeBot", "ai_training", "network_verified_claimed_actor", 1)]
    http = [{"site_id": "pagup.com", "http_method": "GET", "http_status": 200, "requests": 7},
            {"site_id": "pagup.com", "http_method": "HEAD", "http_status": 200, "requests": 1},
            {"site_id": "pagup.com", "http_method": "GET", "http_status": 304, "requests": 1},
            {"site_id": "better-robots.com", "http_method": "GET", "http_status": 200, "requests": 1},
            {"site_id": "better-robots.com", "http_method": "GET", "http_status": 404, "requests": 1}]
    return {"files": files, "actors": actors, "http": http, "daily": [], "archive_comparison": []}


class HistoricalFigureTests(unittest.TestCase):
    def test_robots_and_probes_are_outside_the_historical_scope(self):
        figures = reconcile.historical_figures(marginals())
        self.assertEqual(figures["governance_requests"], 11)
        self.assertEqual(figures["stored_provider_origin_ai_get200"], 4)
        self.assertEqual(figures["stored_provider_origin_ai_llms_get200"], 1)
        self.assertEqual(figures["stored_provider_origin_ai_other_get200"], 3)
        # Pairs are counted on site-path pairs: /identity.json on two sites is two pairs.
        self.assertEqual(figures["stored_provider_origin_ai_site_path_pairs"], 3)
        self.assertEqual(figures["stored_provider_origin_ai_other_site_path_pairs"], 2)
        self.assertEqual(figures["stored_cloudflare_unattributed_get200"], 4)
        self.assertEqual(figures["stored_network_claimed_ai_get200"], 1)
        self.assertEqual(figures["stored_provider_origin_excluding_user_fetch_get200"], 3)

    def test_disagreeing_marginals_stop_the_computation(self):
        data = marginals()
        data["actors"][0]["get200"] = 5
        with self.assertRaises(DwrError):
            reconcile.historical_figures(data)


class MethodStatusDeductionTests(unittest.TestCase):
    def test_split_deduced_only_when_no_other_combination_has_mass(self):
        result = project.deduce_method_status(marginals())
        self.assertTrue(result["pagup.com"])
        # better-robots.com has a GET 404: its errors are not known to be POST 405.
        self.assertFalse(result["better-robots.com"])
        self.assertTrue(result["gautierdorval.com"])  # no rows at all: vacuously consistent, nothing is split


class AttributionRuleTests(unittest.TestCase):
    def test_unknown_and_under_review_levels_never_become_main_population(self):
        rules = load_json(REPO_ROOT / "config" / "attribution-rules.json")["assessments"]
        eligible = {tier for tier, spec in rules.items() if spec["eligible_for_main_population"]}
        self.assertEqual(eligible, {PROVIDER})
        for tier in ("cloudflare_verified_unattributed", "network_verified_claimed_actor"):
            self.assertTrue(rules[tier]["depends_on_cloudflare_predicate"])
            self.assertEqual(rules[tier]["attribution_assessment"], "recorded_classification_reliability_under_review")
        self.assertFalse(rules[PROVIDER]["depends_on_cloudflare_predicate"])

    def test_initiation_is_never_inferred_from_role_or_provider(self):
        rules = load_json(REPO_ROOT / "config" / "attribution-rules.json")
        self.assertEqual(rules["initiation_provenance"]["default"], "unknown")
        self.assertIn("never inferred", rules["initiation_provenance"]["rule"])


class ScopeRuleTests(unittest.TestCase):
    def test_main_population_classes_and_mechanical_rules(self):
        rules = load_json(REPO_ROOT / "config" / "scope-rules.json")
        main = {name for name, spec in rules["classes"].items() if spec["main_population"]}
        self.assertEqual(main, {"core_governance", "discovery_index"})
        self.assertEqual(rules["missing_registry_entry"], "fail")
        self.assertTrue(rules["llms_txt"]["isolated"])

    def test_registry_keeps_control_bucket_and_descriptors_separate(self):
        from dwr.common import read_csv
        rows = read_csv(REPO_ROOT / "config" / "scope-registry.csv")
        for row in rows:
            if row["path"] == "/robots.txt":
                self.assertEqual(row["scope_class"], "control_resource")
            if row["path"] == "/.well-known/__undeclared__":
                self.assertEqual(row["scope_class"], "undeclared_bucket")
            if row["path"] == "/llms.txt":
                self.assertEqual(row["scope_class"], "discovery_index")
        runtime_named = [r for r in rows if "runtime" in r["path"] or "mcp" in r["path"]]
        self.assertTrue(runtime_named)
        self.assertTrue(all(r["scope_class"] in ("operational_descriptor", "supporting_documentation") for r in runtime_named),
                        [r["path"] for r in runtime_named if r["scope_class"] not in ("operational_descriptor", "supporting_documentation")])


if __name__ == "__main__":
    unittest.main()
