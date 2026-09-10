"""Minimal read-only MCP stdio server; no listener, shell tool, or network calls.

Implements the 2025-11-25 lifecycle/tools subset. This is not a complete MCP SDK
or a hosted connector. Tool protocol transcripts contain synthetic records only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

from .service import CheckingService, InputError, ROOT, normalize


PROTOCOL_VERSION = "2025-11-25"
MAX_MESSAGE_BYTES = 65536
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False,
               "idempotentHint": True, "openWorldHint": False}
INPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "terminal_id": {"type": ["string", "null"], "enum": ["facility_apm_elizabeth", "synthetic_other_terminal", None],
                        "description": "APM Elizabeth ID, the synthetic other terminal, or null if unknown."},
        "actor_role": {"type": ["string", "null"], "enum": ["truck_driver", "other", None]},
        "driver_id": {"type": ["string", "null"], "pattern": "^syn-driver-[a-z-]{1,40}$",
                      "description": "Synthetic driver alias supplied by the user, not a real driver identifier. Do not guess."},
        "current_sealink_id": {"type": ["string", "null"], "pattern": "^SYN-SL-[A-Z]{1,8}$",
                              "description": "Current synthetic SeaLink alias; never substitute an old identifier or invent one."},
        "trip_at": {"type": ["string", "null"], "maxLength": 40,
                    "description": "Exact supplied trip timestamp including seconds and timezone. Use null if absent; never use today's date to fill it."},
        "question_scope": {"type": "string", "enum": ["induction", "terminal_entry", "trip_dispatch", "route"]},
        "company_changed": {"type": ["boolean", "null"],
                            "description": "Whether the user reports a company change. This does not establish a SeaLink change."},
    },
}
TOOLS = [
    {"name": "check_apm_induction", "title": "Check synthetic APM induction evidence",
     "description": "Use for the synthetic APM Elizabeth driver-induction experiment. Query the server-owned knowledge graph and completion evidence using the user's supplied facts. Missing facts must stay null. The caller cannot supply completion evidence. Returns a single-requirement result, sources, missing facts, and separate unchecked trip coverage. No real driver verification or dispatch clearance. Use when asked whether the synthetic driver has induction, can enter, can dispatch, or can use a route; broader questions will retain a coverage gap.",
     "inputSchema": INPUT_SCHEMA, "annotations": ANNOTATIONS},
    {"name": "get_drayage_graph_context", "title": "Inspect retained drayage graph evidence",
     "description": "Read public archived evidence, the prototype induction definition, graph counts, route directions, Port Street observation limits, or unimplemented coverage. This is not a live policy or routing check. No arbitrary file or database query access.",
     "inputSchema": {"type": "object", "additionalProperties": False,
                     "properties": {"topic": {"type": "string", "enum": ["summary", "induction", "route_directions", "port_street", "coverage"]}},
                     "required": ["topic"]}, "annotations": ANNOTATIONS},
]


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def strict_loads(raw):
    def reject_constant(value):
        raise ValueError("Non-finite JSON number")
    return json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_constant=reject_constant)


class Session:
    def __init__(self, service=None, audit_path: Path | None = None):
        self.service = service or CheckingService()
        self.state = "new"
        self.audit_path = audit_path
        self.sequence = 0
        self.previous_event_hash = None

    def audit(self, method, request_id, arguments, response):
        if self.audit_path is None:
            return
        from .graph import digest
        self.sequence += 1
        event = {"sequence": self.sequence, "recorded_at": datetime.now(timezone.utc).isoformat(),
                 "surface": "mcp_client_not_yet_attributed_to_provider", "method": method,
                 "request_id": request_id, "validated_arguments": arguments,
                 "response": response, "previous_event_hash": self.previous_event_hash}
        event["event_hash"] = digest(event)
        self.previous_event_hash = event["event_hash"]
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(encode(event) + "\n")

    def handle(self, request):
        request_id = request.get("id") if isinstance(request, dict) else None
        def error(code, message):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return error(-32600, "Invalid JSON-RPC request")
        if "id" in request and request_id is None:
            return error(-32600, "MCP request ids cannot be null")
        if request_id is not None and (type(request_id) not in (str, int) or len(str(request_id)) > 128):
            request_id = None
            return error(-32600, "Invalid request id")
        method = request["method"]
        params = request.get("params", {})
        if request_id is None:
            if method == "notifications/initialized" and self.state == "initializing":
                self.state = "ready"
            return None  # JSON-RPC notifications do not receive responses.
        if not isinstance(params, dict):
            return error(-32602, "params must be an object")
        if method == "initialize":
            if self.state != "new":
                return error(-32600, "Session already initialized")
            if not isinstance(params.get("protocolVersion"), str) or not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
                return error(-32602, "initialize requires protocolVersion, capabilities and clientInfo")
            self.state = "initializing"
            result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "drayage-kg-prototype", "version": "0.1.0"},
                      "instructions": "Synthetic, draft, single-requirement experiment only. Preserve missing facts, source limits and unchecked trip coverage. Never issue dispatch or entry clearance."}
        elif method == "ping":
            result = {}
        elif self.state != "ready":
            return error(-32600, "Initialize the session before using tools")
        elif method == "tools/list":
            if params.get("cursor") is not None:
                return error(-32602, "This server has no additional tool pages")
            result = {"tools": TOOLS}
        elif method == "tools/call":
            if set(params) - {"name", "arguments", "_meta"}:
                return error(-32602, "Unsupported tools/call parameter")
            name = params.get("name")
            args = params.get("arguments", {})
            if not isinstance(name, str) or name not in {tool["name"] for tool in TOOLS}:
                return error(-32602, "Unknown tool")
            try:
                if name == "check_apm_induction":
                    validated = normalize(args)
                    payload = self.service.check(args)
                else:
                    if not isinstance(args, dict) or set(args) != {"topic"} or not isinstance(args["topic"], str):
                        raise InputError("Expected only a topic string")
                    payload = self.service.context(args["topic"])
                    validated = args.copy()
                result = {"content": [{"type": "text", "text": encode(payload)}],
                          "structuredContent": payload, "isError": False}
                response = {"jsonrpc": "2.0", "id": request_id, "result": result}
                self.audit(name, request_id, {"as_received": args, "normalized": validated}, response)
                return response
            except InputError as exc:
                result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
            except Exception:
                # Do not emit tracebacks, paths, raw input or accidental secrets to the client.
                result = {"content": [{"type": "text", "text": "Checking service failed; no result or clearance is available."}], "isError": True}
        else:
            return error(-32601, "Method not found")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(input_stream, output_stream, session):
    while True:
        raw = input_stream.readline(MAX_MESSAGE_BYTES + 1)
        if not raw:
            break
        size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
        if size > MAX_MESSAGE_BYTES:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Message too large; session closed"}}
            output_stream.write(encode(response) + "\n")
            output_stream.flush()
            break
        try:
            response = session.handle(strict_loads(raw))
        except (ValueError, UnicodeError, RecursionError):
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON"}}
        if response is not None:
            output_stream.write(encode(response) + "\n")
            output_stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="Record validated synthetic tool exchanges in .runtime")
    options = parser.parse_args()
    audit_path = None
    if options.audit:
        runtime = ROOT / ".runtime"
        runtime.mkdir(exist_ok=True, mode=0o700)
        audit_path = runtime / f"mcp-session-{uuid.uuid4().hex}.jsonl"
        audit_path.touch(mode=0o600, exist_ok=False)
        print(f"Synthetic MCP audit: {audit_path}", file=sys.stderr, flush=True)
    serve(sys.stdin.buffer, sys.stdout, Session(audit_path=audit_path))


if __name__ == "__main__":
    main()
