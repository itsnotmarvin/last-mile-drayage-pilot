"""Source-bound comparisons of reports, never legal or operational clearance.

The frozen catalog is a reviewable transcription of numeric baselines and
reported prerequisites. It does not determine jurisdiction, exceptions, current
policy, verified credentials, or applicability to a real move. These results
remain separate from the requirement evaluator's met/not_met outcomes.
"""
import copy
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from .common import digest

_CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'data/reported_checks.json').read_text())
CATALOG_VERSION = digest(_CATALOG)
ENGINE_VERSION = 'reported-fact-comparisons-v1'
LIMITS = [
    'These are draft comparisons of reported facts with specifically retained source text, not human-approved compliance evaluators.',
    'A value at or below a cited baseline does not establish eligibility, permit validity, route access, terminal entry or dispatch clearance.',
    'Roadway jurisdiction, exceptions, actual permits, complete axle/bridge rules, current conditions and credential verification remain separate requirements.',
    'The checks are bound to a pinned evidence release; changed or missing source bindings suppress their comparisons until reviewed.',
]


def catalog():
    return copy.deepcopy(_CATALOG)


def unavailable(reason='EVIDENCE_UNAVAILABLE'):
    return {'schema_version':'drayage-reported-checks-v1','catalog_version':CATALOG_VERSION,
            'engine_version':ENGINE_VERSION,'status':'unavailable','approval_status':'draft_not_human_approved',
            'operational_permission':'not_issued','checks':[],'priority_actions':[],
            'not_run_check_ids':[c['id'] for c in _CATALOG['checks']],
            'reason_codes':[reason],'limits':LIMITS.copy()}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int,float)):
        raise ValueError('Not a numeric report')
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError('Not a positive finite measurement')
    return result


