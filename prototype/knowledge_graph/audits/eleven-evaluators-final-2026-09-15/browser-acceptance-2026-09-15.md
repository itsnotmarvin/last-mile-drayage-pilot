# Browser acceptance — first passing capture, September 15, 2026

Prior status was `not_run`: the automation harness hit `ERR_BLOCKED_BY_CLIENT`
on the local URL in every attempt. This run drove the user's real Chrome via
remote debugging instead, against the same running app
(`.runtime/integrated-app-2026-09-12`, port 8765, pinned release `f5dffe0f`).

## Flow exercised (synthetic driver user, fresh access key)

1. Login page renders clean: branding, Describe → Review → Assess steps,
   access-key field, synthetic-only disclaimers. No console-visible errors.
2. Login with a freshly issued synthetic driver key succeeds; existing
   conversations list; "+ New trip" opens the Describe step with the
   trucker-style placeholder.
3. Submitted statement: "Can I take this truck to APM Elizabeth tomorrow
   morning? Gross weight 80000 lb, height 14 ft 7 in. I have my valid TWIC
   with me. Synthetic test only."
4. Statement preserved verbatim with author and timestamp. Review proposed
   80000 lb, 175 in (14 ft 7 in converted correctly), APM Elizabeth —
   all matching the statement.
5. Checkbox confirmation ("I compared the listed facts...") then "Confirm
   facts and assess" renders the assessment: "Trip clearance is not
   established... permission not issued," with reported-fact comparisons
   below. No permission language anywhere.

## Result

Pass for the core Describe → Review → Assess path in a real browser: layout
clean at desktop width, statement fidelity exact, extraction correct,
assessment conservative. Screenshots: `/tmp/app-check-*.png` (local only, not
archived). Responsive/accessibility review and dispatcher-side walkthrough
remain open. This note is descriptive and outside the sealed artifact manifest.
