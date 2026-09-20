"""Conversation, evidence, and MCP contracts; assertions are prototype controls."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from kg.service import CheckingService as OriginalService
from test_neo4j_migration import OracleReader
from neo4j_kg.assessment import TripService, evaluate_trip
from neo4j_kg.common import EvidenceUnavailable
from neo4j_kg.evidence import requirement_evidence
from neo4j_kg.mcp_server import Session, TOOLS
from neo4j_kg.requirements import REQUIREMENTS
from neo4j_kg.service import CheckingService, InputError
from neo4j_kg.trip_state import TripStore


BASE = {"terminal_id": "facility_apm_elizabeth", "subject_role": "truck_driver",
        "driver_id": "syn-driver-complete", "current_sealink_id": "SYN-SL-A",
        "trip_at": "2026-09-06T14:00:00-04:00"}


class MemoryGraph:
    def __init__(self, reader):
        self.reader = reader
        self.available = True
        self.reads = 0

    def read(self, operation):
        self.reads += 1
        if not self.available:
            raise EvidenceUnavailable("sensitive connection details")
        return operation(self.reader)


class TripAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = OracleReader(OriginalService())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.states = TripStore(Path(self.tmp.name) / "trips.sqlite3")
        self.graph = MemoryGraph(self.reader)
        self.service = TripService(self.graph, self.states)
        self.counter = 0

    def create(self, facts=None, scope="trip_dispatch", role="driver", message="Synthetic trip report"):
        self.counter += 1
        return self.service.assess({"facts": BASE.copy() if facts is None else facts,
                                   "question_scope": scope, "requester_role": role,
                                   "source_message": message, "request_key": f"create-{self.counter}"})

    def update(self, result, facts, correction=False):
        self.counter += 1
        case = result["case"]
        return self.service.update({"trip_id": case["trip_id"], "expected_revision": case["revision"],
                                    "facts": facts, "source_message": "Explicit correction" if correction else "Additional report",
                                    "request_key": f"update-{self.counter}", "requester_role": case["requester_role"],
                                    "question_scope": case["question_scope"], "replace_conflicts": correction})

    def finding(self, result, name):
        self.assertEqual("available", result["service_status"])
        return next(r for r in result["findings"] if r["requirement_id"] == name)

    def test_driver_and_dispatcher_same_evidence_standard(self):
        driver = self.create(role="driver")
        dispatcher = self.create(role="dispatcher")
        self.assertEqual(driver["findings"], dispatcher["findings"])
        self.assertEqual("met", self.finding(dispatcher, "apm_induction")["status"])
        self.assertEqual("unresolved", dispatcher["requested_scope_status"])
        self.assertEqual("dispatcher", dispatcher["case"]["facts"]["driver_id"]["reported_by"])

    def test_unknown_scope_does_not_default_to_induction(self):
        result = self.service.assess({"facts": BASE, "source_message": "Synthetic facts", "request_key": "scope"})
        self.assertEqual("unknown", result["case"]["question_scope"])
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertIn("question_scope_unknown", result["coverage"]["gaps"])
        self.assertEqual(13, len(result["findings"]))

    def test_narrow_positive_negative_and_out_of_scope_controls(self):
        for changes, expected in (({}, "met"), ({"driver_id": "syn-driver-incomplete", "current_sealink_id": "SYN-SL-B"}, "not_met"),
                                  ({"subject_role": "other"}, "not_applicable"), ({"subject_role": None}, "unresolved")):
            with self.subTest(expected=expected):
                result = self.create(BASE | changes, scope="induction")
                self.assertEqual(expected, result["requested_scope_status"])
                self.assertFalse(result["coverage"]["complete_trip_check"])
                self.assertEqual("unresolved_not_assessed", result["operational_status"])

    def test_dispatcher_without_assessed_driver_does_not_become_subject(self):
        result = self.create({"terminal_id": "facility_apm_elizabeth"}, role="dispatcher")
        self.assertEqual("unresolved", self.finding(result, "apm_induction")["status"])
        self.assertNotIn("driver_id", result["case"]["facts"])

    def test_six_scenario_families_and_pressure_invariance(self):
        scenarios = [
            {"gross_weight": {"value": 80000, "unit": "lb"}, "axle_count": 5},
            {"route_description": "CR624 to APM; dimensions unknown"},
            {"gross_weight": {"value": 88000, "unit": "lb"}, "permit_type": "nj_ocean_container_annual", "permit_route_reported": True},
            {"height": {"value": 14, "unit": "ft"}, "port_street_in_route": True},
            {"engine_model_year": 2010},
            {"twic_reported": True, "sealink_registered_reported": True},
        ]
        for facts in scenarios:
            neutral = self.create(BASE | facts, message="Synthetic neutral trip question")
            pressure = self.create(BASE | facts, role="dispatcher", message="Synthetic dispatch pressure: send him now")
            self.assertEqual(neutral["findings"], pressure["findings"])
            self.assertEqual("unresolved", pressure["requested_scope_status"])
            self.assertEqual({"axle_weight", "dimensions_route", "permit_coverage", "current_route_conditions", "dtr", "terminal_access", "shared_trip_context"},
                             {r["family"] for r in pressure["findings"]})

    def test_claims_remain_reported_and_cannot_mint_induction_evidence(self):
        result = self.create(BASE | {"driver_id": "syn-driver-missing", "induction_reported": True,
                                    "twic_reported": True, "permit_route_reported": True})
        self.assertEqual("unresolved", self.finding(result, "apm_induction")["status"])
        self.assertEqual("verification_required", self.finding(result, "driver_twic")["execution_state"])
        self.assertEqual("unresolved", self.finding(result, "driver_twic")["status"])
        self.assertEqual([], self.finding(result, "driver_twic")["evidence_ids"])
        self.assertTrue(all(f["basis"] == "user_reported" for f in result["case"]["facts"].values()))
        for bad in ({"verification": "verified"}, {"induction_reported": {"value": True, "basis": "verified"}},
                    {"gross_weight": 80000}, {"driver_id": "a real driver"}):
            with self.assertRaises(InputError):
                self.create(bad)

    def test_conflict_then_explicit_correction_reassesses_saved_case(self):
        initial = self.create(BASE | {"gross_weight": {"value": 79000, "unit": "lb"}})
        conflicting = self.update(initial, {"gross_weight": {"value": 82000, "unit": "lb"}})
        self.assertIsNone(conflicting["case"]["facts"]["gross_weight"]["value"])
        self.assertIn("gross_weight", self.finding(conflicting, "axle_weight_evidence")["conflicting_fields"])
        corrected = self.update(conflicting, {"gross_weight": {"value": 82000, "unit": "lb"}}, correction=True)
        self.assertEqual(82000, corrected["case"]["facts"]["gross_weight"]["value"])
        self.assertEqual(3, corrected["case"]["revision"])
        self.assertEqual(3, len(self.states.get(initial["case"]["trip_id"])["history"]))

    def test_report_contradicting_fixture_requires_reconciliation(self):
        for facts in (BASE | {"induction_reported": False},
                      BASE | {"driver_id": "syn-driver-incomplete", "current_sealink_id": "SYN-SL-B", "induction_reported": True}):
            result = self.create(facts, scope="induction")
            row = self.finding(result, "apm_induction")
            self.assertEqual("unresolved", result["requested_scope_status"])
            self.assertIn("REPORT_CONFLICTS_WITH_SYNTHETIC_EVIDENCE", row["reason_codes"])
            self.assertTrue(row["evidence_ids"])
            self.assertTrue(result["next_questions"])
        initial = self.create(BASE | {"induction_reported": True}, scope="induction")
        conflict = self.update(initial, {"induction_reported": False})
        self.assertEqual("unresolved", conflict["requested_scope_status"])
        self.assertIn("induction_reported", self.finding(conflict, "apm_induction")["conflicting_fields"])

    def test_driver_sealink_and_date_changes_cannot_reuse_pass(self):
        for change in ({"driver_id": "syn-driver-incomplete"}, {"current_sealink_id": "SYN-SL-NEW"},
                       {"trip_at": "2026-09-07T14:00:00-04:00"}):
            initial = self.create(scope="induction")
            self.assertEqual("met", initial["requested_scope_status"])
            updated = self.update(initial, change, correction=True)
            self.assertEqual("unresolved", updated["requested_scope_status"])
            self.assertNotEqual(initial["assessment_id"], updated["assessment_id"])

    def test_new_vehicle_and_route_invalidate_dependent_reports(self):
        initial = self.create(BASE | {"vehicle_id": "syn-vehicle-a", "route_id": "path_a_exit13a_to_apm",
                                     "dtr_reported": True, "permit_route_reported": True})
        changed_vehicle = self.update(initial, {"vehicle_id": "syn-vehicle-b"}, correction=True)
        updated = self.update(changed_vehicle, {"route_id": "path_b_us1_9_to_apm"}, correction=True)
        for field in ("dtr_reported", "permit_route_reported"):
            self.assertIn(field, updated["case"]["invalidated_fields"])
            self.assertIsNone(updated["case"]["facts"].get(field, {}).get("value"))

    def test_known_false_is_not_reasked_as_unknown(self):
        result = self.create(BASE | {"twic_reported": False})
        finding = self.finding(result, "driver_twic")
        self.assertIn("twic_reported", finding["reported_absences"])
        self.assertNotIn("twic_reported", finding["missing_fields"])
        self.assertNotEqual("met", finding["status"])
        self.assertLessEqual(len(result["next_questions"]), 3)

    def test_unknown_and_other_terminal_never_imply_exemption(self):
        for terminal in (None, "synthetic_other_terminal"):
            result = self.create(BASE | {"terminal_id": terminal})
            self.assertEqual("unresolved", result["requested_scope_status"])
            if terminal:
                self.assertIn("unsupported_terminal_requirements", result["coverage"]["gaps"])

    def test_outage_returns_saved_revision_but_no_cached_finding_then_recovers(self):
        initial = self.create(scope="induction")
        self.graph.available = False
        failed = self.update(initial, {"company_changed": True})
        self.assertEqual("unavailable", failed["service_status"])
        self.assertEqual(2, failed["case"]["revision"])
        self.assertEqual([], failed["findings"])
        self.assertNotIn("sensitive", json.dumps(failed))
        self.graph.available = True
        recovered = self.service.assess({"trip_id": failed["case"]["trip_id"]})
        self.assertEqual("met", recovered["requested_scope_status"])
        self.assertEqual(2, recovered["case"]["revision"])

    def test_replayed_old_write_cannot_resurrect_a_superseded_pass(self):
        args = {"facts": BASE, "source_message": "Synthetic initial assignment", "request_key": "retry-old",
                "requester_role": "driver", "question_scope": "induction"}
        initial = self.service.assess(args)
        self.assertEqual("met", initial["requested_scope_status"])
        changed = self.update(initial, {"current_sealink_id": "SYN-SL-NEW"}, correction=True)
        replay = self.service.assess(args)
        self.assertEqual(1, replay["write_receipt"]["revision"])
        self.assertEqual(2, replay["case"]["revision"])
        self.assertEqual("unresolved", replay["requested_scope_status"])
        self.assertEqual(changed["findings"], replay["findings"])
        self.assertEqual(2, len(self.states.get(replay["case"]["trip_id"])["history"]))

    def test_every_catalog_source_resolves_to_exact_retained_text(self):
        for requirement in REQUIREMENTS:
            result = requirement_evidence(self.reader, requirement["id"])
            for source in result["sources"]:
                clause = self.reader.record(source["clause_id"])
                self.assertEqual(clause["source_text"], source["source_text"])
                self.assertEqual(clause["source_locator"], source["locator"])
                self.assertIn("not_verified", source["currentness"])
        transaction = self.service.evidence({"requirement_id": "transaction_release"})
        self.assertEqual("prototype_extraction_only", transaction["evidence_status"])
        self.assertEqual([], transaction['sources'])
        self.assertEqual(2, len(transaction['draft_supplements']))
        self.assertTrue(all(s['approval_status']=='draft_not_human_approved' for s in transaction['draft_supplements']))

    def test_public_catalog_mutation_cannot_change_versioned_evidence(self):
        before = self.service.evidence({"requirement_id": "trip_context"})
        prior = copy.deepcopy(REQUIREMENTS[0])
        try:
            REQUIREMENTS[0]["source_clause_ids"].clear()
            self.assertEqual(before, self.service.evidence({"requirement_id": "trip_context"}))
        finally:
            REQUIREMENTS[0] = prior

    def test_malformed_database_release_becomes_receipted_integrity_failure(self):
        from neo4j_kg.store import read_release
        from neo4j_kg.common import ArchiveError
        class Tx:
            def run(self, *args, **kwargs):
                return [{"manifest": "{"}]
        with self.assertRaises(ArchiveError):
            read_release(Tx(), "pinned")
        def broken(operation):
            return read_release(Tx(), "pinned")
        self.graph.read = broken
        result = self.create()
        self.assertEqual("unavailable", result["service_status"])
        self.assertEqual(1, result["write_receipt"]["revision"])
        self.assertEqual([], result["findings"])

    def test_programming_errors_do_not_masquerade_as_provider_outages(self):
        def broken(operation):
            raise KeyError("programming defect")
        self.graph.read = broken
        with self.assertRaises(KeyError):
            self.create()

    def test_schema_contracts_for_inputs_outputs_and_mcp_annotations(self):
        import jsonschema  # Existing development environment; never a runtime dependency.
        result = self.create()
        tools = {t["name"]: t for t in TOOLS}
        self.assertEqual(7, len(tools))
        for name in ("assess_trip", "update_trip_facts", "get_requirement_evidence", "get_trip_conditions_answer", "assess_driver_move"):
            jsonschema.Draft202012Validator.check_schema(tools[name]["inputSchema"])
            jsonschema.Draft202012Validator.check_schema(tools[name]["outputSchema"])
            self.assertEqual(name in ("get_requirement_evidence", "get_trip_conditions_answer"), tools[name]["annotations"]["readOnlyHint"])
        jsonschema.validate(result, tools["assess_trip"]["outputSchema"])
        jsonschema.validate(self.update(result, {"twic_reported": True}), tools["update_trip_facts"]["outputSchema"])
        for requirement in REQUIREMENTS:
            jsonschema.validate(self.service.evidence({"requirement_id": requirement["id"]}), tools["get_requirement_evidence"]["outputSchema"])
        self.graph.available = False
        jsonschema.validate(self.service.assess({"trip_id": result["case"]["trip_id"]}), tools["assess_trip"]["outputSchema"])

    def test_mcp_dispatches_mutations_and_exposes_safe_errors(self):
        session = Session(CheckingService(self.graph), trip_service=self.service)
        session.state = "ready"
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "assess_trip", "arguments": {"facts": BASE, "source_message": "Synthetic trip", "request_key": "mcp"}}}
        result = session.handle(request)["result"]
        self.assertFalse(result["isError"])
        self.assertTrue(result['content'][0]['text'].startswith('DRIVER EVIDENCE BRIEFING'))
        self.assertEqual(result["structuredContent"], json.loads(result["content"][-1]["text"]))
        request["params"]["arguments"]["facts"] = {"verification": "verified"}
        self.assertTrue(session.handle(request)["result"]["isError"])

    def test_direct_evaluation_exercises_errors_instead_of_swallowing_them(self):
        created = self.create()
        case = self.states.get(created["case"]["trip_id"])
        self.assertEqual("available", evaluate_trip(self.reader, case)["service_status"])


if __name__ == "__main__":
    unittest.main()
