# Bounded first knowledge-graph run

## Objective

Design and implement an evidence-preserving local knowledge graph with a
deterministic APM induction checking service, then measure one consumer chat
provider's use of its tool without claiming trip clearance.

## Read first

`AGENTS.md`, `README.md`, `docs/design.md`, `tests/test_graph.py`, the parent
`docs/data_dictionary.md`, and the parent
`docs/knowledge-graph/001-apm-safety-induction.md`.

## Constraints

Only edit this prototype directory. No source promotion, live legal
interpretation, new dependencies, ADRs, unrelated refactors, real personal
data, public hosting, account security changes, or production mutations.
Do not delete, skip, weaken, or narrow tests to make the goal pass. Do not
repair the parent visual-manifest failure as part of this work.

Use the installed NetworkX 3.6.1 and Python standard library. Keep the storage
adapter separable so choosing a production database is a later human decision.
Do not claim this in-memory graph is TypeDB or a persistent database.

## Validate

`python3 -m unittest discover -s tests -v` from
`/Users/marbin/Developer/last-mile-drayage-pilot/prototype/knowledge_graph`.
Also capture a real provider prompt, tool arguments, tool response, and final
answer. Distinguish consumer app, API, and CLI surfaces in every result.

## Document

Write concise, targeted documentation for all changes; update this directory's
Markdown notes and make drafts, evidence limits, and test limits explicit.

## Checkpoints

1. Isolated graph import and passing archive tests (complete).
2. Reviewable graph/check model and frozen prototype acceptance cases.
3. Deterministic service, transport contract, negative/boundary tests.
4. Provider connection and captured tests, or a specific setup dependency.
5. Adversarial QA, diff review, result summary in `PROGRESS.md`.

## Stop condition

Complete only when the local suite passes, the model and limits are documented,
and at least one provider's actual tool use has been captured and scored against
the frozen prototype cases. Failures in provider behavior are valid measured
results, not a reason to change expected outcomes. An API-only run cannot meet
the consumer-app condition unless the user explicitly chooses API-first.

Stop and ask if the remaining work requires login/consent, a public endpoint,
new dependency, provider spend, application configuration change, or human
resolution of a consequential policy/modeling ambiguity. Report incomplete
provider validation honestly; do not mark the goal achieved at that boundary.

