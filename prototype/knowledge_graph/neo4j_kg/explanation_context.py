"""Select explanations from existing requirements, never infer legal eligibility.

Text hints rank topics only. They do not extract measurements, grant approvals,
select a route, or replace missing structured facts. Unmapped reports stay quoted
and unverified. This module contains no experiment IDs or frozen prompt matches.
"""
import re
from html import escape

from .driver_brief import retained_text
from .common import digest
from .reported_checks import catalog


# Additional bindings for explanation-only passages in the same reviewed release.
# These bind presentation, not new legal evaluators or promoted source records.
_CATALOG = catalog()
_BINDINGS = _CATALOG["source_bindings"] | {'reg_nj_access_network_600_series': {'source_id': 'njac_16_32_truck_access_current_2023',
                                      'locator': 'PDF page 3, N.J.A.C. 16:32-1.4(a)(3); PDF page '
                                                 '9, Appendix C',
                                      'source_text_sha256': '0932863281ac23784a11926aa029b45209ee32d66bdc9249623f0d37a5214003'},
 'reg_nj_terminal_access_102_inch_standard_truck': {'source_id': 'njac_16_32_truck_access_current_2023',
                                                    'locator': 'PDF pages 3-4, N.J.A.C. '
                                                               '16:32-1.5(a)(2)',
                                                    'source_text_sha256': '446c8d56aae43f92e5504945a2fc177405aa2b4b6261a17843fff5a27b37dad9'},
 'reg_nj_toll_authority_approval_13_18_portal_copy': {'source_id': 'njac_13_18_osow_portal_copy_2026_08_24',
                                                      'locator': 'PDF page 5, N.J.A.C. '
                                                                 '13:18-1.9(a)(2)',
                                                      'source_text_sha256': 'bf1bb235bf12c481375da48589e10a2b71b054627fa7ed5193886ac3eb976ec0'}}

TOPICS = {
    'permit': (r'permit|approv|authorit|covered|coverage',
               ('permit_type', 'permit_route_reported', 'turnpike_approval_reported',
                'local_approval_reported', 'port_approval_reported', 'terminal_approval_reported'),
               ('permit_eligibility', 'cross_authority_coverage')),
    'access': (r'route|local|appendix|road|width|height|length|dimension',
               ('width', 'height', 'overall_length', 'semitrailer_length', 'route_description', 'route_id'),
               ('dimensions_and_route',)),
    'weight': (r'weigh|axle|bridge|spacing|scale',
               ('gross_weight', 'axle_count', 'axle_layout', 'axle_weights', 'axle_spacings'),
               ('axle_weight_evidence',)),
}
APPROVALS = {
    'permit_route_reported': 'permit coverage of this exact route',
    'turnpike_approval_reported': 'toll-road approval',
    'local_approval_reported': 'county/local approval',
    'port_approval_reported': 'Port Authority approval',
    'terminal_approval_reported': 'terminal handling approval',
}
PERMITS = {'nj_ocean_container_annual': 'NJ annual ocean-container permit',
           'nj_single_trip': 'NJ single-trip permit', 'none': 'no permit reported',
           'other': 'another permit type'}


def value(a, field):
    return a['case']['facts'].get(field, {}).get('value')


def source_statement(case):
    """Current statement; never merge earlier statements across corrections."""
    if 'source_message' in case:
        return case['source_message']
    records = list(case.get('facts', {}).values())
    return max(records, key=lambda r: r.get('recorded_at', ''), default={}).get('source_text', '')


def literal(text):
    """Keep caller-supplied prose inert, including Markdown links/directives."""
    text = escape(str(text), quote=False)
    return re.sub(r'([\\`*_\[\]{}()#!|>])', r'\\\1', text).replace('\n', ' ')


def topics(a):
    text = source_statement(a['case']).lower()
    # Questions rank the explanation; surrounding reports still select topics.
    questions = ' '.join(s for s in re.split(r'(?<=[.!?])\s+', text) if '?' in s)
    selected = {f['requirement_id'] for f in a['findings']}
    ranked = []
    for position, (topic, (pattern, fields, requirements)) in enumerate(TOPICS.items()):
        if not selected.intersection(requirements):
            continue
        score = 3 * bool(re.search(pattern, questions)) + bool(re.search(pattern, text))
        score += any(value(a, field) is not None for field in fields)
        if score:
            ranked.append((-score, position, topic))
    return [r[2] for r in sorted(ranked)] or (['access', 'weight', 'permit'] if selected else [])


