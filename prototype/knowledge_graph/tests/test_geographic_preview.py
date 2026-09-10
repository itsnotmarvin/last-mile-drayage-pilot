import copy
import json
import unittest

from tools.author_geographic_preview import REPO, build_segments, clip_at_gate


class GeographicPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roads = json.loads((REPO/'data/raw/gis/official/njogis_apm_study_area_roads_2026_07_26.geojson').read_text())
        cls.edges = json.loads((REPO/'data/processed/physical_edges.json').read_text())
        cls.nodes = json.loads((REPO/'data/processed/physical_nodes.geojson').read_text())

    def test_archived_geometry_preserves_endpoints_and_partial_gate_segment(self):
        result = build_segments(self.roads, self.edges, self.nodes)
        self.assertEqual(9, len(result))
        for segment in result:
            reference = segment['properties']['geometry_reference']
            self.assertEqual(reference['start_coordinate'], segment['geometry']['coordinates'][0])
            if segment['properties']['edge_id'] != 'edge_shared_tripoli_gate':
                self.assertEqual(reference['end_coordinate'], segment['geometry']['coordinates'][-1])
        gate = result[-1]
        self.assertAlmostEqual(.17, gate['properties']['gate_centerline_offset_metres'], places=2)
        # Stop at the projected gate, not the far end of the full GIS feature.
        self.assertGreater(gate['geometry']['coordinates'][-1][0], -74.159)
        self.assertLess(gate['geometry']['coordinates'][-1][0], -74.158)

    def test_disconnected_feature_order_is_rejected(self):
        edges = copy.deepcopy(self.edges)
        edges['edges'][0]['official_feature_ids'].reverse()
        with self.assertRaisesRegex(ValueError, 'Disconnected GIS feature'):
            build_segments(self.roads, edges, self.nodes)

    def test_wrong_way_traversal_is_rejected(self):
        roads = copy.deepcopy(self.roads)
        feature = next(f for f in roads['features'] if f['properties']['OBJECTID'] == 40708)
        feature['properties']['ONEWAY'] = 'TF'
        with self.assertRaisesRegex(ValueError, 'one-way direction conflict'):
            build_segments(roads, self.edges, self.nodes)

    def test_gate_far_from_centerline_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'more than one metre'):
            clip_at_gate([[-74.16, 40.67], [-74.15, 40.67]], [-74.155, 40.68])


if __name__ == '__main__':
    unittest.main()
