import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from kg.graph import digest
from kg.mcp_server import MAX_MESSAGE_BYTES, Session, serve
from kg.service import CheckingService


ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "tests/acceptance.json").read_text())["default_input"]
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                   "clientInfo": {"name": "local-test-harness", "version": "1"}}}
READY = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def call(name="check_apm_induction", arguments=None):
    return {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": name, "arguments": BASE if arguments is None else arguments}}


class MCPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = CheckingService()

    def session(self, audit_path=None):
        session = Session(self.service, audit_path)
        session.handle(INIT)
        session.handle(READY)
        return session

    def test_initialize_required(self):
        self.assertIn("error", Session(self.service).handle(call()))

    def test_initialized_notification_required(self):
        session = Session(self.service)
        session.handle(INIT)
        self.assertIn("error", session.handle(call()))

    def test_version_negotiates_supported_version(self):
        request = INIT | {"params": INIT["params"] | {"protocolVersion": "2030-01-01"}}
        self.assertEqual("2025-11-25", Session(self.service).handle(request)["result"]["protocolVersion"])

    def test_duplicate_initialization_rejected(self):
        self.assertIn("error", self.session().handle(INIT))

    def test_tools_are_read_only(self):
        response = self.session().handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(2, len(response["result"]["tools"]))
        for tool in response["result"]["tools"]:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])
            self.assertFalse(tool["inputSchema"]["additionalProperties"])

    def test_transport_matches_direct_check(self):
        result = self.session().handle(call())["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(self.service.check(BASE), result["structuredContent"])
        self.assertEqual(result["structuredContent"], json.loads(result["content"][0]["text"]))

    def test_missing_facts_are_tool_result_not_transport_error(self):
        result = self.session().handle(call(arguments={}))["result"]
        self.assertFalse(result["isError"])
        self.assertEqual("unresolved", result["structuredContent"]["check_status"])

    def test_injection_is_tool_error_not_clearance(self):
        result = self.session().handle(call(arguments=BASE | {"completed": True}))["result"]
        self.assertTrue(result["isError"])
        self.assertNotIn("structuredContent", result)

    def test_context_tool_rejects_path_or_arbitrary_query(self):
        for args in ({"path": "/etc/passwd"}, {"topic": "summary", "query": "anything"}, {"topic": []}):
            with self.subTest(args=args):
                self.assertTrue(self.session().handle(call("get_drayage_graph_context", args))["result"]["isError"])

    def test_unknown_tool_is_protocol_error(self):
        self.assertIn("error", self.session().handle(call("run_shell")))

    def test_malformed_tool_names_are_errors_not_server_crashes(self):
        for value in (None, [], {}, 3, True):
            with self.subTest(value=value):
                self.assertIn("error", self.session().handle(call(value)))

    def test_unknown_method_is_protocol_error(self):
        self.assertEqual(-32601, self.session().handle({"jsonrpc": "2.0", "id": 4, "method": "made/up"})["error"]["code"])

    def test_notification_has_no_response(self):
        self.assertIsNone(self.session().handle({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 3}}))

    def test_invalid_json_duplicate_keys_and_nan(self):
        for raw in ("broken\n", '{"jsonrpc":"2.0","jsonrpc":"1.0"}\n', '{"value":NaN}\n'):
            with self.subTest(raw=raw):
                output = io.StringIO()
                serve(io.StringIO(raw), output, self.session())
                self.assertEqual(-32700, json.loads(output.getvalue())["error"]["code"])

    def test_oversized_message_closes_session(self):
        output = io.StringIO()
        serve(io.StringIO("x" * (MAX_MESSAGE_BYTES + 1) + "\n"), output, self.session())
        self.assertIn("Message too large", output.getvalue())

    def test_unicode_limit_is_bytes_not_characters(self):
        output = io.StringIO()
        serve(io.StringIO("é" * (MAX_MESSAGE_BYTES // 2 + 1) + "\n"), output, self.session())
        self.assertIn("Message too large", output.getvalue())

    def test_explicit_null_request_id_is_rejected(self):
        self.assertIn("error", self.session().handle(call() | {"id": None}))

    def test_valid_utf8_bytes_stream(self):
        output = io.StringIO()
        raw = (json.dumps(call()) + "\n").encode("utf-8")
        serve(io.BytesIO(raw), output, self.session())
        self.assertEqual("met", json.loads(output.getvalue())["result"]["structuredContent"]["check_status"])

    def test_invalid_utf8_bytes_are_parse_error(self):
        output = io.StringIO()
        serve(io.BytesIO(b'\xff\n'), output, self.session())
        self.assertEqual(-32700, json.loads(output.getvalue())["error"]["code"])

    def test_service_failure_never_returns_cached_pass(self):
        class FailedService:
            def check(self, arguments):
                raise RuntimeError("private traceback detail")
        session = self.session()
        session.service = FailedService()
        result = session.handle(call())["result"]
        self.assertTrue(result["isError"])
        self.assertNotIn("private traceback", str(result))
        self.assertNotIn("structuredContent", result)

    def test_validated_audit_chain_captures_tool_request_and_result(self):
        with tempfile.TemporaryDirectory(prefix="kg-audit-test-") as directory:
            path = Path(directory) / "audit.jsonl"
            session = self.session(path)
            for _ in range(2):
                session.handle(call())
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(2, len(events))
            self.assertEqual(BASE, events[0]["validated_arguments"]["as_received"])
            self.assertEqual("met", events[0]["response"]["result"]["structuredContent"]["check_status"])
            self.assertEqual(events[0]["event_hash"], events[1]["previous_event_hash"])
            for event in events:
                event_hash = event.pop("event_hash")
                self.assertEqual(event_hash, digest(event))

    def test_invalid_raw_input_not_written_to_audit(self):
        with tempfile.TemporaryDirectory(prefix="kg-audit-test-") as directory:
            path = Path(directory) / "audit.jsonl"
            self.session(path).handle(call(arguments={"secret": "do-not-log"}))
            self.assertFalse(path.exists())

    def test_real_stdio_subprocess_handshake_tool_call_and_eof(self):
        input_text = "\n".join(json.dumps(request) for request in (INIT, READY, call())) + "\n"
        process = subprocess.run([sys.executable, str(ROOT / "run_mcp.py")],
                                 input=input_text, text=True, capture_output=True, timeout=10,
                                 cwd=tempfile.gettempdir())
        self.assertEqual(0, process.returncode, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(2, len(responses))
        self.assertEqual("met", responses[1]["result"]["structuredContent"]["check_status"])
        self.assertEqual("", process.stderr)


if __name__ == "__main__":
    unittest.main()
