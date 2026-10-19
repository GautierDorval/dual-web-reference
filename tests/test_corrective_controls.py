"""Adversarial synthetic tests of production controls; never evidence of a real leak."""
import copy
import tempfile
import unittest
from pathlib import Path
from tests import __init__
from dwr import disclosure, edition_rules, frozen, measurement, metrics, verify
from dwr.common import REPO_ROOT, DwrError, load_json, write_text

R1 = "2026-09-15_2026-10-15-r1"
R2 = "2026-09-15_2026-10-15-r2"


def synthetic():
    resources = [{"site_id": "example.invalid", "path": f"/document-{i}.md", "main_population": "true", "scope_class": "core_governance"} for i in range(10)]
    monthly = [{"site_id": r["site_id"], "path": r["path"], "actor_role": "user_initiated_fetch", "actor_name": "synthetic-agent", "stored_identity_tier": "provider_origin_verified_actor", "request_count": "1"} for r in resources]
    daily = [{"date_utc": "2026-09-20", "site_id": "example.invalid", "population": "main_documentary", "actor_role": "protected_strata", "stored_identity_tier": "protected_strata", "http_method": "ANY", "http_status": "ANY", "request_count": "10"}]
    return {**{k: [] for k in disclosure.TABLES}, "resources": resources, "consultations": monthly, "daily": daily}


def history(candidate, superseded=False):
    return {"status": "assessed", "releases": [{"edition_id": R1, "accessible": True, "superseded": superseded, "tables": copy.deepcopy(candidate)}]}


class CombinedDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.old = load_json(frozen.rule_path(R1, "small-cell-policy.json"))
        self.policy = load_json(REPO_ROOT / "config/small-cell-policy.json")

    def legacy(self, data):
        return verify.isolated_protected_daily_groups(data["consultations"], data["resources"], data["daily"], self.old)

    def test_B1_real_historical_function_passes_one_day_but_new_gate_blocks(self):
        candidate = synthetic()
        self.assertEqual(self.legacy(candidate), {"detailed_protected_rows": 0, "groups_below_minimum": []})
        self.assertEqual(sum(int(r["request_count"]) for r in candidate["consultations"]), 10)
        self.assertFalse(disclosure.assess(candidate, history(candidate), self.policy)["allowed"])
        coarse = disclosure.coarsen(candidate, self.policy)
        self.assertEqual(coarse["daily"], [])
        self.assertTrue(disclosure.assess(coarse, history(candidate), self.policy)["allowed"])
        self.assertEqual(candidate["daily"][0]["request_count"], "10")

    def test_B2_real_function_passes_both_revisions_but_changed_protected_delta_is_blocked(self):
        previous = synthetic()
        for r in previous["consultations"]:
            r["request_count"] = "20"
        previous["daily"][0]["request_count"] = "100"
        previous["daily"].append({**previous["daily"][0], "date_utc": "2026-09-21"})
        candidate = copy.deepcopy(previous)
        candidate["consultations"][3]["request_count"] = "21"
        candidate["daily"][1]["request_count"] = "101"
        self.assertEqual(self.legacy(previous), self.legacy(candidate))
        self.assertEqual(self.legacy(candidate)["groups_below_minimum"], [])
        for superseded in (False, True):
            result = disclosure.assess(disclosure.coarsen(candidate, self.policy), history(previous, superseded), self.policy)
            self.assertFalse(result["allowed"])
            self.assertIn("new_or_revised_protected_fine_cells_not_assessed", result["reasons"])

    def test_coverage_complement_is_removed_and_never_replaced_with_zero(self):
        candidate = synthetic()
        candidate["daily"] = []
        candidate["coverage"] = [{"date_utc": "2026-09-20", "aggregate_count": "12", "v3_count": "12", "aggregate_minus_v3": "0"}]
        self.assertFalse(disclosure.assess(candidate, history(candidate), self.policy)["allowed"])
        coarse = disclosure.coarsen(candidate, self.policy)
        self.assertTrue(all(coarse["coverage"][0][k] is None for k in disclosure.COVERAGE_COUNTS))
        self.assertTrue(disclosure.assess(coarse, history(candidate), self.policy)["allowed"])

    def test_missing_history_is_not_a_pass_and_unrecognized_surfaces_block(self):
        candidate = disclosure.coarsen(synthetic(), self.policy)
        self.assertEqual(disclosure.assess(candidate, {}, self.policy)["status"], "not_assessed")
        with self.assertRaises(DwrError):
            disclosure.enforce(candidate, {}, self.policy)
        candidate["unassessed_export"] = []
        self.assertFalse(disclosure.assess(candidate, history(candidate), self.policy)["allowed"])

    def test_network_predicate_is_protected_and_single_role_or_family_has_explicit_residual(self):
        self.assertTrue(disclosure.protected({"stored_identity_tier": "network_verified_claimed_actor"}, self.policy))
        candidate = synthetic()
        candidate["consultations"] = []
        candidate["daily"] = [{"date_utc":"2026-09-20", "population":"main_documentary", "http_method":"GET", "http_status":"200", "actor_role": "ai_training", "stored_identity_tier": "provider_origin_verified_actor", "request_count": "1"}]
        candidate["family_daily"] = [{"date_utc":"2026-09-20", "actor_role": "ai_training", "family": "one-resource", "request_count": "1"}]
        result = disclosure.assess(candidate, history(candidate), self.policy)
        self.assertTrue(result["allowed"])
        self.assertTrue(any("sole" in r for r in result["residual_cases"]))
        self.assertTrue(any("single-resource" in r for r in result["residual_cases"]))

    def test_actual_r2_passes_combined_gate_and_r1_is_frozen(self):
        self.assertTrue(frozen.verify(R1)["files"])
        result = disclosure.enforce(disclosure.tables(REPO_ROOT / "data/editions" / R2), disclosure.inventory(), self.policy)
        self.assertTrue(result["allowed"])
        with self.assertRaises(DwrError):
            frozen.refuse_write(R1)


