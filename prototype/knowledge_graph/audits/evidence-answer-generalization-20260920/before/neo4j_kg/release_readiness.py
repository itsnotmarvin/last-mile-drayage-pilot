"""Evidence-bound engineering readiness report; cannot authorize a production launch."""
import hashlib
import json
import re
from pathlib import Path

from .common import ROOT, ArchiveError, digest, verify_files
from .source_review import source_inventory
from .requirements import applicable_requirements
from .reported_checks import catalog


def runtime_hashes(root=ROOT):
    root = Path(root)
    paths = [p for folder in ('neo4j_kg', 'trip_app') for p in (root/folder).rglob('*')
             if p.suffix in ('.py', '.js', '.css', '.html')]
    paths += [root/'run_neo4j_mcp.py', root/'data/reported_checks.json', root/'data/release_scope.json',
              root/'tools/review_release.py']
    paths += [root / p for p in ('data/source_candidates/2026-09-13/bridge-supplement.json',
                                 'data/source_candidates/2026-09-13/import-availability-supplement.json')]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def verify_capture(directory, current_hashes, graph_release=None):
    """Validate artifact bytes and full current-runtime coverage, never only counts."""
    directory = Path(directory).resolve()
    try:
        manifest = json.loads((directory/'artifact-manifest.json').read_text())
        if manifest.get('algorithm') != 'sha256' or not isinstance(manifest['files'], dict):
            raise ValueError('Invalid manifest structure')
        for name, entry in manifest['files'].items():
            if not isinstance(name, str) or Path(name).is_absolute():
                raise ValueError('Invalid artifact name')
            path = (directory/name).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                raise ValueError('Artifact path is outside capture')
            expected = entry['sha256'] if isinstance(entry, dict) else entry
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Artifact hash mismatch')
            if isinstance(entry, dict) and 'bytes' in entry and path.stat().st_size != entry['bytes']:
                raise ValueError('Artifact size mismatch')
        if 'summary.json' not in manifest['files']:
            raise ValueError('Summary is not bound by the artifact manifest')
        summary = json.loads((directory/'summary.json').read_text())
        recorded = summary['runtime_sha256']
        if not isinstance(recorded, dict) or any(not isinstance(p, str) or not isinstance(h, str)
                                                or not re.fullmatch('[0-9a-f]{64}', h) for p, h in recorded.items()):
            raise ValueError('Invalid runtime hashes')
        missing = sorted(set(current_hashes) - set(recorded))
        removed = sorted(set(recorded) - set(current_hashes))
        changed = sorted(p for p in current_hashes if p in recorded and current_hashes[p] != recorded[p])
        status = 'matches_current_runtime' if not missing and not changed and not removed else 'stale_for_current_runtime'
        release_binding = ('not_checked' if graph_release is None else
                           'passed' if summary.get('graph_release') == graph_release else 'failed')
        if status == 'matches_current_runtime' and release_binding == 'failed':
            status = 'stale_for_current_release'
        return {'status': status, 'graph_release_binding': release_binding,
                'artifact_integrity': 'passed', 'missing_runtime_paths': missing,
                'changed_runtime_paths': changed, 'removed_runtime_paths': removed,
                'limits': 'Hash equality establishes artifact/implementation binding; it does not authenticate reviewers or prove test adequacy.'}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {'status': 'invalid_capture', 'artifact_integrity': 'failed',
                'missing_runtime_paths': [], 'changed_runtime_paths': [], 'removed_runtime_paths': [],
                'limits': 'Capture is missing, malformed or changed; no passing verification is inferred.'}


