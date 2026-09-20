"""Read-only source inventory and candidate-release impact review.

No import, source promotion, policy approval or credential lookup is performed.
Both releases must pass their content-addressed integrity contract first.
"""
import copy
import json
import re

from .common import ArchiveError, digest, validate_release
from .requirements import applicable_requirements
from .reported_checks import catalog

VERSION = 'drayage-source-review-v1'


def _records(release):
    try:
        if not isinstance(release, dict):
            raise ArchiveError('Expected release object')
        validate_release(release)
        records = {}
        for node in release['nodes']:
            body = json.loads(node['record_json'])
            if not isinstance(body, dict):
                raise ArchiveError('Expected object evidence record')
            if not isinstance(node['id'], str) or not isinstance(node['kind'], str):
                raise ArchiveError('Expected evidence identity and kind')
            if node['kind'] == 'source_document':
                files = body.get('archived_files', [])
                if not isinstance(files, list) or any(
                        not isinstance(f, dict) or not isinstance(f.get('path'), str)
                        or not isinstance(f.get('sha256'), str)
                        or not re.fullmatch('[0-9a-f]{64}', f['sha256']) for f in files):
                    raise ArchiveError('Invalid archived file references')
            if node['kind'] == 'mutable_observation' and not isinstance(body.get('archive_context', {}), dict):
                raise ArchiveError('Invalid observation context')
            records[node['id']] = {**node, 'body': body}
        if not isinstance(release['file_hashes'], dict):
            raise ArchiveError('Expected source file hash map')
        if any(not isinstance(p, str) or not isinstance(h, str)
               or not re.fullmatch('[0-9a-f]{64}', h) for p, h in release['file_hashes'].items()):
            raise ArchiveError('Invalid source file hashes')
        return records
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ArchiveError('Invalid source-review release') from exc


def source_inventory(release):
    records = _records(release)
    requirements = applicable_requirements({}, 'trip_dispatch')
    checks = catalog()['checks']
    sources = []
    for sid, node in sorted(records.items()):
        if node['kind'] != 'source_document':
            continue
        source = node['body']
        clauses = [cid for cid, item in records.items()
                   if item['kind'] == 'source_clause' and item['body'].get('source_id') == sid]
        observations = [oid for oid, item in records.items() if item['kind'] == 'mutable_observation'
                        and item['body'].get('archive_context', {}).get('source_id') == sid]
        reqs = [r['id'] for r in requirements if set(clauses) & set(r['source_clause_ids'])]
        sources.append({
            'source_id': sid, 'title': source.get('title'), 'publisher': source.get('publisher'),
            'url': source.get('url'), 'publication_date': source.get('publication_date'),
            'accessed_date': source.get('accessed_date'),
            'record_sha256': digest(source),
            'archived_files': copy.deepcopy(source.get('archived_files', [])),
            'clause_ids': sorted(clauses), 'observation_ids': sorted(observations),
            'requirement_ids': reqs,
            'reported_check_ids': [c['id'] for c in checks if set(clauses) & set(c['source_clause_ids'])],
            'assigned_reviewer': None, 'review_status': 'pending_human_review',
            'rule_review_trigger': 'Material source change, correction, reported error or applicability question.',
            'operating_context_requirement': ('Obtain suitable current verification for each move; an archived observation is not live status.'
                                              if observations else None)})
    return {'schema_version': VERSION, 'graph_release': release['revision'],
            'operational_use': False, 'sources': sources,
            'requirements_without_retained_clauses': [r['id'] for r in requirements if not r['source_clause_ids']],
            'missing_required_clause_ids': sorted({cid for r in requirements for cid in r['source_clause_ids']
                                                  if cid not in records or records[cid]['kind'] != 'source_clause'}),
            'limits': ['Source inventory is not a completeness or current-law certification.',
                       'Publication dates, access dates, rule versions and operating-condition observations remain distinct.',
                       'No periodic refresh or successful download automatically approves a source.']}


def review_packet(release):
    """Retain complete stored clauses alongside draft mappings for human review."""
    records = _records(release)
    inventory = source_inventory(release)
    return {**inventory, 'packet_status': 'draft_not_human_approved',
            'reported_catalog_matches_release': catalog()['graph_release'] == release['revision'],
            'requirements': applicable_requirements({}, 'trip_dispatch'),
            'reported_check_catalog': catalog(),
            'retained_clauses': [{'clause_id': nid, 'record': copy.deepcopy(n['body'])}
                                 for nid, n in sorted(records.items()) if n['kind'] == 'source_clause'],
            'review_instructions': [
                'Read complete governing sources and exceptions; retained excerpts alone cannot establish completeness.',
                'Review source locators, extraction accuracy, jurisdiction, conflicts and clause-to-requirement mappings.',
                'Define accepted verification evidence and reviewed positive, negative, missing and conflicting cases.',
                'Record reviewer identity, decision, unresolved issues and exact source/check versions outside this draft packet.']}


