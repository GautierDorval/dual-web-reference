"""Inactive synthetic decision evidence: calendar, noninterference and reconstruction."""
import copy
import unittest
from tests import __init__
from dwr import future_projection as f
from dwr.common import DwrError, REPO_ROOT, SITE_IDS, IDENTITY_TIERS, canonical_json
from dwr.dates import window_from_strings

NATURE='synthetic_only_not_observed_traffic'
WINDOW=window_from_strings('2099-01-01','2099-02-01')
DAY='2099-01-02'
RESOURCE={'site_id':SITE_IDS[0],'path':'/synthetic','family':'policy','main_population':True}
ROW={'date_utc':DAY,'site_id':SITE_IDS[0],'path':'/synthetic','actor_family':'fixture','actor_name':'Fixture',
     'actor_role':'ai_training','stored_identity_tier':f.TIER,'http_method':'GET','http_status':200,
     'request_count':3,'measurement_epoch_id':'fixture-epoch'}
EVIDENCE={'archive_status':'archived','observation_status':'observed','source_qualification':'qualified',
          'coverage_status':'partial_declared','evidence_status':'declared'}


def coverage(rows=(), evidence=None, **kwargs):
    return f.coverage_synthetic(rows,[RESOURCE],window=WINDOW,evidence=evidence or {},nature=NATURE,**kwargs)


def demand(rows=(),option='U0',window=WINDOW):
    return f.on_demand_synthetic(rows,window=window,nature=NATURE,option=option)


