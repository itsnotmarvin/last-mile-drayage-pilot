"""Bounded road/permit predicates over admitted synthetic adapter receipts.

Results address documented subchecks, never route clearance. An issuer's permit
limits cannot rewrite the baseline weight rule or another authority's decision.
"""
from decimal import Decimal
from .common import digest


def _result(checks, ids=(), limits=()):
    statuses = [c['status'] for c in checks]
    status = ('not_met' if 'not_met' in statuses else 'unresolved'
              if not statuses or 'unresolved' in statuses else 'met')
    return {'status': status, 'checks': checks,
            'reason_codes': list(dict.fromkeys(c['id'].upper() for c in checks if c['status'] != 'met')),
            'used_receipt_ids': sorted(set(ids)), 'limits': list(limits)}


def _check(checks, name, predicate, detail):
    checks.append({'id': name, 'status': 'unresolved' if predicate is None else 'met' if predicate else 'not_met',
                   'detail': detail})


def _one(evidence, kind, checks, ids):
    records = evidence.get(kind, [])
    if not records:
        _check(checks, kind+'_verification_required', None, 'No admitted '+kind+' verification for this trip.')
        return None
    if len({digest(r['payload']) for r in records}) > 1:
        _check(checks, kind+'_verification_conflict', None, 'Current '+kind+' observations disagree.')
        return None
    ids.extend(r['id'] for r in records)
    return records[0]['payload']


def _route(evidence, checks, ids):
    route = _one(evidence, 'route', checks, ids)
    if route:
        _check(checks, 'complete_route_sequence', True if route['complete_sequence_verified'] else None,
               'The exact ordered route must be verified; a stored route name or directions cannot substitute.')
        _check(checks, 'ordinary_vehicle_load_scope', None if route['exception_claimed'] else True,
               'Special vehicle/load exceptions require separate reviewed rules.')
        for segment in route['segments']:
            _check(checks, segment['segment_id']+'_access',
                   {'permitted': True, 'prohibited': False, 'unknown': None}[segment['access']],
                   'Authority route-access observation; current postings and other predicates remain separate.')
    return route


def _measure(checks, name, actual, limit):
    _check(checks, name, None if actual is None or limit is None else Decimal(str(actual)) <= Decimal(str(limit)),
           'Measured '+str(actual)+'; upper bound '+str(limit)+'. No tolerance or exception inferred.')


def _quantities(scale, dimensions):
    out = {}
    if scale:
        weights = [a['weight_lb'] for a in scale['axle_layout']['axles']]
        axles = scale['axle_layout']['axles']
        tandems = [sum(a['weight_lb'] for a in axles[i:j+1])
                   for i in range(len(axles)) for j in range(i+1, len(axles))
                   if 40 <= axles[j]['position_inches']-axles[i]['position_inches'] <= 96]
        out.update(gross_lb=scale['gross_weight_lb'], single_axle_lb=max(weights), tandem_lb=max(tandems, default=0))
    if dimensions:
        out.update({k: dimensions[k] for k in ('width_inches','height_inches','overall_length_inches','semitrailer_length_inches')})
    return out


def axle_weight(evidence, facts, at):
    checks, ids = [], []
    scale = _one(evidence, 'scale', checks, ids)
    route = _route(evidence, checks, ids)
    if scale:
        _check(checks, 'scale_method', None if scale['weighing_method'] == 'unknown' else True,
               'Loaded individual measurements are supplied by the synthetic scale adapter.')
    if scale and route and not route['exception_claimed']:
        from .bridge_math import evaluate_axles
        for segment in route['segments']:
            result = evaluate_axles(scale['axle_layout'], segment['weight_regime'])
            for check in result['checks']:
                checks.append({'id': segment['segment_id']+'_'+check['id'], 'status': check['status'],
                               'detail': str(check['detail']) + ' Actual: '+str(check.get('actual'))+'; limit: '+str(check.get('limit'))})
            if result['status'] == 'unresolved' and not any(c['status']=='unresolved' for c in result['checks']):
                _check(checks, 'weight_regime_unresolved', None, ', '.join(result['reason_codes']))
            for field, limit in segment['posted_limits'].items():
                if field in ('gross_lb','single_axle_lb','tandem_lb'):
                    _measure(checks, segment['segment_id']+'_posting_'+field, _quantities(scale,None).get(field), limit)
    return _result(checks, ids, ['Ordinary baseline axle/gross/bridge comparisons only; permits and special exceptions do not alter this result.',
                               'Non-Interstate bridge/tandem applicability remains a source-scope gap. Tire and specialized vehicle rules are outside coverage.',
                               'Bridge premises include separately disclosed draft extractions from the graph-linked archived guide.'])


