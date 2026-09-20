"""Compact complete-move delivery; the existing service owns every check/write."""
from .driver_brief import driver_brief, retained_text
from .service import InputError


PRESENTATION = ('Display answer_markdown verbatim as your answer, with its Markdown source links. '
                'It is already the prepared driver-facing explanation. Do not summarize or rewrite '
                'its rule passages: configuration, standard-truck, network, return and exception '
                'conditions are consequential. You may add one brief sentence acknowledging an '
                'explicit correction before it. Do not expose the internal trip_id, revision or '
                'assessment_id. Do not add a separate legal conclusion.')


def assess_move(service, arguments):
    """Discriminate operations before delegation; never let a move lose scope."""
    if not isinstance(arguments, dict):
        raise InputError('Expected a complete-move operation')
    action = arguments.get('action')
    common = {'facts', 'source_message', 'request_key', 'requester_role'}
    required = {'create': common - {'requester_role'},
                'update': common | {'trip_id', 'expected_revision'},
                'read': {'trip_id'}}
    if not isinstance(action, str) or action not in required:
        raise InputError('action must be create, update or read')
    allowed = required[action] | ({'replace_conflicts'} if action == 'update' else set())
    if action == 'create':
        allowed |= {'requester_role'}
    args = {k: v for k, v in arguments.items() if k != 'action'}
    if required[action] - args.keys() or args.keys() - allowed:
        raise InputError('Missing required or unexpected complete-move arguments; scope is always trip_dispatch')
    if action in ('update', 'read'):
        saved = service.trip_store.get(args['trip_id'])
        if saved['question_scope'] != 'trip_dispatch':
            raise InputError('This saved case has a narrow scope; use its original trip tools')
    if action == 'read':
        return service.assess(args)
    args['question_scope'] = 'trip_dispatch'
    return service.update(args) if action == 'update' else service.assess(args)


