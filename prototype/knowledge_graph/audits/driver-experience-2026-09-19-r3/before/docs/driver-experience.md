# Use the local drayage assistant

**September 19 status:** the local connector and four-turn walkthrough work,
but final driver presentation acceptance remains open. Claude can omit supplied
links or qualifications when summarizing. The [observed review](../audits/driver-experience-2026-09-19/consumer-review.md)
records the exact failures; this guide does not claim a finished experience.

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

These are stored route descriptions, not certified truck routes. State any
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

Successful `assess_trip` and `update_trip_facts` responses contain three text
blocks: a prepared driver answer, a detailed source briefing, and the full JSON
assessment. `structuredContent` remains the same full assessment. Consumers
that parse JSON from text must use the final block; evidence and legacy tools
retain their existing output shape. Narrow scopes fall back to a detailed
briefing rather than a broad APM trip answer.

The prepared answer preserves access-rule qualifiers and source links, but
Claude's final narration can shorten them. The full source delivery is not
proof that the user actually received a faithful explanation. The latest
four-turn capture and reproducible evidence checks are in the
[driver experience checkpoint](../audits/driver-experience-2026-09-19/README.md).
