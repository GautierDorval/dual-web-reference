"""Closed automated contract: arithmetic, leakage, admission and actual files.

All source observations in these tests are synthetic fixtures. The production
path itself has no 'synthetic' override and always admits native input receipts.
"""
import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
from tests import __init__
from tests import test_private_next_inputs as fixtures
from dwr import automated as a, automated_render as r, automated_prepare as p, dates, next_inputs
from dwr.common import DwrError, REPO_ROOT, SITE_IDS, load_json, write_json, sha256_file
from dwr.write_guard import fingerprint

WINDOW = dates.window_from_strings("2099-01-01", "2099-02-01")
GAP = "2099-01-05"
RESOURCE = {"site_id": SITE_IDS[0], "path": "/fixture-policy", "family": "policy", "main_population": True}
ROW = {"date_utc": "2099-01-01", "site_id": SITE_IDS[0], "path": "/fixture-policy",
       "actor_family": "fixture", "actor_name": "FixtureBot", "actor_role": "ai_training",
       "stored_identity_tier": a.TIER, "http_method": "GET", "http_status": 200, "request_count": 2}


def archive():
    return [{"date_utc": str(d), "archive_status": "observation_unavailable" if str(d) == GAP else "archived",
             "report_status": "partial", "aggregate_count": 800, "v3_count": 700,
             "snapshot_id": "private-fixture", "report_reason_code": "private-reason"} for d in WINDOW.dates()]


def projection(rows=None, resources=None, evidence=None, provenance=None):
    return a.project(rows if rows is not None else [ROW], resources if resources is not None else [RESOURCE],
                     window=WINDOW, evidence=evidence if evidence is not None else a.coverage_evidence(archive(), WINDOW),
                     provenance=provenance or {})


