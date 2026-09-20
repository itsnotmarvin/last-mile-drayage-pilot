"""Service-owned explanation claims; source text never becomes trip permission."""

BOUNDARIES = [
    'Use the scoped result, not schedule pressure, to explain this assessment. No operational permission is issued.',
    'Unresolved must be expressed as: Permission has not been established. This is not permission to proceed, and it is also not a finding that the trip is illegal. Never say, or imply, that nothing prevents dispatch — including phrasings like "none of this means you can\'t go".',
    'Reported values above a retained reference are comparisons, not established violations; values at or below it are not clearance.',
    'Do not choose a required permit type or declare an approval unnecessary from a dimension alone. Applicability and exceptions remain separate.',
    'A rough route can identify follow-up questions; only the required complete route and verification evidence can resolve route checks.',
    'Historical bulletins are unknown for this trip. Never describe them as active/current from an effective date or until-further-notice wording.',
    'Do not invent probability rankings, registry checks, enforcement outcomes, or reconciliation of conflicting tariff clauses.',
    'Preserve reported, user-confirmed, synthetically verified, and real-authority-verified evidence as distinct categories.',
]


def answer_guidance(assessment):
    """Keep qualification adjacent to every comparison and historical reference.

    The full assessment retains original source text for inspection. This
    projection does not quote historical detour commands as current advice.
    """
    available = assessment['service_status'] == 'available'
    checks = assessment.get('reported_fact_checks', {}).get('checks', []) if available else []
    comparisons = [{
        'check_id': c['check_id'], 'requirement_id': c['requirement_id'],
        'status': c['status'], 'comparison': c['comparison'],
        'statement': c['summary'], 'qualification': c['context'],
        'next_action': c['next_action'], 'source_clause_ids': c['source_clause_ids'],
        'claim_type': 'reported_fact_comparison_not_legal_finding',
    } for c in checks if c['comparison'] is not None]
    history = [{
        'condition_id': o['condition_id'], 'source_id': o['source_id'],
        'archived_at': o['record'].get('archive_context', {}).get('observed_at'),
        'current_status': 'unknown_for_this_trip',
        'statement': 'An archived operating bulletin is retained for source review. Its restrictions have not been verified for this trip.',
        'next_action': 'Confirm route membership and obtain current conditions from the responsible authority before treating this bulletin as applicable.',
    } for o in assessment['evidence_package']['observations']] if available else []
    return {
        'schema_version': 'drayage-answer-guidance-v1',
        'assessment_id': assessment['assessment_id'],
        'trip_id': assessment['case']['trip_id'], 'revision': assessment['case']['revision'],
        'service_status': assessment['service_status'],
        'opening': assessment['decision_brief']['summary'],
        'operational_permission': 'not_issued',
        'reported_comparisons': comparisons,
        'open_requirements': [{
            'requirement_id': f['requirement_id'], 'label': f['label'],
            'status': f['status'], 'missing_fields': f['missing_fields'],
            'reason_codes': f['reason_codes'], 'limits': f['limits'],
        } for f in assessment['findings'] if f['status'] == 'unresolved'] if available else [],
        'historical_context': history,
        'next_questions': assessment['next_questions'] if available else [],
        'boundaries': BOUNDARIES.copy(),
    }


def explanation_package(assessment):
    """Model-facing projection; the application retains the complete assessment.

    Exact numeric source passages remain available beside IDs and scope notes.
    Raw mutable bulletin instructions are intentionally confined to the full
    evidence record, while the projection explicitly reports their existence.
    """
    guidance = answer_guidance(assessment)
    ids = {cid for c in guidance['reported_comparisons'] for cid in c['source_clause_ids']}
    return {
        'assessment_id': assessment['assessment_id'], 'versions': assessment['versions'],
        'service_status': assessment['service_status'],
        'decision_brief': assessment['decision_brief'], 'answer_guidance': guidance,
        'findings': assessment['findings'], 'coverage': assessment['coverage'],
        'reported_fact_checks': assessment['reported_fact_checks'],
        'comparison_sources': [s for s in assessment['evidence_package']['sources'] if s['clause_id'] in ids],
        'evidence_limits': assessment['evidence_package']['limits'],
        'limits': ['This is an explanation projection of the saved assessment, not a complete source archive.',
                   'Original source passages and historical bulletins remain in the application evidence view.',
                   'User confirmation records the reported facts; it does not authenticate credentials or measurements.'],
    }
