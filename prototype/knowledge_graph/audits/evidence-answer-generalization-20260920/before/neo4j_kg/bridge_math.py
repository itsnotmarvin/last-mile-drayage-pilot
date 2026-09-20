"""Bounded axle and bridge-formula comparisons for reviewed layouts.

The caller supplies measurements already normalized to ``axle_layout.NORMALIZED_SCHEMA``
and establishes route, receipt, ordinary-vehicle and no-exception premises.  This
module still fails closed for malformed layouts, unknown regimes and axle centers
less than 40 inches apart.

Bridge limits use exact rational arithmetic.  The reviewed guide says to round W
to the nearest 500 pounds but does not state a tie rule.  At an exact midpoint the
lower value is enough to pass, a value above the upper value fails, and the band
between them stays unresolved.  Table 1 is deliberately not a lookup source here.
"""
from fractions import Fraction
import math

from .axle_layout import MAX_AXLES


REGIMES = {'federal_interstate', 'nj_noninterstate'}
FEDERAL_SINGLE_AXLE_LIMIT_LB = 20_000
NJ_SINGLE_AXLE_LIMIT_LB = 22_400
TANDEM_LIMIT_LB = 34_000
GROSS_LIMIT_LB = 80_000
TWO_TANDEM_LIMIT_LB = 68_000
TANDEM_MIN_INCHES = 40
TANDEM_MAX_INCHES = 96
TWO_TANDEM_MIN_SPAN_INCHES = 36 * 12


