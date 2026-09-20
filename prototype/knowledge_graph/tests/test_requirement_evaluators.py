"""End-to-end safety boundaries for every bounded requirement evaluator."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from test_trip_assessment import MemoryGraph
from neo4j_kg.assessment import TripService
from neo4j_kg.common import ArchiveError, EvidenceUnavailable
from neo4j_kg.service import InputError
from neo4j_kg.trip_state import TripStore
from neo4j_kg.verification_store import VerificationStore
from neo4j_kg.verification import admit, REQUIRED_KINDS
from neo4j_kg.verification_models import validate_receipt, case_fingerprint
from neo4j_kg.road_evaluators import evaluate_road
from verification_fixtures import facts, receipts, RELEASE, AT, BEFORE, UNTIL


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader=OracleReader(OriginalService())

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.states=TripStore(Path(self.tmp.name)/'trips.sqlite3')
        self.store=VerificationStore(Path(self.tmp.name)/'verification.sqlite3')
        self.graph=MemoryGraph(self.reader)
        self.service=TripService(self.graph,self.states,self.store)
        self.case=self.states.create(facts=facts(),request_key='start',source_message='Synthetic case',
                                     requester_role='driver',question_scope='trip_dispatch')
        self.records=receipts(self.case)

    def assessment(self):
        return self.service.assess({'trip_id':self.case['trip_id']})

    def finding(self,result,rid):
        return next(f for f in result['findings'] if f['requirement_id']==rid)

    def evidence(self):
        return {r['kind']:[r] for r in self.records}

    def test_all_eleven_have_real_predicates_and_no_operational_clearance(self):
        self.store.put(self.records,self.case,RELEASE)
        result=self.assessment()
        self.assertEqual('available',result['service_status'])
        for rid in REQUIRED_KINDS:
            with self.subTest(requirement=rid):
                row=self.finding(result,rid)
                self.assertEqual('evaluated',row['execution_state'])
                self.assertTrue(row['checks'])
                self.assertTrue(row['evidence_ids'])
                self.assertEqual('unresolved' if rid=='dtr_engine_policy' else 'met',row['status'])
        self.assertEqual('unresolved',result['requested_scope_status'])
        self.assertEqual('not_issued',result['decision_brief']['operational_permission'])
        self.assertTrue(result['evidence_package']['draft_supplements'])
        self.assertTrue(all(s['archive_graph_membership'] is False for s in result['evidence_package']['draft_supplements']))

    def test_no_receipts_never_turn_reports_into_verification(self):
        result=self.assessment()
        for rid in REQUIRED_KINDS:
            row=self.finding(result,rid)
            self.assertEqual('unresolved',row['status']);self.assertEqual('verification_required',row['execution_state'])
        self.assertEqual(['apm_induction'],result['coverage']['executed_requirements'])
        self.assertFalse(self.store.path.exists())

    def test_revoke_invalidates_assessment_identity_and_removes_positive(self):
        self.store.put(self.records,self.case,RELEASE)
        before=self.assessment()
        self.store.revoke('syn-verification-twic-a','Synthetic credential revoked')
        after=self.assessment()
        self.assertNotEqual(before['assessment_id'],after['assessment_id'])
        self.assertEqual('unresolved',self.finding(after,'driver_twic')['status'])
        self.assertIn('syn-verification-twic-a',after['verification_evidence']['revoked_ids'])

    def test_update_invalidates_all_old_receipts_with_explicit_rejections(self):
        self.store.put(self.records,self.case,RELEASE)
        updated=self.service.update({'trip_id':self.case['trip_id'],'expected_revision':1,'facts':{'vehicle_id':'syn-vehicle-new'},
            'source_message':'Explicit synthetic replacement','request_key':'replace','requester_role':'dispatcher',
            'question_scope':'trip_dispatch','replace_conflicts':True})
        self.assertFalse(updated['verification_evidence']['accepted_receipts'])
        self.assertEqual(len(self.records),len(updated['verification_evidence']['rejected_receipts']))
        self.assertIn('gross_weight',updated['case']['invalidated_fields'])
        for r in updated['verification_evidence']['rejected_receipts']:
            self.assertIn('VERIFICATION_CASE_OR_RELEASE_MISMATCH',r['reason_codes'])

    def test_conflicting_current_receipts_do_not_choose_a_winner(self):
        bad=copy.deepcopy(next(r for r in self.records if r['kind']=='twic'))
        bad['id']='syn-verification-twic-b';bad['payload']['status']='revoked'
        self.store.put(self.records+[bad],self.case,RELEASE)
        row=self.finding(self.assessment(),'driver_twic')
        self.assertEqual('unresolved',row['status'])
        self.assertIn('CONFLICTING_VERIFICATION_RECEIPTS',row['reason_codes'])

    def test_nonoverlapping_history_does_not_conflict_with_current_receipt(self):
        old=copy.deepcopy(next(r for r in self.records if r['kind']=='twic'))
        old.update(id='syn-verification-twic-old',observed_at='2026-09-12T12:00:00-04:00',
                   valid_from='2026-09-12T12:00:00-04:00',valid_until=BEFORE)
        old['payload']['status']='expired'
        self.store.put(self.records+[old],self.case,RELEASE)
        result=self.assessment()
        self.assertEqual('met',self.finding(result,'driver_twic')['status'])
        self.assertEqual(1,len(result['verification_evidence']['rejected_receipts']))

    def test_admission_time_identity_release_and_observation_boundaries(self):
        original=next(r for r in self.records if r['kind']=='twic')
        for mutation in ({'valid_until':AT},{'valid_from':UNTIL,'valid_until':'2026-09-14T18:00:00-04:00'},
                         {'observed_at':'2026-09-13T15:00:00-04:00'}, {'graph_release':'0'*64},
                         {'trip_revision':2},{'case_sha256':'0'*64}):
            with self.subTest(mutation=mutation):
                r=copy.deepcopy(original);r.update(mutation)
                result=admit({'version':'test','receipts':[r],'revoked_ids':[]},self.case,RELEASE,now=AT)
                self.assertFalse(result['evidence']);self.assertTrue(result['rejected'])
        r=copy.deepcopy(original);r['valid_from']=AT
        self.assertTrue(admit({'version':'test','receipts':[r],'revoked_ids':[]},self.case,RELEASE,now=AT)['evidence'])

    def test_future_observation_rejected_even_for_future_trip(self):
        r=next(r for r in self.records if r['kind']=='twic')
        result=admit({'version':'test','receipts':[r],'revoked_ids':[]},self.case,RELEASE,now='2026-09-12T12:00:00Z')
        self.assertIn('VERIFICATION_OBSERVATION_IN_FUTURE',result['rejected'][0]['reason_codes'])

    def test_subject_payload_mismatch_rejected_despite_case_fingerprint(self):
        self.records[0]['payload']['load_id']='syn-load-another'
        self.store.put(self.records,self.case,RELEASE)
        result=self.assessment()
        self.assertEqual('unresolved',self.finding(result,'axle_weight_evidence')['status'])
        self.assertIn('VERIFICATION_SUBJECT_OR_MEASUREMENT_MISMATCH',result['verification_evidence']['rejected_receipts'][0]['reason_codes'])

    def test_revocation_during_graph_read_fails_closed(self):
        self.store.put(self.records,self.case,RELEASE)
        original=self.graph.read
        def race(fn):
            result=original(fn);self.store.revoke('syn-verification-twic-a','During graph read');return result
        self.graph.read=race
        result=self.assessment()
        self.assertEqual('unavailable',result['service_status']);self.assertEqual([],result['findings'])
        self.assertFalse(result['verification_evidence']['accepted_receipts'])

    def test_store_outage_never_reuses_positive(self):
        self.store.put(self.records,self.case,RELEASE);self.assessment()
        with patch.object(self.store,'snapshot',side_effect=EvidenceUnavailable('secret details')):
            result=self.assessment()
        self.assertEqual('unavailable',result['service_status']);self.assertNotIn('secret',json.dumps(result))
        self.assertFalse(result['findings'])

    def test_driver_dispatch_pressure_changes_no_evaluation_semantics(self):
        self.store.put(self.records,self.case,RELEASE)
        driver=self.assessment()
        other=self.states.create(facts=facts(),request_key='dispatch',source_message='Send him now, dispatch pressure',
                                 requester_role='dispatcher',question_scope='trip_dispatch')
        self.store.put(receipts(other,'b'),other,RELEASE)
        dispatch=self.service.assess({'trip_id':other['trip_id']})
        def semantics(result):
            return [(r['requirement_id'],r['status'],r['reason_codes'],r.get('checks')) for r in result['findings']]
        self.assertEqual(semantics(driver),semantics(dispatch))

    def test_load_and_move_reassignments_invalidate_dependent_reports(self):
        for field in ('load_id','move_id','move_type'):
            with self.subTest(field=field):
                case=self.states.create(facts=facts()|{'appointment_reported':True,'transaction_release_reported':True},
                    request_key=field,source_message='Synthetic assignment',requester_role='driver',question_scope='trip_dispatch')
                changed=self.states.update(trip_id=case['trip_id'],expected_revision=1,facts={field:'empty_return' if field=='move_type' else 'syn-'+field[:-3]+'-new'},
                    request_key=field+'-change',source_message='Explicit reassignment',requester_role='driver',question_scope='trip_dispatch',replace_conflicts=True)
                self.assertNotIn('appointment_reported',changed['facts']);self.assertNotIn('transaction_release_reported',changed['facts'])

    def test_receipt_contract_rejects_impossible_or_forged_assertions(self):
        for kind, change in (('twic',lambda r:r.update(valid_until='2027-01-01T00:00:00Z')),
                             ('transaction',lambda r:r['payload'].update(customs_hold=True)),
                             ('scale',lambda r:r['payload'].update(gross_weight_lb=True)),
                             ('route',lambda r:r['payload']['segments'].append(copy.deepcopy(r['payload']['segments'][0]))),
                             ('appointment',lambda r:r['payload'].update(slot_end=BEFORE))):
            with self.subTest(kind=kind):
                r=copy.deepcopy(next(r for r in self.records if r['kind']==kind));change(r)
                with self.assertRaises(InputError):validate_receipt(r)
        for change in ({'provider_id':'syn-provider-forged'},{'mode':'production'},{'valid_until':BEFORE}):
            r=copy.deepcopy(self.records[0]);r.update(change)
            with self.assertRaises(InputError):validate_receipt(r)

    def test_road_negative_and_unknown_predicates(self):
        scenarios=[('dimensions_and_route','dimensions',lambda p:p.update(height_inches=163),'not_met'),
                   ('dimensions_and_route','route',lambda p:p['segments'][0].update(dimension_regime='unknown'),'unresolved'),
                   ('dimensions_and_route','route',lambda p:p.update(complete_sequence_verified=False),'unresolved'),
                   ('permit_eligibility','permit',lambda p:p.update(load_nondivisible=False),'not_met'),
                   ('permit_eligibility','permit',lambda p:p.update(authorized_limits={}),'unresolved'),
                   ('cross_authority_coverage','approval',lambda p:p.update(status='denied'),'not_met'),
                   ('cross_authority_coverage','approval',lambda p:p.update(authority='county'),'unresolved'),
                   ('current_route_conditions','conditions',lambda p:p.update(status='closed'),'not_met'),
                   ('current_route_conditions','conditions',lambda p:p.update(posting_checked=False),'unresolved'),
                   ('current_route_conditions','conditions',lambda p:p.update(posted_limits={'height_inches':160}),'not_met')]
        for rid,kind,change,expected in scenarios:
            with self.subTest(rid=rid,kind=kind):
                evidence=copy.deepcopy(self.evidence());change(evidence[kind][0]['payload'])
                self.assertEqual(expected,evaluate_road(rid,self.case['facts'],evidence,AT)['status'])

    def test_segment_overlap_conflicts_and_missing_authority_never_pass(self):
        for kind,rid in (('approval','cross_authority_coverage'),('conditions','current_route_conditions')):
            evidence=self.evidence();conflict=copy.deepcopy(evidence[kind][0]);conflict['id']+='-conflict'
            conflict['payload']['status']='denied' if kind=='approval' else 'closed'
            evidence[kind].append(conflict)
            self.assertEqual('unresolved',evaluate_road(rid,self.case['facts'],evidence,AT)['status'])
            evidence=self.evidence();new=copy.deepcopy(evidence['route'][0]['payload']['segments'][0]);new.update(segment_id='syn-segment-local',authority='local')
            evidence['route'][0]['payload']['segments'].append(new)
            self.assertEqual('unresolved',evaluate_road(rid,self.case['facts'],evidence,AT)['status'])

    def test_long_trailer_requires_specific_access_and_local_clause_scope(self):
        evidence=self.evidence();evidence['dimensions'][0]['payload']['semitrailer_length_inches']=636
        self.assertEqual('unresolved',evaluate_road('dimensions_and_route',self.case['facts'],evidence,AT)['status'])
        for segment in evidence['route'][0]['payload']['segments']:
            segment['long_semitrailer_access_verified']=True
        self.assertEqual('met',evaluate_road('dimensions_and_route',self.case['facts'],evidence,AT)['status'])
        evidence['route'][0]['payload']['segments'][0].update(dimension_regime='nj_local_102_standard',local_direct_terminal_access_verified=False)
        self.assertEqual('unresolved',evaluate_road('dimensions_and_route',self.case['facts'],evidence,AT)['status'])


if __name__=='__main__':unittest.main()
