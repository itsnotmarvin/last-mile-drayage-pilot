"""Read-only APM terminal-status observation: parser, provenance, wiring.

Terminal operating context must never satisfy a requirement or clear a trip:
every test below holds decision outputs fixed while varying only the
observation's availability and content.
"""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import URLError

from kg.service import CheckingService as OriginalService
from neo4j_kg import terminal_status
from neo4j_kg.assessment import TripService
from neo4j_kg.mcp_server import TOOLS
from neo4j_kg.trip_state import TripStore
from test_neo4j_migration import OracleReader
from test_trip_assessment import BASE, MemoryGraph

ROWS_HTML = b"""<html><body><nav>Elizabeth</nav>
<h1>Row Closures</h1>
<p><strong>B400-B800, G050, G100, G220, GW82-GW98, RR Closed areas.</strong>
Any import within free time and affected by a row closure will be extended accordingly.</p>
</body></html>"""

GATE_HTML = b"""<html><body><nav>Elizabeth</nav>
<h1>Gate information</h1>
<h2>Live gate cameras</h2><p>Cameras will update every few minutes.</p>
<h2>Happiness Index</h2><p>During gate hours the stats below are updated every 15 minutes.</p>
<h2>Truck Turn Times</h2>
<p><strong>The graphs below show real-time data related to the amount of time trucks spend.</strong></p>
</body></html>"""

GATE_OPEN_HTML = GATE_HTML.replace(
    b"<h2>Truck Turn Times</h2>",
    b"<p>APM Terminals Elizabeth will be returning to normal gate hours, 6AM-4PM, on Mon. 7/13.</p>"
    b"<h2>Truck Turn Times</h2>")

ALERT_HTML = b"""<html><body><nav>News & Updates</nav>
<div>16 September 2026</div>
<h1>Short-Term Vessel Schedule 9/16/26</h1>
<h3>Vessels</h3>
<ul><li>Navios Constellation (TP12) - Working - ETA 9/16 @ 2300</li></ul>
<p><strong>APM Terminals Elizabeth will be closed Mon. 9/7 in observance of Labor Day.</strong></p>
</body></html>"""

PAGES = {
    terminal_status.ROW_CLOSURES_URL: ROWS_HTML,
    terminal_status.GATE_INFO_URL: GATE_HTML,
    terminal_status.STATUS_UPDATE_URL: ALERT_HTML,
}

KEYED = {"row_closures": ROWS_HTML, "gate_info": GATE_HTML, "status_update": ALERT_HTML}


def stub_get(url, timeout):
    return PAGES[url]


