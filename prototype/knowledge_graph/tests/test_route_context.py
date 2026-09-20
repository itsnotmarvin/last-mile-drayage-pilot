"""Graph-backed route_context: C2/C3 regression plus assessment invariants.

Topology discovery is explanatory only: it must never satisfy a requirement,
verify a fact, or change met/not_met/unresolved semantics.
"""
import copy
import tempfile
import unittest

from kg.service import CheckingService as OriginalService
from neo4j_kg.assessment import TripService
from neo4j_kg.followups import build_followups
from neo4j_kg.mcp_server import TOOLS
from neo4j_kg.route_context import (
    GRAPH_BACKED_ROUTES,
    build_route_context,
)
from neo4j_kg.trip_state import TripStore
from test_neo4j_migration import OracleReader, RELEASE
from test_trip_assessment import BASE, MemoryGraph

PINNED = "f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c"

# C2 regression: exact ordered segment expectations from the pinned release.
EXPECTED_ROUTES = {
    "path_a_exit13a_to_apm": ["edge_a_exit13a_connector", "edge_shared_north_avenue",
                              "edge_shared_mclester", "edge_shared_tripoli_gate"],
    "path_b_us1_9_to_apm": ["edge_b_us1_south", "edge_b_north_avenue_to_merge",
                            "edge_shared_north_avenue", "edge_shared_mclester",
                            "edge_shared_tripoli_gate"],
}


class RouteContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = OracleReader(OriginalService())

    def test_pinned_release_identity(self):
        self.assertEqual(RELEASE["revision"], PINNED)

    def test_named_routes_resolve_exact_c2_sequences(self):
        for route_id, expected in EXPECTED_ROUTES.items():
            with self.subTest(route=route_id):
                context = build_route_context(self.reader, route_id, PINNED)
                self.assertEqual("resolved_from_pinned_graph", context["status"])
                self.assertEqual(route_id, context["route_id"])
                self.assertEqual("route_family", context["route_kind"])
                self.assertEqual(PINNED, context["graph_release"])
                segments = context["segments"]
                self.assertEqual(expected, [s["segment_id"] for s in segments])
                self.assertEqual(list(range(1, len(expected) + 1)),
                                 [s["sequence"] for s in segments])
                # Connectivity: every link joins end-to-start.
                for first, second in zip(segments, segments[1:]):
                    self.assertEqual(first["ends_at"], second["starts_at"])
                # C3 regression per segment.
                for segment in segments:
                    self.assertTrue(segment["name"], segment["segment_id"])
                    self.assertEqual(1, len([segment["starts_at"]]))
                    self.assertEqual(1, len([segment["ends_at"]]))
                    self.assertTrue(segment["jurisdictions"], segment["segment_id"])
                    self.assertTrue(all(j["kind"] in ("jurisdiction", "facility_jurisdiction")
                                        for j in segment["jurisdictions"]))
                    self.assertTrue(segment["njogis_categories"], segment["segment_id"])
                    self.assertTrue(segment["governing_clause_ids"], segment["segment_id"])
                self.assertTrue(context["candidate_requirement_ids"], route_id)
                self.assertIn("Graph-derived candidate structure only",
                              context["limits"][0])

    def test_unbacked_routes_stay_unavailable(self):
        for value in (None, "other", "path_nope"):
            with self.subTest(route=value):
                context = build_route_context(self.reader, value, PINNED)
                self.assertEqual("unavailable_route_not_graph_backed", context["status"])
                self.assertEqual(value, context["route_id"])
                self.assertEqual([], context["segments"])
                self.assertEqual([], context["candidate_requirement_ids"])

    def test_topology_never_satisfies_requirements(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from pathlib import Path
        service = TripService(MemoryGraph(self.reader), TripStore(Path(tmp.name) / "trips.sqlite3"))
        facts = dict(BASE, route_id="path_a_exit13a_to_apm")
        result = service.assess({"facts": facts, "question_scope": "trip_dispatch",
                                 "requester_role": "driver",
                                 "source_message": "Synthetic route resolution control",
                                 "request_key": "route-context-control"})
        # Decision semantics unchanged: nothing met except graph-backed induction.
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        for finding in result["findings"]:
            if finding["requirement_id"] == "apm_induction":
                self.assertEqual("met", finding["status"])
            else:
                self.assertEqual("unresolved", finding["status"])
        road = [f for f in result["findings"] if f["requirement_id"] == "dimensions_and_route"][0]
        self.assertIn("REQUIRED_FACTS_MISSING", road["reason_codes"])
        # ...while candidate structure is present and explanatory.
        context = result["evidence_package"]["route_context"]
        self.assertEqual("resolved_from_pinned_graph", context["status"])
        self.assertEqual(EXPECTED_ROUTES["path_a_exit13a_to_apm"],
                         [s["segment_id"] for s in context["segments"]])
        self.assertTrue(context["candidate_requirement_ids"])
        # Output schema still validates with the new block.
        import jsonschema
        tools = {t["name"]: t for t in TOOLS}
        jsonschema.validate(result, tools["assess_trip"]["outputSchema"])

    def test_unavailable_context_keeps_assessment_intact(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from pathlib import Path
        service = TripService(MemoryGraph(self.reader), TripStore(Path(tmp.name) / "trips.sqlite3"))
        facts = dict(BASE, route_id="other",
                     route_description="Unmapped private yard road, exact path unknown")
        result = service.assess({"facts": facts, "question_scope": "trip_dispatch",
                                 "requester_role": "driver",
                                 "source_message": "Synthetic unmapped route control",
                                 "request_key": "route-context-other"})
        self.assertEqual("unavailable_route_not_graph_backed",
                         result["evidence_package"]["route_context"]["status"])
        self.assertEqual("unresolved", result["requested_scope_status"])
        import jsonschema
        tools = {t["name"]: t for t in TOOLS}
        jsonschema.validate(result, tools["assess_trip"]["outputSchema"])

    def test_builder_result_is_json_stable(self):
        import json
        context = build_route_context(self.reader, "path_a_exit13a_to_apm", PINNED)
        clone = copy.deepcopy(context)
        self.assertEqual(context, json.loads(json.dumps(context)))
        self.assertEqual(context, clone)

    def _assess(self, facts, scope="trip_dispatch", message="Synthetic follow-up control",
               key="route-followup"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from pathlib import Path
        service = TripService(MemoryGraph(self.reader), TripStore(Path(tmp.name) / "trips.sqlite3"))
        result = service.assess({"facts": facts, "question_scope": scope,
                                 "requester_role": "driver", "source_message": message,
                                 "request_key": key})
        return service, result

    def test_backed_route_grounds_followup_wording(self):
        service, result = self._assess(dict(BASE, route_id="path_a_exit13a_to_apm"),
                                       key="route-followup-backed")
        questions = {q["field"]: q for q in result["next_questions"]}
        self.assertIn("route_description", questions)
        grounded = questions["route_description"]
        self.assertEqual("missing_fact", grounded["kind"])
        self.assertIn("FR NJ TURNPIKE SB TO NJ 81 NB -> North Avenue -> McLester Street -> Tripoli Street",
                      grounded["question"])
        self.assertIn("path_a_exit13a_to_apm", grounded["question"])
        self.assertTrue(grounded["requirement_ids"])
        self.assertIn("port_street_in_route", questions)
        port = questions["port_street_in_route"]
        self.assertEqual("missing_fact", port["kind"])
        self.assertIn("Port Street", port["question"])
        self.assertIn("North Avenue", port["question"])
        self.assertIn("does not establish absence", port["question"])

    def test_unbacked_route_keeps_generic_followup(self):
        service, result = self._assess(dict(BASE, route_id="other"), key="route-followup-other")
        context = result["evidence_package"]["route_context"]
        self.assertEqual("unavailable_route_not_graph_backed", context["status"])
        case = service.trip_store.get(result["case"]["trip_id"])
        generic = build_followups(case, result["findings"])
        self.assertEqual(generic, result["next_questions"])
        by_field = {q["field"]: q for q in result["next_questions"]}
        if "route_description" in by_field:
            self.assertNotIn("->", by_field["route_description"]["question"])

    def test_statuses_identical_before_after_grounding(self):
        service, result = self._assess(dict(BASE, route_id="path_a_exit13a_to_apm"),
                                       key="route-followup-status")
        case = service.trip_store.get(result["case"]["trip_id"])
        before = build_followups(case, result["findings"])
        after = result["next_questions"]
        # Same fields in the same order with the same owners, kinds, and
        # requirement coverage; only human-facing wording may change.
        self.assertEqual([q["field"] for q in before], [q["field"] for q in after])
        for old, new in zip(before, after):
            self.assertEqual(old["field"], new["field"])
            self.assertEqual(old["kind"], new["kind"])
            self.assertEqual(old["owner"], new["owner"])
            self.assertEqual(old["requirement_ids"], new["requirement_ids"])
            self.assertEqual(old["reason"] is not None, new["reason"] is not None)
        changed = [new["field"] for old, new in zip(before, after)
                   if old["question"] != new["question"]]
        self.assertEqual(["route_description", "port_street_in_route"], changed)
        # Decision outputs untouched by wording.
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        self.assertEqual("not_cleared", result["decision_brief"]["status"])
        self.assertEqual("unresolved", result["decision_brief"]["scoped_result"])
        self.assertEqual("not_issued", result["decision_brief"]["operational_permission"])
        for finding in result["findings"]:
            expected = "met" if finding["requirement_id"] == "apm_induction" else "unresolved"
            self.assertEqual(expected, finding["status"], finding["requirement_id"])

    def test_port_street_stays_unresolved_when_backed(self):
        _, result = self._assess(dict(BASE, route_id="path_a_exit13a_to_apm"),
                                 key="route-followup-port")
        case_facts = result["case"]["facts"]
        self.assertIsNone(case_facts.get("port_street_in_route", {}).get("value"))
        conditions = [f for f in result["findings"] if f["requirement_id"] == "current_route_conditions"][0]
        self.assertEqual("unresolved", conditions["status"])
        self.assertIn("port_street_in_route", conditions["missing_fields"])
        self.assertIn("port_street_in_route", [q["field"] for q in result["next_questions"]])


if __name__ == "__main__":
    unittest.main()
