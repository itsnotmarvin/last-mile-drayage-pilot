"""Draft extractions tied to source documents read from the pinned Neo4j graph.

These do not change the graph or promote clauses. They disclose the additional
archived passages used by draft evaluators while retaining approval boundaries.
"""
import hashlib
import json
from .common import ROOT, ARCHIVE, ArchiveError, digest

PATHS = ('data/source_candidates/2026-09-13/bridge-supplement.json',
         'data/source_candidates/2026-09-13/import-availability-supplement.json')
FIELDS = {'id','requirement_ids','source_id','source_file_path','source_file_sha256',
          'locator','source_text','interpretation_boundary'}
RELEASE = 'f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c'
TOP_FIELDS = {'schema_version', 'graph_release', 'approval_status', 'operational_use', 'entries'}
# Pin the exact draft interpretation consumed by this engine. These hashes are
# change detection, not human approval or proof of the document's authenticity.
# A source-text or mapping change requires a deliberate evaluator revision.
ENTRY_HASHES = {
    'draft_nj_bridge_equation': '94773156c6d3dcd70920b625a5f0a591c0156f0245ad21115fd3f40934c6a2bc',
    'draft_nj_bridge_w_definition': 'fbff835a718fb75e8c76df27b527921dc338bedddd5eaca541f20d8f787a0770',
    'draft_nj_bridge_l_definition': 'e691ab907d70eb40f3c3d79ca6fd90ae441190cc58ea137c71cb071e038a65db',
    'draft_nj_bridge_n_definition': '1d16159faf2387687603e08aede74c214b6545cdc89bfa5442c424e483aed20c',
    'draft_nj_bridge_group_coverage': '1ae13b87cefbdfaf4b8455ba346195fb535cffa8ccc6f411b38e2ffc1d37496f',
    'draft_nj_single_axle_definition': '4e716c0254da46bdd5bf262396536bc30723f2f0fa462572b17da471478f785d',
    'draft_nj_tandem_limit': '4085829d1f6e396c79f80c3073dadc7eed6f569ae074dbae617a2caf1ff706ab',
    'draft_nj_gross_limit': '8bdb01dc43d068c0024d55ab8a24048e1bd783b9002e6daee0aeb5b7fe8688a4',
    'draft_nj_bridge_may_lower_caps': 'bc46c5a27fb84f3eb898100a768eb8df941c388666783d77a526842f41ef34fd',
    'draft_nj_two_tandem_exception': 'abd05966a0fc72d676df50edef5fe3fccddc1f7ba8ebbe4749994f87788319b1',
    'draft_nj_bridge_interstate_scope': '12065dbd002ea6fc53df3a7b073624856418c0ee6a2cde51c366fee7f7e801c8',
    'draft_import_no_holds': 'a0ac09d1550b121aa1f3c31abad3aa4fe0272b192f35a2aa37333f0ab790f153',
    'draft_import_available': '3ba39d9578ef00eed9809363cce0eccf582eefaacaf7b7191725959db66c9ce0',
}
REQUIRED_SUPPLEMENTS = {
    'axle_weight_evidence': tuple(k for k in ENTRY_HASHES if k.startswith('draft_nj_')),
    'transaction_release': ('draft_import_no_holds', 'draft_import_available'),
}


def source_coverage_gaps(requirement, package, release):
    """Check delivered evidence before publishing a bounded factual conclusion."""
    sources = {s['clause_id'] for s in package['sources'] if s.get('source_text')}
    missing = [cid for cid in requirement['source_clause_ids'] if cid not in sources]
    delivered = {}
    for entry in package['draft_supplements']:
        if not isinstance(entry, dict):
            continue
        eid = entry.get('id')
        if (isinstance(eid, str) and eid in ENTRY_HASHES
                and FIELDS <= set(entry)
                and digest({k: entry[k] for k in FIELDS}) == ENTRY_HASHES[eid]
                and entry.get('graph_release') == release == RELEASE
                and entry.get('approval_status') == 'draft_not_human_approved'
                and entry.get('archive_graph_membership') is False
                and entry.get('operational_use') is False):
            delivered[eid] = delivered.get(eid, 0) + 1
    missing += [eid for eid in REQUIRED_SUPPLEMENTS.get(requirement['id'], ())
                if delivered.get(eid) != 1]
    return missing


def draft_supplements(evaluation, requirement_ids):
    selected=set(requirement_ids)
    entries=[]
    for relative in PATHS:
        try:
            raw=json.loads((ROOT/relative).read_text())
            if (not isinstance(raw, dict) or set(raw) != TOP_FIELDS
                    or raw['schema_version']!='drayage-draft-source-supplement-v1'
                    or raw['graph_release']!=evaluation.versions['graph_release']
                    or raw['graph_release'] != RELEASE
                    or raw['approval_status']!='draft_not_human_approved'
                    or raw['operational_use'] is not False or not isinstance(raw['entries'],list)):
                raise ArchiveError('Draft supplement release/approval contract mismatch')
            for entry in raw['entries']:
                if (not isinstance(entry, dict) or set(entry)!=FIELDS
                        or not isinstance(entry['id'], str)
                        or not isinstance(entry['requirement_ids'],list)
                        or any(not isinstance(rid, str) for rid in entry['requirement_ids'])
                        or digest(entry) != ENTRY_HASHES.get(entry['id'])):
                    raise ArchiveError('Draft supplement entry contract mismatch')
                if not selected.intersection(entry['requirement_ids']):
                    continue
                source=evaluation.reader.record(entry['source_id'])
                matched=[f for f in source['archived_files'] if f['path']==entry['source_file_path']
                         and f['sha256']==entry['source_file_sha256']]
                path=(ARCHIVE/entry['source_file_path']).resolve()
                if (not matched or not path.is_relative_to(ARCHIVE.resolve()) or not path.is_file()
                        or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['source_file_sha256']):
                    raise ArchiveError('Draft extraction no longer matches graph-linked source bytes')
                if any(not isinstance(entry[k],str) or not entry[k].strip() for k in FIELDS-{'requirement_ids'}):
                    raise ArchiveError('Invalid draft extraction text')
                entries.append({**entry,'publisher':source['publisher'],'title':source['title'],
                                'url':source['url'],'publication_date':source.get('publication_date'),
                                'accessed_date':source.get('accessed_date'),
                                'graph_release':raw['graph_release'], 'supplement_sha256':digest(raw),
                                'approval_status':'draft_not_human_approved',
                                'extraction_status':'prototype_extraction_only',
                                'archive_graph_membership':False,'operational_use':False})
        except (OSError,KeyError,TypeError,ValueError) as exc:
            raise ArchiveError('Draft source supplement is unavailable or invalid') from exc
    if len({e['id'] for e in entries})!=len(entries):
        raise ArchiveError('Duplicate draft extraction identity')
    required = {eid for rid in selected for eid in REQUIRED_SUPPLEMENTS.get(rid, ())}
    if required - {entry['id'] for entry in entries}:
        raise ArchiveError('Required draft source extraction is missing')
    return entries
