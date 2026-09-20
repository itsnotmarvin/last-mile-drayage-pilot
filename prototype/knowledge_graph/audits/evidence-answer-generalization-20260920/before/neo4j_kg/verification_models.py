"""Strict operator-only synthetic verification contracts, never model input.

Provider aliases stand for fixture adapters, not authenticated real authorities.
No caller-facing MCP or application endpoint accepts these receipts.
"""
import copy
from decimal import Decimal
import re

from .common import digest
from .service import InputError, timestamp

VERSION = 'drayage-verification-v1'


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required, 'additionalProperties': False}


def enum(*values):
    return {'enum': list(values)}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def alias(prefix):
    return {'type': 'string', 'pattern': '^'+re.escape(prefix)+'[a-z0-9-]{1,64}$', 'maxLength': 100}


def segment_ref():
    """Synthetic adapter alias or pinned-graph road-segment identity.

    Graph identities (edge_*) are opaque here; membership in the trip's
    resolved route is enforced at admission time, never by shape alone.
    """
    return {'anyOf': [alias('syn-segment-'),
                      {'type': 'string', 'pattern': '^edge_[a-z0-9_]{1,64}$', 'maxLength': 100}]}


BOOL = {'type': 'boolean'}
NUMBER = {'type': 'number', 'minimum': 0, 'maximum': 10000000}
POSITIVE = {**NUMBER, 'exclusiveMinimum': 0}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
TIME = {'type': 'string', 'format': 'timestamp'}
HASH = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
DRIVER = {'type': 'string', 'pattern': '^syn-driver-[a-z-]{1,40}$'}
SEALINK = {'type': 'string', 'pattern': '^SYN-SL-[A-Z]{1,8}$'}
VEHICLE = alias('syn-vehicle-')
TRAILER = alias('syn-trailer-')
LOAD = alias('syn-load-')
MOVE = alias('syn-move-')
TERMINAL = enum('facility_apm_elizabeth')
ROUTE = enum('path_a_exit13a_to_apm', 'path_b_us1_9_to_apm', 'other')
MOVE_TYPE = enum('import_pickup', 'empty_pickup', 'export_dropoff', 'empty_return', 'unknown')
AUTHORITY = enum('nj_state', 'county', 'local', 'nj_turnpike', 'port', 'terminal')
EQUIPMENT = {'vehicle_id': VEHICLE, 'trailer_id': TRAILER, 'load_id': LOAD}
ROUTE_BINDING = {'route_id': ROUTE, 'route_description': TEXT}
MOVE_BINDING = {'move_id': MOVE, 'move_type': MOVE_TYPE, 'terminal_id': TERMINAL}
LIMIT_FIELDS = ('gross_lb', 'single_axle_lb', 'tandem_lb', 'height_inches', 'width_inches',
                'overall_length_inches', 'semitrailer_length_inches')
LIMITS = obj({k: POSITIVE for k in LIMIT_FIELDS}, [])
from .axle_layout import NORMALIZED_SCHEMA

