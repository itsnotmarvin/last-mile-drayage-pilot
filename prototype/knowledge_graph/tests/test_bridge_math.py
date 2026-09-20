"""Exact bridge-formula boundaries and draft source-binding controls."""
import hashlib
import json
from pathlib import Path
import unittest

from neo4j_kg.bridge_math import evaluate_axles


ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENT = ROOT / 'data/source_candidates/2026-09-13/bridge-supplement.json'
SOURCE = ROOT.parents[1] / 'data/raw/documents/state/nj_size_weight_guidebook_2024.pdf'
SOURCE_SHA256 = '5a427385dfb7ad26e4d571c1bdd44348d976e82fcfcb78121a9ddd02a415fb70'
ENTRY_FIELDS = {
    'id', 'requirement_ids', 'source_id', 'source_file_path',
    'source_file_sha256', 'locator', 'source_text', 'interpretation_boundary'}


def layout(positions, weights):
    return {'axles': [
        {'position_inches': position, 'weight_lb': weight}
        for position, weight in zip(positions, weights)]}


def by_id(result, check_id):
    return next(row for row in result['checks'] if row['id'] == check_id)


class BridgeMathTests(unittest.TestCase):
    def test_standard_five_axle_layout_checks_all_subgroups(self):
        result = evaluate_axles(
            layout([0, 144, 192, 576, 624], [12000, 17000, 17000, 17000, 17000]),
            'federal_interstate')
        self.assertEqual('met', result['status'])
        self.assertEqual([], result['reason_codes'])
        bridge_checks = [row for row in result['checks'] if row['id'].startswith('bridge_group_')]
        self.assertEqual(10, len(bridge_checks))
        self.assertEqual(68000, by_id(result, 'bridge_group_2_5')['actual'])
        self.assertEqual(68000, by_id(result, 'bridge_group_2_5')['limit'])
        self.assertIn('two consecutive tandem sets', by_id(result, 'bridge_group_2_5')['detail'])
        self.assertEqual('met', by_id(result, 'federal_gross_vehicle')['status'])

    def test_inner_subgroup_failure_is_not_hidden_by_gross_and_tandem_passes(self):
        result = evaluate_axles(
            layout([0, 120, 174, 228], [10000, 15000, 15000, 15000]),
            'federal_interstate')
        self.assertEqual('not_met', result['status'])
        self.assertEqual('met', by_id(result, 'federal_gross_vehicle')['status'])
        self.assertEqual('met', by_id(result, 'tandem_axles_2_3')['status'])
        self.assertEqual('met', by_id(result, 'tandem_axles_3_4')['status'])
        subgroup = by_id(result, 'bridge_group_2_4')
        self.assertEqual('not_met', subgroup['status'])
        self.assertEqual(45000, subgroup['actual'])
        self.assertEqual({'lower_lb': 42500, 'upper_lb': 43000}, subgroup['limit'])
        self.assertIn('BRIDGE_LIMIT_EXCEEDED', result['reason_codes'])

    def test_tandem_spacing_endpoints_are_inclusive(self):
        for spacing, weight in ((40, 16500), (96, 17000)):
            with self.subTest(spacing=spacing):
                result = evaluate_axles(
                    layout([0, spacing], [weight, weight]), 'federal_interstate')
                tandem = by_id(result, 'tandem_axles_1_2')
                self.assertEqual('met', tandem['status'])
                self.assertEqual(34000, tandem['limit'])
                self.assertEqual('met', result['status'])

    def test_tandem_limit_failure_is_reported_separately(self):
        result = evaluate_axles(
            layout([0, 48], [17001, 17000]), 'federal_interstate')
        self.assertEqual('not_met', result['status'])
        self.assertEqual('not_met', by_id(result, 'tandem_axles_1_2')['status'])
        self.assertIn('TANDEM_LIMIT_EXCEEDED', result['reason_codes'])

    def test_three_axle_cluster_within_96_inches_is_not_treated_as_two_tandems(self):
        result = evaluate_axles(
            layout([0, 40, 80], [12000, 12000, 12000]), 'federal_interstate')
        self.assertEqual('unresolved', result['status'])
        cluster = by_id(result, 'tandem_cluster_1_3')
        self.assertEqual('unresolved', cluster['status'])
        self.assertEqual(36000, cluster['actual'])
        self.assertEqual(34000, cluster['limit'])
        self.assertIn('MULTI_AXLE_TANDEM_CLASSIFICATION_UNRESOLVED',
                      result['reason_codes'])

    def test_gross_and_individual_boundaries_are_exact(self):
        at_limit = evaluate_axles(layout([0], [20000]), 'federal_interstate')
        above_limit = evaluate_axles(layout([0], [20000.01]), 'federal_interstate')
        self.assertEqual('met', at_limit['status'])
        self.assertEqual('not_met', above_limit['status'])
        self.assertEqual('not_met', by_id(above_limit, 'federal_single_axle_1')['status'])

        gross = evaluate_axles(
            layout([0, 120, 240, 360, 480], [16000, 16000, 16000, 16000, 16000.01]),
            'federal_interstate')
        self.assertEqual('not_met', by_id(gross, 'federal_gross_vehicle')['status'])
        self.assertIn('FEDERAL_GROSS_LIMIT_EXCEEDED', gross['reason_codes'])

    def test_exact_rounding_midpoint_preserves_lower_upper_uncertainty(self):
        expected = {
            42500: 'met',
            42750: 'unresolved',
            43000: 'unresolved',
            43001: 'not_met',
        }
        for total, status in expected.items():
            with self.subTest(total=total):
                result = evaluate_axles(
                    layout([0, 54, 108], [14000, 14000, total - 28000]),
                    'federal_interstate')
                check = by_id(result, 'bridge_group_1_3')
                self.assertEqual(status, check['status'])
                self.assertEqual({'lower_lb': 42500, 'upper_lb': 43000}, check['limit'])
                self.assertIn('exactly halfway', check['detail'])
                self.assertIn('does not use Table 1', check['detail'])
                self.assertEqual(status, result['status'])
        unresolved = evaluate_axles(
            layout([0, 54, 108], [14000, 14000, 14750]), 'federal_interstate')
        self.assertIn('BRIDGE_ROUNDING_TIE_UNRESOLVED', unresolved['reason_codes'])

    def test_fractional_foot_span_is_not_rounded_to_a_table_row(self):
        result = evaluate_axles(
            layout([0, 57, 114], [14000, 14000, 15000]), 'federal_interstate')
        check = by_id(result, 'bridge_group_1_3')
        self.assertEqual('met', result['status'])
        self.assertEqual(43000, check['limit'])
        self.assertIn('L=19/2 ft', check['detail'])
        self.assertIn('exact equation result 43125 lb', check['detail'])

    def test_two_tandem_exception_starts_at_36_feet(self):
        at_boundary = evaluate_axles(
            layout([0, 48, 384, 432], [17000, 17000, 17000, 17000]),
            'federal_interstate')
        exception = by_id(at_boundary, 'bridge_group_1_4')
        self.assertEqual('met', at_boundary['status'])
        self.assertEqual(68000, exception['limit'])
        self.assertIn('two consecutive tandem sets', exception['detail'])

        below_boundary = evaluate_axles(
            layout([0, 48, 383, 431], [17000, 17000, 17000, 17000]),
            'federal_interstate')
        ordinary = by_id(below_boundary, 'bridge_group_1_4')
        self.assertEqual('not_met', ordinary['status'])
        self.assertNotIn('two consecutive tandem sets', ordinary['detail'])

    def test_centers_less_than_40_inches_fail_closed(self):
        result = evaluate_axles(
            layout([0, 39], [10000, 10000]), 'federal_interstate')
        self.assertEqual('unresolved', result['status'])
        self.assertIn('CLOSE_AXLE_GROUP_UNSUPPORTED', result['reason_codes'])
        self.assertEqual('unresolved', by_id(result, 'axle_spacing_1_2')['status'])
        self.assertFalse(any(row['id'].startswith('bridge_group_') for row in result['checks']))

    def test_noninterstate_single_limit_can_fail_but_cannot_clear_group_scope(self):
        at_limit = evaluate_axles(
            layout([0, 120], [22400, 22400]), 'nj_noninterstate')
        self.assertEqual('unresolved', at_limit['status'])
        self.assertEqual('met', by_id(at_limit, 'nj_single_axle_1')['status'])
        self.assertEqual('met', by_id(at_limit, 'nj_single_axle_2')['status'])
        self.assertIn('NJ_NONINTERSTATE_GROUP_SCOPE_UNRESOLVED', at_limit['reason_codes'])

        above_limit = evaluate_axles(layout([0], [22401]), 'nj_noninterstate')
        self.assertEqual('not_met', above_limit['status'])
        self.assertEqual('not_met', by_id(above_limit, 'nj_single_axle_1')['status'])
        self.assertIn('NJ_SINGLE_AXLE_LIMIT_EXCEEDED', above_limit['reason_codes'])
        self.assertEqual('unresolved', by_id(above_limit, 'nj_noninterstate_group_limits')['status'])

    def test_unknown_regime_and_invalid_layout_return_unresolved(self):
        unknown = evaluate_axles(layout([0], [10000]), 'county_road')
        self.assertEqual('unresolved', unknown['status'])
        self.assertEqual(['ROAD_REGIME_UNSUPPORTED'], unknown['reason_codes'])
        self.assertEqual('road_regime', unknown['checks'][0]['id'])
        unhashable = evaluate_axles(layout([0], [10000]), {'kind': 'unknown'})
        self.assertEqual('unresolved', unhashable['status'])
        self.assertEqual(['ROAD_REGIME_UNSUPPORTED'], unhashable['reason_codes'])

        invalid = evaluate_axles({'axles': [{'position_inches': 1, 'weight_lb': 10000}]},
                                 'federal_interstate')
        self.assertEqual('unresolved', invalid['status'])
        self.assertEqual(['INVALID_AXLE_LAYOUT'], invalid['reason_codes'])

    def test_result_and_check_contracts_are_closed(self):
        result = evaluate_axles(layout([0], [10000]), 'federal_interstate')
        self.assertEqual({'status', 'reason_codes', 'checks'}, set(result))
        self.assertTrue(result['checks'])
        for check in result['checks']:
            self.assertEqual({'id', 'status', 'actual', 'limit', 'detail'}, set(check))
            self.assertIn(check['status'], {'met', 'not_met', 'unresolved'})


