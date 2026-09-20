"""Tracing must report actual reads without confusing them with supplied passages."""
import unittest
from neo4j_kg.retrieval_trace import TracedTransaction, begin, finish, phase, receipt


class Transaction:
    def run(self, query, **params):
        if query=='fail':
            raise RuntimeError('secret connection detail')
        return [{'node': {'id': 'rule-a'}, 'id':'source-a'}]


class RetrievalTraceTests(unittest.TestCase):
    def test_validation_reads_and_supplied_evidence_are_distinct(self):
        token=begin(True)
        try:
            tx=TracedTransaction(Transaction())
            with phase('release_validation'):
                tx.run('MATCH (n) RETURN n', revision='pinned')
            tx.run('MATCH (n {id:$id}) RETURN n', id='rule-a')
            r=receipt({'sources':[{'clause_id':'rule-a','source_text':'exact passage'}],
                       'findings':[{'source_clause_ids':['not-delivered'],'evidence_ids':['syn-evidence']} ]})
            self.assertEqual(['release_validation','assessment_retrieval'],[q['phase'] for q in r['queries']])
            self.assertEqual(['rule-a'],r['delivered_passage_clause_ids'])
            self.assertEqual(['syn-evidence'],r['reported_evidence_ids'])
            self.assertEqual(['rule-a','source-a'],r['queries'][1]['record_ids'])
        finally: finish(token)

    def test_disabled_tracing_preserves_query_result(self):
        token=begin(False)
        try:
            self.assertEqual(Transaction().run('q'),TracedTransaction(Transaction()).run('q'))
            self.assertEqual([],receipt({})['queries'])
        finally: finish(token)

    def test_requests_do_not_leak_previous_trace(self):
        token=begin(True)
        TracedTransaction(Transaction()).run('q')
        finish(token)
        token=begin(True)
        try:self.assertEqual([],receipt({})['queries'])
        finally:finish(token)

    def test_failed_query_records_type_without_exception_secret(self):
        token=begin(True)
        try:
            with self.assertRaises(RuntimeError):TracedTransaction(Transaction()).run('fail')
            r=receipt({})
            self.assertEqual('error',r['queries'][0]['status'])
            self.assertNotIn('secret',str(r))
        finally:finish(token)
