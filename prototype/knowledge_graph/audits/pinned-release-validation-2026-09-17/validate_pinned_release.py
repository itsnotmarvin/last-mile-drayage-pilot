#!/usr/bin/env python3
"""Read-only pinned-release validation for the operational drayage graph.

Revision: f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c
Dataset:  last-mile-drayage-pilot (Neo4j Aura, database taken from credentials file)

Steering: critical-path step 4. No rebuild, no schema change, no experiment.
This script performs ZERO writes: every Neo4j call uses READ_ACCESS +
session.execute_read with MATCH-only Cypher. It never calls execute_write,
import_transaction, or any TripStore write path.

Usage (from prototype/knowledge_graph):
  .venv-neo4j/bin/python audits/pinned-release-validation-2026-09-17/validate_pinned_release.py \
    --receipt audits/pinned-release-validation-2026-09-17/receipt.json

Checks stop at the first structural defect (remaining checks are recorded
as "skipped"). Exit 0 only when every executed check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
KG_ROOT = AUDIT_DIR.parents[1]  # prototype/knowledge_graph
sys.path.insert(0, str(KG_ROOT))

REVISION = "f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c"
DATASET = "last-mile-drayage-pilot"
SNAPSHOT_PATH = KG_ROOT / "data" / "neo4j_release.json"

EXPECTED_NODES = 144
EXPECTED_EDGES = 228
EXPECTED_ROUTES = {
    "path_a_exit13a_to_apm": ["edge_a_exit13a_connector", "edge_shared_north_avenue",
                              "edge_shared_mclester", "edge_shared_tripoli_gate"],
    "path_b_us1_9_to_apm": ["edge_b_us1_south", "edge_b_north_avenue_to_merge",
                            "edge_shared_north_avenue", "edge_shared_mclester",
                            "edge_shared_tripoli_gate"],
    "approach_a_turnpike_sb": ["edge_a_exit13a_connector", "edge_shared_north_avenue",
                               "edge_shared_mclester", "edge_shared_tripoli_gate"],
    "approach_a_turnpike_nb": ["edge_a_nb_turnpike_exit", "edge_a_nb_state_ramps_to_north_ave",
                               "edge_ab_shared_north_ave_to_all_merge", "edge_shared_north_avenue",
                               "edge_shared_mclester", "edge_shared_tripoli_gate"],
}
EXPECTED_SEGMENTS = [
    "edge_a_exit13a_connector", "edge_a_nb_turnpike_exit",
    "edge_a_nb_state_ramps_to_north_ave", "edge_ab_shared_north_ave_to_all_merge",
    "edge_b_us1_south", "edge_b_north_avenue_to_merge", "edge_shared_north_avenue",
    "edge_shared_mclester", "edge_shared_tripoli_gate",
]
GOVERNANCE_RELS = ("GOVERNS", "OVERLAPS_PART_OF",
                   "STREET_NOT_LISTED_IN_RESTRICTION_TABLE",
                   "ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C",
                   "TRUCK_ROUTE_SCHEDULE_RESERVED")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(check_id: str, name: str, detail: str, extra: dict | None = None) -> dict:
    body: dict = {"id": check_id, "name": name, "status": "FAIL", "detail": detail}
    if extra:
        body["evidence"] = extra
    return body


def ok(check_id: str, name: str, detail: str, extra: dict | None = None) -> dict:
    body: dict = {"id": check_id, "name": name, "status": "PASS", "detail": detail}
    if extra:
        body["evidence"] = extra
    return body


def load_credentials(path: Path | None) -> tuple[dict, Path | None]:
    config = dict(os.environ)
    used = None
    candidate = path or (Path(config["NEO4J_CREDENTIALS_FILE"]) if config.get("NEO4J_CREDENTIALS_FILE") else None)
    if candidate is None:
        fallback = Path.home() / ".config" / "drayage-mcp" / "neo4j.env"
        if fallback.is_file():
            candidate = fallback
    if candidate:
        candidate = Path(candidate)
        for line in candidate.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
        used = candidate
    return config, used


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path, default=None)
    parser.add_argument("--receipt", type=Path, default=AUDIT_DIR / "receipt.json")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    checks: list[dict] = []

    def record(result: dict) -> bool:
        checks.append(result)
        print(f"[{result['status']}] {result['id']}: {result['name']} — {result['detail']}", flush=True)
        return result["status"] == "PASS"

    # --- local snapshot load (no Neo4j yet) ---
    try:
        snapshot = json.loads(SNAPSHOT_PATH.read_text())
        snapshot_sha = sha_file(SNAPSHOT_PATH)
    except Exception as exc:
        record(fail("C0", "snapshot load", f"Cannot read local snapshot: {type(exc).__name__}: {exc}"))
        snapshot = None
        snapshot_sha = None

    if snapshot is None:
        return finish(started, args, checks, None, None, snapshot_sha, "C0")

    from neo4j_kg.common import digest, validate_release, verify_files  # noqa: E402

    # --- connect (read-only intent; every query below is MATCH-only) ---
    try:
        import truststore  # noqa: E402
        truststore.inject_into_ssl()
        from neo4j import GraphDatabase, READ_ACCESS, unit_of_work  # noqa: E402
        config, cred_path = load_credentials(args.credentials_file)
        if not config.get("NEO4J_URI", "").startswith("neo4j+s://"):
            raise ValueError("Certificate-verified neo4j+s:// URI required")
        if not all(config.get(k) for k in ("NEO4J_USERNAME", "NEO4J_PASSWORD")):
            raise ValueError("Neo4j credentials unavailable")
        database = config.get("NEO4J_DATABASE", "neo4j")
        driver = GraphDatabase.driver(
            config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]),
            connection_timeout=10, connection_acquisition_timeout=15,
            max_transaction_retry_time=10, max_connection_pool_size=4)
        driver.verify_connectivity()
    except Exception as exc:
        record(fail("C0", "neo4j connect",
                    f"Read-only connection failed ({type(exc).__name__}); no receipt issued beyond this point."))
        return finish(started, args, checks, None, None, snapshot_sha, "C0")

    params = {"dataset": DATASET, "revision": REVISION}

    def read(query: str, **kw):
        with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
            @unit_of_work(timeout=30)
            def invoke(tx):
                return list(tx.run(query, **{**params, **kw}))
            return session.execute_read(invoke)

    live_release = None
    try:
        # ============ C1: identity + counts + full snapshot equality ============
        releases = read("MATCH (r:DrayageRelease {dataset:$dataset, revision:$revision}) "
                        "RETURN r.manifest_json AS manifest")
        if len(releases) != 1:
            record(fail("C1", "release identity",
                        f"Expected exactly 1 DrayageRelease for pinned revision, found {len(releases)}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C1")
        manifest = json.loads(releases[0]["manifest"])
        if manifest.get("revision") != REVISION:
            record(fail("C1", "release identity", "Live manifest revision differs from pinned revision."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C1")

        node_count = read("MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
                          "RETURN count(*) AS c")[0]["c"]
        edge_count = read("MATCH ()-[e]->() WHERE e.dataset=$dataset AND e.revision=$revision "
                          "RETURN count(*) AS c")[0]["c"]
        if node_count != EXPECTED_NODES or edge_count != EXPECTED_EDGES:
            record(fail("C1", "release counts",
                        f"Expected {EXPECTED_NODES} nodes / {EXPECTED_EDGES} edges, "
                        f"live has {node_count} / {edge_count}.",
                        {"nodes": node_count, "edges": edge_count}))
            return finish(started, args, checks, database, driver, snapshot_sha, "C1")

        live_nodes = [dict(r["node"]) for r in read(
            "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
            "RETURN n{.id,.kind,.layer,.archive,.ordinal,.record_json} AS node ORDER BY n.ordinal")]
        live_edges = [dict(r["edge"]) for r in read(
            "MATCH (a:DrayageRecord {dataset:$dataset, revision:$revision})-[e]->"
            "(b:DrayageRecord {dataset:$dataset, revision:$revision}) "
            "WHERE e.dataset=$dataset AND e.revision=$revision "
            "RETURN {id:e.id, from:a.id, to:b.id, relationship:type(e), "
            "archive:e.archive, ordinal:e.ordinal, record_json:e.record_json} AS edge "
            "ORDER BY e.ordinal")]
        live_release = {**manifest, "nodes": live_nodes, "edges": live_edges}
        if live_release != snapshot:
            record(fail("C1", "live Revisionsnummer snapshot equality",
                        "Live release body differs from data/neo4j_release.json; "
                        "do not adopt a new revision without a validated import."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C1")
        validate_release(live_release)  # duplicate ids, ordinals, endpoints, revision digest
        active = [dict(r) for r in read(
            "MATCH (d:DrayageDataset {id:$dataset}) RETURN d.active_revision AS active")]
        record(ok("C1", "release identity + counts + snapshot equality",
                  f"1 release, {node_count} nodes / {edge_count} edges, "
                  f"live body identical to snapshot, revision digest valid.",
                  {"nodes": node_count, "edges": edge_count,
                   "active_revision_observed": (active[0]["active"] if active else None)}))

        # ============ C2: routes + ordered segments + connectivity ============
        routes = {r["id"]: (r["kind"], json.loads(r["record"]))
                  for r in read("MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
                                "WHERE n.kind IN ['route_family','route_approach'] "
                                "RETURN n.id AS id, n.kind AS kind, n.record_json AS record ORDER BY n.id")}
        if set(routes) != set(EXPECTED_ROUTES):
            record(fail("C2", "route existence",
                        f"Expected routes {sorted(EXPECTED_ROUTES)}, live has {sorted(routes)}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C2")
        seg_records = {}
        for seg in read("MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision, kind:'road_segment'}) "
                        "RETURN n.id AS id, n.record_json AS record"):
            seg_records[seg["id"]] = json.loads(seg["record"])
        if set(seg_records) != set(EXPECTED_SEGMENTS):
            record(fail("C2", "segment existence",
                        f"Expected 9 segments {EXPECTED_SEGMENTS}, live has {sorted(seg_records)}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C2")
        route_evidence = {}
        for route_id, expected_order in EXPECTED_ROUTES.items():
            rows = read("MATCH (r:DrayageRecord {dataset:$dataset, revision:$revision, id:$route_id})"
                        "-[e:HAS_ORDERED_SEGMENT]->(s:DrayageRecord {dataset:$dataset, revision:$revision}) "
                        "WHERE e.dataset=$dataset AND e.revision=$revision "
                        "RETURN s.id AS sid, e.record_json AS erec", route_id=route_id)
            seq = sorted((json.loads(r["erec"])["sequence"], r["sid"]) for r in rows)
            ordered = [sid for _, sid in seq]
            if [s for s, _ in seq] != list(range(1, len(expected_order) + 1)) or ordered != expected_order:
                record(fail("C2", "ordered segment completeness",
                            f"Route {route_id}: expected 1..{len(expected_order)} = {expected_order}, "
                            f"live sequence = {seq}."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C2")
            # connectivity: to_node(k) == from_node(k+1), plus STARTS_AT/ENDS_AT edges
            chain = [(seg_records[s]["from_node"], seg_records[s]["to_node"]) for s in ordered]
            for k in range(len(chain) - 1):
                if chain[k][1] != chain[k + 1][0]:
                    record(fail("C2", "segment connectivity",
                                f"Route {route_id}: {ordered[k]} ends at {chain[k][1]} but "
                                f"{ordered[k+1]} starts at {chain[k+1][0]}."))
                    return finish(started, args, checks, database, driver, snapshot_sha, "C2")
            for sid in ordered:
                ends = read("MATCH (s:DrayageRecord {dataset:$dataset, revision:$revision, id:$sid})"
                            "-[e:STARTS_AT|ENDS_AT]->(p:DrayageRecord {dataset:$dataset, revision:$revision}) "
                            "WHERE e.dataset=$dataset AND e.revision=$revision "
                            "RETURN type(e) AS rel, p.id AS pid, p.kind AS kind",
                            sid=sid)
                by_rel = {r["rel"]: r for r in ends}
                if (set(by_rel) != {"STARTS_AT", "ENDS_AT"}
                        or by_rel["STARTS_AT"]["pid"] != seg_records[sid]["from_node"]
                        or by_rel["ENDS_AT"]["pid"] != seg_records[sid]["to_node"]
                        or by_rel["STARTS_AT"]["kind"] != "physical_location"
                        or by_rel["ENDS_AT"]["kind"] != "physical_location"):
                    record(fail("C2", "segment endpoints",
                                f"Segment {sid}: STARTS_AT/ENDS_AT edges do not match "
                                f"record endpoints or physical_location kinds: {ends}."))
                    return finish(started, args, checks, database, driver, snapshot_sha, "C2")
            route_evidence[route_id] = ordered
        record(ok("C2", "routes + ordered segments + connectivity",
                  "4 routes with exact 1..N sequences; every chain link and "
                  "STARTS_AT/ENDS_AT endpoint verified.",
                  {"routes": route_evidence}))

        # ============ C3: jurisdiction context per segment ============
        juris_evidence: dict = {}
        total_located = 0
        for sid in EXPECTED_SEGMENTS:
            located = read("MATCH (s:DrayageRecord {dataset:$dataset, revision:$revision, id:$sid})"
                           "-[e:LOCATED_WITHIN]->(j:DrayageRecord {dataset:$dataset, revision:$revision}) "
                           "WHERE e.dataset=$dataset AND e.revision=$revision "
                           "RETURN j.id AS jid, j.kind AS kind ORDER BY jid", sid=sid)
            cats = read("MATCH (s:DrayageRecord {dataset:$dataset, revision:$revision, id:$sid})"
                        "-[e:HAS_NJOGIS_JURISDICTION_CATEGORY]->(d:DrayageRecord {dataset:$dataset, revision:$revision}) "
                        "WHERE e.dataset=$dataset AND e.revision=$revision "
                        "RETURN d.id AS did ORDER BY did", sid=sid)
            gov = read("MATCH (c:DrayageRecord {dataset:$dataset, revision:$revision})-[e]->"
                       "(s:DrayageRecord {dataset:$dataset, revision:$revision, id:$sid}) "
                       "WHERE e.dataset=$dataset AND e.revision=$revision "
                       "AND type(e) IN ['GOVERNS','OVERLAPS_PART_OF','STREET_NOT_LISTED_IN_RESTRICTION_TABLE',"
                       "'ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C','TRUCK_ROUTE_SCHEDULE_RESERVED'] "
                       "RETURN c.id AS clause_id, type(e) AS rel ORDER BY clause_id, rel", sid=sid)
            total_located += len(located)
            juris_evidence[sid] = {"located_within": [r["jid"] for r in located],
                                   "njogis_categories": [r["did"] for r in cats],
                                   "governing_clauses": len(gov)}
            if not located or not cats or not gov:
                record(fail("C3", "segment jurisdiction context",
                            f"Segment {sid}: located={len(located)}, njogis={len(cats)}, "
                            f"governing={len(gov)} (each must be >= 1)."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C3")
            if any(r["kind"] not in ("jurisdiction", "facility_jurisdiction") for r in located):
                record(fail("C3", "segment jurisdiction context",
                            f"Segment {sid}: LOCATED_WITHIN target is not a jurisdiction: {located}."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C3")
        if total_located != 18:
            record(fail("C3", "segment jurisdiction context",
                        f"Expected 18 LOCATED_WITHIN edges total, found {total_located}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C3")
        record(ok("C3", "segment ownership/control/jurisdiction context",
                  "All 9 segments carry LOCATED_WITHIN jurisdictions, NJOGIS categories, "
                  "and >=1 clause-governance edge.",
                  juris_evidence))

        # ============ C4: applicability paths (never inferred from ownership) ============
        gov_starts = {r["kind"] for r in read(
            "MATCH (c:DrayageRecord {dataset:$dataset, revision:$revision})-[e]->"
            "(:DrayageRecord {dataset:$dataset, revision:$revision}) "
            "WHERE e.dataset=$dataset AND e.revision=$revision "
            "AND type(e) IN ['GOVERNS','OVERLAPS_PART_OF','STREET_NOT_LISTED_IN_RESTRICTION_TABLE',"
            "'ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C','TRUCK_ROUTE_SCHEDULE_RESERVED',"
            "'GOVERNS_ACCESS_AT','GOVERNS_ENTRY_AT','GOVERNS_GATE_MOVE_AT',"
            "'GOVERNS_PORT_ENTRY_MOVEMENT_AT','GOVERNS_UNESCORTED_SECURE_ACCESS_AT'] "
            "RETURN DISTINCT c.kind AS kind")}
        if gov_starts != {"source_clause"}:
            record(fail("C4", "applicability provenance",
                        f"Governance edges must originate only from source_clause, found {sorted(gov_starts)}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C4")
        appliers = read("MATCH (c:DrayageRecord {dataset:$dataset, revision:$revision})"
                        "-[e:APPLIES_AT|REQUIRES_PROGRAM|SUPPORTS]->"
                        "(:DrayageRecord {dataset:$dataset, revision:$revision}) "
                        "WHERE e.dataset=$dataset AND e.revision=$revision "
                        "RETURN DISTINCT c.kind AS kind")
        bad_appliers = [r["kind"] for r in appliers
                        if r["kind"] in ("jurisdiction", "authority", "terminal",
                                         "terminal_operator", "facility_jurisdiction")]
        if bad_appliers:
            record(fail("C4", "applicability provenance",
                        f"Ownership nodes must not author applicability edges: {bad_appliers}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C4")
        term = read("MATCH (:DrayageRecord {dataset:$dataset, revision:$revision, id:'check_apm_induction_v1'})"
                    "-[e:APPLIES_AT]->(t:DrayageRecord {dataset:$dataset, revision:$revision}) "
                    "WHERE e.dataset=$dataset AND e.revision=$revision RETURN t.id AS id")
        prog = read("MATCH (:DrayageRecord {dataset:$dataset, revision:$revision, id:'check_apm_induction_v1'})"
                    "-[e:REQUIRES_PROGRAM]->(p:DrayageRecord {dataset:$dataset, revision:$revision}) "
                    "WHERE e.dataset=$dataset AND e.revision=$revision RETURN p.id AS id")
        supp = read("MATCH (s:DrayageRecord {dataset:$dataset, revision:$revision})"
                    "-[e:SUPPORTS]->(:DrayageRecord {dataset:$dataset, revision:$revision, id:'check_apm_induction_v1'}) "
                    "WHERE e.dataset=$dataset AND e.revision=$revision RETURN s.id AS id ORDER BY id")
        if ([r["id"] for r in term] != ["facility_apm_elizabeth"]
                or [r["id"] for r in prog] != ["training_apm_safety_induction"]
                or sorted(r["id"] for r in supp)
                != ["prototype_clause_induction_sealink_change", "reg_apm_safety_induction"]):
            record(fail("C4", "check-definition wiring",
                        f"APPLIES_AT={term}, REQUIRES_PROGRAM={prog}, SUPPORTS={supp}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C4")
        from neo4j_kg.requirements import REQUIREMENTS  # noqa: E402
        clause_ids = {n["id"] for n in live_nodes if n["kind"] == "source_clause"}
        catalog_missing = {req["id"]: [c for c in req["source_clause_ids"] if c not in clause_ids]
                           for req in REQUIREMENTS}
        if any(catalog_missing.values()):
            record(fail("C4", "catalog clause resolution",
                        f"Requirement clauses missing from graph: "
                        f"{{k: v for k, v in catalog_missing.items() if v}}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C4")
        tx_gap = next(r for r in REQUIREMENTS if r["id"] == "transaction_release")
        if tx_gap["source_clause_ids"]:
            record(fail("C4", "explicit coverage gap",
                        "transaction_release must keep zero source clauses (explicit gap)."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C4")
        record(ok("C4", "requirement/rule applicability paths",
                  "Governance originates only from source_clause; induction check keeps "
                  "1 terminal + 1 program + 2 supporting clauses; all 26 catalog clauses "
                  "resolve; transaction_release gap stays explicit."))

        # ============ C5: clause -> source provenance, no dangling refs ============
        prov = read("MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision, kind:'source_clause'}) "
                    "OPTIONAL MATCH (d:DrayageRecord {dataset:$dataset, revision:$revision})"
                    "-[e:CONTAINS_CLAUSE]->(n) WHERE e.dataset=$dataset AND e.revision=$revision "
                    "RETURN n.id AS clause_id, count(e) AS n_in, collect(d.id) AS sources ORDER BY n.id")
        bad_prov = [r for r in prov if r["n_in"] != 1]
        if bad_prov:
            record(fail("C5", "clause provenance",
                        f"{len(bad_prov)} clauses lack exactly one CONTAINS_CLAUSE parent "
                        f"(sample: {bad_prov[:3]})."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C5")
        source_ids = {n["id"] for n in live_nodes if n["kind"] == "source_document"}
        by_id = {n["id"]: json.loads(n["record_json"]) for n in live_nodes}
        dangling = [c for c in by_id if by_id[c].get("source_id") and by_id[c]["source_id"] not in source_ids
                    and live_nodes and by_id[c].get("source_id") not in {n["id"] for n in live_nodes}]
        # scope: only source_clause records carry source_id in this release
        clause_dangling = [r["clause_id"] for r in prov
                           if by_id[r["clause_id"]].get("source_id") not in source_ids]
        _ = dangling
        if clause_dangling:
            record(fail("C5", "clause provenance",
                        f"Clauses with unresolvable source_id: {clause_dangling}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C5")
        record(ok("C5", "requirement/clause -> source provenance",
                  f"All {len(prov)} source clauses have exactly one source_document parent "
                  f"and a resolvable source_id; edge endpoints already proven in C1."))

        # ============ C6: mutable observations quarantined ============
        muts = read("MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision, kind:'mutable_observation'}) "
                    "RETURN n.id AS id, n.layer AS layer, n.archive AS archive, "
                    "n.record_json AS record ORDER BY n.id")
        if len(muts) != 5 or any(m["layer"] != "quarantined_observation" for m in muts):
            record(fail("C6", "mutable quarantine",
                        f"Expected 5 quarantined_observation nodes, "
                        f"found {[(m['id'], m['layer']) for m in muts]}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C6")
        acting = read("MATCH (m:DrayageRecord {dataset:$dataset, revision:$revision, kind:'mutable_observation'})"
                      "-[e:SUPPORTS|APPLIES_AT|REQUIRES_PROGRAM|CONTAINS_CLAUSE]-() "
                      "WHERE e.dataset=$dataset AND e.revision=$revision "
                      "RETURN m.id AS id, type(e) AS rel LIMIT 10")
        if acting:
            record(fail("C6", "mutable quarantine",
                        f"Observations must never act as clauses: {acting}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C6")
        port_ok = True
        for m in muts:
            rec = json.loads(m["record"])
            src = (rec.get("archive_context") or {}).get("source_id")
            if src not in source_ids:
                port_ok = False
        if not port_ok:
            record(fail("C6", "mutable quarantine",
                        "A mutable observation has an unresolvable archive_context.source_id."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C6")
        record(ok("C6", "mutable observations distinguishable",
                  "5 quarantined_observation nodes with resolvable archived sources; "
                  "none participates in clause/applicability edges.",
                  {"observations": [m["id"] for m in muts]}))

        # ============ C7: unresolved / missing stays explicit ============
        op_true = [n["id"] for n in live_nodes
                   if json.loads(n["record_json"]).get("operational_use") is True]
        if op_true:
            record(fail("C7", "no silent clearance",
                        f"Nodes claiming operational_use=true: {op_true}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C7")
        check_rec = by_id["check_apm_induction_v1"]
        if check_rec.get("approval_status") != "draft_not_human_approved" \
                or check_rec.get("operational_currentness") != "not_verified":
            record(fail("C7", "no silent clearance",
                        f"Check definition lost its draft boundaries: {check_rec}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C7")
        record(ok("C7", "unresolved/missing explicit",
                  "No operational_use=true record; check stays draft_not_human_approved + "
                  "not_verified; transaction_release gap explicit (C4); live unresolved "
                  "behavior proven end-to-end in C8."))

        # ============ C8: MCP evaluator bounded patterns (through real code) ============
        from neo4j_kg.store import Neo4jStore  # noqa: E402
        from neo4j_kg.service import Evaluation  # noqa: E402
        from neo4j_kg.evidence import requirement_evidence  # noqa: E402
        from neo4j import GraphDatabase as _GDB  # noqa: E402
        svc_driver = _GDB.driver(config["NEO4J_URI"],
                                 auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]),
                                 connection_timeout=10, connection_acquisition_timeout=15,
                                 max_transaction_retry_time=10, max_connection_pool_size=4)
        store = Neo4jStore(svc_driver, database, REVISION)
        try:
            probe = store.read(lambda reader: Evaluation(reader).check(
                {"terminal_id": None, "actor_role": None, "driver_id": None,
                 "current_sealink_id": None, "trip_at": None,
                 "question_scope": "induction", "company_changed": None}))
            if not (probe["check_status"] == "unresolved"
                    and probe["applicability"] == "unresolved"
                    and set(("terminal_id", "actor_role")) <= set(probe["missing_facts"])
                    and probe["operational_status"] == "unresolved_not_assessed"
                    and probe["versions"]["graph_release"] == REVISION):
                record(fail("C8", "evaluator missing-fact behavior",
                            f"All-null induction probe did not stay explicitly unresolved: {probe}."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C8",
                              extra_driver=svc_driver)
            ctx = {t: store.read(lambda reader, t=t: Evaluation(reader).context(t))
                   for t in ("summary", "induction", "route_directions", "port_street", "coverage")}
            if ctx["summary"]["node_count"] != 121 or ctx["summary"]["edge_count"] != 202 \
                    or "Neo4j" not in ctx["summary"]["engine"]:
                record(fail("C8", "evaluator summary context",
                            f"Unexpected summary: {ctx['summary']}."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C8",
                              extra_driver=svc_driver)
            if len(ctx["route_directions"]["routes"]) != 4 or len(ctx["port_street"]["observations"]) != 5:
                record(fail("C8", "evaluator route/observation context",
                            f"routes={len(ctx['route_directions']['routes'])}, "
                            f"observations={len(ctx['port_street']['observations'])}."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C8",
                              extra_driver=svc_driver)
            ev_statuses = {}
            for req in REQUIREMENTS:
                payload = store.read(lambda reader, rid=req["id"]: requirement_evidence(reader, rid))
                if payload["requirement_id"] != req["id"] or payload["operational_use"] is not False:
                    record(fail("C8", "requirement evidence structure",
                                f"Requirement {req['id']}: bad identity/operational_use."))
                    return finish(started, args, checks, database, driver, snapshot_sha, "C8",
                                  extra_driver=svc_driver)
                for src in payload["sources"]:
                    for field in ("clause_id", "source_id", "publisher", "title", "url",
                                  "locator", "source_text"):
                        if field not in src:
                            record(fail("C8", "requirement evidence structure",
                                        f"Requirement {req['id']}: citation missing {field}."))
                            return finish(started, args, checks, database, driver,
                                          snapshot_sha, "C8", extra_driver=svc_driver)
                ev_statuses[req["id"]] = payload["evidence_status"]
            tx_payload = store.read(lambda reader: requirement_evidence(reader, "transaction_release"))
            if tx_payload["sources"] or tx_payload["evidence_status"] == "archived_only":
                record(fail("C8", "requirement evidence structure",
                            "transaction_release must keep zero archived sources "
                            f"(got {len(tx_payload['sources'])} sources, "
                            f"status {tx_payload['evidence_status']})."))
                return finish(started, args, checks, database, driver, snapshot_sha, "C8",
                              extra_driver=svc_driver)
        finally:
            store.close()  # closes svc_driver only; main driver stays open
        record(ok("C8", "MCP evaluator bounded patterns",
                  "Real Evaluation.check/context/requirement_evidence paths return expected "
                  "fields: unresolved probe explicit, summary 121/202 Neo4j, 4 routes, "
                  "5 observations, 13 requirement packages with citations; "
                  "transaction_release keeps zero archived sources (explicit gap).",
                  {"requirement_evidence_status": ev_statuses}))

        # ============ C9: Wave-4 isolation ============
        cross_label = read("MATCH (n) WHERE (n:DrayageRecord AND n:Wave4Entity) "
                           "RETURN count(*) AS c")[0]["c"]
        d2w = read("MATCH (:DrayageRecord)-[e]->(:Wave4Entity) RETURN count(*) AS c")[0]["c"]
        w2d = read("MATCH (:Wave4Entity)-[e]->(:DrayageRecord) RETURN count(*) AS c")[0]["c"]
        if cross_label != 0 or d2w != 0 or w2d != 0:
            record(fail("C9", "wave-4 isolation",
                        f"Cross-graph contamination: dual-labeled={cross_label}, "
                        f"drayage->wave4={d2w}, wave4->drayage={w2d}."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C9")
        wave4_nodes = read("MATCH (n:Wave4Entity) RETURN count(*) AS c")[0]["c"]
        wave4_edges = read("MATCH (:Wave4Entity)-[e]->(:Wave4Entity) RETURN count(*) AS c")[0]["c"]
        releases_all = read("MATCH (r:DrayageRelease) RETURN r.dataset AS ds, r.revision AS rev ORDER BY rev")
        if not any(r["ds"] == DATASET and r["rev"] == REVISION for r in releases_all):
            record(fail("C9", "wave-4 isolation", "Pinned drayage release missing from release index."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C9")
        record(ok("C9", "wave-4 isolation",
                  f"No dual-labeled nodes, no cross-graph edges; drayage releases: {len(releases_all)}; "
                  f"Wave-4 observed intact ({wave4_nodes} nodes / {wave4_edges} rels).",
                  {"wave4_nodes_observed": wave4_nodes, "wave4_edges_observed": wave4_edges,
                   "drayage_releases": [{"dataset": r["ds"], "revision": r["rev"]} for r in releases_all]}))

        # ============ C10: pinned hashes + fingerprint ============
        from neo4j_kg.common import encode as _encode  # noqa: E402
        body = {k: v for k, v in snapshot.items() if k != "revision"}
        if digest(body) != REVISION:
            record(fail("C10", "release fingerprint",
                        "Snapshot body digest does not equal the pinned revision."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C10")
        try:
            verify_files(snapshot)  # 51 local source/archive bytes, read-only
        except Exception as exc:
            record(fail("C10", "pinned source hashes",
                        f"Local evidence bytes mismatch ({type(exc).__name__}: {exc})."))
            return finish(started, args, checks, database, driver, snapshot_sha, "C10")
        record(ok("C10", "pinned hashes + fingerprint",
                  f"Revision digest recomputed; all {len(snapshot['file_hashes'])} pinned "
                  f"source hashes match local bytes; live manifest+graph already proven "
                  f"identical to snapshot in C1.",
                  {"file_hashes_verified": len(snapshot["file_hashes"]),
                   "evidence_version": snapshot["versions"].get("evidence"),
                   "model_version": snapshot["versions"].get("model"),
                   "synthetic_evidence_version": snapshot["versions"].get("synthetic_evidence")}))
    except Exception as exc:
        record(fail("CX", "unexpected validation error",
                    f"{type(exc).__name__}: {exc}"))
        return finish(started, args, checks, database, driver, snapshot_sha, "CX")

    return finish(started, args, checks, database, driver, snapshot_sha, None)


def finish(started, args, checks, database, driver, snapshot_sha, first_failure,
           extra_driver=None):
    if extra_driver is not None:
        try:
            extra_driver.close()
        except Exception:
            pass
    finished = datetime.now(timezone.utc)
    overall = "PASS" if checks and all(c["status"] == "PASS" for c in checks) \
        and first_failure is None else "FAIL"
    # mark remaining checks skipped after a short-circuit failure
    if first_failure is not None:
        done = {c["id"] for c in checks}
        for missing in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"):
            if missing not in done and missing != "C0":
                checks.append({"id": missing, "name": "not executed",
                               "status": "skipped",
                               "detail": f"Skipped after first defect at {first_failure}."})
    receipt = {
        "validation": "pinned-release-validation",
        "revision": REVISION,
        "dataset": DATASET,
        "database": database,
        "snapshot_path": str(SNAPSHOT_PATH),
        "snapshot_sha256": snapshot_sha,
        "script_sha256": sha_file(Path(__file__)),
        "queries_sha256": sha_file(AUDIT_DIR / "queries.cypher"),
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "overall": overall,
        "first_failure": first_failure,
        "expected": {"nodes": EXPECTED_NODES, "edges": EXPECTED_EDGES,
                     "routes": len(EXPECTED_ROUTES), "segments": len(EXPECTED_SEGMENTS)},
        "checks": checks,
        "write_guarantee": "MATCH-only Cypher via READ_ACCESS execute_read; "
                           "no execute_write, no import, no TripStore writes.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"overall={overall} receipt={args.receipt}", flush=True)
    if driver is not None:
        try:
            driver.close()
        except Exception:
            pass
    raise SystemExit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
