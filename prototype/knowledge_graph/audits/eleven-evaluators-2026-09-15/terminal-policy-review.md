# Terminal policy review — September 15, 2026 (independent)

Scope: every hardcoded policy constant in `neo4j_kg/terminal_evaluators.py`
checked against the retained source-clause text at pinned graph release
`f5dffe0f...` (31 clauses read live from Neo4j). This is the review Astra's
`terminal_policy_review` task was going to run before usage limits killed it.
Method: clause text extracted via `Neo4jStore.read`, compared constant by
constant. No code was changed for this review.

## 34-1101 registration branch — MATCHES

- Code: effective `2023-07-02 00:01 America/New_York`; registration at or after
  the threshold with `meets_2014_emissions_standard is True` counts toward met;
  engine model year alone never establishes the standard.
- Source (Subrule 34-1101, PDF p.56): "Beginning July 2, 2023 at 12:01 AM, only
  Drayage Trucks that are equipped with an engine that meets or exceeds federal
  EPA on-road emission standards for engine model year 2014 heavy-duty
  diesel-fueled shall be permitted to complete registration."
- Verdict: exact match, including the 12:01 AM threshold and the year-vs-standard
  distinction the code enforces in its detail string.

## 34-1140 entry branch — MATCHES, with disclosed gaps

- Code blocks: trip ≥ 2028-05-01 → year 2000 or older blocked; trip ≥ 2027-05-01
  → 1999 or older; trip ≥ 2023-07-02 → 1998 or older; all at 12:01 AM NY time.
  `year_ok = engine_model_year > cutoff` (strictly newer passes).
- Source (Subrule 34-1140, PDF p.56): identical three blocks with identical
  cutoffs and identical 12:01 AM effective times.
- Verdict: match. Two disclosed non-gaps: clause (c) Alternative (Drayage) Truck
  per 34-1060 has no reviewed predicate (34-1060 is not among the 31 retained
  clauses; the code says so in its detail string), and clause (a)
  DTR-record verifiability is approximated by registered-and-active (conservative
  direction: the whole evaluator is `force_status="unresolved"`, so it can never
  issue a pass — confirmed in the live capture where `dtr_engine_policy` is
  unresolved on every assessment).

## 34-1100 registration + 10-day amendment — MATCHES

- Code: registration date strictly before local entry date
  (`registered_date < trip_date`); change-to-amendment elapsed whole calendar
  days in America/New_York, `elapsed_days <= 10`; future-dated or
  predates-registration sequences unresolved.
- Source (Subrule 34-1100, PDF p.55): "registered in the DTR prior to the date
  of entry" and "amended within ten (10) calendar days of the change."
- Verdict: match. The exactly-10-days boundary (met) is an adapter reading of
  "within ten calendar days," stated in the check detail. Same-date registration
  can never satisfy "prior to the date" — the strict `<` is the conservative
  correct reading.

## RFID Class 8 branch — MATCHES

- Code: applies only when receipt asserts `class_8 is True`; requires assigned,
  valid, properly mounted; non-Class-8 skips the branch as met-scope.
- Source (RFID clause, PDF p.4): "All Class 8 drayage trucks seeking entry ...
  must be registered in the DTR and have a valid RFID tag properly mounted on
  the vehicle. No tag, no entry."
- Verdict: match. The code does not repeat "no entry" as an operational denial —
  correct, because no evaluator issues entry permission (limits strings say so).

## TWIC — MATCHES, adapter semantics disclosed

- Code: scope limited to unescorted secure-area access; exception claimed →
  unresolved; valid required; trip strictly before `credential_expires_at`
  (equality counts as expired); physical possession required.
- Source (33 CFR 101.514(a)): "All persons requiring unescorted access to secure
  areas ... must possess a TWIC before such access is granted."
- Verdict: scope and possession match. Expiry strictness and the
  physically-present field are synthetic-adapter semantics, not source quotes —
  both are disclosed verbatim in their check detail strings, and both fail
  toward unresolved, never toward a pass.

## SeaLink — MATCHES

- Code: case-bound record must be active; TWIC must be registered with the Port
  Authority on that record. TWIC validity and possession stay separate checks.
- Source (SeaLink clause, PDF p.4): "SeaLink is mandatory for all truckers ...
  Anyone with SeaLink identification must also have a TWIC. You must register
  your TWIC with the Port Authority."
- Verdict: match, including the separation the source itself draws between
  holding SeaLink, holding TWIC, and registering TWIC.

## APM appointment — MATCHES, adapter semantics disclosed

- Code: applies only to `facility_apm_elizabeth`; appointment confirmed;
  `slot_start <= trip < slot_end` (start-inclusive, end-exclusive).
- Source (APM clause, PDF p.11/18): "ALL GATE MOVES AT APMT REQUIRE AN
  APPOINTMENT. All appointments must be made on the TERMPoint website or APP."
- Verdict: requirement and scope match. Slot-boundary inclusivity is adapter
  semantics, disclosed in the detail string, consistent with the
  start-inclusive/end-exclusive convention used across `verification.py`.

## Transaction release — DRAFT, disclosed as draft

- Code: import-pickup moves only; `fully_available` explicit; all five modeled
  hold fields must be explicit before absence is established.
- Source: retained Port Authority import-pickup passage (container availability;
  freight, customer, demurrage, customs holds) held as a draft supplement, not
  a promoted clause.
- Verdict: acceptable as labeled. The fifth field (`other_hold`) is modeling
  beyond the four named holds; the check calls them "modeled hold fields,"
  which is accurate. Limits strings mark the supplement draft, non-approved,
  non-operational.

## Overall

No policy constant contradicts its retained source text. Every adapter-semantics
choice (expiry strictness, slot inclusivity, exactly-10-days, fifth hold field)
is disclosed in its check detail and fails toward unresolved. The engine-policy
evaluator cannot return met by construction. No changes requested.
