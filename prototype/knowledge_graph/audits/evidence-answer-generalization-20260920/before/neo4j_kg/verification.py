"""Read-time evidence admission. Only the operator store supplies receipts.

An admitted record is a synthetic adapter assertion, never a real authority
credential. Time intervals are start-inclusive/end-exclusive. Historical records
outside the trip interval are rejected without conflicting with current records.
"""
from datetime import datetime, timezone
from .common import digest
from .service import InputError, timestamp
from .verification_models import validate_receipt, case_fingerprint, CONTRACT_VERSION

ENGINE_VERSION = 'bounded-requirement-evaluators-v1'
REQUIRED_KINDS = {
    'axle_weight_evidence': ('scale', 'route'),
    'dimensions_and_route': ('dimensions', 'route'),
    'permit_eligibility': ('permit', 'scale', 'dimensions', 'route'),
    'cross_authority_coverage': ('route', 'approval'),
    'current_route_conditions': ('route', 'conditions', 'scale', 'dimensions'),
    'dtr_registration_and_rfid': ('dtr',), 'dtr_engine_policy': ('dtr',),
    'driver_twic': ('twic',), 'sealink_registration': ('sealink',),
    'apm_appointment': ('appointment',), 'transaction_release': ('transaction',),
}
EQUIPMENT = ('vehicle_id', 'trailer_id', 'load_id')
BINDING_FIELDS = {
    'scale': EQUIPMENT + ('gross_weight', 'axle_layout'),
    'dimensions': EQUIPMENT + ('width', 'height', 'overall_length', 'semitrailer_length'),
    'route': EQUIPMENT + ('route_id', 'route_description', 'terminal_id'),
    'permit': EQUIPMENT + ('route_id', 'route_description', 'permit_type'),
    'approval': EQUIPMENT + ('route_id', 'route_description'),
    'conditions': EQUIPMENT + ('route_id', 'route_description'),
    'dtr': ('vehicle_id',), 'twic': ('driver_id',),
    'sealink': ('driver_id', 'current_sealink_id'),
    'appointment': ('move_id', 'move_type', 'terminal_id', 'vehicle_id'),
    'transaction': ('move_id', 'move_type', 'terminal_id', 'load_id'),
}
MEASUREMENTS = {'gross_weight': 'gross_weight_lb', 'width': 'width_inches',
                'height': 'height_inches', 'overall_length': 'overall_length_inches',
                'semitrailer_length': 'semitrailer_length_inches'}


def required_fields(requirement_id):
    return list(dict.fromkeys(('trip_at',) + tuple(
        f for kind in REQUIRED_KINDS[requirement_id] for f in BINDING_FIELDS[kind])))


SEGMENTED_KINDS = ('route', 'approval', 'conditions')


def _referenced_segments(kind, payload):
    if not isinstance(payload, dict):
        return set()
    if kind == 'route':
        segments = payload.get('segments')
        if not isinstance(segments, list):
            return set()
        return {s.get('segment_id') for s in segments if isinstance(s, dict)}
    if kind == 'approval':
        segment_ids = payload.get('segment_ids')
        return set(segment_ids) if isinstance(segment_ids, list) else set()
    if kind == 'conditions':
        segment_id = payload.get('segment_id')
        return {segment_id} if segment_id is not None else set()
    return set()


def restrict_evidence_to_segments(admission, segment_ids):
    """Move receipts referencing off-route segments into rejected evidence.

    Pure function used only when the trip route resolved from the pinned
    graph. Unknown segments fail closed instead of evaluating against the
    wrong road. The admission digest is recomputed so version identity stays
    exact.
    """
    ordered_segment_ids = list(segment_ids)
    segment_ids = set(ordered_segment_ids)
    evidence = {kind: list(records) for kind, records in admission.get('evidence', {}).items()}
    rejected = list(admission.get('rejected', []))
    for kind in SEGMENTED_KINDS:
        kept = []
        for receipt in evidence.get(kind, []):
            payload = receipt.get('payload', {})
            reasons = []
            if not _referenced_segments(kind, payload) <= segment_ids:
                reasons.append('VERIFICATION_SEGMENT_NOT_ON_RESOLVED_ROUTE')
            if kind == 'route' and [s['segment_id'] for s in payload['segments']] != ordered_segment_ids:
                reasons.append('VERIFICATION_ROUTE_SEQUENCE_MISMATCH')
            if not reasons:
                kept.append(receipt)
            else:
                rejected.append({'id': receipt.get('id', 'unknown'), 'kind': kind,
                                 'reason_codes': reasons})
        evidence[kind] = kept
    admission_version = digest({'accepted': sorted(r['id'] for rs in evidence.values() for r in rs),
                                'rejected': rejected,
                                'revoked_ids': admission.get('revoked_ids', [])})
    return {**admission, 'evidence': evidence, 'rejected': rejected,
            'admission_version': admission_version}


