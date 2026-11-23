"""Public M2 entrypoints, historical preservation and fail-closed distribution."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from tests import __init__
from tests.test_audit_followup import copy_candidate, unreviewed_m2_fixture, R1, R2
from tests.test_distribution import cli, snapshot
from dwr import automated, automated_public as public, distribution, edition_rules
from dwr.common import REPO_ROOT, DwrError, canonical_json, load_json


class AutomatedPublicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'candidate'
        self.root.mkdir()
        copy_candidate(self.root)
        unreviewed_m2_fixture(self.root)
        for name in ('analysis', 'scripts', '.github'):
            shutil.copytree(REPO_ROOT/name, self.root/name, ignore=shutil.ignore_patterns('__pycache__'))
        self.target = self.root/'data/editions'/public.EDITION

    def run_ok(self, *args):
        result = cli(self.root, *args)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_actual_offline_commands_reproduce_m2_without_mutating_m1(self):
        before = {f'{prefix}/{eid}': snapshot(self.root/prefix/eid)
                  for prefix in ('data/editions', 'figures') for eid in (R1,R2)}
        payload = snapshot(self.target)
        for command in ('analyze','render','build-site','verify'):
            self.run_ok(command)
        first = snapshot(self.root/'site/dist')
        self.run_ok('render'); self.run_ok('build-site')
        self.assertEqual(first, snapshot(self.root/'site/dist'))
        self.assertEqual(payload, snapshot(self.target))
        for key, data in before.items(): self.assertEqual(data, snapshot(self.root/key))
        self.assertEqual(len(payload),54)
        self.assertFalse(any('daily-family' in p or 'diagnostic' in p or p.endswith('.html') for p in payload))
        doc = load_json(self.target/'projection.json')
        self.assertEqual(doc['metrics']['selected_requests'],223)
        self.assertIsNone(doc['on_demand']['request_count'])
        self.assertIsNone(doc['comparison']['growth'])
        latest = load_json(self.root/'data/latest.json')
        self.assertEqual(latest['latest_candidate_edition'],public.EDITION)
        self.assertIsNone(latest['latest_published_edition'])
        self.assertEqual(load_json(self.root/'data/status.json')['latest_available_data_date'],'2026-11-14')
        for lang in ('en','fr'):
            for name in ('explorer','figures','editions','m1-explorer','m1-figures'):
                self.assertIn(f'{lang}/{name}.html',first)
            current=first[f'{lang}/explorer.html'].decode()
            self.assertIn(public.EDITION,current)
            self.assertNotIn('<a href="https://gautierdorval.com', current)
            self.assertIn('m1-explorer.html',current)
            self.assertIn(R2,first[f'{lang}/m1-explorer.html'].decode())
        catalog=load_json(self.target/'catalog.json')
        self.assertEqual(catalog['operational_state_source'],'../../../config/editions.json')
        self.assertNotIn('reports',catalog)

    def test_unadmitted_surfaces_and_changes_refuse_before_replacing_site(self):
        self.run_ok('build-site')
        before = snapshot(self.root/'site/dist')
        mutations = [
            (self.target/'daily-family-summary.csv', b'not-admitted\n'),
            (self.target/'diagnostics/private.json', b'{}'),
            (self.target/'report.fr.html', b'private report'),
            (self.target/'resource-summary.csv', (self.target/'resource-summary.csv').read_bytes()+b'\n'),
            (self.root/'config/automated-distribution.json', b'{}'),
        ]
        for path, content in mutations:
            with self.subTest(path=path.name):
                previous=path.read_bytes() if path.exists() else None
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
                try:
                    for command in ('build-site','verify'):
                        result=cli(self.root,command)
                        self.assertNotEqual(result.returncode,0)
                        self.assertIn('distribution_',result.stdout+result.stderr)
                        self.assertNotIn('Traceback',result.stdout+result.stderr)
                    self.assertEqual(before,snapshot(self.root/'site/dist'))
                finally:
                    if previous is None: path.unlink()
                    else: path.write_bytes(previous)
                    if path.parent.name=='diagnostics': path.parent.rmdir()

    def test_v1_schema_and_newly_learned_manifest_are_not_admitted(self):
        original=load_json(self.target/'projection.json')
        changed=copy.deepcopy(original);changed['contract']=automated.CONTRACT
        with self.assertRaises(DwrError): public.payload_files(changed,public.EDITION)
        changed=copy.deepcopy(original);changed['tables']['family_daily']=[]
        with self.assertRaises(DwrError): public.payload_files(changed,public.EDITION)
        manifest=self.root/'config/automated-distribution.json'
        doc=load_json(manifest)
        injected=f'data/editions/{public.EDITION}/learned.csv'
        (self.root/injected).write_bytes(b'new data')
        doc['files'][injected]=hashlib.sha256(b'new data').hexdigest()
        manifest.write_text(canonical_json(doc),encoding='utf-8')
        with self.assertRaises(DwrError): distribution.check_sources(self.root)

    def test_approval_is_separate_and_covers_nested_m2_figures(self):
        config=load_json(self.root/'config/editions.json')
        entry=next(e for e in config['editions'] if e['edition_id']==public.EDITION)
        payload=edition_rules.payload_manifest(public.EDITION,self.root)
        self.assertEqual(len(payload['files']),54)
        self.assertTrue(any('/figures/' in name for name in payload['files']))
        self.assertIsNone(edition_rules.latest_pointer([entry],lambda _:payload['digest']))
        entry.update(availability_status='publicly_accessible', reference_release_status='approved',
                     approved_release_at='2026-11-22')
        self.assertIsNone(edition_rules.latest_pointer([entry],lambda _:payload['digest']))
        entry['approval_receipt']={'edition_id':public.EDITION,'scope':'edition_payload_and_figures',
            'reviewer':'synthetic reviewer','evidence':['synthetic test only'], 'reviewed_at':'2026-11-22',
            'decisions':{k:'approved' for k in ('technical','editorial','distribution')},'content_digest':payload['digest']}
        entry['review_status']=entry['approval_receipt']['decisions'].copy()
        self.assertEqual(edition_rules.latest_pointer([entry],lambda _:payload['digest']),public.EDITION)
        figure=next(self.target.glob('figures/*.svg'))
        figure.write_bytes(figure.read_bytes()+b' ')
        changed=edition_rules.payload_manifest(public.EDITION,self.root)['digest']
        self.assertIsNone(edition_rules.latest_pointer([entry],lambda _:changed))

    def test_registry_cannot_admit_an_unrecognized_profile(self):
        config=load_json(self.root/'config/editions.json')
        entry=next(e for e in config['editions'] if e['edition_id']==public.EDITION)
        entry['data_contract']=automated.CONTRACT
        (self.root/'config/editions.json').write_text(canonical_json(config),encoding='utf-8')
        with self.assertRaises(DwrError): distribution.check_sources(self.root)

    def test_display_candidate_does_not_advance_the_private_preparation_cursor(self):
        from dwr import next_inputs
        from unittest.mock import patch
        private=self.root/'private-fixture'
        private.mkdir()
        with patch.object(next_inputs,'REPO_ROOT',self.root), patch('dwr.pipeline.REPO_ROOT',self.root):
            self.assertEqual(str(next_inputs.window(private).start),'2026-10-15')
            self.assertEqual(next_inputs.initial_state(private)['latest_available_data_date'],'2026-10-14')
            state=private/'preparation/status.json'
            state.parent.mkdir()
            state.write_text(canonical_json({'pending_window_start':'2026-11-15',
                'latest_available_data_date':'2026-11-14'}),encoding='utf-8')
            self.assertEqual(str(next_inputs.window(private).start),'2026-11-15')
            self.assertEqual(next_inputs.initial_state(private)['latest_available_data_date'],'2026-11-14')

    def test_legacy_writers_refuse_m2_before_mutation(self):
        before=snapshot(self.target)
        private=Path(self.temp.name)/'private'
        private.mkdir()
        registry=self.root/'config/editions.json'
        config=load_json(registry)
        entry=next(e for e in config['editions'] if e['edition_id']==public.EDITION)
        for availability in ('local_candidate','publicly_accessible'):
            entry['availability_status']=availability
            registry.write_text(canonical_json(config),encoding='utf-8')
            for command in ('normalize','qualify','project-public','acquire-readonly','prepare-edition'):
                with self.subTest(availability=availability,command=command):
                    args=[command]
                    if command!='prepare-edition':args+=['--private-root',str(private)]
                    result=cli(self.root,*args)
                    self.assertNotEqual(result.returncode,0)
                    # The public projection CLI first protects every exposed edition.
                    expected=('public_or_historical_edition_immutable'
                              if command=='project-public' and availability=='publicly_accessible'
                              else 'automated_edition_requires_its_own_contract')
                    self.assertIn(expected,result.stderr)
                    self.assertEqual(before,snapshot(self.target))
                    self.assertEqual(list(private.iterdir()),[])


if __name__=='__main__': unittest.main()