def reported_context(a):
    """Preserve reports without converting prose into verified structured facts."""
    lines = []
    facts = a['case']['facts']
    compared = {c['comparison']['field'] for c in a['reported_fact_checks']['checks']
                if c.get('comparison') is not None}
    for field in ('gross_weight', 'width', 'height', 'overall_length', 'semitrailer_length'):
        record = facts.get(field)
        if record and record['value'] is not None and field not in compared:
            lines.append('Reported ' + field.replace('_', ' ') + ': ' + literal(record['value'])
                         + (' ' + record['unit'] if record.get('unit') else '')
                         + '; retained as a report, without a supported comparison in this assessment.')
    if value(a, 'permit_type') is not None:
        lines.append('Permit reported: ' + PERMITS[value(a, 'permit_type')] + '.')
    for field in ('axle_count', 'axle_weights', 'axle_spacings', 'load_divisible',
                  'container_sealed', 'trip_at'):
        record = facts.get(field)
        if record and record['value'] is not None:
            label = ('Unclassified reported weight values (not individual-axle measurements)'
                     if field == 'axle_weights' else field.replace('_', ' ').capitalize() + ' reported')
            lines.append(label + ': ' + literal(record['value']) + (' ' + record['unit'] if record.get('unit') else '') + '.')
    for field, label in APPROVALS.items():
        if value(a, field) is not None:
            lines.append(label[0].upper() + label[1:] + ': reported ' + ('held' if value(a, field) else 'not held') + '.')
    # Retain unstructured context as a quotation only. No invented individual
    # axle layout, date/time, per-credential status or measurement is admitted.
    text = source_statement(a['case'])
    patterns = [
        (r'\b(?:axle|tandem|spacing|steer)\b', ('axle_weights', 'axle_layout')),
        (r'(?:driver|credential|appointment).{0,90}(?:satisfied|verified|complete|valid)',
         ('twic_reported', 'sealink_registered_reported', 'induction_reported')),
        (r'(?:legal|within).{0,35}(?:width|height|length|dimension|weight)|(?:dimension|weight).{0,35}(?:legal|within)',
         ('width', 'height', 'semitrailer_length')),
        (r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d|\b\d{4}-\d{2}-\d{2}\b',
         ('trip_at',)),
    ]
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        if any(re.search(pattern, sentence, re.I) and any(value(a, f) is None for f in fields)
               for pattern, fields in patterns):
            if sentence.strip():
                lines.append('Additional reported context, not independently verified or fully structured: “'
                             + literal(sentence.strip()) + '”')
    return list(dict.fromkeys(lines))


def source_links(a, ids):
    if (a['evidence_package']['status'] != 'available'
            or a['versions'].get('graph_release') != _CATALOG['graph_release']):
        return None
    sources = {s['clause_id']: s for s in a['evidence_package']['sources']}
    for cid in ids:
        source, expected = sources.get(cid), _BINDINGS.get(cid)
        if (source is None or expected is None
                or source.get('source_id') != expected['source_id']
                or source.get('locator') != expected['locator']
                or digest(source.get('source_text')) != expected['source_text_sha256']):
            return None
    grouped = {}
    for cid in ids:
        s = sources[cid]
        locator = (s.get('provenance_review') or {}).get('recommended_locator', s['locator'])
        entry = grouped.setdefault(s['url'], {'title': s['title'], 'locators': []})
        if locator not in entry['locators']:
            entry['locators'].append(locator)
    return '; '.join(f"[{entry['title']}, {'; '.join(entry['locators'])}]({url})"
                     for url, entry in grouped.items())


