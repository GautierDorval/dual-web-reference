"""Profile B behaviour, independent margin oracle and real offline CLI admission.

All source rows and SQL receipts in this module are synthetic fixtures. They do
not replace the separate qualification of the real, previously acquired inputs.
"""
import contextlib
import copy
import io
import itertools
import json
import tempfile
import threading
import unittest
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from tests import __init__
from tests import test_automated_contract as f, test_private_next_inputs as native
from dwr import automated as a, automated_render as r, automated_prepare as p, automated_inference as inference
from dwr import cli, next_inputs
from dwr.common import DwrError, REPO_ROOT, canonical_json, load_json, sha256_file, write_json
from dwr.write_guard import fingerprint


def project(rows=None, resources=None):
    return a.project([f.ROW] if rows is None else rows, [f.RESOURCE] if resources is None else resources,
                     window=f.WINDOW, evidence=a.coverage_evidence(f.archive(), f.WINDOW), provenance={},
                     contract=a.PROFILE_B_CONTRACT)


class ProfileBProjectionTests(unittest.TestCase):
    def test_changed_family_days_are_indistinguishable_only_in_profile_b(self):
        resources=[f.RESOURCE, {**f.RESOURCE, 'path':'/fixture-identity', 'family':'identity'}]
        first=[f.ROW, {**f.ROW,'path':'/fixture-identity','date_utc':'2099-01-02'}]
        swapped=[{**row,'date_utc':'2099-01-02' if row['date_utc']=='2099-01-01' else '2099-01-01'} for row in first]
        self.assertNotEqual(r.files(f.projection(first,resources)),r.files(f.projection(swapped,resources)))
        doc=project(first,resources)
        self.assertEqual(r.files(doc),r.files(project(swapped,resources)))
        old=f.projection(first,resources)
        for table in a.table_fields(a.PROFILE_B_CONTRACT):
            self.assertEqual(doc['tables'][table],old['tables'][table])
        self.assertEqual(doc['metrics'],old['metrics'])
        self.assertEqual(doc['on_demand'],old['on_demand'])
        self.assertEqual(doc['comparison'],old['comparison'])
        self.assertEqual(doc['graphs'],old['graphs'])
        self.assertEqual(doc['measurement'],old['measurement'])

    def test_closed_contract_catalog_manifest_reports_and_monthly_g06(self):
        doc=project();files=r.files(doc)
        self.assertEqual(len(files),56)
        self.assertNotIn('family_daily',doc['tables'])
        self.assertNotIn('family_daily',json.loads(files['schema.json'])['properties']['tables']['properties'])
        self.assertNotIn('family_daily',json.loads(files['catalog.json'])['tables'])
        self.assertNotIn('daily-family-summary.csv',files)
        self.assertNotIn('daily-family-summary.csv',json.loads(files['manifest.json'])['files'])
        self.assertEqual(doc['availability_status'],'local_release_candidate')
        self.assertFalse(doc['public_output_approved'])
        for name in ('catalog.json','manifest.json','figures.json'):
            self.assertEqual(json.loads(files[name])['contract'],a.PROFILE_B_CONTRACT)
        self.assertEqual(files['family-summary.csv'],r.files(f.projection())['family-summary.csv'])
        self.assertEqual(files['figures/G06.csv'],r.files(f.projection())['figures/G06.csv'])
        for lang in ('en','fr'):
            report=files[f'report.{lang}.html'].decode()
            self.assertNotIn('daily-family-summary.csv',report)
            self.assertIn('family-summary.csv',report)
            self.assertIn('daily-summary.csv',report)
            self.assertIn('profile B' if lang=='en' else 'profil B',report)
            self.assertIn('not anonymization' if lang=='en' else "pas une anonymisation",report)
        for mutation in (lambda d:d['tables'].update(family_daily=[]),
                         lambda d:d.update(private_count=7),
                         lambda d:d['tables']['daily'][0].update(family='policy'),
                         lambda d:d.update(public_output_approved=True),
                         lambda d:d.update(contract='dwr-automated/3.0.0'),
                         lambda d:d['disclosure_profile'].update(daily_dimensions=['family'])):
            changed=copy.deepcopy(doc);mutation(changed)
            with self.assertRaises(DwrError):r.files(changed)

    def test_all_bytes_ignore_excluded_rows_and_object_order(self):
        def reversed_keys(value):
            if isinstance(value,dict):return {k:reversed_keys(value[k]) for k in reversed(value)}
            if isinstance(value,list):return [reversed_keys(v) for v in value]
            return value
        for rows in ([f.ROW],[]):
            doc=project(rows);expected=r.files(doc)
            self.assertEqual(r.files(json.loads(expected['projection.json'])),expected)
            self.assertEqual(r.files(reversed_keys(doc)),expected)
            for rejection in ({'actor_role':'user_initiated_fetch'},{'actor_role':'unknown'},
                              {'http_method':'POST'},{'http_status':404},
                              {'stored_identity_tier':'network_verified_claimed_actor'}):
                excluded={**f.ROW,**rejection,'request_count':999999,'actor_name':'PRIVATE_REJECTED_MARKER'}
                self.assertEqual(r.files(project([excluded,*rows,excluded])),expected)
        self.assertNotEqual(r.files(project([{**f.ROW,'request_count':3}])),r.files(project()))

    def test_extra_file_directory_and_corruption_are_refused_then_recovery_passes(self):
        doc=project();files=r.files(doc)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for n,v in files.items():
                path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(v)
            self.assertTrue(r.verify(root,doc)['passed'])
            extra=root/'daily-family-summary.csv';extra.write_text('date_utc,family,request_count\n')
            with self.assertRaises(DwrError):r.verify(root,doc)
            extra.unlink();hidden=root/'extra';hidden.mkdir()
            with self.assertRaises(DwrError):r.verify(root,doc)
            hidden.rmdir();(root/'daily-summary.csv').write_bytes(files['daily-summary.csv']+b'1')
            with self.assertRaises(DwrError):r.verify(root,doc)
            (root/'daily-summary.csv').write_bytes(files['daily-summary.csv'])
            self.assertTrue(r.verify(root,doc)['passed'])

    def test_bounds_match_all_small_two_by_three_tables_not_just_a_formula_copy(self):
        systems=defaultdict(list)
        for cells in itertools.product(range(5),repeat=6):
            if sum(cells)>4:continue
            row_sums=(sum(cells[:3]),sum(cells[3:]))
            column_sums=tuple(cells[i]+cells[i+3] for i in range(3))
            systems[(row_sums,column_sums)].append(cells)
        self.assertEqual(sum(map(len,systems.values())),210)
        resources=[{**f.RESOURCE,'path':f'/fixture-{i}','family':f'family-{i}'} for i in range(3)]
        for (_,columns),solutions in systems.items():
            witness=solutions[0]
            rows=[{**f.ROW,'date_utc':f'2099-01-0{1+i//3}','path':f'/fixture-{i%3}',
                   'request_count':n} for i,n in enumerate(witness) if n]
            result=inference.assess(project(rows,resources))
            found={(b['date_utc'],b['path']):(b['lower'],b['upper']) for b in result['bounds']}
            for i in range(6):
                if columns[i%3]:
                    self.assertEqual(found[(f'2099-01-0{1+i//3}',f'/fixture-{i%3}')],
                                     (min(s[i] for s in solutions),max(s[i] for s in solutions)))
            self.assertFalse(any(b['date_utc']==f.GAP for b in result['bounds']))
        self.assertGreater(len(systems),100)

    def test_degenerate_disclosures_empty_selection_and_old_contract_are_not_mislabelled(self):
        result=inference.assess(project())
        self.assertEqual(result['fixed_positive_cells'],1)
        self.assertEqual(result['fixed_zero_cells'],29)
        self.assertEqual(result['unfixed_cells'],0)
        self.assertEqual(inference.assess(project([]))['variables'],0)
        with self.assertRaises(DwrError):inference.assess(f.projection())


