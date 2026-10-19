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
from dwr import typo, common, disclosure, edition_rules, frozen, maintenance, pipeline, render, site_build, verify
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
                report=verify.Report();verify.check_maintenance(report)
                self.assertTrue(next(c for c in report.checks if c['check']=='declared_approvals_have_valid_receipts')['passed'])
                state=load_json(root/'data/status.json')
                self.assertEqual(state['candidate_state'],'approved_reference')
                self.assertEqual(next(e for e in load_json(root/'data/index.json')['editions'] if e['edition_id']==R2)['reference_release_status'],'approved')
                self.assertEqual(state['last_review']['state'],'approved')
                self.assertEqual(state['last_review']['date'],entry['approval_receipt']['reviewed_at'])
                html=(root/'site/dist/en/editions.html').read_text(encoding='utf-8')
                self.assertIn('2026-11-20',html)
                self.assertIn('Technical: approved',html)
                self.assertNotIn('&#x27;technical&#x27;',html)
                self.assertNotIn('published_at',html)

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
                render.cmd(R2);site_build.cmd(R2)
                self.assertIn('approval invalid',edition_rules.status_label(entry,'en'))
                self.assertIn('reference approval invalid',(root/'README.md').read_text(encoding='utf-8'))
                self.assertEqual(load_json(root/'data/status.json')['candidate_state'],'approval_invalid')
                self.assertEqual(next(e for e in load_json(root/'data/index.json')['editions'] if e['edition_id']==R2)['reference_release_status'],'approval_invalid')
                html=(root/'site/dist/en/editions.html').read_text(encoding='utf-8')
                self.assertIn('approval invalid',html)
                self.assertNotIn('2026-11-20',html)
                self.assertIsNone(load_json(root/'data/latest.json')['latest_published_edition'])
                report=verify.Report();verify.check_maintenance(report)
                self.assertFalse(next(c for c in report.checks if c['check']=='declared_approvals_have_valid_receipts')['passed'])

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

    def test_generated_date_order_and_conflicting_review_decisions_are_refused(self):
        entry=controls.ReviewTests().approved(R2,'a'*64)
        self.assertTrue(edition_rules.approved(entry,lambda _:'a'*64))
        entry['generated_at']='2026-11-21'
        self.assertFalse(edition_rules.approved(entry,lambda _:'a'*64))
        entry.pop('generated_at')
        for review in (None, {}, {'technical':'approved','editorial':'awaiting_review','distribution':'approved'}):
            entry['review_status']=review
            self.assertFalse(edition_rules.approved(entry,lambda _:'a'*64))

    def test_catalog_stripping_removes_planning_and_verify_rejects_mutable_fields(self):
        specimen={'dates':{'published_at':None,'next_review_target':{}},'status':'candidate_not_reviewed','files':[{'status':'candidate','rows':1}]}
        stripped=edition_rules.strip_operational_state(specimen)
        self.assertNotIn('published_at',stripped['dates'])
        self.assertNotIn('next_review_target',stripped['dates'])
        self.assertNotIn('status',stripped)
        self.assertNotIn('status',stripped['files'][0])
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root);path=root/'data/editions'/R2/'catalog.json';original=load_json(path)
            with patch.object(verify,'REPO_ROOT',root):
                for key in ('availability_status','status','next_review_target'):
                    bad=copy.deepcopy(original)
                    if key=='next_review_target':bad['dates'][key]={}
                    else:bad[key]='candidate'
                    write_json(path,bad);report=verify.Report();verify.check_catalog(report,path.parent)
                    state=next(c for c in report.checks if c['check']=='observation_dates_valid_and_operational_state_external')
                    self.assertFalse(state['passed'],key)

    def test_french_status_names_the_edition_keeps_r1_context_and_required_spacing(self):
        edition=render.Edition(R2)
        label=edition_rules.status_label(edition.entry,'fr')
        self.assertIn('accessible publiquement ; référence non approuvée',label)
        self.assertEqual(typo.punctuation_violations(label),0)
        self.assertEqual(typo.punctuation_violations('candidate locale; référence'),1)
        self.assertEqual(typo.punctuation_violations('`locale; code` https://example.invalid/a; « citation; exacte » &amp;'),0)
        for name in ('README.fr.md','README.md'):
            text=(REPO_ROOT/name).read_text(encoding='utf-8')
            self.assertIn('r2',text[:650]);self.assertIn('r1',text[:650])
        text=render.case_rows(edition,'fr')
        self.assertIn('(EN ; FR : `/ai-usage-policy/`)',text)

    def test_visible_source_metadata_is_required_even_when_invisible_title_keeps_it(self):
        import re
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root)
            path=root/'figures'/R2/'G09-gautierdorval.com.fr.compact.svg'
            original=path.read_text(encoding='utf-8')
            altered,count=re.subn(r'<text\b[^>]*>[^<]*data/editions/[^<]*</text>', '', original)
            self.assertGreater(count,0)
            self.assertIn('<desc',altered)
            path.write_text(altered,encoding='utf-8')
            with patch.object(verify,'REPO_ROOT',root),patch.object(render,'REPO_ROOT',root):
                report=verify.Report();verify.check_rendering(report,R2)
            result=next(c for c in report.checks if c['check']=='figures_carry_dates_edition_source_and_alt')
            self.assertFalse(result['passed'])

    def test_private_preparation_reconciles_resource_active_days_with_joint_source(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp);eid=prepare_inputs(private);path=private/'working'/eid/'qualified.json';source=load_json(path)
            resource=next(r for r in source['resources'] if r.get('counts'))
            resource['counts']['days']+=1
            write_json(path,source)
            result=maintenance.prepare(private,datetime(2026,11,17,tzinfo=timezone.utc))
            self.assertEqual(result['outcome'],'validation_failed')
            self.assertEqual(result['reason'],'qualified_counts_differ_from_joint')

    def test_verify_refuses_declared_approval_without_a_valid_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);copy_candidate(root)
            with patch.object(common,'REPO_ROOT',root),patch.object(verify,'REPO_ROOT',root):
                config=load_json(root/'config/editions.json')
                entry=next(e for e in config['editions'] if e['edition_id']==R2)
                report=verify.Report();verify.check_maintenance(report)
                self.assertTrue(next(c for c in report.checks if c['check']=='declared_approvals_have_valid_receipts')['passed'])
                entry['reference_release_status']='approved'
                for receipt in (None, {}, [], {'decisions':'approved'}):
                    entry['approval_receipt']=receipt
                    write_json(root/'config/editions.json',config)
                    report=verify.Report();verify.check_maintenance(report)
                    self.assertFalse(next(c for c in report.checks if c['check']=='declared_approvals_have_valid_receipts')['passed'])
                    self.assertTrue(next(c for c in report.checks if c['check']=='latest_points_only_to_reviewed_publication')['passed'])

    def test_punctuation_checks_quote_code_and_inline_boundaries(self):
        for text in ('a;b', 'a!b', 'a?b', '« citation; exacte »;', '“literal; text”; next',
                     '`a;b`; suite', 'mot</em>;suite'):
            with self.subTest(text=text):self.assertEqual(typo.punctuation_violations(text),1)
        for text in ('« citation; exacte » ; suite', '`a;b` ; suite', '&amp;',
                     'https://example.invalid/a;b', 'a ; b ! c ?', '"literal; text"'):
            with self.subTest(text=text):self.assertEqual(typo.punctuation_violations(text),0)
        self.assertEqual(typo.html_punctuation_violations('<p>mot<em>visible</em>;suite</p>'),1)
        self.assertEqual(typo.html_punctuation_violations('<p>&laquo; citation; exacte &raquo;;suite</p>'),1)
        self.assertEqual(typo.html_punctuation_violations('<pre>a;b</pre><script>a;b</script><style>a;b</style><p><code>a;b</code> ; suite &amp; fin</p>'),0)

    def test_verify_checks_rendered_french_prose(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);page=root/'site/dist/fr/index.html';page.parent.mkdir(parents=True)
            with patch.object(verify,'REPO_ROOT',root):
                for text,expected in (('<p>mot<em>visible</em>;suite</p>',False),
                                      ('<p>mot<em>visible</em> ; suite</p>',True)):
                    page.write_text(text,encoding='utf-8')
                    report=verify.Report();verify.check_site(report)
                    self.assertEqual(next(c for c in report.checks if c['check']=='french_site_punctuation_has_required_spacing')['passed'],expected)
