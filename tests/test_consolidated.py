"""Counterexamples for consolidated audit findings; synthetic sources only."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tests import __init__
from tests.test_next_edition import prepare_inputs
from dwr import dates, edition_rules, future_projection, joint, maintenance, measurement, pipeline, png, project, render, revisions, write_guard
from dwr.common import REPO_ROOT, DwrError, canonical_json, load_json, write_json, write_text

R2 = "2026-09-15_2026-10-15-r2"
LOCAL = "2026-09-15_2026-10-15-r3"


def registry(root):
    (root/"config").mkdir()
    for name in write_guard.REGISTRIES:
        shutil.copyfile(REPO_ROOT/"config"/name, root/"config"/name)
    config = load_json(root/"config/editions.json")
    row = deepcopy(config["editions"][1])
    row.update(edition_id=LOCAL, revision=3, availability_status="local_candidate", supersedes=None)
    config["editions"].append(row)
    write_json(root/"config/editions.json",config)
    return config


class WriterControls(unittest.TestCase):
    def test_genuine_local_revision_runs_all_derivatives_and_failure_keeps_target(self):
        from tests.test_audit_followup import copy_candidate
        from dwr import common, frozen, public_checks, verify
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);copy_candidate(root)
            config=load_json(root/"config/editions.json")
            row=deepcopy(config["editions"][1])
            row.update(edition_id=LOCAL,revision=3,availability_status="local_candidate")
            config["editions"].append(row);write_json(root/"config/editions.json",config)
            with ExitStack() as stack:
                for module in (common,frozen,pipeline,render,revisions,png,verify):
                    stack.enter_context(patch.object(module,"REPO_ROOT",root))
                result=revisions.prepare(LOCAL)
                self.assertEqual(result["status"],"local_candidate")
                data=root/"data/editions"/LOCAL;fig=root/"figures"/LOCAL
                self.assertEqual(len(list(fig.glob("*.svg"))),48)
                self.assertTrue((data/"SHA256SUMS.txt").is_file())
                self.assertTrue(all(public_checks.reconcile_tables(data).values()))
                pipeline.cmd_analyze(LOCAL)
                render.render_figures(render.Edition(LOCAL))
                pipeline.cmd_prepare_edition(LOCAL)
                before=[write_guard.fingerprint(p) for p in (data,fig)]
                with patch.object(pipeline,"derive_stage",side_effect=RuntimeError("synthetic finalization failure")),self.assertRaises(RuntimeError):
                    revisions.prepare(LOCAL)
                self.assertEqual(before,[write_guard.fingerprint(p) for p in (data,fig)])
                with patch.object(png,"_render",side_effect=lambda p:write_text(p/"png/test.png","synthetic PNG marker")):
                    self.assertEqual(png.prepare(LOCAL)["status"],"local_candidate_png_installed")

    def test_all_public_writers_refuse_before_private_read_or_browser_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=registry(root)
            with patch.object(pipeline,"REPO_ROOT",root), patch.object(revisions,"REPO_ROOT",root), patch.object(png,"REPO_ROOT",root), patch.object(png,"_render") as browser:
                for downgrade in (False, True):
                    if downgrade:
                        config["editions"][1]["availability_status"]="local_candidate"
                        write_json(root/"config/editions.json",config)
                    for label,call in (("project",lambda:pipeline.cmd_project_public(root/"absent-private",R2)),
                                 ("prepare",lambda:pipeline.cmd_prepare_edition(R2)),
                                 ("revision",lambda:revisions.prepare(R2)),("png",lambda:png.prepare(R2))):
                        with self.subTest(downgrade=downgrade,call=label), self.assertRaises(DwrError) as failure:
                            call()
                        expected = "revision_target_not_local_unapproved" if label=="revision" and not downgrade else "public_or_historical_edition_immutable"
                        self.assertEqual(failure.exception.code,expected)
                    self.assertFalse((root/"data").exists())
                    browser.assert_not_called()

    def test_unknown_invalid_registry_and_approval_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=registry(root)
            with self.assertRaises(DwrError):write_guard.admit(root,"2026-09-15_2026-10-15-r99")
            for key,value in (("reference_release_status","approved"),("approval_receipt",{}),("availability_status","private_candidate")):
                changed=deepcopy(config);changed["editions"][-1][key]=value
                write_json(root/"config/editions.json",changed)
                with self.assertRaises(DwrError):write_guard.admit(root,LOCAL)
            write_json(root/"config/editions.json",config)
            write_json(root/"config/publication-inventory.json",{"releases":[]})
            with self.assertRaises(DwrError):write_guard.admit(root,LOCAL)

    def test_local_transaction_commit_failure_rollback_and_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);registry(root)
            data=root/"data/editions"/LOCAL;fig=root/"figures"/LOCAL
            write_text(data/"table.csv","old\n");write_text(fig/"figure.svg","old\n")
            before=[write_guard.fingerprint(p) for p in (data,fig)]
            with self.assertRaisesRegex(RuntimeError,"catalogue"):
                with write_guard.transaction(root,LOCAL) as stage:
                    write_text(stage/"payload/table.csv","new\n")
                    raise RuntimeError("catalogue")
            self.assertEqual(before,[write_guard.fingerprint(p) for p in (data,fig)])
            with write_guard.transaction(root,LOCAL) as stage:
                write_text(stage/"payload/table.csv","new\n")
                with self.assertRaises(DwrError):
                    with write_guard.transaction(root,LOCAL):pass
            self.assertEqual((data/"table.csv").read_text(),"new\n")
            self.assertFalse(list((root/".dwr-work").iterdir()))
            before=[write_guard.fingerprint(p) for p in (data,fig)]
            rename=os.rename
            def fail_second(source,dest):
                if Path(dest)==fig and Path(source).name=="figures":raise OSError("synthetic installation failure")
                return rename(source,dest)
            with patch.object(write_guard.os,"rename",side_effect=fail_second),self.assertRaises(OSError):
                with write_guard.transaction(root,LOCAL) as stage:
                    write_text(stage/"payload/table.csv","other\n")
            self.assertEqual(before,[write_guard.fingerprint(p) for p in (data,fig)])

    def test_interrupted_lock_blocks_readers_and_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);registry(root)
            write_text(root/".dwr-work"/(LOCAL+".lock"),'{"state":"installing"}')
            with self.assertRaises(DwrError):write_guard.assert_readable(root,LOCAL)
            with self.assertRaises(DwrError):
                with write_guard.transaction(root,LOCAL):pass

    def test_destination_change_is_not_overwritten_by_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);registry(root);target=root/"data/editions"/LOCAL
            write_text(target/"value","original")
            with self.assertRaisesRegex(DwrError,"edition_destination_changed"):
                with write_guard.transaction(root,LOCAL) as stage:
                    write_text(stage/"payload/value","candidate")
                    write_text(target/"value","concurrent writer")
            self.assertEqual((target/"value").read_text(),"concurrent writer")
            replace=os.replace
            def change_at_rename(source,dest):
                if Path(source)==target:write_text(target/"value","changed at rename")
                return replace(source,dest)
            with patch.object(write_guard.os,"replace",side_effect=change_at_rename),self.assertRaisesRegex(DwrError,"edition_destination_changed"):
                with write_guard.transaction(root,LOCAL) as stage:
                    write_text(stage/"payload/value","candidate")
            self.assertEqual((target/"value").read_text(),"changed at rename")

    def test_path_escape_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);registry(root)
            with self.assertRaises(DwrError):write_guard.checked_path(root,root.parent/"outside")
            link=root/"data"
            try:link.symlink_to(root/"config",target_is_directory=True)
            except OSError:
                if os.name!="nt":self.skipTest("symlink capability unavailable")
                quote=lambda p:"'"+str(p).replace("'","''")+"'"
                command="New-Item -ItemType Junction -Path "+quote(link)+" -Target "+quote(root/"config")+" | Out-Null"
                created=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],capture_output=True,timeout=15)
                self.assertEqual(created.returncode,0,"junction setup failed")
                self.assertTrue(link.is_junction())
            with self.assertRaises(DwrError):write_guard.admit(root,LOCAL)

    def test_public_analyses_are_comparisons_with_unchanged_bytes(self):
        dirs=[REPO_ROOT/"data/editions"/R2,REPO_ROOT/"figures"/R2]
        before=[write_guard.fingerprint(p) for p in dirs]
        pipeline.cmd_analyze(R2)
        render.compare_figures(render.Edition(R2))
        self.assertEqual(before,[write_guard.fingerprint(p) for p in dirs])


class EpochAndContract(unittest.TestCase):
    def test_two_clean_epochs_traverse_catalog_metrics_delta_and_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            private=Path(tmp);eid=prepare_inputs(private)
            path=private/"working"/eid/"normalized.json";norm=load_json(path)
            for row in norm["joint_rows"]:
                row.setdefault("classifier_version",norm["measurement_provenance"]["days"][row["date_utc"]]["epochs"][0]["classifier_version"])
            write_json(path,norm)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["preparation_status"],"complete_private",result)
            target=private/"preparation/candidates"/eid
            catalog=load_json(target/"payload/catalog.json")
            self.assertEqual(catalog["measurement"]["epoch_resolution"],"multiple_epochs_resolved")
            self.assertEqual(catalog["versions"]["classifier_recorded"],["synthetic-new","synthetic-old"])
            self.assertEqual(load_json(target/"payload/metrics.json")["measurement"]["epoch_resolution"],"multiple_epochs_resolved")
            self.assertIn("classifier_adapters",load_json(target/"delta-report.json"))
            self.assertIn("multiple_epochs_resolved",(target/"figures/G08.en.svg").read_text(encoding="utf-8"))

    def test_same_classifier_in_different_epoch_definition_is_not_comparable(self):
        base={k:"same" for k in edition_rules.COMPARABILITY_KEYS}
        base.update(coverage_status="complete_declared",period_start_inclusive="2026-09-15",period_end_exclusive="2026-10-15",
                    versions={"measurement_epoch_id":"multiple_epochs_resolved","classifier_recorded":["v1"]},
                    measurement={"epoch_definitions":{"a":{"classifier_version":"v1"},"b":{"classifier_version":"v1"}}})
        other=deepcopy(base);other["measurement"]["epoch_definitions"]["c"]=other["measurement"]["epoch_definitions"].pop("b")
        self.assertIn("changed:epoch_definitions",edition_rules.comparable(base,other)[1])

    def test_resolved_epochs_are_not_classifier_versions_or_unresolved_mixtures(self):
        row={"date_utc":"2026-10-20","classifier_version":"v1"}
        provenance={"days":{"2026-10-20":{"epochs":[
            {"epoch_id":"epoch-a","classifier_version":"v1","attribution_rules":"rules","deployment_evidence":"synthetic"},
            {"epoch_id":"epoch-b","classifier_version":"v2","attribution_rules":"rules","deployment_evidence":"synthetic"}]}}}
        report=measurement.qualify([row,{**row,"classifier_version":"v2"}],
            [{"date_utc":"2026-10-20","archive_status":"archived","report_status":"complete"}],provenance)
        self.assertEqual(report["epoch_resolution"],"multiple_epochs_resolved")
        self.assertEqual(report["classifier_versions"],["v1","v2"])
        self.assertEqual(report["epochs"],["epoch-a","epoch-b"])
        for bad in ("v one","a/b","",None):
            with self.assertRaises(DwrError):measurement.token(bad)
        adapted=edition_rules.classifier_adapter({"versions":{"classifier_recorded":"classifier-v1"}})
        self.assertEqual(adapted["values"],["classifier-v1"])
        self.assertFalse(adapted["inferred"])

    def test_all_projection_tables_deterministic_and_resource_days_use_union(self):
        with tempfile.TemporaryDirectory() as tmp:
            private=Path(tmp);eid=prepare_inputs(private)
            norm=load_json(private/"working"/eid/"normalized.json")
            qual=load_json(private/"working"/eid/"qualified.json")
            entry={"edition_id":eid,"window":dates.window_from_strings("2026-10-15","2026-11-15")}
            a=project.project(qual,norm,entry,"synthetic")
            reverse=deepcopy(norm);reverse["joint_rows"].reverse();reverse["archive_inventory"]["days"].reverse()
            q2=deepcopy(qual);q2["resources"].reverse()
            b=project.project(q2,reverse,entry,"synthetic")
            self.assertEqual(canonical_json(a),canonical_json(b))
            for key in ("daily","actors","family_daily"):
                self.assertTrue(all("measurement_epoch_id" in r for r in a[key]))
            expected=joint.path_counts(norm["joint_rows"])
            for r in a["resource_summary"]:
                self.assertEqual(r["days_with_rows"],expected[r["site_id"],r["path"]]["days"])

    def test_future_contract_rejected_rows_cannot_change_any_returned_byte(self):
        allowed={"date_utc":"2026-10-20","site_id":"synthetic","path":"/a","actor_role":"ai_training",
                 "actor_family":"synthetic","actor_name":"Synthetic","stored_identity_tier":future_projection.TIER,
                 "http_method":"GET","http_status":200,"request_count":3,"measurement_epoch_id":"e1"}
        resources=[{"site_id":"synthetic","path":"/a","family":"policy","main_population":True}]
        first=future_projection.prepare_synthetic([allowed],resources,nature="synthetic_only_not_observed_traffic")
        variants = [
            ({"actor_role":"user_initiated_fetch"}, True),
            ({"actor_role":"unknown"}, True),
            ({"stored_identity_tier":"network_verified_claimed_actor"}, True),
            ({"stored_identity_tier":"unknown"}, True),
            ({"stored_identity_tier":"claimed_actor"}, True),
            ({"http_method":"HEAD"}, True),
            ({"http_method":"POST"}, True),
            ({"http_status":304}, True),
            ({"http_status":404}, True),
            ({}, False), ({}, "false"), ({}, None)]
        for changes, population in variants:
            with self.subTest(changes=changes, population=population):
                extra = {"site_id":"synthetic","path":"/protected-only","main_population":population,"family":"protected"}
                second=future_projection.prepare_synthetic([allowed,{**allowed,**changes,
                    "request_count":983,"path":"/protected-only","private_digest":"rejected-source"}],
                    resources + ([extra] if population is not None else []),
                    nature="synthetic_only_not_observed_traffic")
                self.assertEqual(canonical_json(first),canonical_json(second))
        search = future_projection.prepare_synthetic([{**allowed, "actor_role":"ai_search"}], resources,
            nature="synthetic_only_not_observed_traffic")
        self.assertEqual(search["metrics"]["selected_requests"], 3)
        with self.assertRaises(DwrError):future_projection.prepare_synthetic([],[],nature="real")


class MonthlyCursor(unittest.TestCase):
    def test_interruption_after_candidate_install_recovers_receipt_without_new_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            private=Path(tmp);eid=prepare_inputs(private)
            with patch.object(maintenance,"atomic_json",side_effect=RuntimeError("synthetic state interruption")),self.assertRaises(RuntimeError):
                maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            target=private/"preparation/candidates"/eid
            before=write_guard.fingerprint(target)
            recovered=maintenance.prepare(private,datetime(2026,11,18,tzinfo=timezone.utc))
            self.assertTrue(recovered["recovered_existing_candidate"])
            self.assertNotEqual(recovered["outcome"],"unchanged")
            self.assertEqual(before,write_guard.fingerprint(target))
            repeated=maintenance.prepare(private,datetime(2026,11,19,tzinfo=timezone.utc))
            self.assertEqual(repeated["outcome"],"unchanged")
            self.assertEqual(load_json(private/"preparation/status.json")["latest_available_data_date"],"2026-11-14")

    def test_missing_last_day_advances_cursor_not_freshness_after_explicit_disposition(self):
        with tempfile.TemporaryDirectory() as tmp:
            private=Path(tmp);eid=prepare_inputs(private)
            path=private/"working"/eid
            norm=load_json(path/"normalized.json");qual=load_json(path/"qualified.json")
            norm["joint_rows"]=[r for r in norm["joint_rows"] if r["date_utc"]!="2026-11-14"]
            norm["marginals"]["daily"]=[r for r in norm["marginals"]["daily"] if r["date_utc"]!="2026-11-14"]
            norm["archive_inventory"]["days"][-1].update(archive_status="unavailable",aggregate_count=None,v3_count=None)
            counts=joint.path_counts(norm["joint_rows"])
            for resource in qual["resources"]:resource["counts"]=counts.get((resource["site_id"],resource["path"]))
            write_json(path/"normalized.json",norm);write_json(path/"qualified.json",qual)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["preparation_status"],"complete_private",result)
            statepath=private/"preparation/status.json";state=load_json(statepath)
            self.assertEqual(state["latest_available_data_date"],"2026-11-13")
            self.assertEqual(state["last_processed_window_end_exclusive"],"2026-11-15")
            # Synthetic explicit disposition; no approval or promotion operation.
            state["pending_window_start"]=None;write_json(statepath,state)
            result=maintenance.prepare(private,datetime(2026,12,17,tzinfo=timezone.utc))
            self.assertEqual(result["edition_id"],"2026-11-15_2026-12-15-r1")
            self.assertEqual(result["outcome"],"source_unavailable")
            self.assertEqual(load_json(statepath)["latest_available_data_date"],"2026-11-13")

    def test_invalid_cursor_is_reported_and_fault_leaves_no_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            private=Path(tmp);eid=prepare_inputs(private)
            with patch.object(maintenance.render,"render_figures",side_effect=OSError("synthetic")):
                result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["outcome"],"validation_failed")
            self.assertFalse((private/"preparation/candidates"/eid).exists())
            self.assertEqual(list((private/"preparation/candidates").iterdir()),[])
            statepath=private/"preparation/status.json";state=load_json(statepath)
            state["pending_window_start"]="2026-11-14";write_json(statepath,state)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result["outcome"],"validation_failed")
            self.assertEqual(result["reason"],"monthly_window_not_anchored")

    def test_calendar_lengths_leap_year_rollover_and_preparation_lock(self):
        for start,days,end in (("2028-02-15",29,"2028-03-15"),("2027-02-15",28,"2027-03-15"),
                               ("2026-04-15",30,"2026-05-15"),("2026-12-15",31,"2027-01-15")):
            window=dates.monthly_window(dates.parse_date(start),15)
            self.assertEqual((window.days,window.end_exclusive.isoformat()),(days,end))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_text(root/"preparation/preparation.lock","synthetic stale lock")
            with self.assertRaises(DwrError):maintenance.prepare(root)