class FixedClock(datetime):
    @classmethod
    def now(cls,tz=None):return native.NOW


class ProfileBPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=native.PrivateNextInputsTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.private=self.fixture.private

    def race_then_replay(self, delayed_contract=None):
        self.admit()
        original=p.private_workspace
        barrier=threading.Barrier(2,timeout=10)
        winner_finished=threading.Event()
        results={};errors={}
        def initial_check(value,contract=a.CONTRACT):
            result=original(value,contract)
            if not getattr(threading.current_thread(),'profile_checked',False):
                threading.current_thread().profile_checked=True
                barrier.wait()
                if contract==delayed_contract and not winner_finished.wait(30):
                    raise RuntimeError('race_winner_did_not_finish')
            return result
        def run(contract):
            try:results[contract]=p.prepare(self.private,native.NOW,contract=contract)
            except Exception as error:errors[contract]=error
            finally:
                if contract!=delayed_contract:winner_finished.set()
        # Only scheduling is controlled: admission, outputs and receipts are real.
        with patch.object(p,'private_workspace',side_effect=initial_check):
            threads=[threading.Thread(target=run,args=(contract,),daemon=True)
                     for contract in (a.CONTRACT,a.PROFILE_B_CONTRACT)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(40)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(results),1,(results,errors))
        self.assertEqual(len(errors),1,(results,errors))
        winner=next(iter(results));loser=next(iter(errors))
        if delayed_contract is not None:self.assertEqual(loser,delayed_contract)
        self.assertIsInstance(errors[loser],DwrError)
        self.assertIn(errors[loser].code,('automated_preparation_busy','automated_requires_separate_contract_workspace'))
        self.assertEqual(results[winner]['outcome'],'new_private_candidate')
        self.assertTrue((self.private/p.workspace_folder(winner)).is_dir())
        self.assertFalse((self.private/p.workspace_folder(loser)).exists())
        self.assertFalse(list(self.private.rglob('preparation.lock')))
        self.assertFalse((self.private/'.automated-preparation.lock').exists())
        sealed=fingerprint(self.private)
        self.assertEqual(p.prepare(self.private,native.NOW,contract=winner)['outcome'],'unchanged')
        with self.assertRaisesRegex(DwrError,'separate_contract_workspace'):
            p.prepare(self.private,native.NOW,contract=loser)
        self.assertEqual(p.prepare(self.private,native.NOW,contract=winner)['outcome'],'unchanged')
        self.assertEqual(fingerprint(self.private),sealed)

    def test_cross_version_race_preserves_winner_replay(self):
        self.race_then_replay()

    def test_stale_initial_check_cannot_poison_completed_other_version(self):
        self.race_then_replay(delayed_contract=a.CONTRACT)

    def test_common_reservation_busy_does_not_create_namespace_or_remove_owner_lock(self):
        reservation=self.private/'.automated-preparation.lock'
        reservation.write_bytes(b'other-cooperating-preparation')
        for contract in (a.CONTRACT,a.PROFILE_B_CONTRACT):
            with self.assertRaisesRegex(DwrError,'automated_preparation_busy'):
                p.prepare(self.private,native.NOW,contract=contract)
            self.assertFalse((self.private/p.workspace_folder(contract)).exists())
            self.assertEqual(reservation.read_bytes(),b'other-cooperating-preparation')

    def admit(self):
        self.fixture.capture();next_inputs.normalize(self.private);next_inputs.qualify_next(self.private)

    def candidate(self):return self.private/'automated-profile-b/candidates'/self.fixture.eid

    def command(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.object(p,'datetime',FixedClock):
            code=cli.main(['prepare-automated-profile-b','--private-root',str(self.private),*args])
        return code,out.getvalue(),err.getvalue()

    def test_actual_cli_admits_sources_is_idempotent_and_recovers_only_its_status(self):
        self.admit()
        protected=['config/editions.json','config/small-cell-policy.json','data/latest.json','data/status.json']
        before={n:sha256_file(REPO_ROOT/n) for n in protected}
        inputs=p.input_manifest(self.private)
        code,out,err=self.command();self.assertEqual(code,0,err)
        result=json.loads(out);self.assertEqual(result['contract'],a.PROFILE_B_CONTRACT)
        self.assertFalse(result['distribution_authorized'])
        candidate=self.candidate();original=fingerprint(candidate)
        doc=load_json(candidate/'projection/projection.json')
        self.assertGreater(doc['metrics']['selected_requests'],0)
        self.assertNotIn('family_daily',doc['tables'])
        self.assertEqual({v['date_utc'] for v in doc['tables']['coverage'] if v['request_count'] is None},native.GAPS)
        self.assertEqual(doc['measurement']['epoch_resolution'],'mixed_epoch_unresolved')
        self.assertEqual(load_json(candidate/'diagnostics/profile-b-inference.private.json'),inference.assess(doc))
        self.assertEqual(json.loads(self.command()[1])['outcome'],'unchanged')
        (self.private/'automated-profile-b/status.json').unlink()
        self.assertEqual(self.command()[0],0)
        self.assertTrue((self.private/'automated-profile-b/status.json').is_file())
        self.assertEqual(fingerprint(candidate),original)
        self.assertEqual(p.input_manifest(self.private),inputs)
        self.assertFalse((self.private/'preparation/status.json').exists())
        self.assertFalse((self.private/'automated').exists())
        self.assertEqual(before,{n:sha256_file(REPO_ROOT/n) for n in protected})
        self.assertEqual(self.command('--edition','anything')[0],2)
        with self.assertRaisesRegex(DwrError,'separate_contract_workspace'):p.prepare(self.private,native.NOW)
        self.assertEqual(fingerprint(candidate),original)

    def test_source_admission_failure_and_output_failure_preserve_then_retry(self):
        self.admit()
        normalized=self.private/'working'/self.fixture.eid/'normalized.json'
        original=normalized.read_bytes();changed=json.loads(original);changed['joint_rows'][0]['request_count']+=1
        write_json(normalized,changed)
        code,_,err=self.command();self.assertEqual(code,2,err)
        self.assertFalse(self.candidate().exists())
        self.assertFalse((self.private/'automated-profile-b/preparation.lock').exists())
        normalized.write_bytes(original)
        with patch.object(r,'verify',side_effect=DwrError('fixture_profile_b_output_failure')):
            code,_,err=self.command();self.assertEqual(code,2);self.assertIn('fixture_profile_b_output_failure',err)
        self.assertEqual(list((self.private/'automated-profile-b/candidates').iterdir()),[])
        self.assertFalse((self.private/'automated-profile-b/preparation.lock').exists())
        self.assertEqual(self.command()[0],0)

    def test_forged_inference_receipt_and_cross_version_workspace_are_refused(self):
        self.admit();self.assertEqual(self.command()[0],0)
        candidate=self.candidate();diagnosis=candidate/'diagnostics/profile-b-inference.private.json'
        original=diagnosis.read_bytes();receipt_path=candidate/'preparation-receipt.json';receipt_original=receipt_path.read_bytes()
        diagnosis.write_bytes(canonical_json({'fixed_positive_cells':0,'claim':'anonymous'}).encode())
        forged=load_json(receipt_path);forged['files']=fingerprint(candidate);forged['files'].pop('preparation-receipt.json')
        write_json(receipt_path,forged)
        state=(self.private/'automated-profile-b/status.json').read_bytes()
        code,_,err=self.command();self.assertEqual(code,2);self.assertIn('private_evidence_or_surfaces_changed',err)
        self.assertEqual((self.private/'automated-profile-b/status.json').read_bytes(),state)
        diagnosis.write_bytes(original);receipt_path.write_bytes(receipt_original)
        self.assertEqual(self.command()[0],0)
        other=native.PrivateNextInputsTests();other.setUp();self.addCleanup(other.doCleanups)
        other.capture();next_inputs.normalize(other.private);next_inputs.qualify_next(other.private)
        p.prepare(other.private,native.NOW)
        old=fingerprint(other.private/'automated')
        with self.assertRaisesRegex(DwrError,'separate_contract_workspace'):
            p.prepare(other.private,native.NOW,contract=a.PROFILE_B_CONTRACT)
        self.assertEqual(fingerprint(other.private/'automated'),old)
        self.assertFalse((other.private/'automated-profile-b').exists())


if __name__=='__main__':unittest.main()
