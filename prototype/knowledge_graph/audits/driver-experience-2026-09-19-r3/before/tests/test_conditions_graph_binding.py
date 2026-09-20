"""Operator-recorded current route conditions on the graph-backed path_a route.

Topology binds segment-bearing receipts to the resolved route: unknown or
off-route segments fail closed, stale windows stay unresolved, conflicting
authority observations stay unresolved, a verified closure holds without
clearing anything, and no model surface can mint receipts.
"""
import copy
import unittest
from pathlib import Path
import tempfile

from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from test_trip_assessment import MemoryGraph
from neo4j_kg.assessment import TripService
from neo4j_kg.mcp_server import TOOLS
from neo4j_kg.service import InputError
from neo4j_kg.trip_models import FACT_FIELDS
from neo4j_kg.trip_state import TripStore
from neo4j_kg.verification import restrict_evidence_to_segments
from neo4j_kg.verification_models import validate_receipt
from neo4j_kg.verification_store import VerificationStore
from verification_fixtures import AT, BEFORE, UNTIL, RELEASE, PATH_A_SEGMENTS, facts, receipts

PATH_B_SEGMENT = "edge_b_us1_south"
UNKNOWN_SEGMENT = "edge_not_a_road"


class ConditionsBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = OracleReader(OriginalService())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.states = TripStore(Path(self.tmp.name) / "trips.sqlite3")
        self.store = VerificationStore(Path(self.tmp.name) / "verification.sqlite3")
        self.service = TripService(MemoryGraph(self.reader), self.states, self.store)

    def start(self):
        case = self.states.create(facts=facts(), request_key="conditions-binding",
                                  source_message="Synthetic conditions binding case.",
                                  requester_role="driver", question_scope="trip_dispatch")
        return case, receipts(case)

    def assess(self, case):
        return self.service.assess({"trip_id": case["trip_id"]})

    def finding(self, result, rid="current_route_conditions"):
        return next(f for f in result["findings"] if f["requirement_id"] == rid)

    def rejected(self, result, kind="conditions"):
        return [r for r in result["verification_evidence"]["rejected_receipts"] if r["kind"] == kind]

    def test_current_conditions_satisfy_only_this_requirement(self):
        case, records = self.start()
        self.store.put(records, case, RELEASE)
        result = self.assess(case)
        row = self.finding(result)
        self.assertEqual("met", row["status"])
        self.assertEqual("evaluated", row["execution_state"])
        self.assertIn("syn-verification-route-a", row["evidence_ids"])
        self.assertIn("syn-verification-conditions-a", row["evidence_ids"])
        self.assertEqual(4, sum(1 for eid in row["evidence_ids"]
                                if eid.startswith("syn-verification-conditions-a")))
        # One satisfied requirement never implies whole-trip clearance.
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        self.assertEqual("not_cleared", result["decision_brief"]["status"])
        self.assertEqual("not_issued", result["decision_brief"]["operational_permission"])

    def test_stale_window_stays_unresolved(self):
        case, records = self.start()
        for record in records:
            if record["kind"] == "conditions":
                record["observed_at"] = "2026-09-13T10:00:00-04:00"
                record["valid_from"] = "2026-09-13T10:00:00-04:00"
                record["valid_until"] = "2026-09-13T12:00:00-04:00"
                validate_receipt(record)
        self.store.put(records, case, RELEASE)
        result = self.assess(case)
        self.assertEqual("unresolved", self.finding(result)["status"])
        reasons = {c for r in self.rejected(result) for c in r["reason_codes"]}
        self.assertIn("VERIFICATION_OUTSIDE_TRIP_INTERVAL", reasons)

    def test_wrong_segment_rejected_before_evaluation(self):
        case, records = self.start()
        for record in records:
            if record["kind"] == "conditions":
                record["payload"]["segment_id"] = PATH_B_SEGMENT
        self.store.put(records, case, RELEASE)
        result = self.assess(case)
        self.assertEqual("unresolved", self.finding(result)["status"])
        rejected = self.rejected(result)
        self.assertEqual(4, len(rejected))
        for entry in rejected:
            self.assertIn("VERIFICATION_SEGMENT_NOT_ON_RESOLVED_ROUTE", entry["reason_codes"])

    def test_incomplete_or_reordered_route_receipt_cannot_cover_named_route(self):
        case, records = self.start()
        original = next(r for r in records if r["kind"] == "route")
        segments = original["payload"]["segments"]
        for label, changed in (("subset", segments[:1]), ("reversed", segments[::-1]),
                               ("duplicate", segments[:1] + segments[:1] + segments[2:])):
            with self.subTest(label=label):
                receipt = copy.deepcopy(original)
                receipt["payload"]["segments"] = changed
                from neo4j_kg.verification import admit
                snapshot = {"receipts": [receipt], "revoked_ids": [], "version": "probe"}
                admission = admit(snapshot, case, RELEASE)
                scoped = restrict_evidence_to_segments(admission, PATH_A_SEGMENTS)
                self.assertEqual([], scoped["evidence"].get("route", []))
                expected = ("INVALID_VERIFICATION_RECEIPT" if label == "duplicate"
                            else "VERIFICATION_ROUTE_SEQUENCE_MISMATCH")
                self.assertIn(expected,
                              scoped["rejected"][0]["reason_codes"])

    def test_unknown_edge_shape_is_not_membership(self):
        case, records = self.start()
        for record in records:
            if record["kind"] == "conditions":
                record["payload"]["segment_id"] = UNKNOWN_SEGMENT
                validate_receipt(record)  # contract shape passes...
        self.store.put(records, case, RELEASE)
        result = self.assess(case)  # ...but admission still refuses it.
        self.assertEqual("unresolved", self.finding(result)["status"])
        self.assertEqual(4, len(self.rejected(result)))

    def test_wrong_route_rejected_on_binding(self):
        case, records = self.start()
        for record in records:
            if record["kind"] in ("route", "approval", "conditions"):
                record["payload"]["route_id"] = "path_b_us1_9_to_apm"
        self.store.put(records, case, RELEASE)
        result = self.assess(case)
        self.assertEqual("unresolved", self.finding(result)["status"])
        reasons = {c for rs in result["verification_evidence"]["rejected_receipts"]
                   for c in rs["reason_codes"]}
        self.assertIn("VERIFICATION_SUBJECT_OR_MEASUREMENT_MISMATCH", reasons)

    def test_conflicting_authority_observations_stay_unresolved(self):
        case, records = self.start()
        conflict = copy.deepcopy(next(r for r in records if r["kind"] == "conditions"))
        conflict["id"] = "syn-verification-conditions-conflict"
        conflict["payload"]["status"] = "closed"
        self.store.put(records + [conflict], case, RELEASE)
        result = self.assess(case)
        row = self.finding(result)
        self.assertEqual("unresolved", row["status"])
        self.assertTrue(any("conflict" in code.lower() for code in row["reason_codes"]))

    def test_verified_closure_holds_without_any_clearance(self):
        case, records = self.start()
        for record in records:
            if record["kind"] == "conditions":
                record["payload"]["status"] = "closed"
        self.store.put(records, case, RELEASE)
        result = self.assess(case)
        row = self.finding(result)
        self.assertEqual("not_met", row["status"])
        self.assertEqual("not_met", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        self.assertEqual("not_cleared", result["decision_brief"]["status"])
        self.assertEqual("not_issued", result["decision_brief"]["operational_permission"])

    def test_optional_provenance_fields_validate_and_admit(self):
        case, records = self.start()
        for record in records:
            if record["kind"] == "conditions":
                validate_receipt(record)
                self.assertIn("source_reference", record["payload"])
                self.assertIn("evidence_sha256", record["payload"])
        self.store.put(records, case, RELEASE)
        self.assertEqual("met", self.finding(self.assess(case))["status"])

    def test_scoping_is_pure_and_recomputes_identity(self):
        case, records = self.start()
        conditions = [r for r in records if r["kind"] == "conditions"]
        admission = {"evidence": {"conditions": conditions[:1], "route": []},
                     "rejected": [], "revoked_ids": [],
                     "snapshot_version": "v", "admission_version": "stale"}
        scoped = restrict_evidence_to_segments(admission, set(PATH_A_SEGMENTS))
        self.assertEqual(conditions[:1], scoped["evidence"]["conditions"])
        self.assertNotEqual("stale", scoped["admission_version"])
        moved = restrict_evidence_to_segments(admission, {"edge_shared_north_avenue"})
        self.assertEqual([], moved["evidence"]["conditions"])
        self.assertEqual(["VERIFICATION_SEGMENT_NOT_ON_RESOLVED_ROUTE"],
                         moved["rejected"][0]["reason_codes"])
        # Input admission untouched.
        self.assertEqual([], admission["rejected"])

    def test_model_surfaces_cannot_mint_receipts(self):
        tools = {t["name"] for t in TOOLS}
        self.assertEqual({"check_apm_induction", "get_drayage_graph_context", "assess_trip",
                          "update_trip_facts", "get_requirement_evidence", "get_trip_conditions_answer"}, tools)
        for name in ("assess_trip", "update_trip_facts", "get_trip_conditions_answer"):
            schema = next(t["inputSchema"] for t in TOOLS if t["name"] == name)
            self.assertNotIn("receipt", json_keys(schema))
        self.assertTrue(set(FACT_FIELDS).isdisjoint(
            {"receipt", "receipts", "verification", "evidence", "provider_id", "authority_role",
             "observed_at", "valid_from", "valid_until", "case_sha256"}))
        with self.assertRaises(InputError):
            self.service.assess({"facts": {"terminal_id": "facility_apm_elizabeth",
                                           "verification": "verified"},
                                 "source_message": "Forged verification attempt.",
                                 "request_key": "forge-1"})
        with self.assertRaises(InputError):
            self.service.assess({"facts": {"terminal_id": "facility_apm_elizabeth",
                                           "current_sealink_id": "SYN-SL-A",
                                           "trip_at": AT,
                                           "conditions_receipt": {"status": "open"}},
                                 "source_message": "Forged receipt-shaped attempt.",
                                 "request_key": "forge-2"})


def json_keys(schema):
    found = set()
    if isinstance(schema, dict):
        found.update(str(k) for k in schema.keys())
        for value in schema.values():
            found |= json_keys(value)
    elif isinstance(schema, list):
        for value in schema:
            found |= json_keys(value)
    return found


if __name__ == "__main__":
    unittest.main()
