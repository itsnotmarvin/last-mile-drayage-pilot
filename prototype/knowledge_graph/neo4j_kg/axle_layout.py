"""Explicit individual-axle reports and measurement reconciliation, not legal limits."""
from decimal import Decimal

from .service import InputError

MAX_AXLES = 32
VERSION = 'individual-axle-layout-v1'


def _object(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def _quantity(units):
    return _object({'value': {'type': 'number', 'minimum': 0},
                    'unit': {'enum': units}})


INPUT_SCHEMA = _object({'axles': {
    'type': 'array', 'minItems': 1, 'maxItems': MAX_AXLES,
    'items': _object({'position': _quantity(['in', 'ft']),
                      'weight': _quantity(['lb', 'kg'])})}})
INPUT_SCHEMA['description'] = (
    'One row per individual axle in front-to-back order. Position is the distance '
    'from the first axle, whose position is zero; subsequent positions strictly '
    'increase. Never put a tandem/group weight into an individual-axle row. '
    'Use null when individual measurements are unknown.')
NORMALIZED_SCHEMA = _object({'axles': {
    'type': 'array', 'minItems': 1, 'maxItems': MAX_AXLES,
    'items': _object({'position_inches': {'type': 'number', 'minimum': 0},
                      'weight_lb': {'type': 'number', 'exclusiveMinimum': 0}})}})
REVIEW_SCHEMA = _object({
    'schema_version': {'const': VERSION},
    'status': {'enum': ['not_supplied', 'reported_only', 'input_review_required']},
    'axle_count': {'type': ['integer', 'null']},
    'total_weight_lb': {'type': ['number', 'null']},
    'span_inches': {'type': ['number', 'null']},
    'gross_difference_lb': {'type': ['number', 'null']},
    'issues': {'type': 'array', 'items': _object({
        'field': {'type': 'string'}, 'code': {'type': 'string'}, 'message': {'type': 'string'}})},
    'operational_permission': {'const': 'not_issued'},
    'limits': {'type': 'array', 'items': {'type': 'string'}}})


def normalize_layout(value, normalize_quantity):
    if (not isinstance(value, dict) or set(value) != {'axles'}
            or not isinstance(value['axles'], list)
            or not 1 <= len(value['axles']) <= MAX_AXLES):
        raise InputError('axle_layout needs 1 to 32 individual axle rows')
    rows = []
    for row in value['axles']:
        if not isinstance(row, dict) or set(row) != {'position', 'weight'}:
            raise InputError('Each individual axle needs position and weight quantities')
        position, _ = normalize_quantity(row['position'], 'axle_layout position', weight=False)
        weight, _ = normalize_quantity(row['weight'], 'axle_layout weight', weight=True)
        if weight <= 0:
            raise InputError('Individual axle weights must be positive')
        if (not rows and position != 0) or (rows and position <= rows[-1]['position_inches']):
            raise InputError('Axle positions must start at zero and strictly increase from front to back')
        rows.append({'position_inches': position, 'weight_lb': weight})
    return {'axles': rows}, None


def _decimal(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Invalid measurement')
    number = Decimal(str(value))
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise ValueError('Invalid measurement')
    return number


def _number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def review_layout(facts, conflicts=()):
    result = {'schema_version': VERSION, 'status': 'not_supplied', 'axle_count': None,
              'total_weight_lb': None, 'span_inches': None, 'gross_difference_lb': None,
              'issues': [], 'operational_permission': 'not_issued', 'limits': [
                  'Individual axle positions and weights are reports, not scale verification.',
                  'Legacy axle arrays may contain groups and are never converted into individual axles.',
                  'Totals and spans do not execute bridge rules or establish road, vehicle or permit eligibility.',
                  'No measurement tolerance or legal exception is assumed when reports disagree.']}
    layout = facts.get('axle_layout', {}).get('value')
    if layout is None:
        return result

    def issue(field, code, message):
        result['issues'].append({'field': field, 'code': code, 'message': message})
        result['status'] = 'input_review_required'

    relevant = {'axle_layout', 'vehicle_id', 'trailer_id'}
    if any(c['field'] in relevant for c in conflicts):
        issue('axle_layout', 'AXLE_ASSIGNMENT_CONFLICT',
              'Resolve the individual axle layout or vehicle/trailer assignment conflict before using its measurements.')
        return result
    try:
        from .trip_models import MAX_WEIGHT_LB, MAX_DIMENSION_INCH
        if facts['axle_layout'].get('unit') is not None:
            raise ValueError('Invalid normalized layout unit')
        if not isinstance(layout, dict) or set(layout) != {'axles'}:
            raise ValueError('Invalid layout')
        rows = layout['axles']
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_AXLES:
            raise ValueError('Invalid axle rows')
        positions, weights = [], []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'position_inches', 'weight_lb'}:
                raise ValueError('Invalid normalized axle')
            positions.append(_decimal(row['position_inches']))
            weights.append(_decimal(row['weight_lb'], positive=True))
            if positions[-1] > MAX_DIMENSION_INCH or weights[-1] > MAX_WEIGHT_LB:
                raise ValueError('Out-of-range normalized measurement')
        if positions[0] != 0 or any(a >= b for a, b in zip(positions, positions[1:])):
            raise ValueError('Invalid ordering')
    except (TypeError, ValueError, KeyError):
        issue('axle_layout', 'INVALID_AXLE_LAYOUT',
              'Confirm individual axle weights and ordered positions measured from the first axle; group totals cannot substitute.')
        return result
    total = sum(weights, Decimal(0))
    result.update(status='reported_only', axle_count=len(rows),
                  total_weight_lb=_number(total), span_inches=_number(positions[-1]))
    disputed = {c['field'] for c in conflicts} & {'axle_count', 'gross_weight'}
    for field in sorted(disputed):
        issue(field, 'AXLE_RECONCILIATION_FACT_CONFLICT',
              'Resolve the conflicting ' + field.replace('_', ' ') + ' reports before reconciling the individual axle layout.')
    count = facts.get('axle_count', {}).get('value')
    if 'axle_count' not in disputed and count is not None and (type(count) is not int or count != len(rows)):
        message = 'The reported axle count differs from the individual layout. Confirm which report is correct.'
        for field in ('axle_layout', 'axle_count'):
            issue(field, 'AXLE_COUNT_MISMATCH', message)
    gross = facts.get('gross_weight', {})
    if 'gross_weight' not in disputed and gross.get('value') is not None:
        try:
            if gross.get('unit') != 'lb':
                raise ValueError('Invalid gross unit')
            difference = total - _decimal(gross['value'], positive=True)
            result['gross_difference_lb'] = _number(difference)
            if difference:
                message = ('The individual axle weights do not sum to the reported gross weight. '
                           'Reconcile the measurements and their timing; no tolerance or corrected value is inferred.')
                for field in ('axle_layout', 'gross_weight'):
                    issue(field, 'AXLE_GROSS_MISMATCH', message)
        except (TypeError, ValueError):
            issue('gross_weight', 'INVALID_GROSS_FOR_AXLE_REVIEW',
                  'A positive normalized gross weight is needed to compare it with the individual axle total.')
    return result