def move_answer(a):
    """Source comparisons for APM; exceptional findings retain the full briefing."""
    if a['service_status'] != 'available':
        return ('Your trip facts are saved, but the evidence service is unavailable. '
                'I cannot reuse previous findings. Retry this saved trip for a fresh assessment. '
                'No operational permission is issued.')
    case = a['case']
    if (case['question_scope'] != 'trip_dispatch'
            or case['facts'].get('terminal_id', {}).get('value') != 'facility_apm_elizabeth'
            or case['conflicts'] or a['input_review']['issues']
            or any(f['status'] != 'unresolved' for f in a['findings'])):
        return driver_brief(a)
    sources = {s['clause_id']: s for s in a['evidence_package']['sources']}
    checks = {c['check_id']: c for c in a['reported_fact_checks']['checks']}

    def cite(cid, label):
        s = sources[cid]
        locator = (s.get('provenance_review') or {}).get('recommended_locator', s['locator'])
        return f"[{label}, {locator}]({s['url']})"

    def comparison(key):
        row = checks.get(key)
        if not row or row['comparison'] is None or not all(cid in sources for cid in row['source_clause_ids']):
            return None
        c = row['comparison']
        unit = 'in' if c['unit'] == 'inch' else 'lb'
        return f"Reported {c['field'].replace('_', ' ')}: {c['reported']:g} {unit}, {c['relation']} the {c['reference']:g} {unit} reference."

    parts = ['**The supplied evidence does not establish that this truck can make this move to APM.** '
             'This is an incomplete assessment, not a finding that the trip is illegal. '
             'The truck comparisons below remain useful; none is permission to proceed.']
    route = a['evidence_package'].get('route_context')
    if route and route['status'] == 'resolved_from_pinned_graph':
        parts.append('**Your route:** ' + ' → '.join(s['name'] or s['segment_id'] for s in route['segments'])
                     + '. This stored sequence is not a legal designation or measured clearance; '
                     'road names and ownership do not establish the applicable rule.')
    else:
        parts.append('No supported stored route sequence resolved; exact roads remain to be established.')
    height = comparison('nj_loaded_height')
    if height:
        parts.append('**Loaded height.** ' + height + ' '
                     + cite('reg_nj_height_limit', 'NJ size/weight guide') + ': '
                     + checks['nj_loaded_height']['context'])
    width = comparison('nj_width_102')
    if width and 'reg_nj_terminal_access_102_inch_standard_truck' in sources:
        parts.append('**Width: the standard-truck qualification matters.** ' + width + ' '
                     + cite('reg_nj_width_limit', 'NJ size/weight guide')
                     + ' also has a separate 96-inch road category; this trip’s category is unconfirmed. '
                     + cite('reg_nj_terminal_access_102_inch_standard_truck', 'NJ truck-access rule')
                     + ' applies specifically to a **102-inch-wide standard truck**, not every truck of that width. '
                     + 'Its retained conditions are: “'
                     + retained_text(sources['reg_nj_terminal_access_102_inch_standard_truck']['source_text'])
                     + '” Whether this truck and these roads qualify is unresolved.')
    length = comparison('nj_semitrailer_53')
    if length:
        parts.append('**Semitrailer length and access.** ' + length + ' '
                     + cite('reg_nj_semitrailer_length', 'NJ size/weight guide') + ': “'
                     + retained_text(sources['reg_nj_semitrailer_length']['source_text'])
                     + '” Configuration, applicable network and direct-access conditions remain unconfirmed.')
    weight = comparison('federal_gross_80000')
    if weight:
        parts.append('**Gross weight.** ' + weight + ' '
                     + cite('reg_federal_interstate_weight', '23 CFR 658.17') + ': '
                     + checks['federal_gross_80000']['context']
                     + ' This comparison does not complete the axle/bridge assessment.')
    creds = []
    for key, label in (('twic_report', 'TWIC'), ('sealink_report', 'SeaLink'), ('appointment_report', 'Appointment')):
        row = checks.get(key)
        if row and all(cid in sources for cid in row['source_clause_ids']):
            # Use each report's actual status, including missing/negative reports.
            cid = row['source_clause_ids'][0]
            creds.append(cite(cid, label) + ': ' + row['summary'] + ' ' + row['context'])
    if creds:
        parts.append('**Terminal prerequisites.** ' + ' '.join(creds))
    terminal = a['evidence_package'].get('current_terminal_status')
    if terminal and terminal['status'] == 'available':
        pages = {s['page']: s for s in terminal['sources']}
        conditions = [f"Fetched {terminal['retrieved_at']}; fetch time is not the effective date or verification."]
        if 'status_update' in pages:
            conditions.append(f"[APM status update]({pages['status_update']['url']}): schedule heading “"
                              + str(terminal.get('latest_notice_heading') or 'not supplied') + '”; separate unverified closure excerpt “'
                              + str(terminal.get('closure_notice_text') or 'not supplied')
                              + '”. The heading does not date that closure or establish arrival-time conditions.')
        if 'row_closures' in pages:
            conditions.append(f"[APM row closures]({pages['row_closures']['url']}): effective time "
                              + str(terminal.get('row_closures_effective') or 'not stated')
                              + '; terminal rows are not public-road closures.')
        if 'gate_info' in pages:
            conditions.append(f"[APM gate/turn times]({pages['gate_info']['url']}): no verified gate-open finding for arrival.")
        parts.append('**Roads and gate at arrival.** ' + ' '.join(conditions))
    else:
        parts.append('**Roads and gate at arrival.** No usable current terminal-page observation is available.')
    parts.append('Current road/gate conditions are not established. Permit/authority coverage, axle/load, '
                 'DTR/RFID, induction and transaction/release checks remain unresolved; missing facts do not mean absent credentials or permits. '
                 'A reported credential is not verified status. Exact road applicability, postings, permits and exceptions remain open.')
    steps = a['decision_brief']['next_steps'][:3]
    if steps:
        parts.append('**Next checks:**\n' + '\n'.join('- ' + s for s in steps))
    parts.append('Synthetic assessment using retained sources; not a promise of latest policy. No operational permission is issued.')
    return '\n\n'.join(parts)