def _json_number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def evaluate_reported_checks(case, evidence, versions, selected, rejected_fields=()):
    if evidence['status'] != 'available':
        return unavailable()
    # An unchanged quotation in a changed release still requires explicit review
    # of the surrounding source/context before this catalog can use that release.
    if versions.get('graph_release') != _CATALOG['graph_release']:
        return unavailable('UNREVIEWED_GRAPH_RELEASE')
    sources = {s['clause_id']:s for s in evidence['sources']}
    requirement_ids = {r['id'] for r in selected}
    rejected = set(rejected_fields)
    conflicted = {c['field'] for c in case['conflicts']} | rejected
    facts = case['facts']
    value = lambda field: facts.get(field,{}).get('value')
    results, skipped, actions = [], [], []
    for definition in _CATALOG['checks']:
        if definition['requirement_id'] not in requirement_ids:
            skipped.append(definition['id']); continue
        conditions = definition.get('when',{})
        if any(value(f) != expected and f not in conflicted for f,expected in conditions.items()):
            skipped.append(definition['id']); continue
        fields = list(dict.fromkeys([*definition['fields'],*conditions]))
        conflicts = sorted(set(fields) & conflicted)
        missing = [f for f in fields if value(f) is None and f not in conflicts]
        row = {'check_id':definition['id'],'requirement_id':definition['requirement_id'],
               'title':definition['title'],'kind':definition['kind'],'status':'manual_review_required',
               'field_names':fields,'missing_fields':missing,'conflicting_fields':conflicts,
               'source_clause_ids':definition['source_clause_ids'].copy(),
               'source_text_sha256':{},'comparison':None,'summary':definition['context'],
               'context':definition['context'],'next_action':definition['next_action'],
               'owner':definition['owner'],'reason_codes':[],
               'reported_inputs':[{ 'field':f,'value':value(f),'unit':facts.get(f,{}).get('unit')} for f in fields]}
        bad_sources = []
        for cid in definition['source_clause_ids']:
            source, expected = sources.get(cid), _CATALOG['source_bindings'][cid]
            if (source is None or source.get('source_id') != expected['source_id']
                    or source.get('locator') != expected['locator']
                    or digest(source.get('source_text')) != expected['source_text_sha256']):
                bad_sources.append(cid)
            else:
                row['source_text_sha256'][cid] = expected['source_text_sha256']
        if bad_sources:
            row.update(status='source_review_required',summary='The retained evidence no longer matches this check’s source binding. No comparison was made.',
                       reason_codes=['SOURCE_BINDING_MISMATCH'],next_action='Review the missing or changed clause and its mapping before re-enabling this comparison.')
        elif conflicts:
            row.update(status='input_review_required',summary='Conflicting or inconsistent reports prevent this comparison.',reason_codes=['CONFLICTING_OR_INCONSISTENT_INPUT'])
            row['next_action'] = 'Resolve the conflicting reported ' + ', '.join(f.replace('_',' ') for f in conflicts) + ' before assessing this item.'
        elif definition['kind'] == 'manual':
            row['summary'] = 'This eligibility check remains unexecuted; the source interpretation or authoritative verification described below is still needed.'
            row['reason_codes'] = ['RULE_OR_VERIFICATION_GAP']
        elif missing:
            row.update(status='missing_facts',summary='No comparison was made because a required reported fact is unknown.',reason_codes=['REPORTED_FACTS_MISSING'])
        elif definition['kind'] == 'numeric':
            field = definition['fields'][0]
            try:
                number = _number(value(field))
                if facts[field].get('unit') != definition['unit']:
                    raise ValueError('Normalized measurement unit mismatch')
                reference = Decimal(str(definition['reference_value']))
                delta = number - reference
                relation = 'above' if delta > 0 else 'below' if delta < 0 else 'at'
                row['comparison'] = {'field':field,'reported':_json_number(number),'reference':_json_number(reference),
                                     'unit':definition['unit'],'relation':relation,'difference':_json_number(delta)}
                row.update(status='attention_required' if delta > 0 else 'comparison_only',
                           summary=f'The reported {field.replace("_"," ")} of {_json_number(number)} {definition["unit"]} is {relation} the cited {_json_number(reference)} {definition["unit"]} reference'
                                   + (f' by {_json_number(abs(delta))} {definition["unit"]}.' if delta else '.')
                                   + ' Applicability and operational eligibility remain unresolved.',
                           reason_codes=['REPORTED_VALUE_ABOVE_REFERENCE' if delta > 0 else 'COMPARISON_IS_NOT_CLEARANCE'])
            except (ValueError, InvalidOperation):
                row.update(status='input_review_required',summary='A positive finite reported measurement with the expected normalized unit is required.',reason_codes=['MEASUREMENT_REVIEW_REQUIRED'])
                row['next_action'] = 'Confirm a positive loaded measurement and its unit for ' + field.replace('_',' ') + '.'
        else:
            field = definition['fields'][0]
            reported = value(field)
            if type(reported) is not bool:
                row.update(status='input_review_required',summary='The reported prerequisite needs an explicit yes, no or unknown value.',reason_codes=['BOOLEAN_REPORT_REQUIRED'])
            elif reported != definition['expected']:
                row.update(status='attention_required',summary='The current report does not match the prerequisite described in the cited source. Applicability, exceptions and actual authorization remain unresolved.',reason_codes=['REPORTED_PREREQUISITE_NOT_SATISFIED'])
            else:
                row.update(status='reported_unverified',summary='The current report matches the described prerequisite; authoritative verification and trip applicability are still outstanding.',reason_codes=['REPORT_IS_NOT_VERIFICATION'])
        results.append(row)
        if row['status'] in ('attention_required','input_review_required','source_review_required'):
            actions.append({'check_id':row['check_id'],'requirement_id':row['requirement_id'],
                            'owner':row['owner'],'action':row['next_action'],'status':row['status']})
    # Known problems come before general missing-information questions. An input
    # or evidence correction takes precedence over a comparison of those inputs.
    priority = {'input_review_required':0,'source_review_required':1,'attention_required':2}
    actions.sort(key=lambda a:priority[a['status']])
    deduped = []
    for action in actions:
        if action['action'] not in {a['action'] for a in deduped}:
            deduped.append(action)
    return {'schema_version':'drayage-reported-checks-v1','catalog_version':CATALOG_VERSION,
            'engine_version':ENGINE_VERSION,'status':'available','approval_status':'draft_not_human_approved',
            'operational_permission':'not_issued','checks':results,'priority_actions':deduped[:3],
            'not_run_check_ids':skipped,'reason_codes':[], 'limits':LIMITS.copy()}