class TerminalStatusTests(unittest.TestCase):
    def test_parse_real_page_shapes(self):
        parsed = terminal_status.parse_pages(dict(KEYED))
        self.assertIn("Closed areas", parsed["row_closures_text"])
        self.assertIn("B400-B800", parsed["row_closures_text"])
        self.assertIsNone(parsed["row_closures_effective"])
        self.assertIsNone(parsed["gate_status_text"])
        self.assertEqual({"live_cameras": True, "turn_times": True, "happiness_index": True},
                         parsed["gate_indicators"])
        self.assertEqual("Short-Term Vessel Schedule 9/16/26", parsed["latest_notice_heading"])
        self.assertEqual("16 September 2026", parsed["latest_notice_date"])
        self.assertIn("closed Mon. 9/7", parsed["closure_notice_text"])

    def test_explicit_gate_sentence_captured_verbatim(self):
        pages = dict(KEYED, gate_info=GATE_OPEN_HTML)
        parsed = terminal_status.parse_pages(pages)
        self.assertIn("returning to normal gate hours", parsed["gate_status_text"])

    def test_changed_layout_is_unavailable_not_invented(self):
        broken = dict(PAGES, **{terminal_status.ROW_CLOSURES_URL: b"<html><body><h1>Rows</h1><p>All good.</p></body></html>"})
        result = terminal_status.fetch(get=lambda url, timeout: broken[url])
        self.assertEqual("unavailable", result["status"])
        self.assertTrue(result["unavailable_reason"].startswith("unexpected_content"))
        self.assertEqual([], result["sources"])

    def test_fetch_error_is_unavailable(self):
        def fail(url, timeout):
            raise URLError("offline")
        result = terminal_status.fetch(get=fail)
        self.assertEqual("unavailable", result["status"])
        self.assertTrue(result["unavailable_reason"].startswith("fetch_error"))
        self.assertFalse(result["operational_use"])

    def test_provenance_recorded_per_source(self):
        result = terminal_status.fetch(get=stub_get)
        self.assertEqual("available", result["status"])
        self.assertIsNone(result["unavailable_reason"])
        self.assertEqual("terminal-status-extractor-v2", result["extractor_version"])
        self.assertEqual("facility_apm_elizabeth", result["terminal_id"])
        self.assertFalse(result["operational_use"])
        self.assertEqual(3, len(result["sources"]))
        for source in result["sources"]:
            self.assertIn(source["url"], [url for _, url in terminal_status.SOURCES])
            self.assertEqual(hashlib.sha256(PAGES[source["url"]]).hexdigest(),
                             source["content_sha256"])
            self.assertEqual("terminal-status-extractor-v2", source["extractor"])
            self.assertTrue(source["retrieved_at"])
        self.assertTrue(any("row-closures" in s["url"] for s in result["sources"]))
        self.assertIn("not dispatch", " ".join(result["limits"]))

    def test_fresh_retrieval_does_not_make_old_notice_current(self):
        now = datetime(2026, 9, 19, 18, tzinfo=timezone.utc)
        result = terminal_status.current_observation(terminal_status.fetch(get=stub_get, now=now), now)
        self.assertEqual("available", result["status"])
        self.assertEqual("unknown_for_this_trip", result["currentness"])
        self.assertEqual("16 September 2026", result["latest_notice_date"])
        self.assertIn("9/7", result["closure_notice_text"])
        self.assertTrue(any("historical" in s for s in result["limits"]))

    def test_stale_future_and_previous_local_day_captures_are_unavailable(self):
        now = datetime(2026, 9, 19, 5, tzinfo=timezone.utc)
        for checked, reason in ((now - timedelta(days=1), "stale_retrieval"),
                                (now - timedelta(hours=2), "stale_retrieval"),
                                (now + timedelta(seconds=1), "future_retrieval")):
            with self.subTest(checked=checked):
                capture = terminal_status.fetch(get=stub_get, now=checked)
                result = terminal_status.current_observation(capture, now)
                self.assertEqual("unavailable", result["status"])
                self.assertEqual(reason, result["unavailable_reason"])
                self.assertIsNone(result["closure_notice_text"])
                self.assertEqual([], result["sources"])

    def test_old_individual_source_cannot_hide_behind_fresh_envelope(self):
        now = datetime(2026, 9, 19, 18, tzinfo=timezone.utc)
        capture = terminal_status.fetch(get=stub_get, now=now)
        capture["sources"][0]["retrieved_at"] = (now - timedelta(days=2)).isoformat()
        self.assertEqual("stale_retrieval", terminal_status.current_observation(capture, now)["unavailable_reason"])

    def test_latest_schedule_selected_by_explicit_date_not_document_order(self):
        pages = dict(KEYED)
        pages["status_update"] = (b"<div>1 January 2020</div><h1>Short-Term Vessel Schedule 9/10/26</h1>"
                                  b"<h2>Short-Term Vessel Schedule 9/18/26</h2>")
        result = terminal_status.parse_pages(pages)
        self.assertEqual("Short-Term Vessel Schedule 9/18/26", result["latest_notice_heading"])
        self.assertEqual("18 September 2026", result["latest_notice_date"])

    def _service(self, fetcher):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        reader = OracleReader(OriginalService())
        return TripService(MemoryGraph(reader), TripStore(Path(tmp.name) / "trips.sqlite3"),
                           terminal_status_fetcher=fetcher)

    def _assess(self, service, key):
        return service.assess({"facts": dict(BASE, route_id="path_a_exit13a_to_apm"),
                               "question_scope": "trip_dispatch", "requester_role": "driver",
                               "source_message": "Synthetic terminal-status control.",
                               "request_key": key})

    def test_open_terminal_text_cannot_clear_trip(self):
        opened = terminal_status.fetch(get=lambda url, timeout: {
            terminal_status.ROW_CLOSURES_URL: ROWS_HTML,
            terminal_status.GATE_INFO_URL: GATE_OPEN_HTML,
            terminal_status.STATUS_UPDATE_URL: ALERT_HTML}[url])
        self.assertEqual("available", opened["status"])
        result = self._assess(self._service(lambda: copy.deepcopy(opened)), "status-open")
        self.assertEqual("available", result["evidence_package"]["current_terminal_status"]["status"])
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        self.assertEqual("not_cleared", result["decision_brief"]["status"])
        self.assertEqual("not_issued", result["decision_brief"]["operational_permission"])
        for finding in result["findings"]:
            expected = "met" if finding["requirement_id"] == "apm_induction" else "unresolved"
            self.assertEqual(expected, finding["status"], finding["requirement_id"])

    def test_unavailable_status_keeps_assessment_intact(self):
        def fail():
            raise URLError("offline")
        result = self._assess(self._service(fail), "status-down")
        current = result["evidence_package"]["current_terminal_status"]
        self.assertEqual("unavailable", current["status"])
        self.assertEqual("unresolved", result["requested_scope_status"])
        self.assertEqual("unresolved_not_assessed", result["operational_status"])
        import jsonschema
        tools = {t["name"]: t for t in TOOLS}
        jsonschema.validate(result, tools["assess_trip"]["outputSchema"])

    def test_available_status_validates_and_matches_unavailable_decisions(self):
        live = terminal_status.fetch(get=stub_get)
        with_status = self._assess(self._service(lambda: copy.deepcopy(live)), "status-on")
        without_status = self._assess(self._service(lambda: None), "status-off")
        for key in ("requested_scope_status", "operational_status"):
            self.assertEqual(without_status[key], with_status[key])
        self.assertEqual([(f["requirement_id"], f["status"]) for f in without_status["findings"]],
                         [(f["requirement_id"], f["status"]) for f in with_status["findings"]])
        self.assertEqual("not_cleared", with_status["decision_brief"]["status"])
        self.assertEqual("available", with_status["evidence_package"]["current_terminal_status"]["status"])
        self.assertIsNone(without_status["evidence_package"]["current_terminal_status"])
        import jsonschema
        tools = {t["name"]: t for t in TOOLS}
        jsonschema.validate(with_status, tools["assess_trip"]["outputSchema"])

    def test_default_skips_network_without_env_flag(self):
        self.assertNotEqual("1", os.environ.get("DRAYAGE_TERMINAL_STATUS_LIVE"))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        reader = OracleReader(OriginalService())
        service = TripService(MemoryGraph(reader), TripStore(Path(tmp.name) / "trips.sqlite3"))
        result = service.assess({"facts": dict(BASE), "question_scope": "trip_dispatch",
                                 "requester_role": "driver",
                                 "source_message": "Synthetic default-offline control.",
                                 "request_key": "status-default"})
        current = result["evidence_package"]["current_terminal_status"]
        self.assertEqual("unavailable", current["status"])
        self.assertEqual("live_fetch_disabled", current["unavailable_reason"])
        self.assertEqual("unresolved", result["requested_scope_status"])


if __name__ == "__main__":
    unittest.main()