def dimensions_route(evidence, facts, at):
    checks, ids = [], []
    dimensions = _one(evidence, 'dimensions', checks, ids)
    route = _route(evidence, checks, ids)
    if dimensions and route:
        _check(checks, 'standard_tractor_semitrailer', True if dimensions['configuration']=='standard_tractor_semitrailer' else None,
               'This evaluator covers an ordinary tractor with one semitrailer.')
        for s in route['segments']:
            sid = s['segment_id']
            regime = s['dimension_regime']
            if regime in ('unknown','terminal'):
                _check(checks, sid+'_dimension_rule_scope', None, 'No generic terminal or unknown-road dimensional clearance rule is inferred.')
                # Still evaluate explicitly observed postings below.
            else:
                _measure(checks,sid+'_width',dimensions['width_inches'],102)
                _measure(checks,sid+'_height',dimensions['height_inches'],162)
                _measure(checks,sid+'_semitrailer_length',dimensions['semitrailer_length_inches'],636)
                if regime == 'nj_local_102_standard':
                    _check(checks,sid+'_local_direct_access', True if s['local_direct_terminal_access_verified'] else None,
                           'Local use must satisfy the direct terminal-access rule; road-network absence is not permission.')
                    _check(checks,sid+'_local_102_scope', True if dimensions['width_inches']==102 else None,
                           'The retained local-access clause explicitly concerns a 102-inch-wide standard truck.')
                if dimensions['semitrailer_length_inches'] > 576:
                    _check(checks,sid+'_long_semitrailer_access', True if s['long_semitrailer_access_verified'] else None,
                           'A trailer over48ft requires verified National Network or exact direct terminal-access scope.')
            for field, limit in s['posted_limits'].items():
                if field in dimensions:
                    _measure(checks,sid+'_posting_'+field,dimensions[field],limit)
    return _result(checks,ids,['Overall length is bound and checked against explicit postings; no universal combination-length limit is invented.',
                              'Network classification, access and postings are synthetic route-adapter evidence, not derived from graph topology.',
                              'Bridge clearance and special equipment/load exceptions remain outside this dimensional subcheck.'])


def permit_eligibility(evidence, facts, at):
    checks, ids = [], []
    permit = _one(evidence,'permit',checks,ids)
    route = _route(evidence,checks,ids)
    scale = _one(evidence,'scale',checks,ids)
    dimensions = _one(evidence,'dimensions',checks,ids)
    if permit:
        typ = permit['permit_type']
        _check(checks,'supported_permit_type', True if typ in ('nj_single_trip','nj_ocean_container_annual') else None,
               'No-permit-needed and other permit classes require a separate applicability decision.')
        if typ not in ('nj_single_trip','nj_ocean_container_annual'):
            return _result(checks,ids,['Permit necessity and unsupported permit classes remain unresolved; an absent permit is not automatically a violation.'])
        _check(checks,'permit_issuer', True if permit['issuer']=='nj_state' else None,'Only the synthetic NJ issuing-adapter scope is implemented.')
        _check(checks,'permit_status', {'valid':True,'revoked':False,'expired':False,'not_found':False,'unknown':None}[permit['status']],
               'The issuing-adapter record must be valid for this exact trip interval and assignment.')
        _check(checks,'permit_conditions',permit['conditions_satisfied'],'Permit restrictions must be satisfied; unknown is unresolved.')
        if typ=='nj_single_trip':
            _check(checks,'single_trip_nondivisible',permit['load_nondivisible'],'Retained single-trip rule is limited to non-divisible loads.')
        elif typ=='nj_ocean_container_annual':
            _check(checks,'sealed_ocean_container',permit['sealed_ocean_borne_container'],
                   'Retained ocean-container rule requires sealed containers of the specified ocean-commerce type.')
            if scale:
                q = _quantities(scale,None)
                _measure(checks,'ocean_gross',q['gross_lb'],90000)
                _measure(checks,'ocean_tandem',q['tandem_lb'],38000)
                axles=scale['axle_layout']['axles']
                if any(axles[i+2]['position_inches']-axles[i]['position_inches']<=192 for i in range(len(axles)-2)):
                    _check(checks,'ocean_triaxle_classification',None,'The retained table gives56,400lb but does not establish a complete tri-axle classification rule in this evaluator.')
            dresult=dimensions_route(evidence,facts,at)
            _check(checks,'ocean_legal_dimensions',True if dresult['status']=='met' else False if dresult['status']=='not_met' else None,
                   'Ocean-container permit does not authorize oversize dimensions.')
        q=_quantities(scale,dimensions)
        for field in ('gross_lb','single_axle_lb','tandem_lb','width_inches','height_inches','overall_length_inches','semitrailer_length_inches'):
            _measure(checks,'permit_envelope_'+field,q.get(field),permit['authorized_limits'].get(field))
        # Contradictory input cannot be silently overwritten by a fixture.
        reports={'load_divisible': None if permit['load_nondivisible'] is None else not permit['load_nondivisible'],
                 'container_sealed': permit['sealed_ocean_borne_container']}
        for field, expected in reports.items():
            reported=facts.get(field,{}).get('value')
            if reported is not None and expected is not None and reported != expected:
                _check(checks,'permit_report_conflict',None,'Load reports disagree with the issuing-adapter evidence.')
    return _result(checks,ids,['This result checks permit type/load prerequisites and its stated numerical envelope only.',
                              'It does not decide whether a permit is required, authorize another jurisdiction, waive bridge rules or prove a trip remains unused.',
                              'The issuing-adapter validity interval is explicit; no extension or blanket five-day window is inferred.'])


