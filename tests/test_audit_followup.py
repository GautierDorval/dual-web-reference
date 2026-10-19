"""Independent-audit regressions: state transitions, malformed receipts and real boundaries."""
import copy
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from tests import __init__
from tests import test_corrective_controls as controls
from tests.test_next_edition import prepare_inputs
from dwr import common, disclosure, edition_rules, frozen, maintenance, pipeline, render, site_build, verify
from dwr.common import REPO_ROOT, DwrError, load_json, write_json, read_csv

R1='2026-09-15_2026-10-15-r1'
R2='2026-09-15_2026-10-15-r2'

def copy_candidate(root):
    for name in ('config','data','figures','schemas','cases','docs','site/assets'):
        shutil.copytree(REPO_ROOT/name,root/name)
    for name in ('README.md','README.fr.md','CITATION.cff','CONTRIBUTING.md','SECURITY.md','NOTICE.md','CHANGELOG.md','LICENSE'):
        if (REPO_ROOT/name).is_file(): shutil.copy2(REPO_ROOT/name,root/name)

class AuditFollowupTests(unittest.TestCase):
    def test_approval_transition_renders_external_state_without_changing_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root)
            with ExitStack() as stack:
                for module in (common,frozen,pipeline,render,site_build,verify):stack.enter_context(patch.object(module,'REPO_ROOT',root))
                stack.enter_context(patch.object(site_build,'DIST',root/'site/dist'))
                before=edition_rules.payload_manifest(R2,root)['digest']
                config=load_json(root/'config/editions.json');entry=next(e for e in config['editions'] if e['edition_id']==R2)
                entry.update(controls.ReviewTests().approved(R2,before));write_json(root/'config/editions.json',config)
                self.assertTrue(edition_rules.approved(entry))
                render.cmd(R2);site_build.cmd(R2)
                self.assertEqual(before,edition_rules.payload_manifest(R2,root)['digest'])
                self.assertTrue(edition_rules.approved(entry))
                self.assertEqual(load_json(root/'data/latest.json')['latest_published_edition'],R2)
                box=render.dates_box(render.Edition(R2),'en')
                self.assertIn('publicly accessible; reference approved',box)
                self.assertIn('publicly accessible; reference approved',(root/'README.md').read_text(encoding='utf-8'))
                report=verify.Report();verify.check_catalog(report,root/'data/editions'/R2)
                self.assertTrue(report.result()['passed'],report.result())
                self.assertNotIn('local candidate',box)
                self.assertNotIn('local candidate',(root/'cases/gautierdorval.com/README.md').read_text(encoding='utf-8'))
                html=(root/'site/dist/en/index.html').read_text(encoding='utf-8')
                self.assertIn('publicly accessible; reference approved',html)
                self.assertNotIn('local candidate',(root/'CITATION.cff').read_text(encoding='utf-8'))
                catalog=load_json(root/f'data/editions/{R2}/catalog.json')
                self.assertFalse(set(catalog)&set(edition_rules.MUTABLE_CATALOG_FIELDS))
                self.assertNotIn('next_review_target',catalog['dates'])
                png=root/f'figures/{R2}/png/G02.en.png';png.write_bytes(png.read_bytes()+b'changed')
                self.assertFalse(edition_rules.approved(entry))

    def test_latest_order_without_superseding_relationship_and_receipt_bounds(self):
        digest='a'*64;fixture=controls.ReviewTests()
        old=fixture.approved(R1,digest);new=fixture.approved('2026-10-15_2026-11-15-r1',digest)
        for rows in ([old,new],[new,old]):self.assertEqual(edition_rules.latest_pointer(rows,lambda _:digest),new['edition_id'])
        bad=copy.deepcopy(new);bad['period_end_exclusive']='2026-11-14'
        self.assertFalse(edition_rules.approved(bad,lambda _:digest))

    def test_malformed_receipt_types_dates_and_evidence_refuse_without_crashing(self):
        valid=controls.ReviewTests().approved(R2,'a'*64)
        for key,value in [('edition_id',[]),('edition_id',42),('approved_release_at','tomorrow'),('approved_release_at','2026-11-19')]:
            bad=copy.deepcopy(valid);bad[key]=value
            if key=='edition_id':bad['approval_receipt']['edition_id']=value
            self.assertFalse(edition_rules.approved(bad,lambda _:'a'*64))
        for key,value in [('evidence','one-string'),('evidence',[None]),('reviewer',1),('reviewed_at','2026-13-01'),('reviewed_at','2026-11-20T01:00:00'),('reviewed_at','2026-10-14')]:
            bad=copy.deepcopy(valid);bad['approval_receipt'][key]=value
            self.assertFalse(edition_rules.approved(bad,lambda _:'a'*64))
        with self.assertRaises(DwrError):edition_rules.parse_edition_id([])

    def test_inventory_function_refuses_missing_incomplete_and_changed_state_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root);path=root/'config/publication-inventory.json'
            original=load_json(path)
            self.assertEqual(disclosure.inventory(root)['status'],'assessed')
            for mutate in (lambda d:d['historical_states'].pop(),lambda d:d['historical_states'][0]['canonical_table_hashes'].update({'consultations.csv':'0'*64}),lambda d:d.update(releases=[])):
                doc=copy.deepcopy(original);mutate(doc);write_json(path,doc)
                self.assertEqual(disclosure.inventory(root)['status'],'not_assessed')
            path.unlink();self.assertEqual(disclosure.inventory(root)['status'],'not_assessed')

    def test_frozen_refuses_an_added_file_not_just_changes_to_known_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root)
            with patch.object(frozen,'REPO_ROOT',root):
                self.assertEqual(frozen.verify(R1)['status'],'historical_bytes_verified')
                (root/f'data/editions/{R1}/unexpected.csv').write_text('synthetic\n',encoding='utf-8')
                with self.assertRaises(DwrError) as caught:frozen.verify(R1)
                self.assertEqual(caught.exception.code,'historical_payload_file_set_changed')

    def test_same_window_revisions_cannot_produce_temporal_growth(self):
        versions={k:'same-attested' for k in edition_rules.COMPARABILITY_KEYS}
        first={'edition_id':R1,'versions':versions,'coverage_status':'complete_declared','dates':{'period_start_inclusive':'2026-09-15','period_end_exclusive':'2026-10-15'}}
        second={**first,'edition_id':R2}
        comparable,reasons=edition_rules.comparable(first,second)
        self.assertFalse(comparable);self.assertIn('revision_not_temporal_growth',reasons)
        self.assertIsNone(edition_rules.growth(10,11,comparable)['value'])

    def test_preparation_refuses_changed_inputs_even_when_counts_still_match(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp);eid=prepare_inputs(private)
            self.assertEqual(maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))['outcome'],'awaiting_review')
            path=private/'working'/eid/'normalized.json';source=load_json(path)
            source['joint_extracted_at']['end']='2026-11-17T00:00:02Z';write_json(path,source)
            result=maintenance.prepare(private,datetime(2026,11,18,tzinfo=timezone.utc))
            self.assertEqual(result['outcome'],'validation_failed')
            self.assertEqual(result['reason'],'existing_candidate_changed_inputs_requires_revision')

    def test_preparation_refuses_archive_and_marginal_mismatches_without_freshness(self):
        for key,reason in [('archive_inventory','archive_joint_daily_mismatch'),('marginals','marginal_joint_daily_mismatch')]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as temp:
                private=Path(temp);eid=prepare_inputs(private);path=private/'working'/eid/'normalized.json';source=load_json(path)
                if key=='archive_inventory':source[key]['days'][0]['aggregate_count']=999
                else:source[key]['daily'][0]['all_requests']=999
                write_json(path,source);result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
                self.assertEqual(result['outcome'],'validation_failed');self.assertEqual(result['reason'],reason)
                self.assertFalse((private/'preparation/candidates'/eid).exists())
                self.assertEqual(load_json(private/'preparation/status.json')['latest_available_data_date'],'2026-10-14')

    def test_disclosure_rejects_new_complement_and_unbacked_resource_family_marginals(self):
        policy=load_json(REPO_ROOT/'config/small-cell-policy.json')
        real=disclosure.tables(REPO_ROOT/'data/editions'/R2);historic=disclosure.inventory()
        self.assertTrue(disclosure.assess(real,historic,policy)['allowed'])
        cases=[]
        a=copy.deepcopy(real);a['coverage'][0]['new_complement']='1';cases.append(a)
        a=copy.deepcopy(real);a['consultations']=[];a['actors']=[];cases.append(a)
        a=copy.deepcopy(real);a['family_daily'][0]['request_count']=str(int(a['family_daily'][0]['request_count'])+1);cases.append(a)
        for case in cases:self.assertFalse(disclosure.assess(case,historic,policy)['allowed'])

    def test_preparation_runs_schema_and_public_marginal_checks(self):
        for target in ('check_tables','reconcile_tables'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as temp:
                private=Path(temp);prepare_inputs(private)
                from dwr import public_checks
                if target=='check_tables':ctx=patch.object(verify,target,side_effect=lambda report,directory:report.add('synthetic_invalid_schema',False))
                else:ctx=patch.object(public_checks,target,return_value={'synthetic_marginal_error':False})
                with ctx:result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
                self.assertEqual(result['outcome'],'validation_failed')
                self.assertEqual(result['reason'],'prepared_projection_schema_or_reconciliation_failed')