class ReviewTests(unittest.TestCase):
    def approved(self, edition_id, digest):
        return {"edition_id": edition_id, "period_end_exclusive": edition_rules.parse_edition_id(edition_id)[1],
                "availability_status": "publicly_accessible", "reference_release_status": "approved", "approved_release_at": "2026-11-20",
                "review_status": {k: "approved" for k in ("technical", "editorial", "distribution")},
                "approval_receipt": {"edition_id": edition_id, "scope": "edition_payload_and_figures", "content_digest": digest,
                                     "reviewer": "synthetic-reviewer", "reviewed_at": "2026-11-20", "evidence": ["synthetic-test"],
                                     "decisions": {k: "approved" for k in ("technical", "editorial", "distribution")}}}

    def test_manifest_excludes_external_receipt_and_detects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(root / f"data/editions/{R1}/payload.json", "{}")
            write_text(root / f"figures/{R1}/test.svg", "<svg/>")
            digest = edition_rules.payload_manifest(R1, root)["digest"]
            entry = self.approved(R1, digest)
            getter = lambda eid: edition_rules.payload_manifest(eid, root)["digest"]
            self.assertTrue(edition_rules.approved(entry, getter))
            write_text(root / "config/editions.json", "external-state")
            self.assertTrue(edition_rules.approved(entry, getter))
            write_text(root / f"data/editions/{R1}/payload.json", '{"changed":true}')
            self.assertFalse(edition_rules.approved(entry, getter))

    def test_latest_unordered_candidate_and_invalid_receipt(self):
        digest = "a" * 64
        one, two = self.approved(R1, digest), self.approved(R2, digest)
        two["supersedes"] = R1
        candidate = {"edition_id": "2026-10-15_2026-11-15-r1", "status": "published", "published_at": "2026-12-01", "reviewed": True}
        self.assertEqual(edition_rules.latest_pointer([two, candidate, one], lambda _: digest), R2)
        two["approval_receipt"]["content_digest"] = "b" * 64
        self.assertEqual(edition_rules.latest_pointer([candidate, two, one], lambda _: digest), R1)
        self.assertIsNone(edition_rules.latest_pointer([candidate], lambda _: digest))

    def test_missing_comparability_is_not_equality_evidence(self):
        self.assertFalse(edition_rules.comparable({}, {})[0])
        base = {k: "same" for k in edition_rules.COMPARABILITY_KEYS}
        base.update(coverage_status="complete_declared", period_start_inclusive="2026-09-15", period_end_exclusive="2026-10-15")
        self.assertTrue(edition_rules.comparable(base, dict(base))[0])
        self.assertFalse(edition_rules.comparable(base, {**base, "scope_registry_sha256": "changed"})[0])
        self.assertFalse(edition_rules.comparable(base, {**base, "period_start_inclusive": "2026-10-15", "period_end_exclusive": "2026-11-15"})[0])