def admit(snapshot, case, release, now=None):
    now = timestamp(now) if now else datetime.now(timezone.utc)
    at_value = case['facts'].get('trip_at', {}).get('value')
    at = timestamp(at_value) if at_value else None
    admitted, rejected = {}, []
    fingerprint = case_fingerprint(case)
    conflicts = {c['field'] for c in case['conflicts']}
    for receipt in snapshot['receipts']:
        reasons = []
        try:
            validate_receipt(receipt)
        except InputError:
            # Store read validation should fail the service before this boundary;
            # this guard also protects direct evaluator/test usage.
            rejected.append({'id': receipt.get('id', 'invalid'), 'kind': receipt.get('kind', 'unknown'),
                             'reason_codes': ['INVALID_VERIFICATION_RECEIPT']})
            continue
        kind, p = receipt['kind'], receipt['payload']
        if receipt['id'] in snapshot['revoked_ids']:
            reasons.append('VERIFICATION_REVOKED')
        if (receipt['trip_id'] != case['trip_id'] or receipt['trip_revision'] != case['revision']
                or receipt['case_sha256'] != fingerprint or receipt['graph_release'] != release):
            reasons.append('VERIFICATION_CASE_OR_RELEASE_MISMATCH')
        if at is None or not timestamp(receipt['valid_from']) <= at < timestamp(receipt['valid_until']):
            reasons.append('VERIFICATION_OUTSIDE_TRIP_INTERVAL')
        observed = timestamp(receipt['observed_at'])
        if observed > now or (at is not None and observed > at):
            reasons.append('VERIFICATION_OBSERVATION_IN_FUTURE')
        for field in BINDING_FIELDS[kind]:
            fact = case['facts'].get(field, {})
            if field in conflicts or fact.get('value') is None:
                reasons.append('VERIFICATION_ASSIGNMENT_UNRESOLVED')
            elif fact['value'] != p.get(MEASUREMENTS.get(field, field)):
                reasons.append('VERIFICATION_SUBJECT_OR_MEASUREMENT_MISMATCH')
        if reasons:
            rejected.append({'id': receipt['id'], 'kind': kind, 'reason_codes': sorted(set(reasons))})
        else:
            admitted.setdefault(kind, []).append(receipt)
    return {'evidence': admitted, 'rejected': rejected, 'revoked_ids': snapshot['revoked_ids'],
            'snapshot_version': snapshot['version'],
            'admission_version': digest({'accepted': sorted(r['id'] for rs in admitted.values() for r in rs),
                                         'rejected': rejected, 'revoked_ids': snapshot['revoked_ids']})}


def evaluate_requirement(requirement_id, facts, admission, trip_at):
    kinds = REQUIRED_KINDS[requirement_id]
    evidence = admission['evidence']
    conflicts = []
    for kind in kinds:
        if kind in ('approval', 'conditions'):
            continue  # Segmented observations are compared by the road evaluator.
        if len({digest(r['payload']) for r in evidence.get(kind, [])}) > 1:
            conflicts.append(kind)
    if conflicts:
        return {'status': 'unresolved', 'reason_codes': ['CONFLICTING_VERIFICATION_RECEIPTS'],
                'checks': [{'id': 'receipt_conflict', 'status': 'unresolved', 'detail': ', '.join(conflicts)}],
                'used_receipt_ids': [], 'limits': []}
    if requirement_id in ('axle_weight_evidence', 'dimensions_and_route', 'permit_eligibility',
                           'cross_authority_coverage', 'current_route_conditions'):
        from .road_evaluators import evaluate_road
        result = evaluate_road(requirement_id, facts, evidence, trip_at)
    else:
        from .terminal_evaluators import evaluate_terminal
        result = evaluate_terminal(requirement_id, facts, evidence, trip_at)
    # A report cannot defeat a trusted negative, nor can a trusted positive
    # silently discard a contradictory current report about the same prerequisite.
    report_map = {
        'dtr_registration_and_rfid': ('dtr_reported',),
        'permit_eligibility': ('permit_route_reported',),
        'driver_twic': ('twic_reported',), 'sealink_registration': ('sealink_registered_reported',),
        'apm_appointment': ('appointment_reported',), 'transaction_release': ('transaction_release_reported',),
    }
    report_fields = list(report_map.get(requirement_id, ()))
    if (requirement_id == 'dtr_registration_and_rfid'
            and any(c['id'] in ('rfid_assigned', 'rfid_valid', 'rfid_properly_mounted')
                    for c in result['checks'])):
        report_fields.append('rfid_reported')
    if result['status'] == 'met' and any(facts.get(f, {}).get('value') is False
                                         for f in report_fields):
        result['status'] = 'unresolved'
        result['reason_codes'].append('REPORT_CONFLICTS_WITH_SYNTHETIC_VERIFICATION')
    return result
