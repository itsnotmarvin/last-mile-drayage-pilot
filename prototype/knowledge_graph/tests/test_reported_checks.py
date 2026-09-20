"""Boundary and adversarial checks for comparisons; no legal-policy assertions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kg.service import CheckingService
from neo4j_kg.assessment import TripService
from neo4j_kg.common import digest
from neo4j_kg.decision_brief import render_trip_report
from neo4j_kg.reported_checks import catalog, CATALOG_VERSION, evaluate_reported_checks
from neo4j_kg.requirements import applicable_requirements
from neo4j_kg.trip_tools import ASSESSMENT_SCHEMA
from neo4j_kg.trip_state import TripStore
from test_neo4j_migration import OracleReader
import test_trip_assessment as fixtures


class ReportedCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader=OracleReader(CheckingService())

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.states=TripStore(Path(self.tmp.name)/'trips.sqlite3')
        self.graph=fixtures.MemoryGraph(self.reader)
        self.service=TripService(self.graph,self.states)
        self.sequence=0

    def assess(self,facts=None,scope='trip_dispatch',role='driver'):
        self.sequence+=1
        return self.service.assess({'facts':facts or {},'question_scope':scope,'requester_role':role,
                                    'source_message':'Synthetic reported facts for source comparison.', 'request_key':'check-'+str(self.sequence)})

    def rows(self,result):
        return {r['check_id']:r for r in result['reported_fact_checks']['checks']}

    def rerun(self,result,**overrides):
        kwargs=dict(case=result['case'],evidence=result['evidence_package'],versions=result['versions'],
                    selected=applicable_requirements(result['case']['facts'],result['case']['question_scope']))
        kwargs.update(overrides)
        return evaluate_reported_checks(**kwargs)

    def test_all_numeric_definitions_below_at_above_with_signed_difference(self):
        for spec in catalog()['checks']:
            if spec['kind']!='numeric':continue
            field=spec['fields'][0]
            for delta,relation,status in [(-1,'below','comparison_only'),(0,'at','comparison_only'),(1,'above','attention_required')]:
                with self.subTest(check=spec['id'],delta=delta):
                    facts={field:{'value':spec['reference_value']+delta,'unit':'in' if spec['unit']=='inch' else 'lb'},**spec.get('when',{})}
                    result=self.assess(facts);row=self.rows(result)[spec['id']]
                    self.assertEqual(status,row['status'])
                    self.assertEqual(delta,row['comparison']['difference'])
                    self.assertEqual(relation,row['comparison']['relation'])
                    self.assertEqual('unresolved',result['requested_scope_status'])
                    self.assertEqual('not_issued',result['decision_brief']['operational_permission'])
                    self.assertNotIn(spec['requirement_id'],result['coverage']['executed_requirements'])

    def test_mixed_units_and_separate_road_terminal_contexts(self):
        result=self.assess({'height':{'value':175,'unit':'in'},'width':{'value':12,'unit':'ft'}})
        rows=self.rows(result)
        self.assertEqual(13,rows['nj_loaded_height']['comparison']['difference'])
        self.assertEqual('above',rows['nj_loaded_height']['comparison']['relation'])
        self.assertEqual('below',rows['terminal_height_195']['comparison']['relation'])
        self.assertIn('does not replace',rows['terminal_height_195']['context'])
        self.assertEqual(144,rows['nj_width_102']['comparison']['reported'])
        self.assertEqual('attention_required',rows['terminal_width_132']['status'])
        self.assertEqual(2,len([a for a in result['reported_fact_checks']['priority_actions'] if 'width' in a['action'].lower()]))

    def test_metric_weight_uses_existing_normalization_without_invented_tolerance(self):
        result=self.assess({'gross_weight':{'value':40000,'unit':'kg'}})
        row=self.rows(result)['federal_gross_80000']
        self.assertAlmostEqual(88184.90487395103,row['comparison']['reported'])
        self.assertEqual('above',row['comparison']['relation'])

    def test_missing_values_never_become_negative_or_pass(self):
        result=self.assess()
        for row in result['reported_fact_checks']['checks']:
            if row['kind']!='manual':
                self.assertEqual('missing_facts',row['status'])
                self.assertIsNone(row['comparison'])
        self.assertEqual([],result['reported_fact_checks']['priority_actions'])

    def test_nonpositive_or_invalid_measurements_do_not_compare(self):
        result=self.assess({'height':{'value':0,'unit':'in'}})
        self.assertEqual('input_review_required',self.rows(result)['nj_loaded_height']['status'])
        for value,unit in [(True,'inch'),(-1,'inch'),(float('nan'),'inch'),(175,'ft')]:
            case=copy.deepcopy(result['case']);case['facts']['height'].update(value=value,unit=unit)
            rows={r['check_id']:r for r in self.rerun(result,case=case)['checks']}
            self.assertEqual('input_review_required',rows['nj_loaded_height']['status'])
            self.assertIsNone(rows['nj_loaded_height']['comparison'])

    def test_every_prerequisite_yes_no_unknown_and_category_selection(self):
        for spec in catalog()['checks']:
            if spec['kind']!='prerequisite':continue
            field=spec['fields'][0]
            for reported,expected in [(spec['expected'],'reported_unverified'),(not spec['expected'],'attention_required'),(None,'missing_facts')]:
                with self.subTest(check=spec['id'],reported=reported):
                    result=self.assess({field:reported,**spec.get('when',{})})
                    self.assertEqual(expected,self.rows(result)[spec['id']]['status'])
                    self.assertEqual('unresolved',result['requested_scope_status'])
        for permit in (None,'none','other'):
            result=self.assess({'permit_type':permit,'gross_weight':{'value':95000,'unit':'lb'}})
            self.assertNotIn('ocean_permit_gross_90000',self.rows(result))
            self.assertIn('ocean_permit_gross_90000',result['reported_fact_checks']['not_run_check_ids'])

    def test_known_problem_precedes_generic_missing_trip_questions(self):
        result=self.assess({'terminal_id':'facility_apm_elizabeth','appointment_reported':False})
        self.assertIn('appointment',result['decision_brief']['next_steps'][0])
        self.assertEqual('trip_at',result['next_questions'][0]['field'])
        self.assertEqual('not_cleared',result['decision_brief']['status'])

    def test_complete_but_ambiguous_axle_arrays_never_trigger_bridge_calculation(self):
        result=self.assess({'gross_weight':{'value':80000,'unit':'lb'},'axle_count':5,
                            'axle_weights':[{'value':12000,'unit':'lb'},{'value':34000,'unit':'lb'},{'value':34000,'unit':'lb'}],
                            'axle_spacings':[{'value':4,'unit':'ft'},{'value':30,'unit':'ft'}]})
        row=self.rows(result)['axle_and_bridge_gap']
        self.assertEqual('manual_review_required',row['status']);self.assertIsNone(row['comparison'])
        self.assertIn('does not retain its equation',row['context'])
        self.assertIn('individual axle or axle-group',row['context'])

    def test_dtr_model_year_and_timestamps_never_create_eligibility_or_live_conditions(self):
        for year in (2006,2013,2014,2026):
            result=self.assess({'engine_model_year':year,'dtr_reported':True,'route_conditions_checked_at':'2026-09-13T10:00:00-04:00'})
            rows=self.rows(result)
            self.assertEqual('manual_review_required',rows['dtr_interpretation_gap']['status'])
            self.assertIsNone(rows['dtr_interpretation_gap']['comparison'])
            self.assertEqual('manual_review_required',rows['current_conditions_gap']['status'])
            self.assertEqual('unresolved',result['requested_scope_status'])

    def test_conflicting_height_and_permit_category_are_suppressed(self):
        first=self.assess({'height':{'value':175,'unit':'in'},'permit_type':'nj_ocean_container_annual','gross_weight':{'value':95000,'unit':'lb'}})
        self.sequence+=1
        updated=self.service.update({'trip_id':first['case']['trip_id'],'expected_revision':1,'requester_role':'driver','question_scope':'trip_dispatch',
                                     'source_message':'Conflicting report','request_key':'conflict','facts':{'height':{'value':160,'unit':'in'},'permit_type':'none'}})
        rows=self.rows(updated)
        self.assertEqual('input_review_required',rows['nj_loaded_height']['status'])
        self.assertIsNone(rows['nj_loaded_height']['comparison'])
        self.assertEqual('input_review_required',rows['ocean_permit_gross_90000']['status'])
        self.assertIsNone(rows['ocean_permit_gross_90000']['comparison'])

    def test_old_inconsistent_source_is_not_used_for_arithmetic(self):
        result=self.assess({'height':{'value':168,'unit':'in'}})
        case=copy.deepcopy(result['case']);case['facts']['height']['source_text']='14 ft 7 in high'
        package=self.rerun(result,case=case,rejected_fields=['height'])
        row=next(c for c in package['checks'] if c['check_id']=='nj_loaded_height')
        self.assertEqual('input_review_required',row['status']);self.assertIsNone(row['comparison'])

    def test_source_text_locator_identity_and_release_changes_suppress_comparison(self):
        result=self.assess({'height':{'value':175,'unit':'in'}})
        for field,value in [('source_text','The limit is 200 inches'),('locator','wrong page'),('source_id','different-source')]:
            evidence=copy.deepcopy(result['evidence_package'])
            next(s for s in evidence['sources'] if s['clause_id']=='reg_nj_height_limit')[field]=value
            row=next(r for r in self.rerun(result,evidence=evidence)['checks'] if r['check_id']=='nj_loaded_height')
            self.assertEqual('source_review_required',row['status']);self.assertIsNone(row['comparison'])
        evidence=copy.deepcopy(result['evidence_package']);evidence['sources']=[s for s in evidence['sources'] if s['clause_id']!='reg_nj_height_limit']
        row=next(r for r in self.rerun(result,evidence=evidence)['checks'] if r['check_id']=='nj_loaded_height')
        self.assertEqual('source_review_required',row['status'])
        package=self.rerun(result,versions={**result['versions'],'graph_release':'a'*64})
        self.assertEqual('unavailable',package['status']);self.assertEqual([],package['checks'])

    def test_catalog_copy_cannot_change_later_calculations_or_version(self):
        c=catalog();self.assertEqual(CATALOG_VERSION,digest(c))
        c['checks'][0]['reference_value']=999
        result=self.assess({'height':{'value':175,'unit':'in'}})
        self.assertEqual(162,self.rows(result)['nj_loaded_height']['comparison']['reference'])
        self.assertEqual(CATALOG_VERSION,result['versions']['reported_check_catalog'])

    def test_scope_unsupported_terminal_and_role_do_not_bypass_boundaries(self):
        driver=self.assess({'height':{'value':175,'unit':'in'}})
        dispatcher=self.assess({'height':{'value':175,'unit':'in'}},role='dispatcher')
        self.assertEqual(driver['reported_fact_checks'],dispatcher['reported_fact_checks'])
        induction=self.assess(fixtures.BASE,scope='induction')
        self.assertEqual([],induction['reported_fact_checks']['checks'])
        self.assertEqual('met',induction['requested_scope_status'])
        other=self.assess({'terminal_id':'synthetic_other_terminal','height':{'value':175,'unit':'in'}})
        self.assertEqual([],other['reported_fact_checks']['checks'])
        self.assertIn('unsupported_terminal_requirements',other['coverage']['gaps'])

    def test_schema_and_outage_have_no_cached_comparisons(self):
        import jsonschema
        result=self.assess({'height':{'value':175,'unit':'in'},'twic_reported':False})
        jsonschema.validate(result,ASSESSMENT_SCHEMA)
        self.graph.available=False
        unavailable=self.service.assess({'trip_id':result['case']['trip_id']})
        jsonschema.validate(unavailable,ASSESSMENT_SCHEMA)
        self.assertEqual([],unavailable['reported_fact_checks']['checks'])
        self.assertEqual([],unavailable['reported_fact_checks']['priority_actions'])
        self.assertEqual('assessment_unavailable',unavailable['decision_brief']['status'])

    def test_report_includes_comparisons_without_granting_permission(self):
        result=self.assess({'height':{'value':175,'unit':'in'}})
        html=render_trip_report(result)
        self.assertIn('175',html);self.assertIn('162',html)
        self.assertIn('Operational permission: not issued.',html)
        self.assertIn('Applicability and operational eligibility remain unresolved.',html)
