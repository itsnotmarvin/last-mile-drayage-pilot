"""A compact domain projection: evidence and rule records become attributes.

The complete evidence graph remains unchanged. Derived scope edges retain the
exact two original edges used to traverse authority <- clause -> subject.
"""
import copy
from collections import defaultdict

DOMAIN_KINDS = {'physical_location', 'road_segment', 'authority', 'terminal_operator', 'terminal'}
SCOPE_RELATIONS = {
    'GOVERNS', 'GOVERNS_GATE_MOVE_AT', 'GOVERNS_ACCESS_AT', 'GOVERNS_ENTRY_AT',
    'GOVERNS_PORT_ENTRY_MOVEMENT_AT', 'GOVERNS_UNESCORTED_SECURE_ACCESS_AT',
    'STREET_NOT_LISTED_IN_RESTRICTION_TABLE', 'OVERLAPS_PART_OF',
    'ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C', 'TRUCK_ROUTE_SCHEDULE_RESERVED', 'REQUIRES',
}


def domain_view(archive):
    original = {n['id']: n for n in archive['nodes']}
    retained = {n['id']: copy.deepcopy(n) for n in archive['nodes']
                if n['kind'] in DOMAIN_KINDS or n['id'] == 'credential_cdl'}
    attribution = {e['source']: e for e in archive['edges'] if e['relationship'] == 'ATTRIBUTED_TO_AUTHORITY'}
    all_rules = {n['id']: n for n in archive['nodes'] if n['kind'] == 'source_clause'}
    for node in retained.values():
        node['citations'] = []
        node['requirements'] = []
        source_ids = set(node['record'].get('source_ids', []))
        for key in ['source_id', 'geometry_source_id', 'sequence_source_id']:
            if node['record'].get(key): source_ids.add(node['record'][key])
        source_ids.update(e['target'] for e in archive['edges'] if e['source'] == node['id'] and e['relationship'] == 'CITES_SOURCE')
        node['citations'] = [copy.deepcopy(original[s]) for s in sorted(source_ids) if s in original and original[s]['kind'] == 'source_document']
    for rid, rule in all_rules.items():
        authority = attribution[rid]['target']
        record = copy.deepcopy(rule)
        source = rule['record'].get('source_id')
        record['citation'] = copy.deepcopy(original[source]) if source in original else None
        record['related_details'] = [copy.deepcopy(original[e['target']]) for e in archive['edges']
                                     if e['source'] == rid and e['relationship'] in {'REQUIRES', 'USES', 'CONDITIONS_REGISTRATION_IN'}]
        record['original_relationships'] = [copy.deepcopy(e) for e in archive['edges'] if rid in (e['source'],e['target'])]
        retained[authority]['requirements'].append(record)
    edges = [copy.deepcopy(e) for e in archive['edges'] if e['source'] in retained and e['target'] in retained]
    grouped = defaultdict(list)
    for e in archive['edges']:
        if e['source'] in all_rules and e['target'] in retained and e['relationship'] in SCOPE_RELATIONS:
            a = attribution[e['source']]
            grouped[(a['target'], e['target'])].append({'rule_id': e['source'], 'scope_relation': e['relationship'],
                                                     'evidence_edge_ids': [a['id'], e['id']]})
    for (source,target), records in sorted(grouped.items()):
        edges.append({'id': f'domain-scope:{source}:{target}', 'source': source, 'target': target,
                      'relationship': 'HAS_RECORDED_RULE_SCOPE', 'record': {'derived': True, 'scope_records': records,
                      'meaning': 'Recorded clauses attributed to this authority have these exact relationships to the subject; this is not a jurisdiction or clearance inference.'}})
    if sum(len(n['requirements']) for n in retained.values()) != len(all_rules):
        raise ValueError('A rule was lost while attaching requirements to authorities')
    return {'schema_version': 'drayage-domain-projection-1', 'nodes': list(retained.values()), 'edges': edges,
            'summary': {'node_count': len(retained), 'edge_count': len(edges), 'retained_rule_records': len(all_rules)},
            'scope': 'Physical roads, locations, terminal, authorities and CDL. All archived rule records are attributes; sources are citations. No current clearance is asserted.',
            'not_displayed': [{'id': n['id'], 'kind': n['kind']} for n in archive['nodes'] if n['id'] not in retained],
            'archive_node_count': len(archive['nodes']), 'archive_edge_count': len(archive['edges'])}