def assess_readiness(release, profile, capture=None, root=ROOT, check_source_files=True):
    inventory = source_inventory(release)
    requirements = applicable_requirements({}, 'trip_dispatch')
    required = {r['id'] for r in requirements}
    def exact_list(value, expected):
        return (isinstance(value, list) and all(isinstance(v, str) for v in value)
                and len(value) == len(expected) and set(value) == expected)
    if (not isinstance(profile, dict) or profile.get('schema_version') != 'drayage-first-release-scope-v1'
            or profile.get('approval_status') != 'draft_not_human_approved'
            or not exact_list(profile.get('required_requirement_ids'), required)
            or not exact_list(profile.get('required_families'), {r['family'] for r in requirements})):
        raise ArchiveError('Scope must preserve the complete draft requirement catalog; a narrowed or purportedly approved profile cannot certify this runtime')
    files = 'not_checked'
    if check_source_files:
        try:
            verify_files(release)
            files = 'passed'
        except (ArchiveError, OSError):
            files = 'failed'
    hashes = runtime_hashes(root)
    capture_status = verify_capture(capture, hashes, release['revision']) if capture else {'status': 'not_supplied'}
    from .verification import REQUIRED_KINDS
    from .road_evaluators import EVALUATORS as ROAD_EVALUATORS
    from .terminal_evaluators import EVALUATORS as TERMINAL_EVALUATORS
    implemented = set(ROAD_EVALUATORS) | set(TERMINAL_EVALUATORS) | {'apm_induction'}
    unimplemented = [r['id'] for r in requirements if r['id'] != 'trip_context' and r['id'] not in implemented]
    # These are facts about this concrete runtime. A JSON checkbox cannot turn
    # synthetic identities, stdlib HTTP or draft source interpretations into a
    # production system. External receipts need separate accountable review.
    blockers = [
        {'id': 'runtime_is_synthetic', 'owner_role': 'engineering',
         'detail': 'The runtime uses synthetic identifiers and local development identity/HTTP. No production-serving mode exists.'},
        {'id': 'draft_policy', 'owner_role': 'domain reviewers',
         'detail': 'Both the scope and reported-check definitions are draft; synthetic induction is not accepted real credential verification.'},
    ]
    if unimplemented:
        blockers.append({'id':'unimplemented_requirement_evaluators','owner_role':'engineering and domain reviewers',
                         'detail':'Implement and validate required evaluators.','requirement_ids':unimplemented})
    blockers += [
        {'id':'bounded_evaluator_coverage','owner_role':'domain reviewers and engineering',
         'detail':'Implemented predicates remain bounded: DTR source conflict, non-Interstate bridge scope, special exceptions, generic transaction/gate release and real issuer integrations are unresolved.'},
        {'id':'draft_supplement_review','owner_role':'source and domain reviewers',
         'detail':'Bridge and import-availability extractions are draft supplements bound to graph-linked archived bytes; they are not approved graph clauses.'}]
    expected_external = {'scope_approval','rule_approval','verification_access','client_acceptance',
                         'production_identity_security','operations_acceptance','release_approval'}
    external = profile.get('external_acceptance_required', [])
    if (not isinstance(external, list) or len(external) != len(expected_external)
            or any(not isinstance(e, dict) or not all(isinstance(e.get(k), str) and e[k].strip()
                   for k in ('id', 'owner_role', 'deliverable')) for e in external)
            or {e['id'] for e in external} != expected_external):
        raise ArchiveError('All external acceptance requirements must remain explicit')
    blockers += [{'id': e['id'], 'owner_role': e['owner_role'], 'detail': e['deliverable']} for e in external]
    if files != 'passed':
        blockers.append({'id': 'source_bytes_unverified', 'owner_role': 'source operator', 'detail': 'Validate all retained source bytes.'})
    if capture_status['status'] != 'matches_current_runtime':
        blockers.append({'id': 'current_runtime_capture_missing', 'owner_role': 'engineering',
                         'detail': 'Capture tests and service behavior against the current runtime, then verify the artifact manifest.'})
    if catalog()['graph_release'] != release['revision']:
        blockers.append({'id': 'reported_catalog_release_mismatch', 'owner_role': 'source reviewer',
                         'detail': 'The reported-check catalog is bound to a different graph release.'})
    if inventory['missing_required_clause_ids'] or inventory['requirements_without_retained_clauses']:
        blockers.append({'id': 'governing_evidence_gaps', 'owner_role': 'domain reviewers',
                         'detail': 'Retain and review the missing governing clauses and their requirement mappings.'})
    return {'schema_version': 'drayage-release-readiness-v1', 'status': 'blocked',
            'operational_permission': 'not_issued', 'production_launch_authorized': False,
            'graph_release': release['revision'], 'scope_sha256': digest(profile),
            'runtime_sha256': hashes, 'source_file_integrity': files,
            'capture_verification': capture_status,
            'required_requirement_ids': [r['id'] for r in requirements],
            'unimplemented_requirement_ids': unimplemented,
            'implemented_bounded_requirement_ids': sorted(set(REQUIRED_KINDS) & implemented),
            'requirements_without_retained_clauses': inventory['requirements_without_retained_clauses'],
            'source_count': len(inventory['sources']), 'blockers': blockers,
            'limits': ['This engineering report is not legal approval, security certification or a production grade.',
                       'Hashes detect changed bytes; they do not prove authenticity against an actor who can replace both artifacts and manifests.',
                       'The current runtime stays synthetic regardless of any submitted approval-like JSON fields.']}