def _segment_evidence(evidence,kind,segment,checks,ids):
    def targets(record):
        payload=record['payload']
        return (segment['segment_id'] in payload['segment_ids'] if kind=='approval'
                else payload['segment_id']==segment['segment_id'])
    targeted=[r for r in evidence.get(kind,[]) if targets(r)]
    mismatched=[r for r in targeted if r['payload']['authority']!=segment['authority']]
    if mismatched:
        ids.extend(r['id'] for r in mismatched)
        _check(checks,segment['segment_id']+'_'+kind+'_authority_mismatch',None,
               'An admitted '+kind+' receipt names this route segment under a different responsible authority.')
    records=[r for r in targeted if r['payload']['authority']==segment['authority']]
    if not records:
        _check(checks,segment['segment_id']+'_'+kind+'_missing',None,'No matching responsible-authority evidence for this route segment.')
        return None
    # Compare overlapping assertions by their semantics, not unrelated segment-list order.
    projections=[{k:v for k,v in r['payload'].items() if k!='segment_ids'} for r in records]
    if len({digest(p) for p in projections})>1:
        _check(checks,segment['segment_id']+'_'+kind+'_conflict',None,'Overlapping authority observations disagree.')
        return None
    ids.extend(r['id'] for r in records)
    return records[0]['payload']


def cross_authority(evidence,facts,at):
    checks,ids=[],[]
    route=_route(evidence,checks,ids)
    if route:
        for s in route['segments']:
            approval=_segment_evidence(evidence,'approval',s,checks,ids)
            if approval:
                _check(checks,s['segment_id']+'_authority_coverage',
                       {'approved':True,'denied':False,'not_required':True,'unknown':None}[approval['status']],
                       'Explicit segment-specific approval or not-required determination from its synthetic responsible-authority adapter.')
                if approval['status']=='approved':
                    _check(checks,s['segment_id']+'_approval_conditions',approval['conditions_satisfied'],
                           'Approval conditions remain separate from another authority’s permit.')
    return _result(checks,ids,['Only the verified complete sequence is covered. Unknown/omitted jurisdictions cannot be inferred from route names.',
                              'A State permit is not an approval for toll, county, local, port or terminal segments.'])


def route_conditions(evidence,facts,at):
    checks,ids=[],[]
    route=_route(evidence,checks,ids)
    scale=_one(evidence,'scale',checks,ids)
    dimensions=_one(evidence,'dimensions',checks,ids)
    q=_quantities(scale,dimensions)
    if route:
        for s in route['segments']:
            p=_segment_evidence(evidence,'conditions',s,checks,ids)
            if p:
                for field in ('posting_checked','closure_checked','lane_and_detour_checked','escort_checked'):
                    _check(checks,s['segment_id']+'_'+field,True if p[field] else None,'Explicit authority observation must cover this condition category.')
                _check(checks,s['segment_id']+'_operating_status',{'open':True,'closed':False,'restricted':None,'unknown':None}[p['status']],
                       'Restricted status requires a reviewed restriction-specific evaluation; a claimed condition checkbox cannot override it.')
                _check(checks,s['segment_id']+'_operating_conditions',p['conditions_satisfied'],'Unknown operating conditions cannot become permission.')
                for field,limit in p['posted_limits'].items():
                    _measure(checks,s['segment_id']+'_current_posting_'+field,q.get(field),limit)
    return _result(checks,ids,['Observations apply only to their explicit validity intervals; no freshness duration is invented.',
                              'Archived Port Street bulletins never establish current conditions. No live road-authority feed is connected.'])


EVALUATORS={'axle_weight_evidence':axle_weight,'dimensions_and_route':dimensions_route,
            'permit_eligibility':permit_eligibility,'cross_authority_coverage':cross_authority,
            'current_route_conditions':route_conditions}

def evaluate_road(requirement_id,facts,evidence,trip_at):
    return EVALUATORS[requirement_id](evidence,facts,trip_at)
