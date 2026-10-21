"""Real CLI and shared-boundary regressions for the closed distribution contract.

Temporary public copies only. Python network attempts are refused in CLI children;
this is cooperative offline qualification, not an OS security sandbox.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch
from tests import __init__
from tests.test_audit_followup import copy_candidate, R1, R2
from dwr import common, distribution as d, frozen, gate, pipeline, site_build, verify
from dwr.common import REPO_ROOT, DwrError

BOOT = '''import os,runpy,sys
os.environ.pop("DWR_PRIVATE_ROOT",None)
def offline(event,args):
 if event.startswith(("socket.connect","socket.getaddrinfo","socket.gethostby","http.client.connect","urllib.Request")):
  raise PermissionError("network_forbidden_by_local_test")
sys.addaudithook(offline)
sys.argv=["scripts/dwr.py",*sys.argv[1:]]
runpy.run_path(sys.argv[0],run_name="__main__")
'''

def cli(root, *args):
    return subprocess.run([sys.executable, '-I', '-B', '-c', BOOT, *args], cwd=root,
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@contextmanager
def patched(root):
    with ExitStack() as stack:
        for module in (common, frozen, pipeline, site_build, verify):
            stack.enter_context(patch.object(module, 'REPO_ROOT', root))
        stack.enter_context(patch.object(site_build, 'DIST', root/'site/dist'))
        yield


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'candidate'
        self.root.mkdir()
        copy_candidate(self.root)
        for name in ('analysis', 'scripts'):
            shutil.copytree(REPO_ROOT/name, self.root/name, ignore=shutil.ignore_patterns('__pycache__'))
        result = cli(self.root, 'build-site')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.valid = snapshot(self.root/'site/dist')

    def refused(self, diagnostic=True):
        for command in ('build-site', 'verify'):
            result = cli(self.root, command)
            self.assertNotEqual(result.returncode, 0, (command, result.stdout))
            if diagnostic:
                self.assertIn('distribution_', result.stdout+result.stderr)
                self.assertNotIn('Traceback', result.stdout+result.stderr)
        self.assertEqual(snapshot(self.root/'site/dist'), self.valid)

    def test_T01_T08_T16_T27_extras_refused_by_actual_commands(self):
        extras = [f'data/editions/{R2}/unexpected.csv', f'figures/{R2}/unexpected.csv',
                  f'figures/{R2}/png/unexpected.png', 'config/unexpected.json',
                  'schemas/extra.schema.json', f'data/editions/{R2}/.hidden',
                  f'data/editions/{R2}/backup.bak', 'config/unexpected.tmp', 'config/unexpected.zip']
        for name in extras:
            with self.subTest(name=name):
                path = self.root/name
                path.write_bytes(b'')
                self.refused()
                path.unlink()
        # A structurally valid image is still not admitted by its extension.
        path = self.root/f'figures/{R2}/png/unexpected.png'
        path.write_bytes((self.root/f'figures/{R2}/png/G02.en.png').read_bytes())
        self.refused(); path.unlink()
        # Actual local Git makes the untracked nature explicit.
        self.git('init', '-q')
        path=self.root/f'data/editions/{R2}/untracked.csv';path.write_text('fixture\n')
        self.assertIn('untracked.csv', self.git('ls-files', '--others', '--exclude-standard').decode())
        self.refused()

    def test_T04_T05_T14_T15_unknown_empty_and_private_editions(self):
        for parent in ('data/editions', 'figures'):
            for populated in (False, True):
                with self.subTest(parent=parent, populated=populated):
                    path=self.root/parent/'2099-01-01_2099-02-01-r1';path.mkdir()
                    if populated:(path/'fixture.csv').write_bytes(b'fixture\n')
                    self.refused();shutil.rmtree(path)
        registry=self.root/'config/editions.json';original=registry.read_bytes()
        doc=json.loads(original);private=copy.deepcopy(doc['editions'][-1])
        private.update(edition_id='2099-01-01_2099-02-01-r1',availability_status='private_candidate')
        doc['editions'].append(private);registry.write_text(json.dumps(doc),encoding='utf-8')
        # A private entry alone grants no new distributable directory.
        d.check_sources(self.root)
        path=self.root/'data/editions'/private['edition_id'];path.mkdir()
        self.refused();path.rmdir()
        doc=json.loads(original);doc['editions'][-1]['availability_status']='private_candidate'
        registry.write_text(json.dumps(doc),encoding='utf-8')
        historical=self.root/f'data/editions/{R2}/metrics.json';before=historical.read_bytes()
        historical.write_bytes(before+b' ')
        self.refused();historical.write_bytes(before);registry.write_bytes(original)

    def test_T09_T12_missing_changed_and_relearned_contract(self):
        names=[f'data/editions/{R1}/catalog.json',f'data/editions/{R2}/disclosure.json',
               f'figures/{R2}/G02.csv','config/scope-registry.csv','schemas/coverage.schema.json',
               'config/publication-inventory.json','config/historical-editions.json']
        for name in names:
            with self.subTest(missing=name):
                p=self.root/name;data=p.read_bytes();p.unlink();self.refused();p.write_bytes(data)
        for name in [f'data/editions/{R2}/metrics.json', f'figures/{R2}/G02.csv',
                     f'data/editions/{R2}/SHA256SUMS.txt', 'config/publication-inventory.json']:
            with self.subTest(changed=name):
                p=self.root/name;data=p.read_bytes();p.write_bytes(data+b' ');self.refused();p.write_bytes(data)
        p=self.root/'config/publication-inventory.json';data=p.read_bytes();doc=json.loads(data)
        injected=f'data/editions/{R2}/learned.csv';(self.root/injected).write_bytes(b'fixture')
        doc['releases'][-1]['files'][injected]=d.sha(b'fixture');p.write_text(json.dumps(doc),encoding='utf-8')
        self.refused();(self.root/injected).unlink();p.write_bytes(data)
        p=self.root/'config/editions.json';data=p.read_bytes()
        for invalid in (b'{"editions":[],"editions":[]}', b'[]',b'{"editions":[null]}',b'{broken'):
            p.write_bytes(invalid)
            for command in ('build-site','verify'):
                result=cli(self.root,command)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('distribution_',result.stdout+result.stderr)
                self.assertNotIn('Traceback',result.stdout+result.stderr)
        p.write_bytes(data)
        with patch.object(Path,'iterdir',side_effect=PermissionError('sensitive fixture')):
            with self.assertRaises(DwrError) as error:d.check_sources(self.root)
        self.assertNotIn('sensitive', str(error.exception))

    def test_T13_T24_T26_T29_T31_valid_deterministic_and_late_output(self):
        with patched(self.root):
            d.check_sources(self.root)
            self.assertIn(f'data/editions/{R2}/disclosure.json',self.valid)
            self.assertIn(f'data/editions/{R2}/delta-report.json',self.valid)
            path=self.root/'site/dist/stale.csv';path.write_text('fixture')
            self.assertFalse(verify.cmd(R2)['passed'])
            site_build.cmd(R2)
            self.assertEqual(snapshot(self.root/'site/dist'),self.valid)
            site_build.cmd(R2)
            self.assertEqual(snapshot(self.root/'site/dist'),self.valid)
            plan,_=site_build.output_plan(R2)
            # No learned output manifest can legitimize the late file.
            path.write_text('fixture')
            with self.assertRaises(DwrError):d.check_output(self.root/'site/dist',plan)
            (self.root/'site/dist/output-manifest.json').write_text(json.dumps({'stale.csv':d.sha(b'fixture')}))
            self.assertFalse(verify.cmd(R2)['passed'])

    def test_T22_T23_T25_source_changes_stage_injection_and_failures(self):
        with patched(self.root):
            write=site_build.write_plan
            def inject(stage,plan):
                write(stage,plan);(stage/'unexpected.csv').write_bytes(b'fixture')
            def source_change(stage,plan):
                write(stage,plan)
                p=self.root/'config/operations.json';p.write_bytes(p.read_bytes()+b' ')
            def registry_change(stage,plan):
                write(stage,plan)
                p=self.root/'config/publication-inventory.json';p.write_bytes(p.read_bytes()+b' ')
            def wrong_output(stage,plan):
                write(stage,plan);(stage/'en/index.html').write_bytes(b'changed')
            for action in (inject,source_change,registry_change,wrong_output):
                before=snapshot(self.root/'config')
                with self.subTest(action=action.__name__),patch.object(site_build,'write_plan',action):
                    with self.assertRaises(DwrError):site_build.cmd(R2)
                    self.assertEqual(snapshot(self.root/'site/dist'),self.valid)
                for name,data in before.items():(self.root/'config'/name).write_bytes(data)
            with patch.object(site_build,'render_pages',side_effect=OSError('synthetic generation failure')):
                with self.assertRaises(OSError):site_build.cmd(R2)
                self.assertEqual(snapshot(self.root/'site/dist'),self.valid)
            original=Path.rename
            def fail_stage(path,target):
                if path.name.startswith('.build-'):raise OSError('synthetic installation failure')
                return original(path,target)
            with patch.object(Path,'rename',fail_stage):
                with self.assertRaises(DwrError) as error:site_build.cmd(R2)
                self.assertEqual(error.exception.code,'site_install_failed')
                self.assertEqual(snapshot(self.root/'site/dist'),self.valid)
            self.assertFalse((self.root/'site/.build.lock').exists())
            self.assertFalse(list((self.root/'site').glob('.build-*')))
            # A preexisting recovery marker is never removed as stale automatically.
            lock=self.root/'site/.build.lock';lock.write_text('different owner')
            with self.assertRaises(DwrError):site_build.cmd(R2)
            self.assertEqual(lock.read_text(),'different owner')

    def test_T23_abrupt_stop_retains_recoverable_backup_and_refuses_restart(self):
        program = BOOT.split('sys.argv=["scripts/dwr.py"')[0] + """
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'analysis'))
from dwr import site_build
def abrupt(stage,target,backup):
 target.rename(backup)
 os._exit(86)
