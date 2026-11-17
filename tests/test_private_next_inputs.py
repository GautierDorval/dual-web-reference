"""Synthetic source receipts exercise the real private next-window pipeline offline."""
import copy
import csv
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tests import __init__
from dwr import acquire, archive, dates, joint, maintenance, next_inputs
from dwr.common import DwrError, REPO_ROOT, SITE_IDS, load_json, sha256_file, write_json, write_text

NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)
GAPS = {"2026-10-16", "2026-10-22", "2026-11-02", "2026-11-07"}


class PrivateNextInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name)
        self.period = dates.window_from_strings("2026-10-15", "2026-11-15")
        self.eid = self.period.edition_id(1)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE governance_daily_rollups(event_date TEXT,domain TEXT,path TEXT,category TEXT,
            method TEXT,status INTEGER,actor_family TEXT,actor_name TEXT,actor_type TEXT,confidence TEXT,hits INTEGER);
          CREATE TABLE governance_artifact_registry(domain TEXT,path TEXT,category TEXT,expected INTEGER,first_seen TEXT);
          CREATE TABLE ai_actor_classifier_versions(version TEXT,rules_sha256 TEXT);
          CREATE TABLE deployment_history_evidence(observed_at TEXT,first_deployed_at TEXT,history_json TEXT);
        """)
        for index, day in enumerate(self.period.dates()):
            for site in SITE_IDS:
                for path, category, method, status, role, tier, count in [
                    ("/llms.txt", "llms", "GET", 200, "ai_training", "provider_origin_verified_actor", index + 1),
                    ("/llms.txt", "llms", "POST", 200, "generic_automation", "unknown_automation", 2),
                    ("/llms.txt", "llms", "GET", 404, "generic_automation", "unknown_automation", 3),
                    ("/robots.txt", "robots", "HEAD", 403, "generic_automation", "unknown_automation", 1),
                ]:
                    self.db.execute("INSERT INTO governance_daily_rollups VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                    (str(day), site, path, category, method, status, "Synthetic", "SyntheticAgent", role, tier, count))
        for site in SITE_IDS:
            self.db.execute("INSERT INTO governance_artifact_registry VALUES (?,?,?,?,?)",
                            (site, "/llms.txt", "llms", 1, "2026-09-01"))
        self.db.execute("INSERT INTO ai_actor_classifier_versions VALUES (?,?)", ("synthetic-old", "a" * 64))
        self.db.execute("INSERT INTO deployment_history_evidence VALUES (?,?,?)",
                        ("2026-10-18T20:00:00Z", "2026-10-18T19:00:00Z", '{"deployments":[]}'))
        write_json(self.private / "lock/acquisition-config.json",
                   {"database_name": "synthetic-only", "account_id": "synthetic", "client_dir": str(self.private)})
        source = {"archive": {"repository": "synthetic/archive", "tables_directory": "sources/archive", "commit": "a" * 40},
                  "graph_serving_repositories": {}, "measurement_provenance": {"days": {
                      "2026-10-18": {"separable": False, "epochs": [
                          {"classifier_version": "synthetic-old"}, {"classifier_version": "synthetic-new"}]}}}}
        write_json(self.private / "lock/sources-config.json", source)
        self.make_archive()

    def client(self, config, sql):
        self.assertTrue(sql.startswith("SELECT "))
        self.assertNotIn(";", sql)
        before = self.db.total_changes
        rows = [dict(r) for r in self.db.execute(sql)]
        return rows, {"rows_read": len(rows), "rows_written": self.db.total_changes - before,
                      "changed_db": False}, 0.0

    def capture(self):
        with patch.object(acquire, "_run_client", side_effect=self.client), patch.object(acquire, "client_version", return_value="synthetic"):
            return next_inputs.acquire_next(self.private, execute=True,
                                           confirm_scope="2026-10-15..2026-11-15", now=NOW)

    def make_archive(self):
        tables = {name: [] for name in archive.TABLES}
        for day in self.period.dates():
            stamp = str(day)
            if stamp in GAPS:
                continue
            sid = "synthetic-" + stamp
            count = self.db.execute("SELECT SUM(hits) FROM governance_daily_rollups WHERE event_date=?", (stamp,)).fetchone()[0]
            tables["reports"].append({"snapshot_id": sid, "source_id": "governance-visibility", "report_date": stamp,
                                      "is_current": "true", "captured_at": stamp + "T12:00:00Z", "report_status": "partial",
                                      "reason_code": "synthetic-partial", "source_commit": "a" * 40})
            tables["governance_daily"].append({"snapshot_id": sid, "report_date": stamp, "aggregate_count": count,
                                               "v3_count": count - (stamp == "2026-10-18"), "reason_code": "synthetic-partial",
                                               "proof_status": "partial"})
            tables["windows"].append({"snapshot_id": sid, "report_date": stamp, "kind": "coverage", "window_index": 0,
                                       "start": stamp + "T00:00:00Z", "end_exclusive": stamp + "T23:59:59Z", "source": "synthetic"})
            for site in SITE_IDS:
                tables["site_counts"].append({"snapshot_id": sid, "report_date": stamp, "site": site, "count": count // 3})
        files = []
        folder = self.private / "sources/archive"
        for month in ("2026-10", "2026-11"):
            for name, rows in tables.items():
                path = folder / f"tables/{month}/{name}.csv"
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(r for r in rows if r["report_date"].startswith(month))
                files.append({"path": path.relative_to(folder).as_posix(), "byte_length": path.stat().st_size,
                              "sha256": sha256_file(path)})
        write_json(folder / "manifest.json", {"repository": "synthetic/archive", "commit": "a" * 40, "files": files})

    def test_actual_sql_acquire_normalize_qualify_and_private_candidate(self):
        protected = ["config/editions.json", "data/status.json", "data/latest.json"]
        before = {name: sha256_file(REPO_ROOT / name) for name in protected}
        log = self.capture()
        self.assertEqual(len(log["queries"]), 42)
        result = next_inputs.normalize(self.private)
        self.assertEqual(result["unavailable_archive_days"], 4)
        self.assertTrue(result["cross_checks"]["all_consistent"])
        next_inputs.qualify_next(self.private)
        # The real writer must preserve gaps and unresolved epochs, never force rows onto an unavailable day.
        prepared = maintenance.prepare(self.private, NOW)
        self.assertEqual(prepared["preparation_status"], "complete_private", prepared)
        candidate = self.private / "preparation/candidates" / self.eid
        exclusions = load_json(candidate / "source-exclusions.private.json")
        self.assertEqual(set(exclusions["dates"]), GAPS)
        measured = load_json(candidate / "measurement-report.json")
        self.assertEqual(measured["days"]["2026-10-18"]["epoch_resolution"], "mixed_epoch_unresolved")
        for stamp in GAPS:
            self.assertEqual(measured["days"][stamp]["coverage_status"], "observation_unavailable")
        self.assertFalse(load_json(candidate / "delta-report.json")["comparable"])
        figures = load_json(candidate / "payload/figures.json")["figures"]
        self.assertTrue(all(f["status"] == "not_available" for f in figures if f["figure_id"].startswith("G09-")))
        for lang, expected in (("en", "Documentary graph unavailable"), ("fr", "Graphe documentaire indisponible")):
            image = (candidate / f"figures/G09-pagup.com.{lang}.compact.svg").read_text(encoding="utf-8")
            self.assertIn(expected, image)
            self.assertNotIn("snapshot None", image)
            self.assertIn("UTC", image)
            self.assertIn("catalog.json", image)
        link_file = next(f for f in load_json(candidate / "payload/catalog.json")["files"] if f["path"] == "links.csv")
        self.assertEqual(link_file["empty_reason"], "source_snapshot_unavailable")
        self.assertEqual(before, {name: sha256_file(REPO_ROOT / name) for name in protected})
        self.assertEqual(next_inputs.normalize(self.private)["rows"], result["rows"])
        self.assertEqual(maintenance.prepare(self.private, NOW)["outcome"], "unchanged")

    def test_consolidation_and_exact_scope_stop_before_any_source_read(self):
        with patch.object(acquire, "_run_client") as runner:
            with self.assertRaisesRegex(DwrError, "next_window_not_consolidated"):
                next_inputs.acquire_next(self.private, execute=True, now=datetime(2026, 11, 16, 23, 59, tzinfo=timezone.utc))
            with self.assertRaisesRegex(DwrError, "scope_confirmation_mismatch"):
                next_inputs.acquire_next(self.private, execute=True, confirm_scope="wrong", now=NOW)
            runner.assert_not_called()

    def test_tampered_raw_result_stops_normalization(self):
        log = self.capture()
        path = self.private / "acquisition" / log["acquisition_id"] / "raw/q02_rollups_2026-10-15.json"
        rows = load_json(path); rows[0]["hits"] += 1; write_json(path, rows)
        with self.assertRaisesRegex(DwrError, "acquisition_result_changed"):
            next_inputs.normalize(self.private)
        self.assertFalse((self.private / "working").exists())

    def test_changed_metadata_cannot_claim_readonly(self):
        log = self.capture()
        path = self.private / "acquisition" / log["acquisition_id"] / "acquisition-log.json"
        log["queries"][0]["meta"]["rows_written"] = 1; write_json(path, log)
        with self.assertRaisesRegex(DwrError, "acquisition_readonly_evidence_missing"):
            next_inputs.normalize(self.private)

    def test_archive_byte_change_is_rejected(self):
        self.capture()
        path = self.private / "sources/archive/tables/2026-10/reports.csv"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(DwrError, "archive_snapshot_integrity_failed"):
            next_inputs.normalize(self.private)

    def test_archive_commit_and_file_set_are_bound(self):
        folder = self.private / "sources/archive"
        with self.assertRaisesRegex(DwrError, "archive_snapshot_identity_mismatch"):
            archive.snapshot_inventory(folder, "b" * 40, self.period, repository="synthetic/archive")
        with self.assertRaisesRegex(DwrError, "archive_snapshot_identity_mismatch"):
            archive.snapshot_inventory(folder, "a" * 40, self.period, repository="different/archive")
        with self.assertRaisesRegex(DwrError, "archive_repository_not_pinned"):
            archive.snapshot_inventory(folder, "a" * 40, self.period, repository=None)
        path = folder / "manifest.json"; value = load_json(path)
        value["files"][0]["path"] = "../elsewhere.csv"; write_json(path, value)
        with self.assertRaisesRegex(DwrError, "archive_snapshot_file_set_mismatch"):
            archive.snapshot_inventory(folder, "a" * 40, self.period, repository="synthetic/archive")

    def test_archive_site_totals_cannot_shift_between_sites(self):
        self.capture()
        folder = self.private / "sources/archive"
        path = folder / "tables/2026-10/site_counts.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["count"] = str(int(rows[0]["count"]) + 1)
        rows[1]["count"] = str(int(rows[1]["count"]) - 1)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        manifest = load_json(folder / "manifest.json")
        for item in manifest["files"]:
            if item["path"] == path.relative_to(folder).as_posix():
                item.update(byte_length=path.stat().st_size, sha256=sha256_file(path))
        write_json(folder / "manifest.json", manifest)
        with self.assertRaisesRegex(DwrError, "archive_joint_site_daily_mismatch"):
            next_inputs.normalize(self.private)

    def test_sql_path_http_difference_is_rejected(self):
        self.capture(); next_inputs.normalize(self.private)
        path = self.private / "working" / self.eid / "normalized.json"
        normalized = load_json(path)
        changed = copy.deepcopy(normalized["marginals"])
        changed["path_http"][0]["requests"] += 1
        self.assertFalse(joint.cross_check(normalized["joint_rows"], changed)["all_consistent"])

    def test_mixed_categories_are_not_assigned_by_minimum(self):
        self.db.execute("UPDATE governance_daily_rollups SET category='different' WHERE event_date='2026-10-18' AND path='/llms.txt'")
        self.capture()
        with self.assertRaisesRegex(DwrError, "producer_category_changed_within_window"):
            next_inputs.normalize(self.private)

    def test_normalized_input_is_bound_back_to_acquisition(self):
        self.capture(); next_inputs.normalize(self.private)
        path = self.private / "working" / self.eid / "normalized.json"
        normalized = load_json(path); normalized["joint_rows"][0]["actor_name"] = "DifferentSyntheticAgent"; write_json(path, normalized)
        with self.assertRaisesRegex(DwrError, "normalized_inputs_differ_from_sources"):
            next_inputs.qualify_next(self.private)

    def test_normalized_provenance_cannot_be_invented(self):
        self.capture(); next_inputs.normalize(self.private)
        path = self.private / "working" / self.eid / "normalized.json"
        normalized = load_json(path)
        normalized["measurement_provenance"] = {"all_days": {"classifier_version": "invented"}}
        write_json(path, normalized)
        with self.assertRaisesRegex(DwrError, "normalized_inputs_differ_from_sources"):
            next_inputs.qualify_next(self.private)

    def test_private_candidate_revalidates_qualified_source_truth(self):
        self.capture(); next_inputs.normalize(self.private); next_inputs.qualify_next(self.private)
        path = self.private / "working" / self.eid / "qualified.json"
        value = load_json(path); value["resources"][0]["found_in_snapshot"] = True; write_json(path, value)
        result = maintenance.prepare(self.private, NOW)
        self.assertEqual(result["reason"], "qualified_inputs_differ_from_sources")
        self.assertFalse((self.private / "preparation/candidates" / self.eid).exists())

    def test_acquisition_source_and_client_version_are_bound(self):
        path = self.private / "lock/acquisition-config.json"
        config = load_json(path); config["expected_client_version"] = "different"; write_json(path, config)
        with patch.object(acquire, "_run_client") as runner, patch.object(acquire, "client_version", return_value="synthetic"):
            with self.assertRaisesRegex(DwrError, "client_version_mismatch"):
                next_inputs.acquire_next(self.private, execute=True, confirm_scope="2026-10-15..2026-11-15", now=NOW)
            runner.assert_not_called()
        self.assertFalse((self.private / "acquisition").exists())
        config.pop("expected_client_version"); write_json(path, config)
        self.capture()
        config["database_name"] = "different-source"; write_json(path, config)
        with self.assertRaisesRegex(DwrError, "acquisition_source_identity_mismatch"):
            next_inputs.normalize(self.private)

    def test_client_timeout_has_failure_receipt_without_partial_acceptance(self):
        with patch.object(acquire, "_client_prefix", return_value=["synthetic-client"]), \
             patch.object(acquire, "client_version", return_value="synthetic"), \
             patch.object(acquire.subprocess, "run", side_effect=subprocess.TimeoutExpired("synthetic-client", 180)):
            with self.assertRaisesRegex(DwrError, "source_unavailable"):
                next_inputs.acquire_next(self.private, execute=True, confirm_scope="2026-10-15..2026-11-15", now=NOW)
        path = next((self.private / "acquisition").glob("*/acquisition-log.json"))
        log = load_json(path)
        self.assertEqual(log["status"], "source_unavailable")
        self.assertIn("ended_at", log)
        self.assertFalse((self.private / "inputs.lock").exists())

    def test_unknown_graph_does_not_become_false_documentary_evidence(self):
        self.capture(); next_inputs.normalize(self.private); next_inputs.qualify_next(self.private)
        value = load_json(self.private / "working" / self.eid / "qualified.json")
        self.assertTrue(all(g["status"] == "source_unavailable" for g in value["graphs"].values()))
        self.assertTrue(all(r["found_in_snapshot"] is None and r["outbound_relations"] is None for r in value["resources"]))
        self.assertTrue(all(c["verified"] is False for c in value["case_checks"]))

    def test_projection_exclusion_does_not_mutate_private_inputs(self):
        self.capture(); next_inputs.normalize(self.private); next_inputs.qualify_next(self.private)
        folder = self.private / "working" / self.eid
        n, q = load_json(folder / "normalized.json"), load_json(folder / "qualified.json")
        before = copy.deepcopy((n, q))
        pn, pq, report = maintenance.projection_inputs(n, q)
        self.assertEqual((n, q), before)
        self.assertTrue(report["excluded_requests"] > 0)
        self.assertTrue(all(r["date_utc"] not in GAPS for r in pn["joint_rows"]))
        self.assertEqual(sum(r["request_count"] for r in n["joint_rows"]),
                         sum(r["request_count"] for r in pn["joint_rows"]) + report["excluded_requests"])

    def test_busy_or_public_destination_is_refused(self):
        write_text(self.private / "inputs.lock", "synthetic competing operator")
        with self.assertRaisesRegex(DwrError, "private_inputs_busy"):
            next_inputs.normalize(self.private)
        with self.assertRaisesRegex(DwrError, "private_root_inside_public_repository"):
            with next_inputs.input_lock(REPO_ROOT):
                self.fail("public destination admitted")

    @unittest.skipUnless(os.name == "nt", "Native Windows directory sharing lock")
    def test_real_windows_directory_lock_clears_before_atomic_install(self):
        import ctypes
        from ctypes import wintypes
        source, target = self.private / "locked", self.private / "installed"
        source.mkdir()
        create = ctypes.windll.kernel32.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                           wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = ctypes.windll.kernel32.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        handle = create(str(source), 1, 3, None, 3, 0x02000000, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with self.assertRaises(OSError) as blocked:
                os.rename(source, target)
            self.assertIn(blocked.exception.winerror, (32, 33))
        except BaseException:
            close(handle)
            raise
        release = threading.Timer(0.15, close, (handle,))
        release.start()
        try:
            maintenance.retry_sharing_violation(os.rename, source, target)
        finally:
            release.join()
        self.assertTrue(target.is_dir())
        self.assertFalse(source.exists())

    def test_persistent_install_and_cleanup_locks_preserve_failure_and_inputs(self):
        self.capture(); next_inputs.normalize(self.private); next_inputs.qualify_next(self.private)
        locked = PermissionError("synthetic sharing lock"); locked.winerror = 32
        with patch.object(maintenance.os, "rename", side_effect=locked), \
             patch.object(maintenance.shutil, "rmtree", side_effect=locked), \
             patch.object(maintenance.time, "sleep"):
            result = maintenance.prepare(self.private, NOW)
        self.assertEqual(result["outcome"], "validation_failed")
        self.assertEqual(result["reason"], "local_input_or_output_invalid")
        self.assertEqual(result["cleanup_status"], "pending")
        self.assertTrue((self.private / "preparation/candidates" / result["cleanup_stage"]).is_dir())
        self.assertFalse((self.private / "preparation/candidates" / self.eid).exists())
        self.assertEqual(load_json(self.private / "preparation/status.json")["latest_available_data_date"], "2026-10-14")
        self.assertTrue((self.private / "working" / self.eid / "qualified.json").is_file())
        # The normal path still succeeds after the external lock is gone.
        self.assertEqual(maintenance.prepare(self.private, NOW)["preparation_status"], "complete_private")
        recovered = load_json(self.private / "preparation/status.json")
        self.assertNotIn("reason", recovered)
        self.assertEqual(recovered["candidate_edition"], self.eid)
        self.assertEqual(recovered["preparation"]["real_next_window"], "local_candidate_available")

    def test_unrelated_filesystem_errors_are_not_retried(self):
        denied = PermissionError("synthetic permission failure"); denied.winerror = 5
        with patch.object(maintenance.time, "sleep") as sleeper:
            with self.assertRaises(PermissionError):
                maintenance.retry_sharing_violation(lambda: (_ for _ in ()).throw(denied))
            sleeper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
