"""Presentation-only topic arrangement and connected view of archived evidence."""
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
EXCLUDED_SOURCE = 'panynj_facilities_map_2020'


def connected_view(data):
    result = copy.deepcopy(data)
    if any(EXCLUDED_SOURCE in (e['source'], e['target']) for e in result['edges']):
        raise ValueError('Facilities map now has relationships; review its exclusion before exporting.')
    result['nodes'] = [n for n in result['nodes'] if n['id'] != EXCLUDED_SOURCE]
    result['summary']['node_count'] = len(result['nodes'])
    endpoints = {n for e in result['edges'] for n in (e['source'], e['target'])}
    result['summary']['isolated_node_count'] = sum(n['id'] not in endpoints for n in result['nodes'])
    result.pop('connectivity_audit', None)
    result['archive_audit_file'] = 'connectivity-audit.json'
    kinds = {}
    for node in result['nodes']:
        kinds[node['kind']] = kinds.get(node['kind'], 0) + 1
    result['summary']['node_kinds'] = kinds
    result['scope'] = 'Connected evidence graph; the unlinked 2020 facilities map remains in the source inventory and archive export.'
    result['view_exclusions'] = [{'node_id': EXCLUDED_SOURCE, 'reason': 'Archived reference — not currently linked'}]
    result['presentation'] = json.loads((ROOT / 'presentation' / 'topics.json').read_text())
    ids = [n for topic in result['presentation']['topics'] for n in topic['nodes']]
    if len(ids) != len(set(ids)) or set(ids) != {n['id'] for n in result['nodes']}:
        raise ValueError('Topic arrangement must contain each visible node exactly once.')
    return result


def topic_layout(data):
    """Use authored within-topic coordinates; headers are annotations, not nodes."""
    saved = json.loads((ROOT / 'presentation' / 'organized-layout.json').read_text())
    from graph_presentation import topology_key
    if saved['topology_key'] != topology_key(data):
        raise ValueError('Organized layout is stale for this graph.')
    expected_topics = data['presentation']['topics']
    actual_topics = [{k:region[k] for k in topic} for region,topic in zip(saved['regions'],expected_topics)]
    if len(saved['regions']) != len(expected_topics) or actual_topics != expected_topics:
        raise ValueError('Organized layout is stale for this topic arrangement.')
    if set(saved['positions']) != {n['id'] for n in data['nodes']}:
        raise ValueError('Organized layout does not preserve visible node membership.')
    if any(len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in saved['positions'].values()):
        raise ValueError('Invalid organized coordinates.')
    return saved
