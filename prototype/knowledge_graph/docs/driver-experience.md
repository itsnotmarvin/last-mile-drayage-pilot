# Use the local drayage assistant

**September 19–20 status: general explanation fixes implemented, with consumer
presentation limits still open.** The earlier four-interaction walkthrough passed,
but the exact original-failure retest later exposed broader failures. The current
implementation has 473 passing tests and 11/12 predeclared development cases.
The updated three-case Claude batch used the MCP and supplied useful sources in
all three answers; the permit answer still omitted a supplied date. See the
[current evidence record](../audits/evidence-answer-generalization-20260920/README.md).

Open **Claude Desktop**, start a new chat, and use the existing
**drayage-kg-prototype** connector. Claude launches the configured connector;
there is no separate browser server to start for this version. The configured
Neo4j service and internet connection must be available.

Describe a synthetic truck and a supported route to APM Elizabeth. Include
loaded height, width, gross weight and semitrailer length with units, the
planned date/time/timezone, and what you know about credentials or permits.
Leave unknown facts unknown. Use synthetic aliases only.

The two supported named routes are:

- **Path A, Exit 13A to APM:** Turnpike connector, North Avenue, McLester Street,
  Tripoli Street. Connector route ID: `path_a_exit13a_to_apm`.
- **Path B, US 1/9 to APM:** US 1/9 south, the North Avenue approach and shared
  North Avenue segment, McLester Street, Tripoli Street. Connector route ID:
  `path_b_us1_9_to_apm`.

These are stored candidate route descriptions, not certified truck routes or
confirmation that the driver selected every listed segment. State any
deviations and whether Port Street is in the actual intended route; the assistant
cannot infer that solely from a stored sequence.

## A demonstration prompt

> I'm the driver for a synthetic demonstration trip, alias syn-driver-complete,
> SeaLink alias SYN-SL-A. Can I take this truck to APM Elizabeth on September 19,
> 2026 at 6:00 p.m. Eastern (2026-09-19T18:00:00-04:00)? My intended route is
> path_a_exit13a_to_apm: the Turnpike Exit 13A connector, North Avenue, McLester
> Street, then Tripoli Street to APM, with no deviations and no Port Street.
> Loaded height is 14 ft 7 in, width 102 inches, gross weight 80000 lb,
> semitrailer length 53 ft. I report having TWIC, SeaLink and an appointment.
> I have no axle measurements, permit details, independent credential verification
> or current road-condition checks. Use our connected drayage assessment and
> explain what the supplied evidence means for my trip, with sources I can inspect.

This is the dated acceptance example. For a different demonstration time,
supply the actual intended timestamp; do not interpret this saved example as
a current conditions report.

## Read the answer and inspect the evidence

The explanation should connect the truck facts to the relevant provisions,
show source links and page/section references, and explain how the findings
affect the combined conclusion. Rules and physical access are separate parts
of the reasoning, not mandatory headings in the response.

An unresolved overall result can still provide useful findings: a reported
height comparison, the conditions attached to local-road access, or why gross
weight alone cannot establish an axle/bridge result. A numerical comparison
does not establish that a specific road is legally available or physically clear.

Open a source link and use its cited page/section. The assessment is based on
retained source passages; a publisher's live document can change. Publication,
archive access, page retrieval and effective dates are different. Ask:

> Show the retained passage supporting that finding, its source and locator,
> and explain which part applies to my reported truck and route.

For a correction, stay in the same chat:

> Correction: the loaded height is 13 ft 6 in, not 14 ft 7 in. Keep the same
> trip and route. What changes in the assessment, and what still needs checking?

Claude should update the saved trip and explain the changed finding with its
source. For a new move, explicitly say it is a separate move and supply its
facts, or start a new chat. Missing facts must not carry over from another move.

## Coverage of this version

This is a local synthetic evidence-explanation prototype. Its bounded checks
do not authorize real-world dispatch. Current road conditions, real credentials
and permits, and full legal coverage are not established by the supplied archive.
511NJ integration is optional and is not part of this version's acceptance.
An APM page fetched today may still contain an old or undated notice.

If the connector reports an unavailable assessment, retry the saved trip.
The assistant must not substitute the previous result. If the answer does not
show sources, it has not met the presentation requirement; ask for the retained
evidence rather than treating an unsupported conclusion as established.

The separate browser workspace and confirmed-assessment bridge remain available
as implemented development work. They are not required to use this Claude version.

## Connector delivery contract

`assess_driver_move` is the primary complete-move tool. Create, update/correction
and read operations use the existing saved-trip service; full `trip_dispatch`
scope is fixed by the tool. A route mentioned in a complete terminal move does
not exclude terminal prerequisites. `get_trip_conditions_answer` freshly
reassesses the saved trip without changing its facts or scope.

Both return a compact source-linked `answer_markdown` with internal trip/revision
binding. The complete-move response instructs Claude to display the prepared
answer without rewriting consequential rule passages. Internal IDs stay out of
the ordinary driver answer. The full supporting assessment is retained locally
in the audit; the compact result does not claim every source record was delivered
to the consumer. Exceptional/bounded findings fall back to the detailed briefing
so they cannot be hidden by an ordinary unresolved-move summary.

Legacy `assess_trip` and `update_trip_facts` retain their three text blocks:
prepared driver answer, detailed source briefing and full JSON assessment.
Their `structuredContent` remains the full assessment. Consumers parsing JSON
from those text blocks must use the final block. `get_requirement_evidence`
remains available for focused retained-passage inspection.

The [historical walkthrough record](../audits/driver-experience-2026-09-19-r4/README.md)
separates actual observed Claude prose from tool payloads. It records one safely
rejected request-token collision and automatic retry. The accepted run preserves
source qualifications and links; future model behavior still warrants the same
bounded walkthrough when the model or delivery changes.


## Incomplete reports and questions

Ask about axle weight, road access or permit coverage even when the destination,
route or measurements are unknown. The tool description now covers those questions.
The answer should retain the relevant source rule, explain which missing fact
determines its application and preserve the unknown in the combined conclusion.
A report of satisfied prerequisites remains a report; it does not create verified
credentials. Group totals do not become individual axle measurements.

An explicitly unsupported terminal still has limited coverage. Its reported
measurements can be displayed without an available rule comparison; this is a
coverage gap, not evidence of legal eligibility. Missing destinations and explicitly
unsupported destinations select different existing catalog scopes.

Claude independently chooses tool use and final wording. An absent source or
omitted supplied fact is a presentation defect even if the tool assessment was
correct. Suggested next checks are not an exhaustive release checklist. See the
[generalization change notes](evidence-answer-generalization.md) for the implementation
and the distinction between local checks and actual consumer evidence.