def compare_releases(baseline, candidate):
    before, after = _records(baseline), _records(candidate)
    requirements = applicable_requirements({}, 'trip_dispatch')
    changed = {nid for nid in set(before) | set(after)
               if before.get(nid) != after.get(nid)}
    bf, cf = baseline['file_hashes'], candidate['file_hashes']
    files = {path for path in set(bf) | set(cf) if bf.get(path) != cf.get(path)}
    old_edges = {e['id']: e for e in baseline['edges']}
    new_edges = {e['id']: e for e in candidate['edges']}
    changed_edges = {eid for eid in set(old_edges) | set(new_edges) if old_edges.get(eid) != new_edges.get(eid)}
    sources, clauses, known_files = set(), set(), set()
    metadata_keys = (set(baseline) | set(candidate)) - {'revision', 'nodes', 'edges', 'file_hashes'}
    metadata_changed = sorted(k for k in metadata_keys if baseline.get(k) != candidate.get(k))
    graph_context = bool(changed_edges) or any(
        {k: v for k, v in before[nid].items() if k not in ('body', 'record_json')}
        != {k: v for k, v in after[nid].items() if k not in ('body', 'record_json')}
        for nid in set(before) & set(after))
    for records in (before, after):
        for nid, node in records.items():
            if node['kind'] == 'source_document':
                paths = {f['path'] for f in node['body'].get('archived_files', [])}
                known_files.update(paths)
                if nid in changed or paths & files:
                    sources.add(nid)
            elif node['kind'] == 'source_clause':
                if nid in changed:
                    clauses.add(nid)
            elif nid in changed:
                graph_context = True
    for records in (before, after):
        clauses.update(nid for nid, n in records.items() if n['kind'] == 'source_clause'
                       and n['body'].get('source_id') in sources)
    # A registry/model/source file without an attributable source can affect
    # the whole release. Never silently conclude that its impact is empty.
    unmapped = files - known_files
    expected_ids = {r['id'] for r in requirements}
    impacted = []
    for req in requirements:
        missing = [cid for cid in req['source_clause_ids']
                   if cid not in after or after[cid]['kind'] != 'source_clause']
        reasons = []
        if set(req['source_clause_ids']) & clauses:
            reasons.append('SUPPORTING_SOURCE_OR_CLAUSE_CHANGED')
        if graph_context:
            reasons.append('GRAPH_CONTEXT_OR_RELATIONSHIP_CHANGED')
        if metadata_changed:
            reasons.append('RELEASE_METADATA_CHANGED_REQUIRES_FULL_REVIEW')
        if unmapped:
            reasons.append('UNATTRIBUTED_FILE_CHANGE_REQUIRES_FULL_REVIEW')
        if missing:
            reasons.append('REQUIRED_CLAUSE_MISSING_IN_CANDIDATE')
        if reasons:
            impacted.append({'requirement_id': req['id'], 'reason_codes': reasons,
                             'missing_clause_ids': missing, 'review_owner_role': req['owner'],
                             'review_status': 'pending_human_review'})
    released_changed = baseline['revision'] != candidate['revision']
    impacted_ids = {r['requirement_id'] for r in impacted}
    assert impacted_ids <= expected_ids
    return {'schema_version': VERSION, 'baseline_release': baseline['revision'],
            'candidate_release': candidate['revision'],
            'status': 'review_required' if released_changed or impacted else 'no_change',
            'operational_use': False, 'automatic_activation': False,
            'changed_record_ids': sorted(changed), 'changed_source_ids': sorted(sources),
            'changed_clause_ids': sorted(clauses), 'changed_file_paths': sorted(files),
            'changed_relationship_ids': sorted(changed_edges), 'unattributed_file_paths': sorted(unmapped),
            'changed_release_metadata_keys': metadata_changed,
            'graph_context_changed': graph_context, 'affected_requirements': impacted,
            'affected_reported_check_ids': [c['id'] for c in catalog()['checks'] if c['requirement_id'] in impacted_ids],
            'required_actions': ([
                'Review complete source text, applicability, exceptions and mappings for every affected requirement.',
                'Bind reviewed check definitions and acceptance evidence to the candidate release.',
                'Verify the candidate import and rollback procedure before any authorized activation.'
            ] if released_changed or impacted else []),
            'limits': ['A no-change comparison establishes equality of the supplied releases, not current law.',
                       'Graph-context or unattributed file changes deliberately require broad review.',
                       'This command never changes Neo4j, source files, connector configuration or operational permission.']}