PAYLOADS = {
    'scale': obj({**EQUIPMENT, 'gross_weight_lb': POSITIVE, 'axle_layout': NORMALIZED_SCHEMA,
                  'weighing_method': enum('fixed_scale', 'portable_scale', 'unknown')}),
    'dimensions': obj({**EQUIPMENT, 'height_inches': POSITIVE, 'width_inches': POSITIVE,
                       'overall_length_inches': POSITIVE, 'semitrailer_length_inches': POSITIVE,
                       'kingpin_to_rear_axle_inches': nullable(POSITIVE),
                       'configuration': enum('standard_tractor_semitrailer', 'other', 'unknown')}),
    'route': obj({**EQUIPMENT, **ROUTE_BINDING, 'terminal_id': TERMINAL,
                 'complete_sequence_verified': BOOL,
                 'exception_claimed': BOOL,
                 'segments': {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': obj({
                     'segment_id': segment_ref(), 'authority': AUTHORITY,
                     'weight_regime': enum('federal_interstate', 'nj_noninterstate', 'unknown'),
                     'dimension_regime': enum('nj_102_network', 'nj_local_102_standard', 'terminal', 'unknown'),
                     'local_direct_terminal_access_verified': BOOL,
                     'long_semitrailer_access_verified': BOOL,
                     'access': enum('permitted', 'prohibited', 'unknown'),
                     'posted_limits': LIMITS})}}),
    'permit': obj({**EQUIPMENT, **ROUTE_BINDING, 'permit_type': enum('none', 'nj_single_trip', 'nj_ocean_container_annual', 'other'),
                  'permit_id': alias('syn-permit-'), 'issuer': enum('nj_state', 'other'),
                  'status': enum('valid', 'revoked', 'expired', 'not_found', 'unknown'),
                  'load_nondivisible': nullable(BOOL), 'sealed_ocean_borne_container': nullable(BOOL),
                  'conditions_satisfied': nullable(BOOL), 'authorized_limits': LIMITS}),
    'approval': obj({**EQUIPMENT, **ROUTE_BINDING, 'authority': AUTHORITY,
                    'segment_ids': {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': segment_ref()},
                    'status': enum('approved', 'denied', 'not_required', 'unknown'),
                    'conditions_satisfied': nullable(BOOL)}),
    'conditions': obj({**EQUIPMENT, **ROUTE_BINDING, 'segment_id': segment_ref(), 'authority': AUTHORITY,
                      'posting_checked': BOOL, 'closure_checked': BOOL, 'lane_and_detour_checked': BOOL,
                      'escort_checked': BOOL, 'status': enum('open', 'closed', 'restricted', 'unknown'),
                      'conditions_satisfied': nullable(BOOL), 'posted_limits': LIMITS,
                      'source_reference': nullable(TEXT), 'evidence_sha256': nullable(HASH)},
                     ['vehicle_id', 'trailer_id', 'load_id', 'route_id', 'route_description',
                      'segment_id', 'authority', 'posting_checked', 'closure_checked',
                      'lane_and_detour_checked', 'escort_checked', 'status',
                      'conditions_satisfied', 'posted_limits']),
    'dtr': obj({'vehicle_id': VEHICLE, 'drayage_truck': nullable(BOOL), 'class_8': nullable(BOOL), 'registered': nullable(BOOL),
                'active': nullable(BOOL), 'rfid_assigned': nullable(BOOL), 'rfid_mounted': nullable(BOOL),
                'rfid_valid': nullable(BOOL), 'registered_at': nullable(TIME),
                'registration_changed_at': nullable(TIME), 'registration_amended_at': nullable(TIME),
                'engine_model_year': {'type': 'integer', 'minimum': 1886, 'maximum': 2100},
                'meets_2014_emissions_standard': nullable(BOOL),
                'registration_event': enum('new_registration', 'existing_registration', 'ownership_change', 'unknown')}),
    'twic': obj({'driver_id': DRIVER, 'unescorted_secure_access': nullable(BOOL), 'exception_claimed': BOOL,
                 'status': enum('valid', 'revoked', 'expired', 'not_found', 'unknown'),
                 'credential_expires_at': nullable(TIME), 'physically_present': nullable(BOOL)}),
    'sealink': obj({'driver_id': DRIVER, 'current_sealink_id': SEALINK,
                    'active': nullable(BOOL), 'twic_registered': nullable(BOOL)}),
    'appointment': obj({**MOVE_BINDING, 'vehicle_id': VEHICLE,
                       'status': enum('confirmed', 'cancelled', 'not_found', 'unknown'),
                       'slot_start': TIME, 'slot_end': TIME}),
    'transaction': obj({**MOVE_BINDING, 'load_id': LOAD, 'fully_available': nullable(BOOL),
                       'holds_complete': BOOL, 'freight_hold': nullable(BOOL), 'customer_hold': nullable(BOOL),
                       'demurrage_hold': nullable(BOOL), 'customs_hold': nullable(BOOL),
                       'other_hold': nullable(BOOL)}),
}
PROVIDERS = {kind: {'provider_id': 'syn-provider-'+kind,
                    'authority_role': role} for kind, role in (
    ('scale', 'scale_operator'), ('dimensions', 'equipment_measurement'),
    ('route', 'road_authority'), ('permit', 'permit_authority'), ('approval', 'road_authority'),
    ('conditions', 'road_authority'), ('dtr', 'port_registry'), ('twic', 'credential_verifier'),
    ('sealink', 'port_registry'), ('appointment', 'terminal_operator'), ('transaction', 'terminal_operator'))}
_BASE = {'schema_version': {'const': VERSION}, 'mode': {'const': 'synthetic_only'},
         'id': alias('syn-verification-'), 'kind': enum(*PAYLOADS),
         'provider_id': alias('syn-provider-'), 'authority_role': TEXT,
         'graph_release': HASH, 'trip_id': {'type': 'string', 'pattern': '^syn-trip-[0-9a-f]{32}$'},
         'trip_revision': {'type': 'integer', 'minimum': 1}, 'case_sha256': HASH,
         'observed_at': TIME, 'valid_from': TIME, 'valid_until': TIME}


def receipt_schema():
    return {'oneOf': [obj({**_BASE, 'kind': {'const': kind},
                          'provider_id': {'const': PROVIDERS[kind]['provider_id']},
                          'authority_role': {'const': PROVIDERS[kind]['authority_role']},
                          'payload': copy.deepcopy(schema)}) for kind, schema in PAYLOADS.items()]}


def case_fingerprint(case):
    return digest({'trip_id': case['trip_id'], 'revision': case['revision'],
                   'facts': {k: {'value': v['value'], 'unit': v.get('unit')} for k, v in case['facts'].items()},
                   'conflicts': case['conflicts']})