class BridgeSupplementTests(unittest.TestCase):
    def test_draft_supplement_is_bound_to_reviewed_archive_bytes(self):
        supplement = json.loads(SUPPLEMENT.read_text())
        self.assertEqual('drayage-draft-source-supplement-v1', supplement['schema_version'])
        self.assertEqual(
            'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c',
            supplement['graph_release'])
        self.assertEqual('draft_not_human_approved', supplement['approval_status'])
        self.assertIs(False, supplement['operational_use'])
        self.assertEqual(SOURCE_SHA256, hashlib.sha256(SOURCE.read_bytes()).hexdigest())

        ids = set()
        for entry in supplement['entries']:
            self.assertEqual(ENTRY_FIELDS, set(entry))
            self.assertNotIn(entry['id'], ids)
            ids.add(entry['id'])
            self.assertEqual(['axle_weight_evidence'], entry['requirement_ids'])
            self.assertEqual('nj_size_weight_guidebook', entry['source_id'])
            self.assertEqual(
                'data/raw/documents/state/nj_size_weight_guidebook_2024.pdf',
                entry['source_file_path'])
            self.assertEqual(SOURCE_SHA256, entry['source_file_sha256'])
            for field in ('id', 'locator', 'source_text', 'interpretation_boundary'):
                self.assertIsInstance(entry[field], str)
                self.assertTrue(entry[field].strip())

        self.assertIn('draft_nj_bridge_equation', ids)
        self.assertIn('draft_nj_single_axle_definition', ids)
        self.assertIn('draft_nj_tandem_limit', ids)
        self.assertIn('draft_nj_gross_limit', ids)
        self.assertIn('draft_nj_two_tandem_exception', ids)
        self.assertIn('draft_nj_bridge_interstate_scope', ids)

    def test_scope_and_rounding_limits_are_explicit(self):
        entries = {row['id']: row for row in json.loads(SUPPLEMENT.read_text())['entries']}
        scope = entries['draft_nj_bridge_interstate_scope']
        self.assertEqual(
            'These weight limitations apply on any highway in New Jersey which '
            'designated as part of the National Interstate System, as provided at '
            '23 U.S.C. 103(c).', scope['source_text'])
        self.assertIn('cannot be met', scope['interpretation_boundary'])
        equation = entries['draft_nj_bridge_equation']['interpretation_boundary']
        self.assertIn('exactly halfway', equation)
        self.assertIn('does not select a result from Table 1', equation)


if __name__ == '__main__':
    unittest.main()
