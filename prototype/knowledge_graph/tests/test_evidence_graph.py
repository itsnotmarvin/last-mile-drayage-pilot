import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import networkx as nx

from evidence_graph import EvidenceGraph, TRAFFIC_INPUT
from export_graph import snapshot, full_graph_svg, render_full_graph
from kg.graph import KnowledgeGraph


def resolve(document, pointer):
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        document = document[int(part)] if isinstance(document, list) else document[part]
    return document


class EvidenceGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = KnowledgeGraph()
        cls.kg = EvidenceGraph()

    def test_archive_records_and_original_edges_unchanged(self):
        for node, attrs in self.base.graph.nodes(data=True):
            self.assertEqual(attrs, self.kg.graph.nodes[node])
        for a, b, key, attrs in self.base.graph.edges(keys=True, data=True):
            self.assertEqual(attrs, self.kg.graph[a][b][key])
        self.assertEqual(34, len(list(nx.isolates(self.base.graph))))
        self.assertTrue(nx.is_frozen(self.kg.graph))

    def test_every_added_edge_has_exact_resolvable_evidence(self):
        for a, b, key, attrs in self.kg.graph.edges(keys=True, data=True):
            if not key.startswith('reference:'):
                continue
            self.assertFalse(attrs['record']['operational_use'])
            for evidence in attrs['record']['evidence']:
                value = resolve(self.kg.documents[evidence['input']], evidence['pointer'])
                self.assertEqual(b, value)
                self.assertEqual(value, evidence['value'])
                if attrs['relationship'] != 'OBSERVED_IN_SOURCE':
                    relative, pointer = self.kg.origins[a]
                    self.assertEqual(relative, evidence['input'])
                    self.assertTrue(evidence['pointer'].startswith(pointer + '/'))
        self.assertFalse(self.kg.unresolved_references)

    def test_quarantine_can_only_link_to_its_archived_source(self):
        for node, attrs in self.kg.graph.nodes(data=True):
            if attrs['layer'] != 'quarantined_observation':
                continue
            self.assertEqual(0, self.base.graph.degree(node))
            edges = self.kg.related(node)
            self.assertEqual(1, len(edges))
            self.assertEqual(0, self.kg.graph.in_degree(node))
            self.assertEqual('OBSERVED_IN_SOURCE', edges[0]['relationship'])
            self.assertEqual(attrs['record']['archive_context']['source_id'], edges[0]['to'])
            self.assertEqual('prohibited', attrs['record']['archive_context']['coupling_eligibility'])

    def test_supported_connections_and_honest_remaining_gap(self):
        self.assertEqual(['facility_apm_elizabeth'], [e['to'] for e in self.kg.related('node_apm_inbound_gate', 'GATE_OF_TERMINAL')])
        self.assertEqual({'reg_panynj_dtr', 'reg_panynj_dtr_engine'}, {e['to'] for e in self.kg.related('representative_older_engine_drayage', 'HAS_RECORDED_RULE_INTERACTION')})
        self.assertEqual(4, len(self.kg.related('representative_osow_ocean_container', 'HAS_RECORDED_RULE_INTERACTION')))
        audit = self.kg.audit()
        self.assertEqual(34, audit['before_isolated_count'])
        self.assertEqual(33, sum(r['connected'] for r in audit['records']))
        self.assertEqual(['panynj_facilities_map_2020'], audit['isolated_nodes'])
        self.assertEqual([121, 1], audit['weak_component_sizes'])
        self.assertFalse(any(a['relationship'] == 'TYPE_OF' for _, _, a in self.kg.graph.edges(data=True)))

    def test_historical_analysis_preserves_limits_and_inputs(self):
        record = self.kg.record('historical_north_avenue_traffic_analysis')
        self.assertEqual(self.kg.documents[TRAFFIC_INPUT], record)
        self.assertEqual('not_supported', record['decision']['path_ranking'])
        self.assertEqual(6, len(self.kg.related('historical_north_avenue_traffic_analysis', 'CITES_SOURCE')))
        self.assertIn(TRAFFIC_INPUT, self.kg.input_hashes)
        self.assertEqual(self.base.evidence_version, self.kg.base_evidence_version)
        self.assertNotEqual(self.base.evidence_version, self.kg.evidence_version)
        self.assertEqual(self.kg.evidence_version, EvidenceGraph().evidence_version)

    def test_no_name_matching_and_dangling_reference_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)
            for relative, document in self.base.documents.items():
                document = copy.deepcopy(document)
                if relative.endswith('entity_nodes.json'):
                    document['entities'][0]['source_ids'] = ['unknown_source']
                    document['entities'][0]['name'] = 'panynj_facilities_map_2020'
                path = archive / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(document))
            (archive / TRAFFIC_INPUT).write_text(json.dumps(self.kg.documents[TRAFFIC_INPUT]))
            changed = EvidenceGraph(archive)
            self.assertEqual('unknown_source', changed.unresolved_references[0]['target'])
            self.assertEqual(0, changed.graph.degree('panynj_facilities_map_2020'))

    def test_enriched_diagram_and_counts_match_actual_graph(self):
        data = snapshot(self.kg)
        svg = full_graph_svg(data)
        root = ET.fromstring(svg)
        self.assertEqual(set(self.kg.graph), {e.attrib['data-node-id'] for e in root.iter() if 'data-node-id' in e.attrib})
        self.assertEqual(self.kg.graph.number_of_edges(), sum('data-edge-id' in e.attrib for e in root.iter()))
        html = render_full_graph(data, svg)
        self.assertIn('122 nodes · 345 directed relationships · 1 unconnected', html)
        self.assertNotIn('__NODE_COUNT__', html)
        self.assertIn('Every relationship (345)', html)
