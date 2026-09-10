"""Auditable exploration relationships, separate from the frozen check service.

Only explicit archive reference fields are resolved. No label matching, inferred
legal applicability, or synthetic hierarchy is used to improve connectivity.
"""
import copy
import hashlib
import json
from pathlib import Path

import networkx as nx

from kg.graph import ARCHIVE, INPUTS, KnowledgeGraph, digest

TRAFFIC_INPUT = 'data/processed/traffic_analysis.json'
SOURCE_FIELDS = {
    'source_id', 'source_ids', 'geometry_source_id', 'sequence_source_id',
    'sequence_source_ids', 'gate_observation_source_id', 'primary_source_id',
    'corroborating_source_ids', 'evidence_source_ids',
}
ENTITY_FIELDS = {
    'authority_entity_id': ('ATTRIBUTED_TO_AUTHORITY', {'authority', 'terminal_operator'}),
    'terminal_entity_id': ('GATE_OF_TERMINAL', {'terminal'}),
    'operator_entity_id': ('RECORDED_OPERATOR', {'terminal_operator'}),
}


def leaves(value, pointer=''):
    """Yield leaf values with their exact RFC 6901 pointer and owning field."""
    if isinstance(value, dict):
        for field, child in value.items():
            path = pointer + '/' + field.replace('~', '~0').replace('/', '~1')
            if isinstance(child, list):
                for i, item in enumerate(child):
                    if isinstance(item, (dict, list)):
                        yield from leaves(item, path + '/' + str(i))
                    else:
                        yield field, path + '/' + str(i), item
            elif isinstance(child, dict):
                yield from leaves(child, path)
            else:
                yield field, path, child


class EvidenceGraph(KnowledgeGraph):
    def __init__(self, archive=ARCHIVE):
        super().__init__(archive)
        self.base_evidence_version = self.evidence_version
        self.original_isolates = sorted(nx.isolates(self.graph))
        self.graph = copy.deepcopy(nx.MultiDiGraph(self.graph))
        self.origins = {}
        for relative, array, key in [
            (INPUTS[0], 'sources', 'source_id'), (INPUTS[1], 'entities', 'entity_id'),
            (INPUTS[2], 'rules', 'rule_id'), (INPUTS[5], 'edges', 'edge_id'),
            (INPUTS[5], 'paths', 'path_id'), (INPUTS[5], 'approaches', 'approach_id'),
            (INPUTS[7], 'profiles', 'profile_id'),
        ]:
            for i, record in enumerate(self.documents[relative][array]):
                self.origins[record[key]] = (relative, f'/{array}/{i}')
        for i, feature in enumerate(self.documents[INPUTS[4]]['features']):
            self.origins[feature['properties']['node_id']] = (INPUTS[4], f'/features/{i}')
        raw = self._path(TRAFFIC_INPUT).read_bytes()
        self.input_hashes[TRAFFIC_INPUT] = hashlib.sha256(raw).hexdigest()
        self.documents[TRAFFIC_INPUT] = json.loads(raw)
        self._node('historical_north_avenue_traffic_analysis', 'historical_traffic_analysis',
                   self.documents[TRAFFIC_INPUT], layer='retained_analysis')
        self.origins['historical_north_avenue_traffic_analysis'] = (TRAFFIC_INPUT, '')
        self.unresolved_references = []
        for node, (relative, origin) in sorted(self.origins.items()):
            for field, pointer, target in leaves(self.record(node)):
                relation = None
                expected = None
                if field in SOURCE_FIELDS:
                    relation, expected = 'CITES_SOURCE', {'source_document'}
                    # Source IDs on registry records identify the record itself.
                    if target == node:
                        continue
                elif field in ENTITY_FIELDS:
                    relation, expected = ENTITY_FIELDS[field]
                elif field == 'rule_id' and pointer.startswith('/rule_interactions/'):
                    relation, expected = 'HAS_RECORDED_RULE_INTERACTION', {'source_clause'}
                if relation:
                    self._reference(node, target, relation, relative, origin + pointer, expected)
        # Only source provenance is permitted for quarantined observations.
        for i, condition in enumerate(self.documents[INPUTS[8]]['conditions']):
            self._reference(condition['condition_id'], self.documents[INPUTS[8]]['source_id'],
                            'OBSERVED_IN_SOURCE', INPUTS[8], '/source_id', {'source_document'})
        self.enrichment_version = digest({
            'inputs': self.input_hashes,
            'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        })
        self.evidence_version = self.enrichment_version
        nx.freeze(self.graph)

    def _reference(self, node, target, relation, relative, pointer, expected):
        if not isinstance(target, str) or target not in self.graph or self.graph.nodes[target]['kind'] not in expected:
            self.unresolved_references.append({'node': node, 'target': target,
                                               'input': relative, 'pointer': pointer})
            return
        # A clause already has its document's CONTAINS_CLAUSE relationship.
        if relation == 'CITES_SOURCE' and any(
            a['relationship'] == 'CONTAINS_CLAUSE'
            for a in self.graph.get_edge_data(target, node, default={}).values()
        ):
            return
        edge_id = 'reference:' + digest([node, target, relation])[:24]
        evidence = {'input': relative, 'pointer': pointer, 'value': target}
        if self.graph.has_edge(node, target, edge_id):
            self.graph[node][target][edge_id]['record']['evidence'].append(evidence)
            return
        self._edge(edge_id, node, relation, target, {
            'layer': 'explicit_archive_references', 'evidence': [evidence],
            'meaning': {
                'CITES_SOURCE': 'The retained record explicitly cites this source; not independent verification.',
                'ATTRIBUTED_TO_AUTHORITY': 'The retained clause names this authority or operator.',
                'GATE_OF_TERMINAL': 'The retained gate record explicitly identifies this terminal.',
                'RECORDED_OPERATOR': 'The retained gate record explicitly identifies this operator.',
                'HAS_RECORDED_RULE_INTERACTION': 'The representative profile records a rule interaction; not a compliance result.',
                'OBSERVED_IN_SOURCE': 'The quarantined observation comes from this dated archived source; no restriction is activated.',
            }[relation],
            'operational_use': False,
        })

    def audit(self):
        isolated = sorted(nx.isolates(self.graph))
        rows = []
        for node in self.original_isolates:
            links = [{"id": key, "from": s, "to": t, **copy.deepcopy(attrs)}
                     for s, t, key, attrs in self.graph.edges(keys=True, data=True)
                     if node in (s, t)]
            rows.append({'node': node, 'connected': bool(links), 'relationships': links,
                         'remaining_gap': None if links else
                         'No explicit reference in the imported records links this source to a graph subject. '
                         'Its geometry-only use limit does not identify a modeled corridor; no edge was guessed.'})
        return {'before_isolated_count': len(self.original_isolates),
                'after_isolated_count': len(isolated), 'isolated_nodes': isolated,
                'weak_component_sizes': sorted(map(len, nx.weakly_connected_components(self.graph)), reverse=True),
                'unresolved_references': copy.deepcopy(self.unresolved_references), 'records': rows}

    def summary(self):
        return {**super().summary(), 'base_evidence_version': self.base_evidence_version,
                'graph_scope': 'archive_with_explicit_references_and_retained_historical_analysis',
                'isolated_node_count': len(list(nx.isolates(self.graph))),
                'checking_service_uses_this_enrichment': False}