def rule_explanations(a):
    """Explanations exist even when no numerical comparison can be executed."""
    out = {}
    selected = set(topics(a))
    if 'access' in selected:
        ids = ['reg_nj_access_network_600_series', 'reg_nj_terminal_access_102_inch_standard_truck',
               'reg_nj_truck_access_local_rule_preservation']
        refs = source_links(a, ids)
        if refs:
            out['access'] = ('**Route access still needs an answer when dimensions are missing.** '
                + refs + ': Appendix C identifies listed county roads in the access network. '
                'The separate terminal-access provision concerns a **102-inch-wide standard truck**, '
                '**unrestricted local roadways**, necessary terminal access and the **direct route**. '
                'It requires return to the National Network or New Jersey Access Network by the direct route, '
                'unless continued use of the unrestricted local roadway is the direct route to the next terminal '
                'on such a roadway; it also describes direct access between the two networks. '
                'Absence from the network list alone establishes neither permission nor prohibition. '
                'Obtain the missing loaded dimensions and confirm the actual road sequence, vehicle category, '
                'direct terminal access and current local restrictions; a stored route cannot establish those conditions.')
            if value(a, 'width') is not None:
                # The numeric width block already quotes the complete access
                # provision. Keep network/local-preservation evidence without
                # repeating its entire explanation.
                refs = source_links(a, ['reg_nj_access_network_600_series',
                                       'reg_nj_truck_access_local_rule_preservation'])
                out['access'] = ('**Network listing and local restrictions.** ' + refs
                    + ': absence from Appendix C alone establishes neither permission nor prohibition. '
                    'The separate direct terminal-access provision below requires unrestricted local roadways; '
                    'current local restrictions and the actual route remain unconfirmed.')
    if 'weight' in selected:
        refs = source_links(a, ['reg_federal_interstate_weight', 'reg_nj_tandem_gross_bridge'])
        if refs:
            out['weight'] = ('**Axle and bridge checks remain separate.** ' + refs
                + ': obtain individual axle weights and spacings and establish the roadway regime and applicable permit limits. '
                'Gross weight, axle count and group totals cannot complete that check or establish release.')
    if 'permit' in selected:
        typ = value(a, 'permit_type')
        cid = ('reg_nj_ocean_container_permit' if typ == 'nj_ocean_container_annual'
               else 'reg_nj_single_trip_osow_permit')
        refs = source_links(a, [cid])
        if refs:
            source = next(s for s in a['evidence_package']['sources'] if s['clause_id'] == cid)
            out['permit'] = ('**What the reported permit can establish.** ' + refs + ': '
                + (('Retained transcription (including a linearized table): “'
                      if (source.get('provenance_review') or {}).get('quotation_form') == 'prose_and_linearized_table'
                      or source.get('verbatim') is not True else 'The retained permit provision says: “')
                   + retained_text(source['source_text']) + '” '
                   if typ is not None and typ != 'none' else
                   'The retained single-trip provision concerns a non-divisible load above legal size or weight limits. ')
                + 'These are source conditions, not a determination that this move qualifies. '
                'Check the actual permit terms, vehicle/load eligibility, dates and approved route. '
                'Unknown divisibility or permit status remains unknown.')
        ids = ['reg_nj_toll_authority_approval_13_18_portal_copy',
               'reg_njta_roadway_use_limitations', 'reg_nj_truck_access_local_rule_preservation',
               'reg_panynj_terminal_weight_dimensions']
        refs = source_links(a, ids)
        if refs:
            out['authorities'] = ('**The authorities have separate responsibilities.** ' + refs
                + ': a reported NJ permit does not establish every other authority’s authorization. '
                'For the actual route, verify state permit coverage and any applicable toll-road, county/local, '
                'Port Authority and terminal requirements with the responsible authority. '
                'Port Authority Marine Terminals approval and terminal handling acceptance are distinct; '
                'neither is established by booking a police escort. Inclusion here does not mean every approval '
                'is required for every trip. The retained NJPASS toll-approval copy has not been independently '
                'checked against the current official code. A reported approval is not independent verification.')
    # Relevance ranking only; these retained reference values do not establish
    # applicability, permission, or an independently verified measurement.
    if 'access' in selected and ((value(a, 'width') or 0) > 132 or (value(a, 'height') or 0) > 195):
        refs = source_links(a, ['reg_panynj_terminal_weight_dimensions'])
        if refs:
            source = next(s for s in a['evidence_package']['sources']
                          if s['clause_id'] == 'reg_panynj_terminal_weight_dimensions')
            out['terminal_dimensions'] = ('**Marine-terminal size and weight provisions.** ' + refs + ': “'
                + retained_text(source['source_text']) + '” This retained provision does not establish '
                'that the assigned terminal has accepted the load or that connecting roads are authorized.')
    return out


def archived_conditions(a):
    if value(a, 'port_street_in_route') is not True:
        return []
    lines = []
    for observation in a['evidence_package']['observations']:
        record = observation['record']
        observed = record.get('archive_context', {}).get('observed_at', observation['accessed_date'])
        lines.append('**Archived operating context, not current directions.** [' + observation['title']
                     + '](' + observation['url'] + '), ' + str(record.get('source_locator', 'retained observation'))
                     + ', observed ' + str(observed) + ': the retained record concerns '
                     + str(record.get('label', 'operating conditions')) + '. '
                     'The current lane, detour and escort instructions are not verified for this trip. '
                     'Recheck the notice and permit route with the responsible road authority and police; '
                     'verify Port Authority authorization and terminal handling acceptance separately.')
    return lines


def next_actions(a):
    actions = []
    for topic in topics(a):
        if topic == 'permit':
            actions.append('Review the permit’s vehicle/load, dates and approved route; establish which separate road, '
                           'Port Authority and terminal approvals apply, and verify them individually.')
        elif topic == 'access':
            actions.append('Supply any missing loaded dimensions; confirm the actual route, direct terminal access '
                           'and current restrictions with the responsible road authorities.')
        elif topic == 'weight':
            actions.append('Obtain any missing individual axle weights and spacings; check the applicable '
                           'axle, group, bridge and permit limits for the actual route.')
    if not actions:
        actions = a['decision_brief']['next_steps']
    return actions[:3]
