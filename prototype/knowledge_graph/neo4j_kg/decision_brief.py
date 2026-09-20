"""Deterministic presentation boundary; no model-written permission is accepted."""

from html import escape
import json


def decision_brief(assessment):
    case = assessment['case']
    unavailable = assessment['service_status'] != 'available'
    issues = assessment['input_review']['issues']
    headline = ('Assessment unavailable' if unavailable else
                'Trip facts need correction' if issues else 'Trip clearance is not established')
    summary = ('The saved trip could not be assessed. No earlier result is reused.' if unavailable else
               'The saved facts conflict with their source text. Correct them before relying on any scoped finding.' if issues else
               'This service has not established permission to dispatch, use a route, or enter a terminal.')
    steps = [i['message'] for i in issues] if issues else [q['question'] for q in assessment['next_questions']]
    if not unavailable and not issues:
        actions = [a['action'] for a in assessment.get('reported_fact_checks',{}).get('priority_actions',[])]
        steps = list(dict.fromkeys(actions + steps))[:3]
    return {
        'schema_version': 'drayage-decision-brief-v1',
        'trip_id': case['trip_id'], 'revision': case['revision'],
        'assessment_id': assessment['assessment_id'],
        'status': 'assessment_unavailable' if unavailable else 'input_correction_required' if issues else 'not_cleared',
        'headline': headline, 'summary': summary,
        'operational_permission': 'not_issued',
        'scope': case['question_scope'],
        'scoped_result': assessment['requested_scope_status'],
        'fact_confirmation': 'not_independently_confirmed',
        'next_steps': steps,
        'limits': [
            'Synthetic development assessment; this is not a finding that the trip is illegal.',
            'A met or not-applicable finding applies only to its stated synthetic subcheck; unresolved requirements remain unresolved.',
            'An exported report is a snapshot; reassess the saved trip after corrections or before using a later revision.',
        ],
    }


def render_reported_checks(assessment):
    """Inert presentation of service-produced comparisons and retained limits."""
    package = assessment.get('reported_fact_checks')
    if package is None:
        return ''
    esc = lambda value: escape(str(value), quote=True)
    if package['status'] != 'available':
        return '<h2>Reported-fact comparisons unavailable</h2><p>No prior comparison is reused. The evidence or its source mapping needs review.</p>'
    if not package['checks']:
        return ''
    sources = {source['clause_id']:source for source in assessment['evidence_package']['sources']}
    parts = ['<h2>What the reported facts show</h2><p>Draft source comparisons. A value at or below a reference does not establish eligibility or permission.</p>']
    order = {'input_review_required':0,'source_review_required':1,'attention_required':2,
             'comparison_only':3,'reported_unverified':4,'manual_review_required':5,'missing_facts':6}
    for check in sorted(package['checks'], key=lambda c:order[c['status']]):
        supporting = []
        for cid in check['source_clause_ids']:
            source = sources.get(cid)
            if source:
                note = source.get('provenance_review')
                locator = note['recommended_locator'] if note else source['locator']
                supporting.append(source['title'] + ' — ' + locator)
        parts.append('<details' + (' open' if check['status'] in ('attention_required','input_review_required','source_review_required') else '')
                     + '><summary>' + esc(check['title']) + ' · ' + esc(check['status'].replace('_',' '))
                     + '</summary><p>' + esc(check['summary']) + '</p><p>' + esc(check['context'])
                     + '</p><p>Next action (' + esc(check['owner']) + '): ' + esc(check['next_action'])
                     + '</p><p>Supporting source: ' + esc('; '.join(supporting) or 'No retained governing clause') + '</p></details>')
    return ''.join(parts)


