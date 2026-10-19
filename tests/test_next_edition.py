"""Synthetic next-edition rehearsal through the actual project/metrics/figure code."""
import tempfile
import unittest
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tests import __init__
from dwr import dates, joint, maintenance, qualify
from dwr.common import REPO_ROOT, SITE_IDS, load_json, write_json, sha256_file


def prepare_inputs(private, *, protected=False):
    window = dates.window_from_strings("2026-10-15", "2026-11-15")
    eid = window.edition_id(1)
    rows, days, provenance = [], [], {"days": {}}
    for index, day in enumerate(window.dates()):
        stamp = day.isoformat()
        versions = ["synthetic-old"] if index < 15 else ["synthetic-new"]
        if index in (2, 3): versions = ["synthetic-old", "synthetic-new"]
        provenance["days"][stamp] = {"separable": index != 2, "epochs": [
            {"classifier_version": v, "attribution_rules": "synthetic-attribution-"+v,
             "deployment_evidence": "synthetic-fixture-only", "epoch_id": v} for v in versions]}
        if index != 4:
            for version in (versions if index == 3 else [versions[0]]):
                rows.append({"date_utc": stamp, "site_id": SITE_IDS[index % 3], "path": "/llms.txt",
                    "producer_category": "llms", "http_method": "GET", "http_status": 200,
                    "actor_family": "synthetic", "actor_name": "SyntheticAgent", "actor_role": "user_initiated_fetch" if protected else "ai_training",
                    "stored_identity_tier": "provider_origin_verified_actor", "request_count": 1 + index % 3,
                    **({"classifier_version": version} if index != 2 else {})})
        count = sum(r["request_count"] for r in rows if r["date_utc"] == stamp)
        days.append({"date_utc":stamp, "archive_status":"unavailable" if index == 4 else "archived",
                     "report_status":"partial" if index == 1 else "complete", "aggregate_count":None if index == 4 else count,
                     "v3_count":None if index == 4 else count, "snapshots":0 if index == 4 else 1,
                     "governance_reason_code":"synthetic_fixture"})
    counts = joint.path_counts(rows)
    registry = qualify.load_registry()
    resources = [{**registry[(site,"/llms.txt")], "site_id":site, "path":"/llms.txt", "resource_id":qualify.resource_id(site,"/llms.txt"),
                  "url":"https://"+site+"/llms.txt", "main_population":True, "llms_txt":True, "counts":counts.get((site,"/llms.txt")),
                  "window_rows_status":"rows_in_window", "producer_category":"llms", "historical_version_status":"synthetic_fixture"} for site in SITE_IDS]
    daily = defaultdict(int)
    for row in rows: daily[row["date_utc"]] += row["request_count"]
    normalized = {"edition_id":eid, "nature":"synthetic_only_not_observed_traffic", "source_mode":"joint_acquisition",
                  "joint_rows":rows, "joint_acquisition":"acq-synthetic", "archive_inventory":{"days":days},
                  "measurement_provenance":provenance, "joint_extracted_at":{"start":"2026-11-17T00:00:00Z","end":"2026-11-17T00:00:01Z"},
                  "marginals":{"daily":[{"date_utc":d,"all_requests":n} for d,n in daily.items()]}}
    qualified = {"edition_id":eid, "resources":resources, "attribution":load_json(REPO_ROOT/"config/attribution-rules.json"),
                 "graphs":{site:{"status":"unavailable", "relations":[], "repositories":[], "snapshot_digest":"synthetic"} for site in SITE_IDS}}
    target=private/"working"/eid
    write_json(target/"normalized.json",normalized);write_json(target/"qualified.json",qualified)
    return eid


class ManualPreparationTests(unittest.TestCase):
    def test_full_next_window_rehearsal_idempotence_epochs_and_unavailable_day(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp);eid=prepare_inputs(private)
            before={p:sha256_file(REPO_ROOT/p) for p in ("data/status.json","data/latest.json","config/editions.json")}
            first=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(first["outcome"],"awaiting_review",first)
            target=private/"preparation/candidates"/eid
            report=load_json(target/"measurement-report.json")
            self.assertEqual(report["days"]["2026-10-17"]["epochs"],["mixed_epoch_unresolved"])
            self.assertEqual(len(report["days"]["2026-10-18"]["epochs"]),2)
            self.assertEqual(report["days"]["2026-10-19"]["coverage_status"],"observation_unavailable")
            self.assertFalse(report["days"]["2026-10-19"]["attribution_comparable"])
            from dwr.common import read_csv
            unavailable=[r for r in read_csv(target/"payload/daily-family-summary.csv") if r["date_utc"]=="2026-10-19"]
            self.assertTrue(unavailable)
            self.assertTrue(all(r["request_count"]=="" and r["observation_status"]=="observation_unavailable" for r in unavailable))

            self.assertEqual(len(list((target/"figures").glob("*.svg"))),48)
            second=maintenance.prepare(private,datetime(2026,11,18,tzinfo=timezone.utc))
            self.assertEqual(second["outcome"],"unchanged",second)
            self.assertEqual(load_json(private/"preparation/status.json")["latest_available_data_date"],"2026-11-14")
            self.assertEqual(before,{p:sha256_file(REPO_ROOT/p) for p in before})
            self.assertIsNone(load_json(target/"delta-report.json")["growth"])

    def test_no_skipped_window_no_freshness_on_unavailable_and_consolidation_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)
            before=maintenance.prepare(private,datetime(2026,11,16,23,59,59,tzinfo=timezone.utc))
            self.assertEqual(before["outcome"],"unchanged")
            failed=maintenance.prepare(private,datetime(2027,2,1,tzinfo=timezone.utc))
            self.assertEqual(failed["outcome"],"source_unavailable")
            self.assertEqual(failed["edition_id"],"2026-10-15_2026-11-15-r1")
            state=load_json(private/"preparation/status.json")
            self.assertEqual(state["latest_available_data_date"],"2026-10-14")
            self.assertFalse(state["planning_activated"])

    def test_new_protected_cells_remain_private_with_blocked_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp);prepare_inputs(private,protected=True)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["outcome"],"awaiting_review",result)
            self.assertEqual(result["distribution_status"],"not_assessed")
            self.assertFalse(result["public_mutation"])

    def test_invalid_sources_fail_without_a_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp);eid=prepare_inputs(private)
            p=private/"working"/eid/"normalized.json";n=load_json(p)
            n["joint_rows"][0]["request_count"]=-1;write_json(p,n)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["outcome"],"validation_failed")
            self.assertFalse((private/"preparation/candidates"/eid).exists())
