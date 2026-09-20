"""Small follow-up answer from a fresh saved-trip assessment.

The full assessment is preserved in the local MCP audit, while the consumer
receives the relevant dated observations and supported comparisons directly.
No fact, scope, requirement result or source is changed by this projection.
"""


def conditions_answer(assessment):
    if assessment['service_status'] != 'available':
        return ('The evidence service is unavailable. Your saved trip facts remain intact, '
                'but I cannot recheck the sources or reuse the previous findings. '
                'Retry this saved trip. No operational permission is issued.')
    evidence = assessment['evidence_package']
    case = assessment['case']
    if (case['question_scope'] not in ('route', 'trip_dispatch', 'terminal_entry')
            or case['facts'].get('terminal_id', {}).get('value') != 'facility_apm_elizabeth'
            or any(f['requirement_id'] == 'current_route_conditions' and f['status'] in ('met', 'not_met')
                   for f in assessment['findings'])):
        # The compact archived-page explanation must not suppress an admitted
        # operator condition result or turn a narrow/other-terminal check into APM.
        from .driver_brief import driver_brief
        return driver_brief(assessment)
    terminal = evidence.get('current_terminal_status')
    sections = [
        '**The supplied sources do not establish that the roads or APM gate are open at your arrival.** '
        'They also do not establish that either is closed. Here is what the dates support.',
    ]
    if terminal and terminal['status'] == 'available':
        pages = {s['page']: s for s in terminal['sources']}

        def page_link(key, label):
            return f"[{label}]({pages[key]['url']})"

        sections.append(f"These {len(pages)} APM pages were retrieved at {terminal['retrieved_at']}. "
                        'Retrieval time dates the fetch, not verification of the contents or '
                        'their effective time. This reassessment does not establish a live public-road check.')
        if 'status_update' in pages:
            link = page_link('status_update', 'APM status update')
            if terminal.get('latest_notice_heading'):
                sections.append(link + ' contains the heading **“' + terminal['latest_notice_heading']
                                + '”**. It is a schedule heading. It does not date a separate closure excerpt.')
            if terminal.get('closure_notice_text'):
                sections.append(link + ' also contains this separate, unverified closure excerpt: **“'
                                + terminal['closure_notice_text'] + '”**. Its own stated date must '
                                'be kept separate from the schedule heading and retrieval time; '
                                'it does not establish conditions at this trip’s arrival.')
        if 'row_closures' in pages and terminal.get('row_closures_text'):
            effective = terminal.get('row_closures_effective')
            sections.append(page_link('row_closures', 'APM row closures')
                            + ': row-closure text is present; its effective time is '
                            + (str(effective) if effective else '**not stated**')
                            + '. These are terminal rows, not public-road closures.')
        if 'gate_info' in pages:
            sections.append(page_link('gate_info', 'APM gate and truck turn-time page')
                            + ': this observation supplies no verified gate-open finding for your arrival. '
                            'A link to a camera or turn-time widget is not an open/closed result.')
    else:
        sections.append('No usable current terminal-page observation is available in this assessment. '
                        'The retained route and size references do not verify current road or gate conditions.')

    sources = {s['clause_id']: s for s in evidence['sources']}
    checks = {c['check_id']: c for c in assessment['reported_fact_checks']['checks']}
    useful = []
    for check_id in ('nj_loaded_height', 'federal_gross_80000'):
        row = checks.get(check_id)
        if not row or row['comparison'] is None:
            continue
        refs = row['source_clause_ids']
        if not refs or not all(cid in sources for cid in refs):
            continue
        c = row['comparison']
        links = []
        for cid in refs:
            source = sources[cid]
            note = source.get('provenance_review') or {}
            locator = note.get('recommended_locator', source['locator'])
            links.append(f"[{source['title']} — {locator}]({source['url']})")
        units = 'inches' if c['unit'] == 'inch' else 'lb'
        useful.append('; '.join(links) + ': your reported ' + c['field'].replace('_', ' ')
                      + f" is {c['reported']:g} {units}, {c['relation']} the cited {c['reference']:g} {units} reference. "
                      + row['context'])
    if useful:
        sections.append('**Useful findings remain:**\n\n' + '\n\n'.join(useful)
                        + '\n\nThese are source comparisons, not route-specific physical clearance '
                        'or a completed axle/bridge assessment. Missing current conditions do not erase them.')
    sections.append('The next checks are current road conditions on your exact segments and APM gate/appointment '
                    'conditions for your arrival. Existing route, axle/load, permit and credential gaps remain '
                    'separate. This synthetic assessment does not issue operational permission.')
    return '\n\n'.join(sections)