def _fraction(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('measurement is not a JSON number')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('measurement is not finite')
    return Fraction(str(value))


def _number(value):
    return value.numerator if value.denominator == 1 else float(value)


def _fraction_text(value):
    if value.denominator == 1:
        return str(value.numerator)
    return f'{value.numerator}/{value.denominator}'


def _layout_rows(layout):
    if not isinstance(layout, dict) or set(layout) != {'axles'}:
        raise ValueError('layout must contain only axles')
    supplied = layout['axles']
    if not isinstance(supplied, list) or not 1 <= len(supplied) <= MAX_AXLES:
        raise ValueError('layout needs 1 to 32 axle rows')
    rows = []
    for supplied_row in supplied:
        if (not isinstance(supplied_row, dict)
                or set(supplied_row) != {'position_inches', 'weight_lb'}):
            raise ValueError('each axle needs only position_inches and weight_lb')
        position = _fraction(supplied_row['position_inches'])
        weight = _fraction(supplied_row['weight_lb'])
        if position < 0 or weight <= 0:
            raise ValueError('positions must be nonnegative and weights positive')
        if (not rows and position != 0) or (rows and position <= rows[-1][0]):
            raise ValueError('positions must start at zero and strictly increase')
        rows.append((position, weight))
    return rows


def _check(check_id, status, actual, limit, detail):
    return {'id': check_id, 'status': status, 'actual': actual,
            'limit': limit, 'detail': detail}


def _comparison(check_id, actual, limit, detail, failure_reason, checks, reasons):
    status = 'met' if actual <= limit else 'not_met'
    checks.append(_check(check_id, status, _number(actual), _number(limit), detail))
    if status == 'not_met':
        reasons.append(failure_reason)


def _finish(checks, reasons):
    statuses = {row['status'] for row in checks}
    status = ('not_met' if 'not_met' in statuses else
              'unresolved' if 'unresolved' in statuses else 'met')
    return {'status': status, 'reason_codes': list(dict.fromkeys(reasons)),
            'checks': checks}


def _is_tandem_gap(gap):
    return Fraction(TANDEM_MIN_INCHES) <= gap <= TANDEM_MAX_INCHES


def _is_two_tandem_exception(positions, start, end):
    return (end - start == 3
            and _is_tandem_gap(positions[start + 1] - positions[start])
            and _is_tandem_gap(positions[end] - positions[end - 1])
            and positions[end] - positions[start] >= TWO_TANDEM_MIN_SPAN_INCHES)


def _rounded_bridge_limit(raw_limit):
    """Return (lower, upper) where different values mean an exact midpoint."""
    lower_multiple = raw_limit // 500
    lower = Fraction(lower_multiple * 500)
    remainder = raw_limit - lower
    if remainder * 2 < 500:
        return lower, lower
    upper = lower + 500
    if remainder * 2 > 500:
        return upper, upper
    return lower, upper


def _bridge_check(rows, start, end, checks, reasons):
    positions = [row[0] for row in rows]
    actual = sum((row[1] for row in rows[start:end + 1]), Fraction())
    count = end - start + 1
    span_inches = positions[end] - positions[start]
    span_feet = span_inches / 12
    check_id = f'bridge_group_{start + 1}_{end + 1}'

    if _is_two_tandem_exception(positions, start, end):
        _comparison(
            check_id, actual, Fraction(TWO_TANDEM_LIMIT_LB),
            (f'Axles {start + 1}-{end + 1} form two consecutive tandem sets; '
             f'their outer span is {_fraction_text(span_feet)} ft. The reviewed '
             '36-ft exception permits no more than 68,000 lb combined, while each '
             'tandem remains subject to its own 34,000-lb check.'),
            'TWO_TANDEM_LIMIT_EXCEEDED', checks, reasons)
        return

    raw_limit = 500 * (span_feet * count / (count - 1) + 12 * count + 36)
    lower, upper = _rounded_bridge_limit(raw_limit)
    base_detail = (f'Axles {start + 1}-{end + 1}: N={count}, '
                   f'L={_fraction_text(span_feet)} ft, exact equation result '
                   f'{_fraction_text(raw_limit)} lb.')
    if lower == upper:
        _comparison(
            check_id, actual, lower,
            f'{base_detail} The result rounds to {_fraction_text(lower)} lb.',
            'BRIDGE_LIMIT_EXCEEDED', checks, reasons)
        return

    limit = {'lower_lb': _number(lower), 'upper_lb': _number(upper)}
    if actual <= lower:
        status = 'met'
    elif actual > upper:
        status = 'not_met'
        reasons.append('BRIDGE_LIMIT_EXCEEDED')
    else:
        status = 'unresolved'
        reasons.append('BRIDGE_ROUNDING_TIE_UNRESOLVED')
    checks.append(_check(
        check_id, status, _number(actual), limit,
        (f'{base_detail} This is exactly halfway between '
         f'{_fraction_text(lower)} and {_fraction_text(upper)} lb. The reviewed '
         'equation text does not choose a tie direction, and this evaluator does '
         'not use Table 1 as a lookup.')))


def _federal_interstate(rows, checks, reasons):
    positions = [row[0] for row in rows]
    for index, (_, weight) in enumerate(rows, 1):
        _comparison(
            f'federal_single_axle_{index}', weight,
            Fraction(FEDERAL_SINGLE_AXLE_LIMIT_LB),
            (f'Axle {index} is compared with the 20,000-lb Interstate limit, '
             'which applies to each axle including an axle in a group.'),
            'FEDERAL_SINGLE_AXLE_LIMIT_EXCEEDED', checks, reasons)

    gross = sum((row[1] for row in rows), Fraction())
    _comparison(
        'federal_gross_vehicle', gross, Fraction(GROSS_LIMIT_LB),
        'The complete axle layout is compared with the 80,000-lb gross limit.',
        'FEDERAL_GROSS_LIMIT_EXCEEDED', checks, reasons)

    close_gaps = set()
    for index, (left, right) in enumerate(zip(positions, positions[1:])):
        gap = right - left
        if gap < TANDEM_MIN_INCHES:
            close_gaps.add(index)
            checks.append(_check(
                f'axle_spacing_{index + 1}_{index + 2}', 'unresolved',
                _number(gap), {'threshold_inches': TANDEM_MIN_INCHES},
                 (f'Axles {index + 1}-{index + 2} are less than 40 inches apart. '
                 'The reviewed guide treats such a group as one axle for weight '
                 'allowance, but this evaluator does not implement that aggregation.')))
            reasons.append('CLOSE_AXLE_GROUP_UNSUPPORTED')
        elif _is_tandem_gap(gap):
            actual = rows[index][1] + rows[index + 1][1]
            _comparison(
                f'tandem_axles_{index + 1}_{index + 2}', actual,
                Fraction(TANDEM_LIMIT_LB),
                (f'Axles {index + 1}-{index + 2} are {_fraction_text(gap)} inches '
                 'apart, within the inclusive 40-96 inch tandem range.'),
                'TANDEM_LIMIT_EXCEEDED', checks, reasons)

    for start in range(len(rows) - 2):
        end = start + 2
        span = positions[end] - positions[start]
        if span <= TANDEM_MAX_INCHES:
            actual = sum((row[1] for row in rows[start:end + 1]), Fraction())
            checks.append(_check(
                f'tandem_cluster_{start + 1}_{end + 1}', 'unresolved',
                _number(actual), TANDEM_LIMIT_LB,
                (f'Axles {start + 1}-{end + 1} place three axle centers within '
                 f'{_fraction_text(span)} inches. The retained tandem passage '
                 'does not establish whether its 34,000-lb cap covers an entire '
                 'multi-axle cluster or only a two-axle set.')))
            reasons.append('MULTI_AXLE_TANDEM_CLASSIFICATION_UNRESOLVED')

    for start in range(len(rows) - 1):
        for end in range(start + 1, len(rows)):
            if any(gap_index in close_gaps for gap_index in range(start, end)):
                continue
            _bridge_check(rows, start, end, checks, reasons)


def _nj_noninterstate(rows, checks, reasons):
    positions = [row[0] for row in rows]
    for index, (position, weight) in enumerate(rows):
        neighboring_gaps = []
        if index:
            neighboring_gaps.append(position - positions[index - 1])
        if index + 1 < len(rows):
            neighboring_gaps.append(positions[index + 1] - position)
        if all(gap > TANDEM_MAX_INCHES for gap in neighboring_gaps):
            _comparison(
                f'nj_single_axle_{index + 1}', weight,
                Fraction(NJ_SINGLE_AXLE_LIMIT_LB),
                (f'Axle {index + 1} is separated by more than 96 inches from '
                 'each neighboring axle and is compared with the reviewed '
                 '22,400-lb New Jersey single-axle limit.'),
                'NJ_SINGLE_AXLE_LIMIT_EXCEEDED', checks, reasons)

    for index, (left, right) in enumerate(zip(positions, positions[1:])):
        gap = right - left
        if gap < TANDEM_MIN_INCHES:
            checks.append(_check(
                f'axle_spacing_{index + 1}_{index + 2}', 'unresolved',
                _number(gap), {'threshold_inches': TANDEM_MIN_INCHES},
                (f'Axles {index + 1}-{index + 2} are less than 40 inches apart. '
                 'The reviewed guide treats such a group as one axle for weight '
                 'allowance, but this evaluator does not implement that aggregation.')))
            reasons.append('CLOSE_AXLE_GROUP_UNSUPPORTED')

    checks.append(_check(
        'nj_noninterstate_group_limits', 'unresolved', None, None,
        ('The reviewed bridge equation, tandem, gross and two-tandem passages '
         'state an Interstate-System scope. They do not establish the complete '
         'group-weight rules for a New Jersey non-Interstate segment.')))
    reasons.append('NJ_NONINTERSTATE_GROUP_SCOPE_UNRESOLVED')


def evaluate_axles(layout, regime):
    """Evaluate a normalized individual-axle layout within a named road regime.

    The function returns only ``met``, ``not_met`` or ``unresolved``.  It never
    raises for caller data, including an unknown regime.
    """
    checks = []
    reasons = []
    supported_regime = isinstance(regime, str) and regime in REGIMES
    if not supported_regime:
        actual = regime if isinstance(regime, str) or regime is None else type(regime).__name__
        checks.append(_check(
            'road_regime', 'unresolved', actual,
            'federal_interstate or nj_noninterstate',
            'A supported road regime is required before axle limits can be selected.'))
        reasons.append('ROAD_REGIME_UNSUPPORTED')
    try:
        rows = _layout_rows(layout)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        rows = None
        checks.append(_check(
            'axle_layout', 'unresolved', None, 'axle_layout.NORMALIZED_SCHEMA',
            ('A layout needs 1-32 positive individual axle weights and ordered '
             'positions beginning at zero.')))
        reasons.append('INVALID_AXLE_LAYOUT')
    if rows is None or not supported_regime:
        return _finish(checks, reasons)
    if regime == 'federal_interstate':
        _federal_interstate(rows, checks, reasons)
    else:
        _nj_noninterstate(rows, checks, reasons)
    return _finish(checks, reasons)
