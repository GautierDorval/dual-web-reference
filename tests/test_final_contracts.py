import copy
import tempfile
import unittest
from pathlib import Path
from tests import __init__
from dwr import disclosure, edition_rules, mdlite, public_checks, typo
from dwr.common import REPO_ROOT, load_json, read_csv, write_text, csv_text

class FinalContractTests(unittest.TestCase):
    def test_empty_history_and_unknown_daily_stratum_are_not_assessed(self):
        policy=load_json(REPO_ROOT/'config/small-cell-policy.json')
        tables=disclosure.tables(REPO_ROOT/'data/editions/2026-09-15_2026-10-15-r2')
        self.assertFalse(disclosure.assess(tables,{'status':'assessed','releases':[]},policy)['allowed'])
        tables['daily'][0]['actor_role']='unqualified_new_role'
        self.assertIn('daily_stratum_not_qualified',disclosure.assess(tables,disclosure.inventory(),policy)['reasons'])

    def test_malformed_approval_never_crashes_or_qualifies(self):
        for decisions in (None, [], 'approved', 1):
            entry={'availability_status':'publicly_accessible','reference_release_status':'approved','approved_release_at':'2026-10-19',
                   'approval_receipt':{'decisions':decisions}}
            self.assertFalse(edition_rules.approved(entry,lambda e:'a'*64))

    def test_nested_window_comparability_distinguishes_revision_from_next_period(self):
        versions={k:'same-attested-contract' for k in edition_rules.COMPARABILITY_KEYS}
        a={'edition_id':'2027-01-15_2027-02-15-r1','versions':versions,'coverage_status':'complete_declared',
           'dates':{'period_start_inclusive':'2027-01-15','period_end_exclusive':'2027-02-15'}}
        b=copy.deepcopy(a);b.update(edition_id='2027-03-15_2027-04-15-r1',dates={'period_start_inclusive':'2027-03-15','period_end_exclusive':'2027-04-15'})
        self.assertEqual(edition_rules.comparable(a,b),(True,[]))
        b['versions']['classifier_recorded']=['unknown']
        self.assertFalse(edition_rules.comparable(a,b)[0])

    def test_typography_preserves_code_quotes_and_urls(self):
        text='16 384 caractères ; « 16 384 » `16 384` https://example.org/16384'
        result=typo.fr(text)
        self.assertIn('16\u202f384 caractères',result)
        self.assertIn('16 384 »',result.replace('\u202f»',' »'))
        self.assertIn('`16 384`',result)
        self.assertIn('https://example.org/16384',result)
        self.assertEqual(result,typo.fr(result))

    def test_measured_links_are_copyable_and_mail_channel_is_retained(self):
        rendered=mdlite.render('[resource](https://gautierdorval.com/llms.txt) [report](mailto:info@pagup.com)')
        self.assertNotIn('href="https://gautierdorval.com',rendered)
        self.assertIn('<code>https://gautierdorval.com/llms.txt</code>',rendered)
        self.assertIn('href="mailto:info@pagup.com"',rendered)

    def test_public_marginals_recompute_and_detect_balanced_cell_error(self):
        source=REPO_ROOT/'data/editions/2026-09-15_2026-10-15-r2'
        self.assertTrue(all(public_checks.reconcile_tables(source).values()))
        # Shift one count between two resources while keeping the grand total.
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)
            for name in disclosure.TABLES.values(): (target/name).write_bytes((source/name).read_bytes())
            rows=read_csv(target/'consultations.csv');a=rows[0];b=next(r for r in rows if r['resource_id']!=a['resource_id'] and int(r['request_count'])>1)
            a['request_count']=str(int(a['request_count'])+1);b['request_count']=str(int(b['request_count'])-1)
            write_text(target/'consultations.csv',csv_text(list(rows[0]),rows))
            self.assertFalse(public_checks.reconcile_tables(target)['public_resource_marginals_recomputed'])

    def test_explorer_has_unique_ids_and_forms_reference_tables(self):
        from html.parser import HTMLParser
        from unittest.mock import patch
        from dwr import site_build
        class Elements(HTMLParser):
            def __init__(self): super().__init__(); self.ids=[]; self.tables=set(); self.targets=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if 'id' in attrs: self.ids.append(attrs['id'])
                if tag=='table': self.tables.add(attrs.get('id'))
                if tag=='form': self.targets.append(attrs.get('data-table'))
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(site_build,'DIST',Path(temp)):
                site_build.explorer_page('2026-09-15_2026-10-15-r2','fr')
            parsed=Elements();parsed.feed((Path(temp)/'fr/explorer.html').read_text(encoding='utf-8'))
            self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
            self.assertEqual(set(parsed.targets),parsed.tables)