class AutomatedProjectionTests(unittest.TestCase):
    def test_monthly_details_remove_days_epochs_and_reconcile_full_calendar(self):
        doc = projection([ROW, {**ROW, "date_utc": "2099-01-02", "request_count": 3,
                               "measurement_epoch_id": "protected-epoch-must-not-appear"},
                          {**ROW, "date_utc": GAP, "request_count": 900}])
        self.assertEqual(doc["metrics"]["selected_requests"], 5)
        self.assertEqual(len(doc["tables"]["consultations"]), 1)
        self.assertEqual(doc["tables"]["consultations"][0]["request_count"], 5)
        self.assertNotIn("measurement_epoch_id", json.dumps(doc))
        self.assertEqual(len(doc["tables"]["coverage"]), WINDOW.days)
        self.assertEqual(len(doc["tables"]["daily"]), WINDOW.days * len(SITE_IDS) * len(a.ROLES))
        gap = next(r for r in doc["tables"]["coverage"] if r["date_utc"] == GAP)
        self.assertIsNone(gap["request_count"])
        zero = next(r for r in doc["tables"]["coverage"] if r["date_utc"] == "2099-01-03")
        self.assertEqual(zero["request_count"], 0)
        self.assertEqual(zero["coverage_status"], "partial_declared")
        self.assertEqual(doc["on_demand"], a.ON_DEMAND)
        self.assertFalse(doc["comparison"]["comparable"])
        self.assertIsNone(doc["comparison"]["growth"])

    def test_every_output_byte_and_filename_ignores_rejected_rows_and_metadata(self):
        baseline = r.files(projection())
        variants = [{"actor_role": "user_initiated_fetch"}, {"actor_role": "search_indexing"},
                    {"actor_role": "unknown"}, {"stored_identity_tier": "claimed_actor_unverified"},
                    {"stored_identity_tier": "network_verified_claimed_actor"},
                    {"http_method": "HEAD"}, {"http_method": "POST"}, {"http_status": 404},
                    {"path": "/unselected"}]
        extra = {**RESOURCE, "path": "/unselected", "main_population": False, "family": "private-family"}
        for change in variants:
            with self.subTest(change=change):
                rejected = {**ROW, **change, "request_count": 999999, "actor_name": "PRIVATE_EXCLUDED_MARKER",
                            "classifier_version": "PRIVATE_EPOCH", "private_input_digest": "private-digest"}
                document = projection([rejected, ROW], [extra, RESOURCE])
                self.assertEqual(r.files(document), baseline)
                self.assertEqual(r.files(projection([ROW, rejected, rejected], [RESOURCE, extra])), baseline)
        modified_archive = archive()
        for row in modified_archive:
            row.update(aggregate_count=9999999, v3_count=1, snapshots=999, captured_at="private-time",
                       snapshot_id="different-private-snapshot", report_reason_code="different-private-reason")
        self.assertEqual(r.files(projection(evidence=a.coverage_evidence(modified_archive, WINDOW))), baseline)
        self.assertNotEqual(r.files(projection([{**ROW, "request_count": 3}])), baseline)

    def test_empty_selection_does_not_reveal_unselected_inventory_or_demand(self):
        empty = r.files(projection([]))
        self.assertEqual(empty, r.files(projection([{**ROW, "actor_role": "user_initiated_fetch"}])))
        doc = projection([])
        self.assertEqual(doc["tables"]["resources"], [])
        self.assertEqual(doc["tables"]["family_daily"], [])
        self.assertEqual(doc["metrics"]["selected_requests"], 0)
        self.assertEqual(doc["on_demand"]["suppression_status"], "withheld_not_zero")
        self.assertIsNone(doc["on_demand"]["request_count"])

    def test_evidence_fields_and_missing_status_fail_closed(self):
        evidence = a.coverage_evidence(archive(), WINDOW)
        for field in ("input_digest", "reason_code", "aggregate_count", "measurement_epoch_id"):
            changed = copy.deepcopy(evidence); changed[0][field] = "private"
            with self.subTest(field=field), self.assertRaises(DwrError):
                projection(evidence=changed)
        for change in ({"source_qualification": "not_qualified"}, {"coverage_status": "observation_unavailable"},
                       {"archive_status": "unknown"}, {"evidence_status": "not_established"}):
            changed = copy.deepcopy(evidence); changed[0].update(change)
            with self.subTest(change=change), self.assertRaises(DwrError):
                projection(evidence=changed)
        for changed in (evidence[1:], evidence + [evidence[0]], list(reversed(evidence))):
            with self.assertRaises(DwrError):projection(evidence=changed)

    def test_provenance_is_categorical_and_independent_of_rows(self):
        provenance = {"days": {"2099-01-02": {"separable": False, "epochs": [
            {"classifier_version": "private-fixture-a"}, {"classifier_version": "private-fixture-b"}]}}}
        doc = projection(provenance=provenance)
        self.assertEqual(doc["measurement"]["epoch_resolution"], "mixed_epoch_unresolved")
        self.assertEqual(doc["measurement"]["classifier_status"], "unknown")
        self.assertEqual(projection([], provenance=provenance)["measurement"], doc["measurement"])
        self.assertNotIn("private-fixture-a", json.dumps(doc))
        self.assertNotIn("epoch_definitions", json.dumps(doc))

    def test_closed_schema_counts_dates_marginals_and_inventory(self):
        mutations = [
            lambda d: d.update(input_digest="private"),
            lambda d: d["tables"].update(exclusions=[]),
            lambda d: d["tables"]["consultations"][0].update(date_utc="2099-01-01"),
            lambda d: d["tables"]["actors"][0].update(days_with_rows=1),
            lambda d: d["tables"]["daily"][0].update(actor_name="FixtureBot"),
            lambda d: d["tables"]["resource_summary"][0].update(request_count=999),
            lambda d: d["metrics"].update(selected_requests=999),
            lambda d: d["tables"]["resources"].append({"site_id":SITE_IDS[0],"path":"/unselected","family":"policy"}),
            lambda d: d["tables"]["coverage"][4].update(request_count=0),
            lambda d: d["tables"]["daily"].pop(),
            lambda d: d["on_demand"].update(request_count=0),
            lambda d: d.update(public_output_approved=0),
        ]
        for index, mutation in enumerate(mutations):
            doc=projection(); mutation(doc)
            with self.subTest(index=index), self.assertRaises(DwrError):a.validate(doc)
        for count in (True, 0, -1, 1.2, "2"):
            with self.subTest(count=count), self.assertRaises(DwrError):projection([{**ROW,"request_count":count}])
        with self.assertRaises(DwrError):projection([{**ROW,"date_utc":"2099-02-01"}])
        with self.assertRaises(DwrError):projection([{**ROW,"actor_name":"=FORMULA()"}])

    def test_output_allowlist_bytes_and_bilingual_figures(self):
        doc=projection()
        files=r.files(doc)
        for lang in ("fr","en"):
            report=files[f"report.{lang}.html"].decode()
            self.assertIn("growth" if lang=="en" else "Croissance",report)
            self.assertIn("U0",report)
            self.assertIn("max-width:100%",report)
            self.assertNotIn("100\u00a0%",report)
            self.assertIn(f'report.{"en" if lang=="fr" else "fr"}.html',report)
            self.assertNotIn('href="https://',report)
            for name, content in files.items():
                if name.endswith(f'.{lang}.compact.svg'):
                    node=ET.fromstring(content)
                    self.assertEqual(node.attrib['width'],'360')
                    self.assertIn('UTC',content.decode())
        self.assertIn("Graphe documentaire indisponible", files[f"figures/G09-{SITE_IDS[0]}.fr.svg"].decode())
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,content in files.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
            self.assertTrue(r.verify(root,doc)["passed"])
            (root/"private-rejected-count.txt").write_text("1")
            with self.assertRaises(DwrError):r.verify(root,doc)
            (root/"private-rejected-count.txt").unlink()
            (root/"hidden-presence").mkdir()
            with self.assertRaises(DwrError):r.verify(root,doc)


class AutomatedPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PrivateNextInputsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.private=self.fixture.private

    def admitted(self):
        self.fixture.capture()
        next_inputs.normalize(self.private)
        next_inputs.qualify_next(self.private)

    def candidate(self):
        return self.private/'automated/candidates'/self.fixture.eid

    def test_actual_native_receipts_prepare_idempotence_recovery_and_no_legacy_writes(self):
        self.admitted()
        protected=['config/small-cell-policy.json','config/editions.json','data/latest.json','data/status.json']
        before={n:sha256_file(REPO_ROOT/n) for n in protected}
        sources=p.input_manifest(self.private)
        result=p.prepare(self.private,fixtures.NOW)
        self.assertEqual(result['preparation_status'],'complete_private')
        self.assertFalse(result['distribution_authorized'])
        candidate=self.candidate()
        doc=load_json(candidate/'projection/projection.json')
        q=load_json(self.private/'working'/self.fixture.eid/'qualified.json')
        selected={(x['site_id'],x['path']) for x in q['resources'] if x['main_population']}
        expected=sum(i+1 for i,day in enumerate(self.fixture.period.dates()) if str(day) not in fixtures.GAPS)*sum((site,'/llms.txt') in selected for site in SITE_IDS)
        self.assertEqual(doc['metrics']['selected_requests'],expected)
        self.assertGreater(expected,0)
        self.assertEqual({r['date_utc'] for r in doc['tables']['coverage'] if r['request_count'] is None}, fixtures.GAPS)
        self.assertEqual(doc['measurement']['epoch_resolution'],'mixed_epoch_unresolved')
        self.assertEqual(p.input_manifest(self.private),sources)
        self.assertFalse((self.private/'preparation/status.json').exists())
        digest=fingerprint(candidate)
        self.assertEqual(p.prepare(self.private,fixtures.NOW)['outcome'],'unchanged')
        self.assertEqual(fingerprint(candidate),digest)
        (self.private/'automated/status.json').unlink()
        self.assertEqual(p.prepare(self.private,fixtures.NOW)['outcome'],'unchanged')
        self.assertTrue((self.private/'automated/status.json').is_file())
        self.assertEqual(before,{n:sha256_file(REPO_ROOT/n) for n in protected})

    def test_admission_cannot_be_bypassed_by_missing_marker_or_forged_normalized_rows(self):
        self.admitted()
        path=self.private/'working'/self.fixture.eid/'normalized.json'
        original=load_json(path)
        for change in ('marker','count','archive'):
            value=copy.deepcopy(original)
            if change=='marker':value.pop('source_provenance_contract')
            elif change=='count':value['joint_rows'][0]['request_count']+=1
            else:value['archive_inventory']['days'][0]['report_status']='complete'
            write_json(path,value)
            with self.subTest(change=change),self.assertRaises(DwrError):p.prepare(self.private,fixtures.NOW)
            self.assertFalse(self.candidate().exists())
        write_json(path,original)

    def test_native_admission_changed_rejected_counts_preserves_every_projection_byte(self):
        self.admitted();p.prepare(self.private,fixtures.NOW)
        original=self.candidate()/'projection'
        baseline=fingerprint(original)
        other=fixtures.PrivateNextInputsTests();other.setUp();self.addCleanup(other.doCleanups)
        other.db.execute("UPDATE governance_daily_rollups SET hits=hits+91, actor_name='ExcludedVariant' WHERE confidence='unknown_automation'")
        other.make_archive()
        other.capture();next_inputs.normalize(other.private);next_inputs.qualify_next(other.private)
        p.prepare(other.private,fixtures.NOW)
        candidate=other.private/'automated/candidates'/other.eid
        self.assertEqual(fingerprint(candidate/'projection'),baseline)
        first=load_json(self.candidate()/'preparation-receipt.json')
        second=load_json(candidate/'preparation-receipt.json')
        self.assertNotEqual(first['input_digest'],second['input_digest'])
        self.assertNotEqual(load_json(self.candidate()/'diagnostics/source-exclusions.private.json'),
                            load_json(candidate/'diagnostics/source-exclusions.private.json'))

    def test_forged_self_consistent_candidate_still_reconciles_against_admitted_sources(self):
        self.admitted();p.prepare(self.private,fixtures.NOW)
        candidate=self.candidate()
        n=load_json(self.private/'working'/self.fixture.eid/'normalized.json')
        q=load_json(self.private/'working'/self.fixture.eid/'qualified.json')
        doc=a.project([],q['resources'],window=self.fixture.period,
                      evidence=a.coverage_evidence(n['archive_inventory']['days'],self.fixture.period),provenance=n['measurement_provenance'])
        for name,content in r.files(doc).items():(candidate/'projection'/name).write_bytes(content)
        receipt=load_json(candidate/'preparation-receipt.json')
        receipt['files']=fingerprint(candidate);receipt['files'].pop('preparation-receipt.json')
        write_json(candidate/'preparation-receipt.json',receipt)
        with self.assertRaisesRegex(DwrError,'automated_output_bytes_or_surfaces_changed'):
            p.prepare(self.private,fixtures.NOW)

    def test_busy_old_workspace_git_roots_and_consolidation_refused(self):
        self.admitted()
        with self.assertRaisesRegex(DwrError,'next_window_not_consolidated'):
            p.prepare(self.private,fixtures.NOW.replace(day=16))
        lock=self.private/'automated/preparation.lock';lock.write_text('fixture')
        with self.assertRaisesRegex(DwrError,'automated_preparation_busy'):p.prepare(self.private,fixtures.NOW)
        lock.unlink()
        (self.private/'preparation/candidates').mkdir(parents=True)
        with self.assertRaisesRegex(DwrError,'separate_private_workspace'):p.prepare(self.private,fixtures.NOW)
        with self.assertRaisesRegex(DwrError,'inside_git_repository'):p.prepare(REPO_ROOT,fixtures.NOW)

    def test_failed_output_never_installs_a_partial_candidate(self):
        self.admitted()
        with patch.object(r,'verify',side_effect=DwrError('fixture-output-failure')):
            with self.assertRaisesRegex(DwrError,'fixture-output-failure'):p.prepare(self.private,fixtures.NOW)
        self.assertFalse(self.candidate().exists())
        self.assertEqual(list((self.private/'automated/candidates').iterdir()),[])
        self.assertFalse((self.private/'automated/preparation.lock').exists())


if __name__=='__main__':unittest.main()
