# From logistics experiments to an evidence-backed assistant

Our original research question was:

> Do frontier tool-using agents produce unsafe, actionable logistics-compliance advice when safe resolution requires identifying missing trip facts and reconciling fresh, conflicting, multi-authority evidence?

We focused on truck access to APM Terminals Elizabeth, New Jersey. A useful answer has to explain which sources support it, why they apply to the described trip, and what information is still missing. A cautious answer can still fail the driver if it never explains the relevant rule.

## What the experiments taught us

The earlier study tested whether assistants would give actionable clearance when important trip facts were missing. The later [original-failure retest](../prototype/knowledge_graph/provider_runs/claude-original-failures-retest-20260919-execution-01/REPORT.md) records the historical comparison: the full study contained 96 responses across four products, while the selected Claude comparison contained eight responses, five previously judged positive for unsafe clearance. Those selected numbers are not the failure rate for the whole study.

This led to a practical question: could we give the assistant a clearer evidence structure and a checking tool, so its explanation stayed connected to the driver's actual situation?

## Connecting the evidence

We organized archived government, road-authority, port and terminal sources into a knowledge graph. Its records represent things such as a road, a rule, an authority, a terminal requirement or a source document. Its connections show how those things relate. A reader can trace a requirement back to a retained passage and identify which authority it belongs to.

The [source registry](../data/metadata.json) records URLs, dates and archive hashes. The [data dictionary](https://github.com/itsnotmarvin/last-mile-drayage-pilot/blob/main/docs/data_dictionary.md) explains the records. The [road-and-regulation map](https://github.com/itsnotmarvin/last-mile-drayage-pilot/blob/main/visuals/last_mile_regulation_map.png) offers a visual introduction.

The first checker handled a narrow synthetic safety-induction case. A [small tool/no-tool comparison](../prototype/knowledge_graph/provider_runs/claude-paired-sealink-20260908/README.md) found that Claude could identify the central evidence gap even without the tool. The tool produced reproducible, source-linked results, but did not consistently prevent unsupported wording. That result remains part of the project.

## Moving the graph into Neo4j and connecting Claude

The working graph was moved into **Neo4j Aura**, a cloud-hosted graph database. The assistant's pinned evidence release has **144 records and 228 relationships**. Older exported diagrams use a different, enriched representation with **121 connected nodes and 345 relationships**; these counts describe separate representations.

The assessment service and Claude connector run locally. MCP is the connection that lets Claude call that service. The graph provides connected evidence; the service selects and checks it; Claude writes the final response. Neo4j itself does not decide whether a truck may go.

The system has its evidence collection before a conversation begins. A driver then describes a trip. The service uses those details to select relevant evidence, retain missing facts and identify useful follow-up questions. Reported details remain distinct from verified evidence. Corrections update the saved trip. Regulatory requirements and physical or current conditions can be explained separately before contributing to the overall answer.

The [Neo4j setup guide](../prototype/knowledge_graph/docs/neo4j-migration.md) and [recorded cloud-graph validation](../prototype/knowledge_graph/audits/pinned-release-validation-2026-09-17/README.md) show how this was implemented. These repositories provide code and records to inspect; they do not provide a public driver service or public access to the database.

## Testing the experience exposed another gap

We repeated four exact prompts from the original Claude failures, twice each. The [eight-response retest](../prototype/knowledge_graph/provider_runs/claude-original-failures-retest-20260919-execution-01/REPORT.md) received two unsafe-clearance positives, five negatives and one unclear result under a single AI review. **None passed every part of the connected-experience criterion.** Independent human adjudication remains outstanding.

The source passages often existed, but the right explanation did not always reach the driver. Claude sometimes skipped the connector; some answers lost supplied facts or qualifications. A correct tool result was therefore insufficient evidence of a complete user experience.

## What changed, and what works now

The [latest changes](../prototype/knowledge_graph/docs/evidence-answer-generalization.md) preserve relevant explanations when measurements are missing, keep reports separate from verified facts, distinguish permit authorities, and label stored routes as candidates. The selection logic uses question topics and supplied fact fields rather than experiment IDs or exact failed prompt strings.

The [current audit](../prototype/knowledge_graph/audits/evidence-answer-generalization-20260920/README.md) records **473 passing local tests** and **11 of 12 development cases passing**. The remaining case concerns a terminal outside the supported scope. The development cases were inspected during implementation and are not an independent holdout.

In three fresh Claude chats, all three answers used the assessment tool, supplied relevant explanations and withheld clearance. Claude still omitted the supplied trip date in the annual-permit answer. A separate final access-rule regression retained a previously omitted exception. Readers can inspect both the [final access answer](../prototype/knowledge_graph/audits/evidence-answer-generalization-20260920/consumer/responses/final_missing_dimensions.txt) and the [permit answer with the date omission](../prototype/knowledge_graph/audits/evidence-answer-generalization-20260920/consumer/responses/annual_permit.txt).

We can demonstrate connected evidence, bounded checks, saved trip corrections and useful source explanations in captured Claude responses. We cannot yet claim consistently complete consumer answers or a measured causal improvement over the original experiment. Live 511NJ integration and the separate browser-to-Claude app bridge remain outside this accepted local workflow. The prototype does not authorize dispatch, route use or terminal entry.

For the present status, start with [Current state](../prototype/knowledge_graph/CURRENT_STATE.md). For the intended experience, read the [driver guide](../prototype/knowledge_graph/docs/driver-experience.md).
