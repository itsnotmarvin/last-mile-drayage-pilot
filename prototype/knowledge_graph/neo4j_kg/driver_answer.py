"""Source-linked driver prose derived from existing checks, never new policy.

The model receives this short answer before the detailed briefing and full JSON.
Comparisons, qualifications, source references and next actions come from the
same assessment. No missing fact is inferred and no rule outcome is changed.
"""
from .driver_brief import driver_brief, retained_text
from .explanation_context import literal, next_actions, reported_context, rule_explanations, topics


def driver_answer(assessment):
    case = assessment['case']
    if (case['question_scope'] not in ('route', 'trip_dispatch')
            or case['facts'].get('terminal_id', {}).get('value') != 'facility_apm_elizabeth'):
        return driver_brief(assessment)
    intro = ('DRIVER EVIDENCE BRIEFING — prepared answer.\n'
             'Present the answer between the markers faithfully, including its links and '
             'qualifications. Do not add legal conclusions, permit advice, dates or guesses. '
             'For a correction, this is the updated answer; describe the change only using '
             'the current comparison. The second text block contains the detailed source '
             'briefing; the final text block and structuredContent preserve the full assessment.\n\n'
             'BEGIN DRIVER ANSWER\n\n')
    if assessment['service_status'] != 'available':
        return intro + ('Your trip facts were saved, but the evidence service is unavailable. '
                        'I cannot provide an assessment or reuse the previous findings. '
                        'Retry this saved trip to obtain a fresh assessment.\n\nEND DRIVER ANSWER')
    evidence = assessment['evidence_package']
    sources = {s['clause_id']: s for s in evidence['sources']}
    checks = {c['check_id']: c for c in assessment['reported_fact_checks']['checks']}
    route = evidence.get('route_context')
    roads = (' → '.join(s['name'] or s['segment_id'] for s in route['segments'])
             if route and route['status'] == 'resolved_from_pinned_graph'
             else 'the route you described (no supported stored sequence resolved)')
    paragraphs = [
        '**The supplied evidence does not establish that this truck can take this route to APM.** '
        'That is an incomplete assessment, not a finding that the trip is illegal. '
        'Here is what your reported truck facts show, and what still determines the answer.',
        '**Stored candidate route:** ' + roads + '. Confirm whether every segment belongs to your actual trip. '
        'This is the stored route description, '
        'not a legal route designation or a measurement of physical clearance.',
    ]
    if case['facts'].get('route_description', {}).get('value'):
        paragraphs.append('**Reported approach:** ' + literal(case['facts']['route_description']['value']))
    reports = reported_context(assessment)
    if reports:
        paragraphs.append('**Reported context, not independently verified.** ' + ' '.join(reports))
    explanations = rule_explanations(assessment)
    for topic in topics(assessment):
        if topic in explanations:
            paragraphs.append(explanations[topic])
        if topic == 'permit' and 'authorities' in explanations:
            paragraphs.append(explanations['authorities'])
    issues = assessment['input_review']['issues']
    if issues:
        paragraphs.append('**Facts needing correction:** ' + ' '.join(i['message'] for i in issues))
    conflicts = case['conflicts']
    if conflicts:
        paragraphs.append('**Conflicting reports:** ' + ', '.join(c['field'].replace('_', ' ') for c in conflicts)
                          + '. Resolve these before using the affected comparisons.')

    def citation(clause_id):
        s = sources[clause_id]
        note = s.get('provenance_review') or {}
        return f"[{s['title']}]({s['url']}), {note.get('recommended_locator', s['locator'])}"

    def group(title, ids, extra_clause=None):
        rows = [checks[i] for i in ids if i in checks and checks[i]['comparison'] is not None]
        if not rows:
            return
        lines = []
        cids = []
        contexts = []
        for row in rows:
            c = row['comparison']
            unit = 'inches' if c['unit'] == 'inch' else 'lb'
            subject = c['field'].replace('_', ' ')
            difference = (f" ({c['difference']:g} {unit} {c['relation']})" if c['relation'] != 'at' else '')
            lines.append(f"Your reported {subject} is {c['reported']:g} {unit}, "
                         f"{c['relation']} the cited {c['reference']:g} {unit} reference{difference}.")
            contexts.append(row['context'])
            cids += row['source_clause_ids']
        lines += list(dict.fromkeys(contexts))
        if extra_clause in sources:
            s = sources[extra_clause]
            if extra_clause == 'reg_nj_terminal_access_102_inch_standard_truck':
                lines.append('The access provision is specifically for a **102-inch-wide standard truck**, '
                             '**unrestricted local roadways** and the **direct route**; '
                             'those qualifications are not confirmed for this truck and route.')
            lines.append('The retained access provision says: “' + retained_text(s['source_text']) + '” '
                         'Whether your truck and route meet those conditions has not been established.')
            cids.append(extra_clause)
        refs = list(dict.fromkeys(cids))
        if not all(cid in sources for cid in refs):
            return  # Do not emit an unsupported comparison if a source binding is absent.
        paragraphs.append('**' + title + '** ' + '; '.join(citation(cid) for cid in refs)
                          + '. ' + ' '.join(lines))

    group('Loaded height.', ['nj_loaded_height'])
    group('Width and local access.', ['nj_width_102', 'nj_width_96'],
          'reg_nj_terminal_access_102_inch_standard_truck')
    group('Semitrailer length.', ['nj_semitrailer_53', 'nj_semitrailer_48_access'],
          'reg_nj_semitrailer_length')
    group('Gross weight.', ['federal_gross_80000', 'nj_gross_80000'])

    prerequisites = []
    for check_id in ('twic_report', 'sealink_report', 'appointment_report'):
        c = checks.get(check_id)
        if c and c['status'] in ('reported_unverified', 'attention_required'):
            refs = c['source_clause_ids']
            if all(cid in sources for cid in refs):
                prerequisites.append(c['title'] + ': ' + c['summary'] + ' ' + c['context']
                                     + ' Source: ' + '; '.join(citation(cid) for cid in refs) + '.')
    if prerequisites:
        paragraphs.append('**Credentials and appointment.** ' + ' '.join(prerequisites))

    terminal = evidence.get('current_terminal_status')
    condition_lines = [
        'The stored route and legal size references do not establish that the roads are '
        'physically clear or the gate is open at your arrival. No verified live public-road '
        'conditions are established by these source comparisons.']
    if terminal and terminal['status'] == 'available':
        condition_lines.append(f"APM pages were retrieved at {terminal['retrieved_at']}. "
                               'Retrieval time does not establish when their contents apply.')
        if terminal.get('latest_notice_heading'):
            condition_lines.append('The schedule heading is “' + terminal['latest_notice_heading']
                                   + '”. It does not date a separate closure excerpt.')
        if terminal.get('closure_notice_text'):
            condition_lines.append('A separate, unverified excerpt says: “' + terminal['closure_notice_text']
                                   + '” That excerpt does not establish conditions at your trip time.')
        if terminal.get('row_closures_text'):
            condition_lines.append('Terminal row-closure text is also present. Its effective time is '
                                   + (str(terminal['row_closures_effective']) if terminal.get('row_closures_effective')
                                      else 'not stated') + '; terminal rows are not public-road closures.')
        condition_lines.append('Sources: ' + '; '.join(
            f"[APM {s['page'].replace('_', ' ')}]({s['url']})" for s in terminal['sources']) + '.')
    else:
        condition_lines.append('No usable current terminal-page observation is available in this assessment.')
    condition_lines.append('Current road/gate checks and trip-specific route, axle/load, permit and '
                           'credential evidence remain separate from these comparisons. '
                           'Being at a cited reference does not establish permission to proceed.')
    paragraphs.append('**What this means for the trip.** ' + ' '.join(condition_lines))
    steps = next_actions(assessment)
    if steps:
        paragraphs.append('**Next steps:**\n' + '\n'.join(f'{i}. {s}' for i, s in enumerate(steps, 1)))
    paragraphs.append('These next steps are not an exhaustive release checklist; unresolved requirements remain unresolved. '
                      'This local synthetic assessment uses retained sources, not a promise of the latest '
                      'law or policy, and does not issue operational permission.')
    return intro + '\n\n'.join(paragraphs) + '\n\nEND DRIVER ANSWER'