def _validate(value, schema):
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try:
                _validate(value, option)
                return
            except InputError:
                pass
        raise InputError('Verification field has an invalid type or value')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise InputError('Verification constant does not match the contract')
    if 'enum' in schema and not any(type(value) is type(v) and value == v for v in schema['enum']):
        raise InputError('Verification enumeration is not supported')
    kind = schema.get('type')
    if kind == 'null' and value is not None:
        raise InputError('Expected unknown verification value')
    elif kind == 'boolean' and type(value) is not bool:
        raise InputError('Expected boolean verification value')
    elif kind in ('number', 'integer'):
        if type(value) not in ((int,) if kind == 'integer' else (int, float)):
            raise InputError('Expected finite numeric verification value')
        number = Decimal(str(value))
        if (not number.is_finite() or number < schema.get('minimum', 0)
                or ('maximum' in schema and number > schema['maximum'])
                or ('exclusiveMinimum' in schema and number <= schema['exclusiveMinimum'])):
            raise InputError('Verification measurement is outside supported bounds')
    elif kind == 'string':
        if (not isinstance(value, str) or len(value) < schema.get('minLength', 0)
                or len(value) > schema.get('maxLength', 2000) or '\x00' in value
                or ('pattern' in schema and not re.fullmatch(schema['pattern'], value))):
            raise InputError('Invalid verification text or synthetic identity')
        if schema.get('format') == 'timestamp':
            timestamp(value)
    elif kind == 'array':
        if not isinstance(value, list) or not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 100):
            raise InputError('Invalid verification collection')
        for item in value:
            _validate(item, schema['items'])
    elif kind == 'object':
        if (not isinstance(value, dict) or set(value)-set(schema['properties'])
                or set(schema['required'])-set(value)):
            raise InputError('Missing or unexpected verification fields')
        for key, item in value.items():
            _validate(item, schema['properties'][key])


def validate_receipt(receipt):
    if not isinstance(receipt, dict) or receipt.get('kind') not in PAYLOADS:
        raise InputError('Unknown verification receipt kind')
    kind = receipt['kind']
    _validate(receipt, obj({**_BASE, 'payload': PAYLOADS[kind]}))
    if any(receipt[field] != expected for field, expected in PROVIDERS[kind].items()):
        raise InputError('Provider is not the configured synthetic adapter for this evidence kind')
    if timestamp(receipt['valid_from']) >= timestamp(receipt['valid_until']):
        raise InputError('Verification requires a nonempty interval: valid_from <= trip_at < valid_until')
    if timestamp(receipt['observed_at']) > timestamp(receipt['valid_until']):
        raise InputError('Observation occurs after its stated validity interval')
    payload = receipt['payload']
    if kind == 'dtr':
        observed = timestamp(receipt['observed_at'])
        event_fields = (
            'registered_at',
            'registration_changed_at',
            'registration_amended_at',
        )
        events = [
            (field, timestamp(payload[field]))
            for field in event_fields
            if payload[field] is not None
        ]
        if any(event_at > observed for _, event_at in events):
            raise InputError('A completed DTR event cannot occur after observed_at')
        if any(earlier_at > later_at for (_, earlier_at), (_, later_at) in zip(events, events[1:])):
            raise InputError(
                'DTR event chronology must be registered_at <= '
                'registration_changed_at <= registration_amended_at'
            )
    if kind == 'appointment' and timestamp(payload['slot_start']) >= timestamp(payload['slot_end']):
        raise InputError('Appointment interval must be nonempty')
    if kind == 'twic' and payload['status'] == 'valid' and payload['credential_expires_at'] is not None:
        if timestamp(receipt['valid_until']) > timestamp(payload['credential_expires_at']):
            raise InputError('TWIC receipt cannot extend beyond credential expiry')
    if kind == 'transaction':
        holds = [payload[k] for k in ('freight_hold', 'customer_hold', 'demurrage_hold', 'customs_hold', 'other_hold')]
        if payload['holds_complete'] and any(h is None for h in holds):
            raise InputError('Complete hold coverage requires explicit hold values')
        if payload['fully_available'] is True and any(h is True for h in holds):
            raise InputError('Available container cannot simultaneously have an unresolved hold')
    if kind == 'route':
        ids = [s['segment_id'] for s in payload['segments']]
        if len(ids) != len(set(ids)):
            raise InputError('Route segment identities must be unique for this ordered sequence')
    if kind == 'approval' and len(payload['segment_ids']) != len(set(payload['segment_ids'])):
        raise InputError('Approval segment identities must be unique')
    if kind == 'scale':
        from .axle_layout import review_layout
        facts = {'axle_layout': {'value': payload['axle_layout'], 'unit': None},
                 'gross_weight': {'value': payload['gross_weight_lb'], 'unit': 'lb'}}
        if review_layout(facts)['status'] != 'reported_only':
            raise InputError('Verified scale payload must contain ordered individual axles reconciling to gross')


CONTRACT_VERSION = digest(receipt_schema())
