# First graph workshop: APM safety induction

Status: workshop draft. Source checked against the retained PDF; graph modeling not yet approved by the user. No database import, operational currentness determination, or driver compliance claim.

## Question for this first piece

What must we know about an assigned driver's safety induction for a planned visit to APM Terminals Elizabeth?

## Retained source

- Source ID: `panynj_truckers_guide`.
- Document: *Truckers Resource Guidebook*.
- Publisher: Port Authority of New York and New Jersey.
- Publication date recorded in the source registry: August 2025.
- Original access date recorded in the registry: June 25, 2026.
- Locator: PDF page 11, printed page 18; APM TERMINALS > Gate Procedures > Mandatory Trucker Training.
- Archive: `data/raw/documents/port_authority/panynj_truckers_resource_guidebook.pdf`.
- Registered and locally checked SHA-256: `420453b5261f855e49628b5c914b575e0f4c73e8bb0b81c14c608aac96d67cb1`.
- Official URL: <https://www.panynj.gov/content/dam/port/shipping/port-truckers-resource-guidebook.pdf>.
- Workshop inspection: September 6, 2026. The relevant PDF spread was visually inspected and the archive hash matched the registry. This was an offline archive check, not a live policy recheck.

Exact first clause, with line wrapping removed:

> All truck drivers are required to complete the MANDATORY online safety induction video/quiz in order to access the terminal

The same section also states the following (paraphrased here):

- Trucking company staff can check a driver's APMT Safety Induction status by SeaLink number through the named induction checker.
- A driver obtaining a new SeaLink card needs to retake the induction using the new SeaLink number.
- Switching companies does not itself require retaking the induction if the driver keeps the same SeaLink number.

These statements describe the retained source. We have not tested the checker, submitted a SeaLink number, established a training expiration period, or verified any actual driver's status.

## First proposed relationships

These are discussion sketches, not approved schema or populated driver records:

```text
Port Authority -> publishes -> Guidebook version
Guidebook version -> contains -> Exact induction clause
Exact induction clause -> supports -> APM induction requirement
APM induction requirement -> applies to -> Truck drivers seeking APM access
APM induction requirement -> requires -> Completion of the safety induction
```

The source publisher and terminal operator have different roles. The guidebook is published by the Port Authority and describes a requirement for APM access; those roles should not be collapsed into one publisher relationship.

Existing IDs to preserve if this draft is later approved for implementation:

- `authority_panynj`
- `operator_apm_terminals`
- `facility_apm_elizabeth`
- `reg_apm_safety_induction`
- `training_apm_safety_induction`
- `panynj_truckers_guide`

## User modeling decision pending

How should we connect a driver, that driver's SeaLink identifier, and evidence of induction completion?

Candidate to discuss: keep completion evidence as a separate record associated with the driver, induction program, and SeaLink identifier it was checked against. Preserve when and how it was checked. This avoids treating a remembered completion as independent of a later SeaLink change, but the user has not approved this model.

No changes have been made to the canonical processed records. Completing this one requirement would not establish that all terminal-entry or trip requirements are satisfied.
