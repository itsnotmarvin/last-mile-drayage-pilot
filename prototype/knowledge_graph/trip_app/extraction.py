"""Bounded local suggestions. Unrecognized language stays for human review.

This is a deterministic convenience adapter, not Claude or a language evaluator.
It proposes reported facts only; every proposed value must be reviewed in the UI.
"""
import re
from neo4j_kg.input_review import LABELS, _dimensions
from neo4j_kg.trip_models import normalize_facts
from neo4j_kg.service import InputError


def suggest(text):
    facts = {}
    for field in LABELS:
        values = _dimensions(text, field)
        if len(values) == 1:
            facts[field] = {'value': float(next(iter(values))), 'unit': 'in'}
    # Only explicitly labeled gross weight, never payload or one axle's weight.
    matches = re.findall(r'\bgross(?: weight)?\s*(?:is\s*|[:=]\s*)?([\d,]+(?:\.\d+)?)\s*(lb|lbs|pounds|kg)\b', text, re.I)
    values = {(float(n.replace(',', '')), 'kg' if u.lower() == 'kg' else 'lb') for n, u in matches}
    if len(values) == 1:
        n, unit = values.pop()
        facts['gross_weight'] = {'value': n, 'unit': unit}
    # Context and negation require interpretation; even these destination matches
    # are presented as suggestions, never committed without review.
    if re.search(r'\b(?:to|destination(?: is|:)?|terminal(?: is|:)?)\s+APM(?:\s+(?:Elizabeth|terminal))?\b', text, re.I):
        facts['terminal_id'] = 'facility_apm_elizabeth'
    for field, pattern in (
        ('driver_id', r'\bsyn-driver-[a-z-]{1,40}\b'),
        ('vehicle_id', r'\bsyn-vehicle-[a-z0-9-]{1,40}\b'),
        ('trailer_id', r'\bsyn-trailer-[a-z0-9-]{1,40}\b'),
        ('current_sealink_id', r'\bSYN-SL-[A-Z]{1,8}\b')):
        values = set(re.findall(pattern, text))
        if len(values) == 1:
            facts[field] = values.pop()
    # No invented timestamps, credential possession, approvals, route IDs or role.
    # Rejecting an invalid suggestion must not discard a captured statement.
    valid = {}
    for field, value in facts.items():
        try:
            normalize_facts({field: value}, 'unknown', text)
            valid[field] = value
        except InputError:
            pass
    return valid
