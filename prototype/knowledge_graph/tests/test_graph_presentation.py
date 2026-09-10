import copy
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from evidence_graph import EvidenceGraph
from export_graph import snapshot, render_full_graph
from graph_presentation import (PRESENTATION, category, full_graph_svg, layout,
                                readable_positions, topology_key)


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = snapshot(EvidenceGraph())

    def test_saved_layout_matches_all_current_nodes(self):
        positions, _, _, engine = layout(self.data)
        self.assertEqual('Graphviz sfdp', engine)
        self.assertEqual({n['id'] for n in self.data['nodes']}, set(positions))
        self.assertTrue((PRESENTATION / (topology_key(self.data) + '.json')).exists())
        self.assertEqual(layout(self.data), layout(self.data))

    def test_label_boxes_do_not_overlap_or_leave_canvas(self):
        positions, width, height, _, boxes = readable_positions(self.data)
        rectangles = []
        for node, (x, y) in positions.items():
            w, h = boxes[node]
            rect = (x-w/2, y-18, x+w/2, y-18+h)
            self.assertGreaterEqual(rect[0], 0)
            self.assertGreaterEqual(rect[1], 0)
            self.assertLessEqual(rect[2], width)
            self.assertLessEqual(rect[3], height)
            for other, box in rectangles:
                overlap = min(rect[2],box[2])>max(rect[0],box[0]) and min(rect[3],box[3])>max(rect[1],box[1])
                self.assertFalse(overlap, (node, other))
            rectangles.append((node,rect))

    def test_presentation_keeps_complete_labels_and_edges(self):
        original = copy.deepcopy(self.data)
        root = ET.fromstring(full_graph_svg(self.data))
        marks = {e.attrib['data-node-id']:e for e in root.iter() if 'data-node-id' in e.attrib}
        for node in self.data['nodes']:
            mark = marks[node['id']]
            self.assertEqual(node['label'], mark.attrib['aria-label'])
            self.assertEqual(category(node), mark.attrib['data-category'])
            circle = next(e for e in mark if e.attrib.get('class') == 'node-circle')
            self.assertEqual('12', circle.attrib['r'])
            for text in mark.findall('{http://www.w3.org/2000/svg}text'):
                self.assertGreater(float(text.attrib['y']),float(circle.attrib['cy'])+12)
        edge_ids = {e.attrib['data-edge-id'] for e in root.iter() if 'data-edge-id' in e.attrib}
        self.assertEqual({e['id'] for e in self.data['edges']}, edge_ids)
        self.assertEqual(original,self.data)
        aliases = json.loads((PRESENTATION/'labels.json').read_text())
        self.assertEqual(set(marks),set(aliases))
        self.assertEqual(len(aliases),len(set(aliases.values())))

    def test_labels_are_on_demand_but_remain_in_the_export(self):
        svg = full_graph_svg(self.data)
        html = render_full_graph(self.data,svg)
        self.assertIn('.edge-label.selected{visibility:visible}',svg)
        self.assertIn('data-action="labels">All relationship labels',html)
        self.assertNotIn('data-action="labels" checked',html)
        labels = [e for e in ET.fromstring(svg).iter() if 'data-edge-label' in e.attrib]
        self.assertEqual(345,len(labels))
        self.assertIn("onclick=()=>{choose('');fit();}",html)

    def test_unseen_topology_does_not_reuse_stale_coordinates(self):
        changed = copy.deepcopy(self.data)
        changed['nodes'].append({'id':'new-node'})
        positions, _, _, engine = layout(changed)
        self.assertIn('fallback',engine)
        self.assertIn('new-node',positions)

    def test_reciprocal_and_parallel_edges_have_separate_curves(self):
        data = {'nodes':[{'id':n,'label':n,'kind':'source_document','layer':'archive','record':{}} for n in ['a','b']],
                'edges':[{'id':str(i),'source':a,'target':b,'relationship':'CITES_SOURCE','record':{}} for i,(a,b) in enumerate([('a','b'),('a','b'),('b','a')])]}
        root = ET.fromstring(full_graph_svg(data))
        paths = [e.attrib['d'] for e in root.iter() if 'data-edge-id' in e.attrib]
        self.assertEqual(3,len(set(paths)))
