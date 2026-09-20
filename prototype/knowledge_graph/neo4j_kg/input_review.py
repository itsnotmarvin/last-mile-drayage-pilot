"""Bounded checks of reported values against caller-supplied source text.

This is not general language understanding or authenticated transcript capture.
Recognized contradictions require clarification; absence of a detected problem
never marks extraction or a reported fact as verified.
"""
from decimal import Decimal
import re

from .service import InputError
from .axle_layout import review_layout

NUMBER = r"\d+(?:\.\d+)?"
FEET = r"(?:feet\b|foot\b|ft\b|['′])"
INCHES = r'(?:inches\b|inch\b|in\b|["″])'
MEASURE = rf"{NUMBER}\s*[- ]?\s*(?:{FEET}(?:\s*[- ]?\s*{NUMBER}\s*[- ]?\s*{INCHES})?|{INCHES})"
LABELS = {"height": r"height|high|tall", "width": r"width|wide",
          "overall_length": r"overall length", "semitrailer_length": r"semitrailer length"}
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}\b", re.I)
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(?:am|pm)\b|\b(?:noon|midnight)\b", re.I)
ZONE = re.compile(r"(?:T\d{2}:\d{2}:\d{2}Z\b|[+-]\d{2}:\d{2}\b|\b(?:UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT)\b|America/[A-Za-z_]+)", re.I)
APPROVAL_TERMS = {
    "permit_route_reported": r"permit route|permit coverage",
    "turnpike_approval_reported": r"turnpike approval|toll[- ]road approval",
    "local_approval_reported": r"local approval|county approval",
    "port_approval_reported": r"port authority approval|port approval",
    "terminal_approval_reported": r"terminal.{0,15}approval",
}
UNCERTAIN = re.compile(r"\bunknown\b|\bunverified\b|\bnot (?:yet )?(?:checked|confirmed|verified)\b", re.I)


def _inches(text):
    match = re.fullmatch(rf"({NUMBER})\s*[- ]?\s*({FEET}|{INCHES})(?:\s*[- ]?\s*({NUMBER})\s*[- ]?\s*{INCHES})?", text, re.I)
    if not match:
        return None
    amount, unit, remainder = match.groups()
    feet = re.fullmatch(FEET, unit, re.I) is not None
    return Decimal(amount) * (12 if feet else 1) + Decimal(remainder or '0')


def _dimensions(text, field):
    label = LABELS[field]
    patterns = [rf"(?<![\w.])(?P<quantity>{MEASURE})\s*[- ]?\s*(?:{label})\b",
                rf"\b(?:{label})\s*(?:(?:is|of)\s+|[:=]\s*)?(?P<quantity>{MEASURE})(?![\w])"]
    values = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            value = _inches(match['quantity'])
            if value is not None:
                values.add(value)
    return values


def consistency_issues(facts):
    """Inspect normalized records, including old saved records, without changing them."""
    issues = []
    for field, record in sorted(facts.items()):
        value = record.get('value')
        if value is None:
            continue
        text = record.get('source_text', '')
        code, message = None, None
        if field in LABELS:
            candidates = _dimensions(text, field)
            if len(candidates) > 1:
                code = 'AMBIGUOUS_DIMENSION_TEXT'
                message = 'Several labeled measurements occur in the statement; clarify the current loaded measurement.'
            elif candidates and abs(next(iter(candidates)) - Decimal(str(value))) > Decimal('0.00001'):
                code = 'DIMENSION_TEXT_MISMATCH'
                message = 'The extracted measurement differs from the labeled source measurement; preserve both feet and inches.'
        elif field in ('trip_at', 'route_conditions_checked_at') and DATE.search(text):
            if not CLOCK.search(text):
                code = 'DATE_ONLY_EXPANDED_TO_TIMESTAMP'
                message = 'The statement includes a date without a time; leave the timestamp unknown and ask for the missing time and timezone.'
            elif not ZONE.search(text):
                code = 'TIMEZONE_NOT_SUPPORTED_BY_TEXT'
                message = 'The statement does not supply a recognized explicit timezone; clarify it before assigning a timestamp.'
        elif field in APPROVAL_TERMS:
            for sentence in re.split(r'[.!?;\n]', text):
                # A positive possession report may explicitly be unverified.
                # That remains a report; lack of verification alone contradicts
                # neither possession nor the reporter's claim. It cannot support
                # an inferred absence, and explicit "unknown" supports neither.
                uncertain = re.search(r'\bunknown\b', sentence, re.I) or (value is False and UNCERTAIN.search(sentence))
                if re.search(APPROVAL_TERMS[field], sentence, re.I) and uncertain:
                    code = 'UNKNOWN_APPROVAL_REPORTED_AS_BOOLEAN'
                    message = 'Unknown approval status cannot become a boolean, and lack of verification does not establish absence; clarify the report.'
                    break
        elif field == 'permit_type' and value == 'none':
            if re.search(r'permit (?:status|need) (?:is )?unknown|(?:do i|do we|does (?:this|it)) need (?:an? )?(?:\w+ )?permit', text, re.I):
                code = 'PERMIT_QUESTION_REPORTED_AS_ABSENCE'
                message = 'A question about permit need does not establish that no permit is held.'
        if code:
            issues.append({'field': field, 'code': code, 'message': message})
    return issues + review_layout(facts)['issues']


def reject_inconsistent_facts(facts):
    issues = consistency_issues(facts)
    if issues:
        details = '; '.join(f"{i['field']}: {i['code']}. {i['message']}" for i in issues)
        raise InputError('Trip facts were not saved. Clarify inconsistent extraction. ' + details)


def input_review(case):
    facts = case['facts']
    issues = consistency_issues(facts)
    layout = review_layout(facts, case.get('conflicts', ()))
    issues += [i for i in layout['issues'] if i not in issues]
    return {
        'schema_version': 'drayage-input-review-v1',
        'text_origin': 'caller_supplied_not_authenticated_transcript',
        'consistency_status': 'issues_detected' if issues else 'no_detected_conflict',
        'issues': issues,
        'axle_layout': layout,
        'confirmation_status': 'not_independently_confirmed',
        'unconfirmed_fields': sorted(k for k, v in facts.items() if v.get('value') is not None),
        'limits': [
            'These bounded text checks do not establish that all extracted facts match the actual conversation.',
            'The MCP caller supplies both facts and source text; a matching pair is not authenticated user confirmation.',
            'The application must capture the original statement and obtain confirmation of consequential facts through its own user interface.',
            'Confirmation of a report does not verify a credential, approval, measurement, or trip eligibility.',
        ],
    }
