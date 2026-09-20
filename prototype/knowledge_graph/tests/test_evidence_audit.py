"""Audit scoring and MCP receipts must not turn missing evidence into a pass."""
import json
from pathlib import Path
import tempfile
import unittest

from neo4j_kg.common import digest
from neo4j_kg.mcp_server import Session
from neo4j_kg.retrieval_trace import TracedTransaction, receipt
from tools.audit_evidence_delivery import coverage


class EvidenceCoverageTests(unittest.TestCase):
    def test_extra_or_duplicate_passages_cannot_replace_missing_evidence(self):
        result = coverage(['needed-a', 'needed-b'], ['needed-a', 'needed-a', 'irrelevant'])
        self.assertEqual(['needed-b'], result['missing'])
        self.assertEqual(0.5, result['required_evidence_recall'])
        self.assertEqual(['irrelevant'], result['extra_clause_ids_not_automatically_errors'])

    def test_focus_omission_is_distinct_from_catalog_unavailability(self):
        self.assertEqual(['rfid'], coverage(['rfid'], ['appointment'])['missing'])
        self.assertEqual([], coverage(['rfid'], ['appointment', 'rfid'])['missing'])

    def test_empty_expectations_do_not_claim_perfect_recall(self):
        self.assertIsNone(coverage([], ['some-clause'])['required_evidence_recall'])


class TraceService:
    def run(self, query, **parameters):
        if query == 'fail':
            raise RuntimeError('secret connection detail')
        return [{'id': 'clause-a'}]

    def context(self, topic):
        if topic != 'empty':
            TracedTransaction(self).run(topic)
        return {'sources': [] if topic == 'empty' else [
            {'clause_id': 'clause-a', 'source_text': 'Retained passage'}]}


class SessionReceiptTests(unittest.TestCase):
    def call(self, session, request_id, arguments):
        return session.handle({'jsonrpc': '2.0', 'id': request_id, 'method': 'tools/call',
                               'params': {'name': 'get_drayage_graph_context',
                                          'arguments': arguments}})

    def test_failed_request_is_receipted_and_next_request_is_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audit.jsonl'
            session = Session(service=TraceService(), audit_path=path)
            session.state = 'ready'
            plain = Session(service=TraceService())
            plain.state = 'ready'
            self.assertEqual(self.call(plain, 1, {'topic': 'ok'}),
                             self.call(session, 1, {'topic': 'ok'}))
            failed = self.call(session, 2, {'topic': 'fail'})
            self.assertTrue(failed['result']['isError'])
            self.call(session, 3, {'topic': 'empty'})
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(['clause-a'], events[0]['retrieval_trace']['delivered_passage_clause_ids'])
            self.assertEqual('error', events[1]['retrieval_trace']['queries'][0]['status'])
            self.assertEqual([], events[2]['retrieval_trace']['queries'])
            self.assertEqual([], receipt({})['queries'])
            self.assertNotIn('secret connection detail', path.read_text() + str(failed))
            previous = None
            for event in events:
                self.assertEqual(previous, event['previous_event_hash'])
                self.assertEqual(digest({k: v for k, v in event.items() if k != 'event_hash'}),
                                 event['event_hash'])
                previous = event['event_hash']

    def test_rejected_input_is_not_copied_into_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audit.jsonl'
            session = Session(service=TraceService(), audit_path=path)
            session.state = 'ready'
            failed = self.call(session, 1, {'unexpected': 'secret rejected input'})
            self.assertTrue(failed['result']['isError'])
            event = json.loads(path.read_text())
            self.assertEqual({'rejected_input_omitted': True}, event['validated_arguments'])
            self.assertNotIn('secret rejected input', path.read_text() + str(failed))
