import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import networkx as nx

from export_graph import export, full_graph_svg, render_html, snapshot
from kg.graph import KnowledgeGraph


class ExportTests(unittest.TestCase):
    def test_snapshot_is_lossless_and_keeps_observations_isolated(self):
        kg = KnowledgeGraph()
        data = snapshot(kg)
        self.assertEqual(set(kg.graph), {n['id'] for n in data['nodes']})
        for node in data['nodes']:
            self.assertEqual(kg.record(node['id']), node['record'])
            if node['kind'] == 'mutable_observation':
                self.assertEqual('quarantined_observation', node['layer'])
                self.assertFalse(any(node['id'] in (e['source'], e['target']) for e in data['edges']))
        expected = {(s, t, k) for s, t, k in kg.graph.edges(keys=True)}
        self.assertEqual(expected, {(e['source'], e['target'], e['id']) for e in data['edges']})
        for edge in data['edges']:
            original = kg.graph[edge['source']][edge['target']][edge['id']]
            self.assertEqual(original['record'], edge['record'])
            self.assertEqual(original['relationship'], edge['relationship'])

    def test_export_round_trip_preserves_all_records_and_parallel_edges(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = export(folder)
            path = Path(folder)
            data = json.loads((path / 'graph.json').read_text())
            graph = nx.read_graphml(path / 'graph.graphml', force_multigraph=True)
            self.assertEqual(summary['node_count'], graph.number_of_nodes())
            self.assertEqual(summary['edge_count'], graph.number_of_edges())
            for node in data['nodes']:
                self.assertEqual(node['record'], json.loads(graph.nodes[node['id']]['record_json']))
            for edge in data['edges']:
                attrs = graph[edge['source']][edge['target']][edge['id']]
                self.assertEqual(edge['record'], json.loads(attrs['record_json']))
                self.assertEqual(edge['relationship'], attrs['relationship'])
            html = (path / 'explorer.html').read_text()
            embedded = html.split('<script id="graph-data" type="application/json">', 1)[1].split('</script>', 1)[0]
            self.assertEqual(data, json.loads(embedded))

    def test_entire_graph_svg_contains_every_node_and_edge(self):
        data = snapshot(KnowledgeGraph())
        root = ET.fromstring(full_graph_svg(data))
        nodes = [e for e in root.iter() if 'data-node-id' in e.attrib]
        edges = [e for e in root.iter() if 'data-edge-id' in e.attrib]
        self.assertEqual({n['id'] for n in data['nodes']}, {e.attrib['data-node-id'] for e in nodes})
        self.assertEqual({e['id'] for e in data['edges']}, {e.attrib['data-edge-id'] for e in edges})
        self.assertEqual(len(data['nodes']), len(nodes))
        self.assertEqual(len(data['edges']), len(edges))
        labels = {e.attrib['data-node-id']: e.attrib['aria-label'] for e in nodes}
        self.assertEqual({n['id']: n['label'] for n in data['nodes']}, labels)
        for node in nodes:
            self.assertIsNotNone(node.find('{http://www.w3.org/2000/svg}circle'))
        relationship_labels = {e.attrib['data-edge-label']: e.text for e in root.iter()
                               if 'data-edge-label' in e.attrib}
        self.assertEqual({e['id']: e['relationship'] for e in data['edges']}, relationship_labels)
        self.assertFalse(any('data-type-source' in e.attrib for e in root.iter()))

    def test_source_text_cannot_escape_json_script(self):
        hostile = {'source_text': '</script><script>alert("evidence")</script>&'}
        html = render_html(hostile)
        embedded = html.split('<script id="graph-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('<', embedded)
        self.assertEqual(hostile, json.loads(embedded))

    def test_snapshot_returns_independent_records(self):
        kg = KnowledgeGraph()
        data = snapshot(kg)
        data['nodes'][0]['record']['changed'] = True
        self.assertNotIn('changed', kg.record(data['nodes'][0]['id']))


if __name__ == '__main__':
    unittest.main()