class FutureCoverageTests(unittest.TestCase):
    def test_T34_T35_T36_calendar_zero_source_archive_and_withholding(self):
        result=coverage()
        days=result['coverage']
        self.assertEqual([r['date_utc'] for r in days],[d.isoformat() for d in WINDOW.dates()])
        self.assertEqual(len(days),31)
        self.assertTrue(all(r['request_count'] is None for r in days))
        observed=coverage(evidence={DAY:EVIDENCE})['coverage'][1]
        self.assertEqual(observed['request_count'],0)
        self.assertEqual(observed['coverage_status'],'partial_declared')
        self.assertEqual(observed['suppression_status'],'not_suppressed')
        for change in ({'observation_status':'observation_unavailable'}, {'source_qualification':'not_qualified'},
                       {'evidence_status':'not_established'}, {'coverage_status':'observation_unavailable'}):
            row=coverage(evidence={DAY:{**EVIDENCE,**change}})['coverage'][1]
            self.assertIsNone(row['request_count']);self.assertEqual(row['suppression_status'],'observation_unavailable')
            self.assertEqual(row['archive_status'],'archived')
        for archive in f.COVERAGE_EVIDENCE_FIELDS['archive_status']:
            row=coverage([ROW],{DAY:{**EVIDENCE,'archive_status':archive}})['coverage'][1]
            self.assertEqual(row['request_count'],3)
        row=coverage([ROW],{DAY:EVIDENCE},withhold_selected=True)['coverage'][1]
        self.assertIsNone(row['request_count']);self.assertEqual(row['suppression_status'],'withheld_not_zero')
        self.assertEqual(coverage(withhold_selected=True)['coverage'][0]['suppression_status'],'observation_unavailable')
        for item in days:
            self.assertEqual(set(item),set(f.COVERAGE_SCHEMA['required']))
        for change in ({'coverage_status':'invented'},{'source_qualification':True}):
            with self.assertRaises(DwrError):coverage(evidence={DAY:{**EVIDENCE,**change}})

    def test_T37_T38_all_output_bytes_ignore_protected_rows_and_reject_complements(self):
        baseline=canonical_json(coverage([ROW],{DAY:EVIDENCE}))
        baseline_auto=canonical_json(f.prepare_synthetic([ROW],[RESOURCE],nature=NATURE))
        baseline_demand=canonical_json(demand())
        variants=[{'actor_role':'user_initiated_fetch'}, {'actor_role':'unknown'},
                  *({'stored_identity_tier':t} for t in IDENTITY_TIERS if t!=f.TIER),
                  {'http_method':'HEAD'}, {'http_method':'POST'}, {'http_status':404}]
        for change in variants:
            for count in (1,97,0):
                with self.subTest(change=change,count=count):
                    protected={**ROW,**change,'request_count':count,'measurement_epoch_id':'protected-fixture',
                               'private_input_digest':'private-fixture','source_diagnostic':'private-fixture'}
                    rows=[ROW,protected]
                    self.assertEqual(canonical_json(coverage(rows,{DAY:EVIDENCE})),baseline)
                    self.assertEqual(canonical_json(f.prepare_synthetic(rows,[RESOURCE],nature=NATURE)),baseline_auto)
                    self.assertEqual(canonical_json(demand(rows)),baseline_demand)
        forbidden=('input_digest','private_input_digest','request_count','capture_count','all_source_count',
                   'rejected_count','measurement_epoch_id','epoch_definitions','reason_code','catalog.measurement.days')
        for field in forbidden:
            with self.subTest(field=field),self.assertRaises(DwrError):
                coverage(evidence={DAY:{**EVIDENCE,field:'must-not-appear'}})
        with self.assertRaises(DwrError):coverage(evidence={'2099-02-01':EVIDENCE})
        with self.assertRaises(DwrError):coverage([{**ROW,'date_utc':'2099-02-01'}])

    def test_T39_arithmetic_counterexamples_do_not_grant_public_approval(self):
        a={**ROW,'actor_role':'user_initiated_fetch','request_count':1}
        b={**a,'date_utc':'2099-01-03','site_id':SITE_IDS[1],'request_count':5}
        c={**a,'date_utc':'2099-01-31','site_id':SITE_IDS[2],'request_count':7}
        total=lambda rows,window=WINDOW:sum(demand(rows,'U1',window)['by_attribution_tier'].values())
        # Zero/one, revision and removing a single contributing site all reveal one.
        self.assertEqual(total([a])-total([]),1)
        self.assertEqual(total([a,b])-total([b]),1)
        self.assertEqual(total([a,b,c])-total([b,c]),1)
        # Adjacent overlapping windows reveal the outgoing cell when incoming is known zero.
        shifted=window_from_strings('2099-01-03','2099-02-02')
        self.assertEqual(total([a,b,c])-total([a,b,c],shifted),1)
        # Public global complements and a denominator reconstruct a withheld count.
        automated=12;global_total=automated+total([a]);self.assertEqual(global_total-automated,1)
        automated_share=automated/global_total
        self.assertEqual(round(automated/automated_share)-automated,1)
        # A previous release of two named contributions defeats later aggregation.
        previously_public_b,previously_public_c=5,7
        self.assertEqual(total([a,b,c])-previously_public_b-previously_public_c,1)
        output=demand([a,b,c],'U1')
        self.assertFalse(output['public_output_approved'])
        self.assertEqual(len(output['risks']),7)
        self.assertNotIn('site_id',str(output));self.assertNotIn('date_utc',str(output))
        self.assertEqual(demand(),demand([a,b,c]))

    def test_T40_T41_tiers_initiation_nature_no_activation_or_mutation(self):
        paths=[REPO_ROOT/'data/latest.json',REPO_ROOT/'config/editions.json',REPO_ROOT/'config/small-cell-policy.json']
        before=[p.read_bytes() for p in paths]
        rows=[{**ROW,'actor_role':'user_initiated_fetch','stored_identity_tier':tier,'request_count':i+1}
              for i,tier in enumerate(IDENTITY_TIERS)]
        output=demand(rows,'U1')
        self.assertEqual(output['by_attribution_tier'],{tier:i+1 for i,tier in enumerate(IDENTITY_TIERS)})
        self.assertEqual(output['initiation_provenance'],'unknown')
        self.assertFalse(output['reference_approval'])
        self.assertEqual(output['activation'],'inactive_requires_owner_decision_and_qualification')
        self.assertEqual(demand([ROW],'U1')['by_attribution_tier'],{})
        self.assertEqual(coverage([ROW],{DAY:EVIDENCE})['nature'],NATURE)
        for function,args in ((f.coverage_synthetic,([],[])),(f.on_demand_synthetic,([],))):
            kwargs={'window':WINDOW,'nature':'observed_traffic'}
            if function==f.coverage_synthetic:kwargs['evidence']={}
            with self.assertRaises(DwrError):function(*args,**kwargs)
        self.assertEqual(before,[p.read_bytes() for p in paths])


if __name__=='__main__':unittest.main()