def render_trip_report(assessment):
    """Render a fresh service result as inert HTML, never arbitrary assistant prose.

    Callers obtain the assessment from TripService. This renderer is not an
    authenticity verifier for externally supplied JSON. It rebuilds the brief
    instead of trusting a caller-provided headline, status, or assistant answer.
    """
    brief = decision_brief(assessment)
    esc = lambda value: escape(str(value), quote=True)
    items = lambda values: '<ul>' + ''.join('<li>' + esc(v) + '</li>' for v in values) + '</ul>'
    rows = []
    for field, fact in sorted(assessment['case']['facts'].items()):
        value = 'Unknown' if fact['value'] is None else json.dumps(fact['value'], ensure_ascii=False)
        rows.append('<tr><th>' + esc(field.replace('_', ' ')) + '</th><td>' + esc(value)
                    + (' ' + esc(fact['unit']) if fact.get('unit') else '') + '</td><td>Reported; unconfirmed</td></tr>')
    findings = []
    for finding in assessment['findings']:
        findings.append('<tr><th>' + esc(finding['label']) + '</th><td>' + esc(finding['status'])
                        + '</td><td>' + esc(finding['execution_state']) + '</td></tr>')
    citations = []
    for source in assessment['evidence_package']['sources']:
        note = source.get('provenance_review')
        locator = note['recommended_locator'] if note else source['locator']
        citations.append('<details><summary>' + esc(source['title']) + ' — ' + esc(locator)
                         + '</summary><p>' + esc(source['publisher']) + ' · ' + esc(source['currentness'])
                         + '</p><p>Source: ' + esc(source['url'])
                         + '</p><p>Published: ' + esc(source['publication_date']) + ' · Accessed: ' + esc(source['accessed_date'])
                         + '</p><pre>' + esc(json.dumps(source['source_text'], ensure_ascii=False, indent=2))
                         + '</pre>' + ('<p>' + esc(note['note']) + '</p>' if note else '') + '</details>')
    for supplement in assessment['evidence_package'].get('draft_supplements', []):
        citations.append('<details><summary>Draft source supplement · ' + esc(supplement['title']) + ' · '
            + esc(supplement['locator']) + '</summary><pre>' + esc(supplement['source_text'])
            + '</pre><p>' + esc(supplement['interpretation_boundary'])
            + '</p><p>Draft extraction; not an approved canonical graph clause.</p></details>')
    for finding in assessment['findings']:
        if finding.get('checks'):
            citations.append('<details><summary>' + esc(finding['label']) + ' · predicate details</summary>'
                + items([c['status'] + ': ' + c['detail'] for c in finding['checks']])
                + items(finding['limits']) + '</details>')
    observations = []
    for observation in assessment['evidence_package']['observations']:
        observations.append('<details><summary>Dated operating observation — currentness unverified</summary><pre>'
                            + esc(json.dumps(observation['record'], ensure_ascii=False, indent=2)) + '</pre></details>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Trip assessment record</title><style>
body{font:17px/1.5 system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 24px;color:#17232c;background:#f7f8fa}
header{border-left:6px solid #956200;background:#fff4d7;padding:20px}h1{margin:0 0 12px;font-size:2rem}
table{border-collapse:collapse;width:100%;background:white}th,td{text-align:left;padding:10px;border-bottom:1px solid #d8dfe4}
pre{white-space:pre-wrap;overflow-wrap:anywhere}details{padding:12px;background:white;margin:8px 0}small{overflow-wrap:anywhere}
</style><main><header><p>Synthetic trip assessment · saved snapshot</p><h1>''' + esc(brief['headline']) + '</h1><p>' + esc(brief['summary']) + '''</p>
<p>Operational permission: not issued.</p></header><h2>Next steps</h2>''' + items(brief['next_steps']) + '''
<h2>Review the reported facts</h2><p>These values have not been independently confirmed against the original conversation.
Confirmation of a report is separate from verification of the underlying evidence.</p><table><tr><th>Fact</th><th>Recorded value</th><th>Basis</th></tr>''' + ''.join(rows) + '''</table>
''' + render_reported_checks(assessment) + '''
<h2>Scoped findings</h2><p>A scoped synthetic result does not establish whole-trip clearance.</p>
<table><tr><th>Requirement</th><th>Result</th><th>Evaluation coverage</th></tr>''' + ''.join(findings) + '''</table>
<h2>Evidence and its limits</h2>''' + ''.join(citations + observations) + items(assessment['coverage']['gaps']) + items(brief['limits']) + '''
<h2>Record identity</h2><small>Trip: ''' + esc(brief['trip_id']) + ' · Revision: ' + esc(brief['revision']) + '<br>Assessment: ' + esc(brief['assessment_id']) + '''</small></main></html>'''
