"""Fresh live-Neo4j checks with isolated synthetic operator/trip stores."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from neo4j_kg.config import connect
from neo4j_kg.store import Neo4jStore
from neo4j_kg.trip_state import TripStore
from neo4j_kg.verification_store import VerificationStore
from neo4j_kg.assessment import TripService
from neo4j_kg.terminal_status import fetch
from verification_fixtures import facts, receipts, RELEASE

OUT = Path(__file__).parent
driver, database = connect(Path.home() / ".config/drayage-mcp/neo4j.env")
graph = Neo4jStore(driver, database, RELEASE)
now = datetime.now(timezone.utc).replace(microsecond=0)
at = now + timedelta(hours=1)
results = []
try:
    for mode, expected in (("missing", "unresolved"), ("open", "met"), ("closed", "not_met"),
                           ("stale", "unresolved"), ("wrong_segment", "unresolved"),
                           ("conflict", "unresolved"), ("partial_route", "unresolved"),
                           ("reversed_route", "unresolved")):
        with tempfile.TemporaryDirectory() as temp:
            states = TripStore(Path(temp) / "trips.sqlite3")
            verifications = VerificationStore(Path(temp) / "verification.sqlite3")
            values = facts()
            values["trip_at"] = at.isoformat()
            case = states.create(facts=values, request_key="live-" + mode,
                                 source_message="Synthetic operator conditions acceptance fixture; not real verification.",
                                 requester_role="driver", question_scope="route")
            records = [r for r in receipts(case) if r["kind"] in ("route", "scale", "dimensions", "conditions")]
            for record in records:
                record.update(observed_at=now.isoformat(), valid_from=now.isoformat(),
                              valid_until=(at + timedelta(hours=1)).isoformat())
                if record["kind"] == "conditions":
                    if mode == "closed": record["payload"]["status"] = "closed"
                    if mode == "wrong_segment": record["payload"]["segment_id"] = "edge_b_us1_south"
                    if mode == "stale":
                        record.update(observed_at=(now-timedelta(days=1)).isoformat(),
                                      valid_from=(now-timedelta(days=1)).isoformat(), valid_until=now.isoformat())
                if record["kind"] == "route":
                    if mode == "partial_route": record["payload"]["segments"] = record["payload"]["segments"][:1]
                    if mode == "reversed_route": record["payload"]["segments"].reverse()
            if mode == "missing": records = []
            if mode == "conflict":
                extra = copy.deepcopy(next(r for r in records if r["kind"] == "conditions"))
                extra["id"] += "-conflict"
                extra["payload"]["status"] = "closed"
                records.append(extra)
            if records: verifications.put(records, case, RELEASE)
            service = TripService(graph, states, verifications)
            result = service.assess({"trip_id": case["trip_id"]})
            finding = next(f for f in result["findings"] if f["requirement_id"] == "current_route_conditions")
            assert result["service_status"] == "available"
            assert finding["status"] == expected, (mode, finding)
            assert result["decision_brief"]["operational_permission"] == "not_issued"
            assert result["versions"]["graph_release"] == RELEASE
            results.append({"case": mode, "expected": expected, "result": result,
                            "synthetic_receipts": records})
            print(mode, finding["status"], flush=True)
    terminal = fetch()
    with (OUT / "live-conditions.json").open("x") as file:
        json.dump({"surface": "Python service against live Neo4j; no model involved", "started_at": now.isoformat(),
                   "finished_at": datetime.now(timezone.utc).isoformat(), "database": database,
                   "cases": results, "terminal_fetch": terminal, "status": "PASS"}, file, indent=2)
    print("PASS: eight live cases; terminal fetch:", terminal["status"], flush=True)
finally:
    driver.close()