class MeasurementTests(unittest.TestCase):
    def test_two_versions_separable_and_unresolved_day_without_defaults(self):
        epochs = [{"classifier_version": version, "attribution_rules": "synthetic-rules", "deployment_evidence": "synthetic-receipt"} for version in ("test-v1", "test-v2")]
        provenance = {"days": {"2026-10-18": {"separable": True, "epochs": epochs}, "2026-10-19": {"separable": False, "epochs": epochs}}}
        rows = [{"date_utc": "2026-10-18", "classifier_version": version, "request_count": n} for version, n in (("test-v1", 3), ("test-v2", 7))]
        rows.append({"date_utc": "2026-10-19", "request_count": 11})
        days = [{"date_utc": day, "archive_status": "archived", "report_status": status} for day, status in (("2026-10-18", "complete"), ("2026-10-19", "partial"))]
        days.append({"date_utc": "2026-10-20", "archive_status": "unavailable"})
        result = measurement.qualify(rows, days, provenance)
        self.assertEqual(sum(r["request_count"] for r in result["rows"]), 21)
        self.assertEqual(result["rows"][-1]["measurement_epoch_id"], "mixed_epoch_unresolved")
        self.assertEqual(result["days"]["2026-10-18"]["coverage_status"], "complete_declared")
        self.assertEqual(result["days"]["2026-10-20"]["coverage_status"], "observation_unavailable")
        self.assertEqual(result["coverage_status"], "mixed_coverage")
        self.assertEqual(measurement.epoch({"date_utc": "2026-11-01"}, {})["measurement_epoch_id"], "unknown")
        self.assertNotIn("classifier-2026-08-24.1", result["epochs"])


class CorrectedMetricsTests(unittest.TestCase):
    def test_actual_metrics_preserve_observations_and_add_exact_denominators(self):
        actual = {m["metric_id"]: m for m in metrics.compute(REPO_ROOT / "data/editions" / R2)["metrics"]}
        expected = {"main.get200":245, "main.site_path_pairs":174, "main.llms_get200":6, "main.other_get200":239,
                    "main.recorded_pairs":269, "main.llms_recorded_pairs":3, "main.other_recorded_pairs":266,
                    "main.failed_origin_selected.get200":17, "main.automated.top3_days_get200":185,
                    "main.daily.sum_check":230, "main.daily.days_with_requests":12,
                    "main.recurrence.pairs_with_1_days":133, "extended.get200":356, "historical.provider_ai.get200":372}
        for key, value in expected.items():
            self.assertEqual(actual[key]["value"], value, key)
        self.assertEqual(actual["main.failed_origin_selected.share"]["denominator"], 262)
        self.assertEqual(actual["main.conditional_pair_share"]["denominator"], 269)
        self.assertIsNone(actual["coverage.aggregate_sum"]["value"])
        self.assertEqual(actual["coverage.aggregate_sum"]["status"], "withheld")
        for actor,count in (("GPTBot",200),("OAI-SearchBot",14),("PerplexityBot",16),("ChatGPT-User",15)):
            self.assertEqual(actual[f"main.actor_name.{actor}.get200"]["value"],count)

    def test_ratios_distinguish_zero_denominator_missing_source_and_measured_zero(self):
        self.assertEqual(metrics.share("x", 0, 4)["value"], 0)
        self.assertIsNone(metrics.share("x", 1, 0)["value"])
        self.assertEqual(metrics.share("x", None, 4)["reason"], "source_unavailable")
        self.assertEqual(metrics.share("x", 1, 0)["reason"], "denominator_zero")
