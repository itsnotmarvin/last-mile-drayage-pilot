"""Pinned immutable Neo4j releases and parameterized, read-only graph queries."""
from __future__ import annotations

import copy
import json
from collections import Counter

from .common import ArchiveError, EvidenceUnavailable, DATASET, encode, validate_release, verify_files


def decode_record(raw):
    """Malformed provider records are integrity failures, not callback defects."""
    try:
        record = json.loads(raw)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ArchiveError("Invalid evidence record encoding") from exc
    if not isinstance(record, dict):
        raise ArchiveError("Evidence record must be an object")
    return record


def read_release(tx, revision):
    try:
        return _read_release(tx, revision)
    except ArchiveError:
        raise
    except (ValueError, KeyError, TypeError, IndexError, RecursionError) as exc:
        raise ArchiveError("Malformed evidence release") from exc


def _read_release(tx, revision):
    rows = list(tx.run(
        "MATCH (r:DrayageRelease {dataset:$dataset, revision:$revision}) "
        "RETURN r.manifest_json AS manifest", dataset=DATASET, revision=revision))
    if len(rows) != 1:
        raise ArchiveError("Validated Neo4j evidence release is unavailable")
    release = decode_record(rows[0]["manifest"])
    release["nodes"] = [dict(row["node"]) for row in tx.run(
        "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
        "RETURN n{.id,.kind,.layer,.archive,.ordinal,.record_json} AS node ORDER BY n.ordinal",
        dataset=DATASET, revision=revision)]
    release["edges"] = [dict(row["edge"]) for row in tx.run(
        "MATCH (a:DrayageRecord {dataset:$dataset, revision:$revision})-[e]->"
        "(b:DrayageRecord {dataset:$dataset, revision:$revision}) "
        "WHERE e.dataset=$dataset AND e.revision=$revision "
        "RETURN {id:e.id, from:a.id, to:b.id, relationship:type(e), "
        "archive:e.archive, ordinal:e.ordinal, record_json:e.record_json} AS edge ORDER BY e.ordinal",
        dataset=DATASET, revision=revision)]
    if release.get("revision") != revision:
        raise ArchiveError("Release identity differs from requested revision")
    return validate_release(release)


class GraphReader:
    """One tool invocation; all graph lookups use a single Neo4j read transaction."""

    def __init__(self, tx, release):
        self.tx = tx
        self.release = release
        self.params = {"dataset": DATASET, "revision": release["revision"]}
        self._nodes = {}

    def node(self, node_id, required=True):
        if node_id not in self._nodes:
            rows = list(self.tx.run(
                "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision, id:$id}) "
                "RETURN n.kind AS kind, n.layer AS layer, n.archive AS archive, n.record_json AS record",
                **self.params, id=node_id))
            if len(rows) > 1:
                raise ArchiveError("Nonunique graph record")
            self._nodes[node_id] = None if not rows else {
                "kind": rows[0]["kind"], "layer": rows[0]["layer"],
                "archive": rows[0]["archive"], "record": decode_record(rows[0]["record"])}
        result = self._nodes[node_id]
        if result is None and required:
            raise ArchiveError("Required graph record is unavailable")
        return copy.deepcopy(result)

    def record(self, node_id):
        return self.node(node_id)["record"]

    def neighbors(self, node_id, relationship, incoming=False):
        # Only this internal boolean changes syntax. Every caller value is a parameter.
        pattern = "(n)<-[e]-(other)" if incoming else "(n)-[e]->(other)"
        return [row["id"] for row in self.tx.run(
            "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision, id:$id}) "
            f"MATCH {pattern} WHERE other:DrayageRecord "
            "AND other.dataset=$dataset AND other.revision=$revision "
            "AND e.dataset=$dataset AND e.revision=$revision AND type(e)=$relationship "
            "RETURN other.id AS id ORDER BY id",
            **self.params, id=node_id, relationship=relationship)]

    def records_by_kind(self, kinds, archive_only=True):
        return [decode_record(row["record"]) for row in self.tx.run(
            "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
            "WHERE n.kind IN $kinds AND (NOT $archive_only OR n.archive=true) "
            "RETURN n.record_json AS record ORDER BY n.ordinal",
            **self.params, kinds=list(kinds), archive_only=archive_only)]

    def summary(self):
        kinds = {row["kind"]: row["count"] for row in self.tx.run(
            "MATCH (n:DrayageRecord {dataset:$dataset, revision:$revision}) "
            "WHERE n.archive=true RETURN n.kind AS kind, count(*) AS count",
            **self.params)}
        return {
            "engine": "Neo4j persistent graph; parameterized read transactions",
            "evidence_version": self.release["versions"]["evidence"],
            "node_count": sum(kinds.values()),
            "edge_count": sum(e["archive"] for e in self.release["edges"]),
            "node_kinds": kinds, "operational_use": False,
            "prototype_node_count": len(self.release["nodes"]),
            "prototype_edge_count": len(self.release["edges"]),
        }


class Neo4jStore:
    def __init__(self, driver, database, revision):
        if not isinstance(revision, str) or len(revision) != 64 or any(c not in "0123456789abcdef" for c in revision):
            raise ArchiveError("Configure a validated, pinned Neo4j release revision")
        self.driver, self.database, self.revision = driver, database, revision

    @classmethod
    def from_environment(cls):
        import os
        from .config import connect
        driver, database = connect()
        try:
            return cls(driver, database, os.environ.get("DRAYAGE_NEO4J_REVISION"))
        except Exception:
            driver.close()
            raise

    def read(self, operation):
        from neo4j import READ_ACCESS, unit_of_work
        from neo4j.exceptions import DriverError, Neo4jError

        @unit_of_work(timeout=30)
        def invoke(tx):
            # Validate fresh database content and source bytes before every answer.
            # There is no cached successful result or fallback to the old backend.
            release = read_release(tx, self.revision)
            verify_files(release)
            return operation(GraphReader(tx, release))

        try:
            with self.driver.session(database=self.database, default_access_mode=READ_ACCESS) as session:
                return session.execute_read(invoke)
        except (DriverError, Neo4jError) as exc:
            raise EvidenceUnavailable("Neo4j evidence provider unavailable") from exc

    def close(self):
        self.driver.close()
