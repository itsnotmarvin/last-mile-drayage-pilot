# Evidence explanations across incomplete trips

This change addresses failures observed in the sealed original-failure Claude
retest. That retest delivered 2 unsafe-clearance positives, 5 negatives and 1
unclear endpoint, but 0/8 full connected-experience passes. The original selected
baseline was 5/8 positives. Those observations are not a controlled causal
estimate of the MCP's effect, and the negative endpoints did not establish a
useful driver experience.

## What changed

A missing measurement no longer removes the potentially relevant explanation.
The answer presents the access rule, the missing facts and why they affect
applicability. Permit questions include retained permit conditions and distinguish
state, toll-road, local, Port Authority and terminal responsibilities. A permit
report never verifies those approvals. The annual-permit table is explicitly
identified as a retained transcription.

The current source statement is saved independently of extracted facts, including
when no fields can be extracted. Group weights, date-only statements and broad
prerequisite reports can be retained as quoted, unverified context. They do not
become invented individual axle measurements, departure timestamps or credential
booleans. This is bounded text recognition, not a complete natural-language parser.
A later correction replaces the current statement while the history retains the
previous one; the renderer does not merge old free-text claims across corrections.

The driver's reported approach stays separate from a stored candidate route.
Unknown destinations do not automatically inherit APM gate observations. The
explicit unsupported-terminal fixture remains outside the existing road-rule
selection boundary; its measurement is preserved without a supported comparison.

The tool description asks consumers to assess weight, dimension, permit and
road-access questions even without a route or terminal. External Claude still
chooses whether to invoke a tool. This change cannot enforce that choice. The
already implemented confirmed-assessment application path requires assessment
before exposing an answer, but its separate live consumer workflow is unverified.

The final recommendation preserves unresolved requirements. Suggested next checks
are not a sufficient release checklist. Archived conditions remain dated context,
not directions or current clearance. Existing positive, negative and out-of-scope
bounded evaluator results retain their full briefing and are not replaced by a
universal hold response.

## Evidence and limits

New static explanations are bound to the reviewed graph release, source identity,
locator and retained text hash. Changed or missing bindings suppress the affected
explanation. These bindings are development change detection, not human approval,
current-law certification or an expansion of legal evaluator coverage.

The original tests remain intact. New behavioral cases cover missing and withdrawn
measurements, changed gross weights, unknown destinations, partial routes, separate
approval reports, date precision, source changes and outages. The predeclared
12-case development set is same-author and was inspected during development;
it is not an independently unseen benchmark. All failed attempts are retained.
See the [implementation and validation record](../audits/evidence-answer-generalization-20260920/README.md).

This work changes presentation, intake preservation and consumer guidance. It
does not change graph evidence, add authority coverage, verify real permits or
credentials, create live traffic coverage or authorize dispatch. A fresh controlled
with/without-MCP study remains necessary for a research claim about causal benefit.
