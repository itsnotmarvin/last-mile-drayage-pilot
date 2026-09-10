import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import networkx as nx

from evidence_graph import EvidenceGraph
from export_graph import export, snapshot, render_full_graph
from graph_presentation import full_graph_svg, label_lines, label_width, PRESENTATION
from organize_graph import connected_view, topic_layout, EXCLUDED_SOURCE


class OrganizedGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=snapshot(EvidenceGraph())
        cls.view=connected_view(cls.archive)

    def test_only_unlinked_map_removed_and_source_archive_preserved(self):
        self.assertEqual(122,len(self.archive['nodes']))
        self.assertEqual(121,len(self.view['nodes']))
        self.assertEqual({n['id'] for n in self.archive['nodes']}-{EXCLUDED_SOURCE},{n['id'] for n in self.view['nodes']})
        self.assertEqual(self.archive['edges'],self.view['edges'])
        for node in self.view['nodes']:
            self.assertEqual(node,next(n for n in self.archive['nodes'] if n['id']==node['id']))
        g=nx.Graph();g.add_nodes_from(n['id'] for n in self.view['nodes']);g.add_edges_from((e['source'],e['target']) for e in self.view['edges'])
        self.assertTrue(nx.is_connected(g))
        self.assertEqual(0,self.view['summary']['isolated_node_count'])

    def test_map_is_not_silently_removed_if_it_gains_a_link(self):
        changed=copy.deepcopy(self.archive)
        changed['edges'].append({'source':EXCLUDED_SOURCE,'target':'facility_apm_elizabeth'})
        with self.assertRaisesRegex(ValueError,'now has relationships'):
            connected_view(changed)

    def test_topics_partition_graph_without_becoming_nodes(self):
        topics=self.view['presentation']['topics']
        members=[n for t in topics for n in t['nodes']]
        self.assertEqual(121,len(members));self.assertEqual(121,len(set(members)))
        self.assertEqual({n['id'] for n in self.view['nodes']},set(members))
        self.assertEqual(['vehicle','roads','terminal','permits','road_rules','traffic'],[t['id'] for t in topics])
        root=ET.fromstring(full_graph_svg(self.view))
        self.assertEqual(121,sum('data-node-id' in e.attrib for e in root.iter()))
        self.assertEqual(345,sum('data-edge-id' in e.attrib for e in root.iter()))
        self.assertEqual(6,sum('data-topic-id' in e.attrib for e in root.iter()))
        self.assertFalse(any('data-type-source' in e.attrib for e in root.iter()))

    def test_topic_labels_fit_and_do_not_overlap(self):
        saved=topic_layout(self.view);aliases=json.loads((PRESENTATION/'labels.json').read_text())
        rects=[]
        for node in self.view['nodes']:
            x,y=saved['positions'][node['id']]
            lines=label_lines(node,aliases)
            if node['layer']=='quarantined_observation':lines+=['Dated · quarantined']
            width=max([46]+[label_width(s) for s in lines]);height=47+len(lines)*16
            rect=(x-width/2,y-18,x+width/2,y-18+height)
            self.assertGreaterEqual(rect[0],0);self.assertGreaterEqual(rect[1],0)
            self.assertLessEqual(rect[2],saved['width']);self.assertLessEqual(rect[3],saved['height'])
            region=next(r for r in saved['regions'] if node['id'] in r['nodes'])
            self.assertGreater(rect[1],region['y']+92)
            for other,box in rects:
                overlap=min(rect[2],box[2])>max(rect[0],box[0]) and min(rect[3],box[3])>max(rect[1],box[1])
                self.assertFalse(overlap,(node['id'],other))
            rects.append((node['id'],rect))

    def test_changed_topics_reject_stale_authored_layout(self):
        changed=copy.deepcopy(self.view);changed['presentation']['topics'][0]['nodes'].pop()
        with self.assertRaisesRegex(ValueError,'topic arrangement'):
            topic_layout(changed)

    def test_export_view_archive_and_inventory_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary=export(tmp);out=Path(tmp)
            view=json.loads((out/'graph.json').read_text());archive=json.loads((out/'graph-archive.json').read_text())
            self.assertEqual(121,summary['node_count']);self.assertEqual(345,summary['edge_count'])
            self.assertEqual(121,len(view['nodes']));self.assertEqual(122,len(archive['nodes']))
            self.assertIn(EXCLUDED_SOURCE,(out/'source-inventory.html').read_text())
            self.assertNotIn(EXCLUDED_SOURCE,(out/'entire-graph.svg').read_text())
            self.assertEqual((out/'index.html').read_text(),(out/'organized-graph.html').read_text())

    def test_explanations_and_incident_relationship_navigation(self):
        html=render_full_graph(self.view,full_graph_svg(self.view))
        self.assertIn('Connected drayage graph',html)
        self.assertIn('121 nodes · 345 directed relationships · 0 unconnected',html)
        self.assertIn('function focusTopic(topic)',html)
        self.assertIn("GATE_OF_TERMINAL:'is a gate of'",html)
        self.assertIn("OBSERVED_IN_SOURCE:'was observed in archived source'",html)
        self.assertIn('button.onclick=()=>choose(other,true)',html)
