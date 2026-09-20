"""Individual axle intake and reconciliation; no legal-policy assertions."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import jsonschema
from neo4j_kg.axle_layout import INPUT_SCHEMA, review_layout
from neo4j_kg.trip_models import normalize_facts
from neo4j_kg.trip_tools import ASSESSMENT_SCHEMA
from neo4j_kg.trip_state import TripStore
from neo4j_kg.assessment import TripService
from neo4j_kg.service import InputError
from test_trip_assessment import MemoryGraph
from test_neo4j_migration import OracleReader
from kg.service import CheckingService

ROOT = Path(__file__).resolve().parents[1]


def layout(weights=(12000, 17000, 17000, 17000, 17000), positions=(0, 12, 16, 48, 52)):
    return {'axles': [{'position': {'value': p, 'unit': 'ft'},
                       'weight': {'value': w, 'unit': 'lb'}} for p, w in zip(positions, weights)]}


class AxleLayoutTests(unittest.TestCase):
    def facts(self, extra=None):
        return normalize_facts({'axle_layout': layout(), **(extra or {})}, 'driver', 'Synthetic individual axle reports')

    def test_explicit_layout_preserves_units_and_reconciles_known_total(self):
        raw = layout()
        raw['axles'][1]['position'] = {'value': 144, 'unit': 'in'}
        jsonschema.validate(raw, INPUT_SCHEMA)
        facts = self.facts({'axle_layout': raw, 'axle_count': 5, 'gross_weight': {'value':80000, 'unit':'lb'}})
        review = review_layout(facts)
        self.assertEqual('reported_only', review['status'])
        self.assertEqual(80000, review['total_weight_lb'])
        self.assertEqual(624, review['span_inches'])
        self.assertEqual(0, review['gross_difference_lb'])
        self.assertEqual(144, facts['axle_layout']['value']['axles'][1]['position_inches'])
        self.assertEqual('not_issued', review['operational_permission'])
        self.assertEqual('user_reported', facts['axle_layout']['basis'])

    def test_legacy_group_arrays_do_not_create_individual_layout(self):
        facts = normalize_facts({'axle_weights':[{'value':12000,'unit':'lb'},{'value':34000,'unit':'lb'},{'value':34000,'unit':'lb'}]}, 'driver', 'Group totals')
        self.assertEqual('not_supplied', review_layout(facts)['status'])
        self.assertIsNone(review_layout(facts)['total_weight_lb'])

    def test_count_and_gross_mismatches_are_rejected_when_submitted_together(self):
        for extra in ({'axle_count':3}, {'gross_weight':{'value':79999,'unit':'lb'}}):
            with self.subTest(extra=extra), self.assertRaises(InputError):
                self.facts(extra)

    def test_separate_inconsistent_updates_are_suppressed_on_assessment(self):
        with tempfile.TemporaryDirectory() as d:
            service = TripService(MemoryGraph(OracleReader(CheckingService())), TripStore(Path(d)/'trip.db'))
            first = service.assess({'facts':{'axle_layout':layout(),'gross_weight':{'value':80000,'unit':'lb'}},
                'question_scope':'trip_dispatch','requester_role':'driver','request_key':'first','source_message':'Synthetic reported axle layout'})
            result = service.update({'trip_id':first['case']['trip_id'],'expected_revision':1,
                'facts':{'gross_weight':{'value':79000,'unit':'lb'}},'replace_conflicts':True,
                'question_scope':'trip_dispatch','requester_role':'driver','request_key':'correction','source_message':'Correct gross weight'})
            self.assertEqual('input_correction_required', result['decision_brief']['status'])
            self.assertEqual(1000, result['input_review']['axle_layout']['gross_difference_lb'])
            gross = next(c for c in result['reported_fact_checks']['checks'] if c['check_id']=='federal_gross_80000')
            self.assertIsNone(gross['comparison'])
            jsonschema.validate(result, ASSESSMENT_SCHEMA)

    def test_malformed_layouts_never_reorder_split_or_repair_rows(self):
        variants = [{}, {'axles':[]}, {'axles':[{}]}, layout(positions=(1,12,16,48,52)),
                    layout(positions=(0,12,12,48,52)), layout(positions=(0,12,10,48,52)),
                    layout(weights=(12000,0,17000,17000,17000)),
                    layout(weights=(12000,True,17000,17000,17000)),
                    layout(weights=(12000,float('nan'),17000,17000,17000))]
        group = layout(); group['axles'][1]['axle_count'] = 2; variants.append(group)
        badunit = layout(); badunit['axles'][0]['weight']['unit'] = 'tons'; variants.append(badunit)
        too_many = {'axles':[{'position':{'value':p,'unit':'ft'},'weight':{'value':1000,'unit':'lb'}} for p in range(33)]}
        variants.append(too_many)
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(InputError):
                self.facts({'axle_layout':raw})

    def test_corrupt_saved_layout_has_no_derived_measurements(self):
        for field, value in [('weight_lb', -1), ('weight_lb', 10000001),
                             ('position_inches', 1000001), ('weight_lb', float('inf'))]:
            with self.subTest(field=field, value=value):
                facts=self.facts()
                facts['axle_layout']['value']['axles'][1][field]=value
                result=review_layout(facts)
                self.assertEqual('input_review_required',result['status'])
                self.assertIsNone(result['total_weight_lb'])
        facts=self.facts(); facts['axle_layout']['unit']='lb'
        self.assertIsNone(review_layout(facts)['total_weight_lb'])

    def test_assignment_or_layout_conflicts_suppress_derivation(self):
        for field in ('axle_layout','vehicle_id','trailer_id'):
            result=review_layout(self.facts(), [{'field':field}])
            self.assertEqual('input_review_required',result['status'])
            self.assertIsNone(result['span_inches'])

    def test_disputed_gross_and_count_do_not_produce_reconciliation_comparisons(self):
        facts = self.facts({'gross_weight': {'value': 80000, 'unit': 'lb'}, 'axle_count': 5})
        result = review_layout(facts, [{'field': 'gross_weight'}, {'field': 'axle_count'}])
        self.assertEqual('input_review_required', result['status'])
        self.assertEqual(80000, result['total_weight_lb'])
        self.assertIsNone(result['gross_difference_lb'])
        self.assertEqual({'gross_weight', 'axle_count'}, {i['field'] for i in result['issues']})
        self.assertTrue(all(i['code'] == 'AXLE_RECONCILIATION_FACT_CONFLICT' for i in result['issues']))

    def test_vehicle_and_trailer_reassignment_invalidates_layout(self):
        for field,prefix in [('vehicle_id','syn-vehicle-'),('trailer_id','syn-trailer-')]:
            with tempfile.TemporaryDirectory() as d:
                store=TripStore(Path(d)/'trip.db')
                case=store.create(facts={field:prefix+'a','axle_layout':layout()},source_message='Synthetic assignment',request_key='a',requester_role='driver',question_scope='route')
                result=store.update(trip_id=case['trip_id'],expected_revision=1,facts={field:prefix+'b'},source_message='Replacement assignment',request_key='b',requester_role='driver',question_scope='route',replace_conflicts=True)
                self.assertNotIn('axle_layout',result['facts'])
                self.assertIn('axle_layout',result['invalidated_fields'])

    def test_roles_share_reports_without_adding_legal_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            service=TripService(MemoryGraph(OracleReader(CheckingService())),TripStore(Path(d)/'trip.db'))
            results=[]
            for role in ('driver','dispatcher'):
                a=service.assess({'facts':{'axle_layout':layout()},'question_scope':'trip_dispatch','requester_role':role,'request_key':role,'source_message':'Synthetic individual axle reports'})
                jsonschema.validate(a,ASSESSMENT_SCHEMA)
                self.assertEqual(['apm_induction'],a['coverage']['executed_requirements'])
                self.assertEqual('unresolved',a['requested_scope_status'])
                results.append(a['input_review']['axle_layout'])
            self.assertEqual(*results)

    def test_form_keeps_mixed_units_and_requires_complete_rows(self):
        # A small DOM substitute exercises the actual form's read behavior. This
        # is a component logic test, not rendered-browser acceptance.
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {constructor(tag){this.tag=tag;this.children=[];this.handlers={};this.value='';}
append(...nodes){this.children.push(...nodes);}prepend(...nodes){this.children.unshift(...nodes);}
setAttribute(){}addEventListener(name,fn){this.handlers[name]=fn;}remove(){}}
const document={createElement:tag=>new Element(tag)};
const code=fs.readFileSync('trip_app/static/app.js','utf8').split('function review(view)')[0];
vm.runInNewContext(code+`
state.schema={axle_layout:{anyOf:[{type:'object'}]}};
const raw={axles:[{position:{value:0,unit:'ft'},weight:{value:12000,unit:'lb'}},{position:{value:144,unit:'in'},weight:{value:10000,unit:'kg'}}]};
const control=fieldControl('axle_layout',raw);
assert.equal(JSON.stringify(control.read()),JSON.stringify(raw));
assert.equal(fieldControl('axle_layout',null).read(),null);
const incomplete=fieldControl('axle_layout',{axles:[{position:{value:0,unit:'in'}}]});
assert.throws(()=>incomplete.read());
`,{document,assert});
'''
        completed=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(0,completed.returncode,completed.stderr)