site_build.install=abrupt
site_build.cmd("2026-09-15_2026-10-15-r2")
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',program],cwd=self.root,capture_output=True,timeout=90)
        self.assertEqual(result.returncode,86,result.stderr)
        self.assertTrue((self.root/'site/.build.lock').is_file())
        self.assertEqual(snapshot(self.root/'site/.dist-backup'),self.valid)
        self.assertFalse((self.root/'site/dist').exists())
        self.assertEqual(len(list((self.root/'site').glob('.build-*'))),1)
        restarted=cli(self.root,'build-site')
        self.assertNotEqual(restarted.returncode,0)
        self.assertIn('site_install_recovery_required',restarted.stderr)
        self.assertEqual(snapshot(self.root/'site/.dist-backup'),self.valid)

    def test_T19_T21_unsafe_names_and_case_normalization(self):
        for name in ('/absolute','../x','a/../x','a//x','C:/x','a\\x','a/NUL.txt','a/x.','a/e\u0301.csv'):
            with self.subTest(name=name),self.assertRaises(DwrError):d.canonical_path(name)
        for names in (['a/x','a/x'],['data/x','DATA/x'],['a/é','a/É']):
            with self.assertRaises(DwrError):d.unique_names(names)
        # Actual Git tree entries can represent names Windows cannot materialize.
        contents=d.check_sources(self.root)
        entries=[(p,'100644','blob') for p in contents]+[(p,'040000','tree') for p in d.parents(contents)]
        for extra in [('data/INDEX.json','100644','blob'),('data/e\u0301.csv','100644','blob'),
                      ('data/link','120000','blob'),('data/submodule','160000','commit')]:
            with self.subTest(extra=extra),self.assertRaises(DwrError):d.check_git([*entries,extra],contents.__getitem__)

    @unittest.skipUnless(os.name=='nt','Windows junction is a platform-specific branch')
    def test_T20_real_windows_junction(self):
        destination=Path(self.temp.name)/'outside';destination.mkdir()
        (destination/'never-read.csv').write_bytes(b'fixture')
        link=self.root/'data/junction-fixture'
        quote=lambda p: "'"+str(p).replace("'", "''")+"'"
        command="$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path "+quote(link)+" -Target "+quote(destination)+" | Out-Null"
        result=subprocess.run(['pwsh','-NoProfile','-Command',command],capture_output=True)
        # Capability failures are explicit skips, never surrogate passes.
        if result.returncode:self.skipTest('junction creation unavailable')
        try:self.refused()
        finally:os.rmdir(link)
        self.assertEqual((destination/'never-read.csv').read_bytes(),b'fixture')

    @unittest.skipIf(os.name=='nt','POSIX FIFO and unprivileged symlink branch; Windows junction tested separately')
    def test_T20_real_posix_symlink_fifo(self):
        link=self.root/'data/link';link.symlink_to(self.root/'config',target_is_directory=True)
        self.refused();link.unlink()
        os.mkfifo(self.root/'data/fifo');self.refused();(self.root/'data/fifo').unlink()

    def test_T32_diagnostic_never_echoes_unknown_sensitive_name_or_contents(self):
        marker='synthetic-sensitive-marker'
        path=self.root/f'data/editions/{R2}'/(marker+'.csv');path.write_text(marker)
        for command in ('verify','build-site'):
            result=cli(self.root,command)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn(marker,result.stdout+result.stderr)

    def test_T42_rendered_readiness_and_historical_state_are_consistent(self):
        with patched(self.root):
            registry=json.loads((self.root/'config/editions.json').read_bytes())
            historical=next(e for e in registry['editions'] if e['edition_id']==R1)
            self.assertIsNone(historical['approval_receipt'])
            self.assertEqual(historical['review_lifecycle'],'historical_frozen_no_approval_recorded')
            self.assertTrue(all(historical['review_status'][k]=='not_approved' for k in ('technical','editorial','distribution')))
            status=json.loads((self.root/'data/status.json').read_bytes())
            self.assertEqual(status['preparation']['code_ready_scope'],'private_prepare_next_synthetic_qualification_only')
            self.assertFalse(status['preparation']['planning_activated'])
            self.assertIsNone(json.loads((self.root/'data/latest.json').read_bytes())['latest_published_edition'])
            for lang,words in (('fr',['Éditions','préparation privée','planification est inactive']),
                               ('en',['Editions','Private preparation','scheduling is inactive'])):
                text=(self.root/f'site/dist/{lang}/editions.html').read_text(encoding='utf-8')
                for word in words:self.assertIn(word,text)
                self.assertNotIn('Ã',text)
                self.assertNotIn('corrections in progress',text)
                self.assertNotIn('corrections en cours',text)

    def git(self,*args):
        result=subprocess.run(['git','-C',str(self.root),*args],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        return result.stdout

    def test_T17_T18_T28_actual_git_history_and_package_without_site(self):
        # Isolated real objects, no remote, no private lock and no copied source history.
        shutil.rmtree(self.root/'site/dist')
        config=self.root/'config/publication-gate.json';doc=json.loads(config.read_bytes())
        doc.pop('published_root',None);doc.pop('distribution_baseline',None)
        config.write_text(json.dumps(doc),encoding='utf-8')
        self.git('init','-q');self.git('config','user.name','Synthetic test')
        self.git('config','user.email','test@example.invalid')
        self.git('add','--','.')
        self.git('commit','-q','-m','Synthetic baseline')
        baseline=self.git('rev-parse','HEAD').decode().strip()
        report=gate.check_ref(self.root,'HEAD',gate.Secrets())
        self.assertTrue(report['passed'],report)
        self.assertEqual(report['distribution_trees_checked'],1)
        doc['published_root']='GautierDorval/dual-web-reference@'+baseline
        config.write_text(json.dumps(doc),encoding='utf-8')
        path=self.root/f'data/editions/{R2}/unexpected.csv';path.write_text('fixture')
        self.git('add','--','config/publication-gate.json',path.relative_to(self.root).as_posix())
        self.git('commit','-q','-m','Synthetic extra')
        report=gate.check_ref(self.root,'HEAD',gate.Secrets())
        self.assertFalse(report['passed']);self.assertTrue(any(f['category']=='distribution_file_set_mismatch' for f in report['findings']))
        path.unlink();self.git('add','-u');self.git('commit','-q','-m','Remove synthetic extra')
        report=gate.check_ref(self.root,'HEAD',gate.Secrets())
        self.assertFalse(report['passed']);self.assertEqual(report['distribution_trees_checked'],3)
        self.assertTrue(any(f['category']=='distribution_file_set_mismatch' for f in report['findings']))
        self.assertFalse((self.root/'site/dist').exists())
        # The private manifest boundary uses the same fixed figure contract.
        with patched(self.root):
            payload=self.root/f'data/editions/{R2}';figures=self.root/f'figures/{R2}'
            required=set(p.name for p in payload.iterdir())-{'SHA256SUMS.txt','delta-report.json'}
            d.check_candidate(payload,figures,R2,required,{'SHA256SUMS.txt','delta-report.json'})
            entry = next(e for e in json.loads((self.root/'config/editions.json').read_bytes())['editions'] if e['edition_id'] == R2)
            self.assertGreater(pipeline._prepare_manifest(entry,payload,figures)['files'],0)
            (figures/'unexpected.csv').write_bytes(b'fixture')
            with self.assertRaises(DwrError):pipeline._prepare_manifest(entry,payload,figures)


    def test_T23_keyboard_interrupt_retains_lock_stage_and_backup(self):
        with patched(self.root):
            original = Path.rename
            def interrupt(path, target):
                if path.name.startswith('.build-'):
                    raise KeyboardInterrupt()
                return original(path, target)
            with patch.object(Path, 'rename', interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    site_build.cmd(R2)
            self.assertFalse((self.root/'site/dist').exists())
            self.assertTrue((self.root/'site/.build.lock').exists())
            self.assertEqual(snapshot(self.root/'site/.dist-backup'), self.valid)
            stages = list((self.root/'site').glob('.build-*'))
            self.assertEqual(len(stages), 1)
            self.assertEqual(snapshot(stages[0]), self.valid)
            with self.assertRaises(DwrError) as error:
                site_build.cmd(R2)
            self.assertEqual(error.exception.code, 'site_install_recovery_required')

    def test_T25_stage_injection_during_final_source_recheck_is_refused(self):
        with patched(self.root):
            original = site_build.source_inputs
            def recheck():
                result = original()
                for stage in (self.root/'site').glob('.build-*'):
                    (stage/'late.csv').write_bytes(b'fixture')
                return result
            with patch.object(site_build, 'source_inputs', recheck):
                with self.assertRaises(DwrError):
                    site_build.cmd(R2)
            self.assertEqual(snapshot(self.root/'site/dist'), self.valid)

    def test_T17_pinned_baseline_ancestors_and_invalid_pins(self):
        shutil.rmtree(self.root/'site/dist')
        config = self.root/'config/publication-gate.json'
        doc = json.loads(config.read_bytes())
        doc.pop('published_root', None)
        doc.pop('distribution_baseline', None)
        config.write_text(json.dumps(doc), encoding='utf-8')
        extra = self.root/f'data/editions/{R2}/old-extra.csv'
        extra.write_bytes(b'fixture')
        self.git('init','-q')
        self.git('config','user.name','Synthetic test')
        self.git('config','user.email','test@example.invalid')
        self.git('add','--','.')
        self.git('commit','-q','-m','Synthetic historical state')
        root = self.git('rev-parse','HEAD').decode().strip()
        extra.unlink()
        doc['published_root'] = 'GautierDorval/dual-web-reference@' + root
        config.write_text(json.dumps(doc), encoding='utf-8')
        self.git('add','-u')
        self.git('commit','-q','-m','Synthetic admitted baseline')
        baseline = self.git('rev-parse','HEAD').decode().strip()
        pin = 'GautierDorval/dual-web-reference@' + baseline
        doc['distribution_baseline'] = pin
        config.write_text(json.dumps(doc), encoding='utf-8')
        self.git('add','-u')
        self.git('commit','-q','-m','Synthetic pinned successor')
        with patch.object(d, 'BASELINE_PIN_SHA256', d.sha(pin.encode())):
            report = gate.check_ref(self.root, 'HEAD', gate.Secrets(), pins=gate.admitted_pins(config))
        self.assertTrue(report['passed'], report)
        self.assertEqual(report['distribution_trees_checked'], 2)
        self.assertEqual(report['distribution_historical_ancestors_pinned'], 1)
        # A changed baseline cannot inherit the old trusted pin.
        with patch.object(d, 'BASELINE_PIN_SHA256', d.sha(b'different pin')):
            report = gate.check_ref(self.root, 'HEAD', gate.Secrets(), pins=gate.admitted_pins(config))
        self.assertFalse(report['passed'])
        self.assertTrue(any(f['category']=='distribution_history_contract_invalid' for f in report['findings']))
        missing = 'GautierDorval/dual-web-reference@' + 'a'*40
        doc['distribution_baseline'] = missing
        config.write_text(json.dumps(doc), encoding='utf-8')
        self.git('add','-u')
        self.git('commit','-q','-m','Synthetic unavailable baseline')
        with patch.object(d, 'BASELINE_PIN_SHA256', d.sha(missing.encode())):
            report = gate.check_ref(self.root, 'HEAD', gate.Secrets(), pins=gate.admitted_pins(config))
        self.assertFalse(report['passed'])
        self.assertTrue(any(f['category']=='distribution_history_contract_invalid' for f in report['findings']))


if __name__=='__main__':unittest.main()
