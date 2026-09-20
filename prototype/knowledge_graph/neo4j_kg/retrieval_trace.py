"""Opt-in, request-local query receipts; not model-facing response content."""
from contextlib import contextmanager
from contextvars import ContextVar

from .common import digest

_active = ContextVar("drayage_trace", default=None)
_phase = ContextVar("drayage_trace_phase", default="assessment_retrieval")


def begin(enabled):
    return _active.set([] if enabled else None)


def finish(token):
    _active.reset(token)


@contextmanager
def phase(name):
    token = _phase.set(name)
    try:
        yield
    finally:
        _phase.reset(token)


def receipt(payload):
    clauses, evidence, observations = set(), set(), set()
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("clause_id"), str) and "source_text" in value:
                clauses.add(value["clause_id"])
            if isinstance(value.get("condition_id"), str) and "source_text" in value:
                observations.add(value["condition_id"])
            if isinstance(value.get("evidence_ids"), list):
                evidence.update(x for x in value["evidence_ids"] if isinstance(x, str))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(payload)
    return {"queries": list(_active.get() or []),
            "delivered_passage_clause_ids": sorted(clauses),
            "reported_evidence_ids": sorted(evidence),
            "delivered_observation_ids": sorted(observations),
            "note": "Release validation reads are not evidence delivered to the model. Reads do not prove use in an answer."}


class TracedTransaction:
    def __init__(self, tx):
        self.tx = tx

    def run(self, query, **parameters):
        trace = _active.get()
        if trace is None:
            return self.tx.run(query, **parameters)
        event = {"phase": _phase.get(), "query_id": digest(query),
                 "cypher": query, "parameters": parameters}
        trace.append(event)
        try:
            rows = list(self.tx.run(query, **parameters))
            identifiers = set()
            for row in rows:
                for value in dict(row).values():
                    if isinstance(value, dict):
                        identifiers.update(value[k] for k in ("id", "from", "to")
                                           if isinstance(value.get(k), str))
                if isinstance(dict(row).get("id"), str):
                    identifiers.add(row["id"])
            if rows and isinstance(parameters.get("id"), str):
                identifiers.add(parameters["id"])
            event.update(status="ok", row_count=len(rows), record_ids=sorted(identifiers),
                         result_hash=digest([dict(row) for row in rows]))
            return rows
        except Exception as exc:
            event.update(status="error", error_type=type(exc).__name__)
            raise
