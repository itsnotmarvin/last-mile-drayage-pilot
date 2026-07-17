#!/usr/bin/env python3
"""Deterministic contradiction pair scan for the APM Elizabeth drayage corridor.

Phase B entry point. Reads the processed artifacts, migrates the pair-disposition
vocabulary, extends the pair ledger to cover all rules, re-adjudicates only the
pairs affected by Phase A evidence (preserving all prior dispositions and pair
IDs), materializes a four-condition evidence matrix for the serious candidate
pairs, and writes exactly one terminal conclusion to
data/processed/contradiction_conclusion.json.

Vocabulary (Phase B): compatible, layered, exception_relationship,
different_scope, different_time_circumstance, blocking_not_contradictory,
unresolved, contradiction_supported.

Precedence when recomputing a pair:
  1. unresolved            — a fact needed to decide is unknown
  2. different_scope       — act, location, addressee/outcome target, or vehicle
                             class provably disjoint
  3. different_time_circumstance
  4. exception_relationship
  5. compatible / layered
  6. blocking_not_contradictory
  7. contradiction_supported — only when every four-condition cell is proven

Usage:
  python3 src/analyze.py --as-of 2026-07-16T12:00:00-04:00 --write
  python3 src/analyze.py --as-of 2026-07-16T12:00:00-04:00 --check
"""

import argparse
import itertools
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *parts: os.path.join(ROOT, *parts)

VOCAB = [
    "compatible", "layered", "exception_relationship", "different_scope",
    "different_time_circumstance", "blocking_not_contradictory",
    "unresolved", "contradiction_supported",
]
RENAME = {
    "unresolved_missing_evidence": "unresolved",
    "potential_contradiction": "contradiction_supported",
}

NJAC_RULES = {"rule_021", "rule_022", "rule_023", "rule_024", "rule_025", "rule_026"}
PA10_RULES = {"rule_035", "rule_036", "rule_037", "rule_038", "rule_039", "rule_040"}
MUNICIPAL_RULES = {"rule_043", "rule_044", "rule_045", "rule_046"}
AFFECTED = NJAC_RULES | PA10_RULES | MUNICIPAL_RULES

# The named blocker (docs/audits/phase_a_source_resolution.md)
BLOCKER = ("PANYNJ authoritative clarification, erratum, or superseding PA-10 "
           "text resolving Subrule 34-1140(c), checked as of 2026-07-16")


def load(name):
    with open(P("data", "processed", name)) as fh:
        return json.load(fh)


def act_of(rec):
    """Operative act for a rule, from the applicability record."""
    if rec.get("act"):
        return rec["act"]
    action = rec.get("action", "")
    if action in ("parking",):
        return "parking"
    if action in ("registration", "credentialing", "dtr_registration"):
        return "registration"
    if rec.get("spatial_target", {}).get("target_type") == "node" or \
       "terminal" in (rec.get("spatial_target", {}).get("label") or "").lower():
        return "terminal_entry"
    return "roadway_operation"


def spatial_label(rec):
    st = rec.get("spatial_target", {})
    return (st.get("label") or st.get("target_type") or "unknown").lower()


def spatially_disjoint(ra, rb):
    """True only when the two rules provably govern disjoint places."""
    la, lb = spatial_label(ra), spatial_label(rb)
    # The 10.16.010 street list contains no modeled corridor street (verified);
    # terminal-area and corridor rules are disjoint from it.
    if "none on modeled corridor" in la or "none on modeled corridor" in lb:
        return True
    return False


def recompute(ra, rb):
    """Documented category logic for a pair of applicability records.

    Returns (disposition, rationale)."""
    ida, idb = ra["rule_id"], rb["rule_id"]
    acta, actb = act_of(ra), act_of(rb)

    # 1. unknown currentness -> unresolved
    for r in (ra, rb):
        if r.get("currentness") in (None, "currentness_unresolved"):
            return ("unresolved",
                    f"Currentness of {r['rule_id']} is unresolved; no determination by assumption.")

    # 2. distinct acts are different scope (registration, parking, roadway
    #    operation, and terminal entry are different acts by project rule)
    if acta != actb:
        return ("different_scope",
                f"Distinct operative acts ({acta} vs {actb}); a requirement on one act cannot "
                f"contradict a requirement on a different act.")

    # 3. provably disjoint locations
    if spatially_disjoint(ra, rb):
        return ("different_scope",
                "Locations provably disjoint: the Elizabeth 4-ton schedule (10.16.010) contains no "
                "modeled corridor street, so it shares no segment with corridor/terminal rules.")

    # 4. express exception relationships (N.J.A.C. 16:32 internal structure)
    njac_pair = {ida, idb} & NJAC_RULES
    if len(njac_pair) == 2:
        if "rule_023" in (ida, idb) and ({ida, idb} & {"rule_022", "rule_021"}):
            return ("exception_relationship",
                    "16:32-1.5 terminal-access provisions are an express exception to the 16:32-1.2(b) "
                    "National Network trip-completion requirement (current text, Supp. 1-3-23).")
        return ("layered",
                "Provisions of the same current chapter (N.J.A.C. 16:32, Supp. 1-3-23) that operate "
                "cumulatively on routing; simultaneously satisfiable.")

    # 5. state savings clause vs municipal rules: preserved, not conflicting
    if ("rule_024" in (ida, idb)) and ({ida, idb} & MUNICIPAL_RULES):
        return ("layered",
                "16:32-1.2(e) expressly preserves municipal restrictions; the preserved municipal rule "
                "operates alongside the state framework. No corridor prohibition exists to collide with "
                "the terminal-access permission (Elizabeth Title 10, Supp. 31).")

    # 6. municipal rules on the corridor
    if {ida, idb} & MUNICIPAL_RULES:
        if "rule_044" in (ida, idb):
            return ("layered",
                    "The 10.16.050 overweight-zone designation is permissive and connects to the Port "
                    "Authority overweight zone; it does not prohibit anything another rule permits or "
                    "require anything another rule prohibits on the same segment.")
        return ("layered",
                "Municipal traffic-control/parking provisions operate cumulatively with the other rule; "
                "no incompatible outcomes on any shared segment (Elizabeth Title 10, Supp. 31).")

    # 7. PA-10 internal pairs at the terminal gate
    pa10_pair = {ida, idb} & PA10_RULES
    if len(pa10_pair) == 2:
        if "rule_036" in (ida, idb):
            return ("unresolved",
                    "Depends on the authoritative interpretation of Subrule 34-1140(c); named blocker: "
                    + BLOCKER + ".")
        if "rule_039" in (ida, idb) or "rule_040" in (ida, idb):
            return ("compatible",
                    "Definitional/verification subrule referenced by the operative subrules of the same "
                    "tariff; same instrument, no independent outcome.")
        return ("layered",
                "Cumulative denial/verification conditions of the same current tariff (PA-10 eff. "
                "2026-05-01, confirmed byte-identical 2026-07-16); two prohibitions can both be "
                "satisfied by not triggering either.")

    # 8. rule_036 against any other terminal-entry rule
    if "rule_036" in (ida, idb):
        return ("unresolved",
                "Pair outcome depends on whether 34-1140(c) is operative as literally drafted; "
                "named blocker: " + BLOCKER + ".")

    # 9. remaining same-act pairs: cumulative requirements
    return ("layered",
            "Same-act requirements that are simultaneously satisfiable; no evidence of incompatible "
            "required/prohibited outcomes on a shared segment, truck set, time, and circumstance.")


def serious_candidates():
    """Four-condition evidence matrices for the pairs that could plausibly have
    been contradictions. Matrix cells: true / false / unknown."""
    def matrix(same_loc, same_truck, same_time, incompat, note):
        return {"same_segment_or_area": same_loc, "same_truck_profile": same_truck,
                "same_time_circumstance": same_time, "incompatible_outcomes": incompat,
                "note": note}

    return [
        {
            "pair": ["rule_036", "rule_037"],
            "label": "PA-10 34-1140(c) literal entry denial vs 34-1101 diesel DTR registration pathway",
            "matrix": matrix("true (APM gate / port terminals)",
                             "true (scn_001: MY2016 diesel, DTR-registered)",
                             "true (2026-07-16, gate hours)",
                             "false",
                             "Different acts: 34-1101 governs registration, 34-1140 governs gate entry. "
                             "Registration eligibility is not an entry permission; condition 4 fails as a "
                             "rule-vs-rule incompatibility."),
            "disposition": "different_scope",
        },
        {
            "pair": ["rule_036", "rule_035"],
            "label": "PA-10 34-1140(c) vs 34-1140(a)-(b) within the same subrule",
            "matrix": matrix("true", "true", "true", "false",
                             "Both clauses are prohibitions addressed to the terminal facility. Two "
                             "overlapping prohibitions cannot produce incompatible required outcomes; "
                             "a literal (c) makes (a)-(b) surplusage (an interpretation problem, not a "
                             "contradiction). Interpretation itself remains blocked."),
            "disposition": "unresolved",
        },
        {
            "pair": ["rule_023", "rule_043"],
            "label": "State terminal-access permission on local streets vs Elizabeth 4-ton exclusion schedule",
            "matrix": matrix("false", "true", "true", "false",
                             "Verified disjoint: no modeled corridor street appears in 10.16.010/10.16.040 "
                             "(Supp. 31). The most plausible municipal-vs-state contradiction pattern is "
                             "affirmatively absent on this corridor."),
            "disposition": "different_scope",
        },
        {
            "pair": ["rule_022", "rule_023"],
            "label": "National Network trip-completion requirement vs terminal-access exception",
            "matrix": matrix("true (corridor streets)", "true (102-inch standard truck)", "true", "false",
                             "Express exception within the same chapter: 16:32-1.5 permits leaving the "
                             "network as necessary for terminal access by the direct route."),
            "disposition": "exception_relationship",
        },
        {
            "pair": ["rule_035", "rule_041"],
            "label": "Tariff engine-year gate denial vs APM appointment mandate (1998-engine truck)",
            "matrix": matrix("true (APM gate)", "true (scn_003: MY1998 diesel)", "true", "false",
                             "Both restrict; the appointment mandate does not require admitting a "
                             "tariff-denied truck. Blocking outcome for the profile, not a contradiction."),
            "disposition": "blocking_not_contradictory",
        },
    ]


def run(as_of, write=False, check=False):
    nodes = load("regulatory_nodes.json")
    app = load("rule_applicability.json")
    pairs_doc = load("rule_pair_evaluations.json")

    rules = nodes["rules"]
    rule_ids = [r["rule_id"] for r in rules]
    app_by_id = {r["rule_id"]: r for r in app["records"]}
    n = len(rule_ids)
    expected_pairs = n * (n - 1) // 2

    pairs = pairs_doc["pairs"]
    by_key = {}
    for p in pairs:
        by_key[frozenset((p["left_rule_id"], p["right_rule_id"]))] = p

    # 1. vocabulary migration (stable pair ids)
    for p in pairs:
        if p["disposition"] in RENAME:
            p["disposition"] = RENAME[p["disposition"]]

    # 2. extend ledger to cover all rules
    max_num = max(int(p["pair_id"].split("_")[1]) for p in pairs)
    added = 0
    for a, b in itertools.combinations(sorted(rule_ids), 2):
        if frozenset((a, b)) in by_key:
            continue
        max_num += 1
        newp = {"pair_id": f"pair_{max_num:04d}", "left_rule_id": a, "right_rule_id": b,
                "disposition": None, "rationale": None, "adjudication": "phase_b_2026_07_16"}
        pairs.append(newp)
        by_key[frozenset((a, b))] = newp
        added += 1

    # 3. re-adjudicate affected pairs only
    readjudicated = 0
    for p in pairs:
        a, b = p["left_rule_id"], p["right_rule_id"]
        affected = bool({a, b} & AFFECTED)
        if p["disposition"] is None or (affected and p["disposition"] == "unresolved") \
           or (affected and p.get("adjudication") == "rule_based_first_pass"):
            ra, rb = app_by_id.get(a), app_by_id.get(b)
            if ra is None or rb is None:
                disp, why = "unresolved", f"No applicability record for {a if ra is None else b}."
            else:
                disp, why = recompute(ra, rb)
            if p["disposition"] is not None and disp != p["disposition"]:
                p["prior_rationale"] = p.get("rationale")
                readjudicated += 1
            elif p["disposition"] is None:
                readjudicated += 1
            p["disposition"], p["rationale"] = disp, why
            p["adjudication"] = "phase_b_2026_07_16"

    # 4. serious-candidate evidence matrices (documented hand adjudication)
    for s in serious_candidates():
        p = by_key.get(frozenset(s["pair"]))
        if p is not None:
            if p["disposition"] != s["disposition"]:
                p["prior_rationale"] = p.get("rationale")
                readjudicated += 1
            p["disposition"] = s["disposition"]
            p["rationale"] = s["matrix"]["note"]
            p["evidence_matrix"] = s["matrix"]
            p["label"] = s["label"]
            p["adjudication"] = "phase_b_2026_07_16_hand"

    # 5. integrity checks
    assert len(pairs) == expected_pairs, (len(pairs), expected_pairs)
    for p in pairs:
        assert p["disposition"] in VOCAB, p
    counts = {}
    for p in pairs:
        counts[p["disposition"]] = counts.get(p["disposition"], 0) + 1

    contradictions = [p for p in pairs if p["disposition"] == "contradiction_supported"]
    unresolved = [p for p in pairs if p["disposition"] == "unresolved"]

    # 6. terminal conclusion — exactly one
    if contradictions:
        conclusion_type = "contradiction_supported"
    elif unresolved:
        conclusion_type = "not_determinable_named_source_unavailable"
    else:
        conclusion_type = "no_contradiction_within_scope"

    conclusion = {
        "schema_version": "0.1.0",
        "generated": "2026-07-16",
        "as_of": as_of,
        "conclusion": conclusion_type,
        "scope": {
            "included": [
                "Roadway operation on both candidate paths (NJ Turnpike Exit 13A / NJ 81 / US 1&9 approaches; "
                "North Ave, North Ave East, McLester St, Tripoli St)",
                "State routing framework N.J.A.C. 16:32 (current, expires 2029-11-30)",
                "Elizabeth municipal Title 10 (Supp. 31, through Ord. 6138 of 2025-06-24)",
                "PA-10 tariff terminal-entry and registry rules (current, byte-verified 2026-07-16)",
                "APM operational gate rules (snapshots 2026-07-16)",
                "Scenarios scn_001-scn_005 (data/processed/scenarios.json)",
            ],
            "excluded": [
                "Field signage (gap 7; web-only phase)",
                "TWIC/secure-area federal credentialing detail (kept out of contradiction scope)",
                "Elizabeth ordinances adopted after 2025-06-24 (not programmatically enumerable)",
                "OS/OW load-specific facts (profile intentionally unresolved)",
            ],
        },
        "unresolved_pairs": [p["pair_id"] for p in unresolved],
        "named_blocker": BLOCKER if unresolved else None,
        "statement": None,
        "summary_counts": counts,
    }

    if conclusion_type == "not_determinable_named_source_unavailable":
        conclusion["statement"] = (
            "Not determinable. Every serious candidate pair in the fully investigated scope resolves to a "
            "non-contradiction disposition except the pairs that turn on PA-10 Subrule 34-1140(c). Clause (c) "
            "read literally denies terminal access to every non-alternative-fuel drayage truck (since "
            "2023-07-02), while PANYNJ's own registration pathway (34-1101), sticker schedule (34-1120), "
            "operational program statements, and APM's live diesel appointment operations treat compliant "
            "MY2014+ diesels as admissible and alternative-fuel trucks as an exemption category. Whether "
            "clause (c) is a drafting artifact of the 2010 phase schedule (present unchanged since at least "
            "June 2019 with deadlines that repeatedly passed without diesel exclusion) or an operative "
            "prohibition contradicted by the agency's own operational framework cannot be resolved without: "
            + BLOCKER + ". If PANYNJ affirmed the literal reading, the 34-1140(c)-vs-operational-framework "
            "pair would satisfy all four contradiction conditions at the gate; if PANYNJ confirmed a drafting "
            "error, every remaining pair classifies as non-contradictory and the corridor result would be "
            "'no contradiction within scope'.")

    if write:
        pairs_doc["summary_counts"] = counts
        pairs_doc["potential_contradictions"] = [p["pair_id"] for p in contradictions]
        pairs_doc["generated"] = "2026-07-16"
        pairs_doc["description"] = (
            "Pairwise disposition ledger for all rules in regulatory_nodes.json "
            f"(n={n}, {expected_pairs} pairs). Phase B vocabulary: " + ", ".join(VOCAB) + ". "
            "Migration: unresolved_missing_evidence->unresolved, potential_contradiction->contradiction_supported. "
            "22 pairs were hand-adjudicated pre-Phase-B; pairs touched by Phase A evidence carry adjudication "
            "phase_b_2026_07_16 (or _hand with an evidence_matrix). Prior rationales preserved in prior_rationale.")
        with open(P("data", "processed", "rule_pair_evaluations.json"), "w") as fh:
            json.dump(pairs_doc, fh, indent=1)
        with open(P("data", "processed", "contradiction_conclusion.json"), "w") as fh:
            json.dump(conclusion, fh, indent=1)

    if check:
        assert sum(counts.values()) == expected_pairs
        assert (conclusion_type == "contradiction_supported") == bool(contradictions)
        for p in pairs:
            ra, rb = app_by_id.get(p["left_rule_id"]), app_by_id.get(p["right_rule_id"])
            if ra and rb and p["disposition"] == "contradiction_supported":
                assert act_of(ra) == act_of(rb), "contradiction across distinct acts is forbidden"

    print(f"rules={n} pairs={len(pairs)} added={added} readjudicated={readjudicated}")
    print("summary:", json.dumps(counts, sort_keys=True))
    print()
    print("TERMINAL CONCLUSION:", conclusion_type)
    if conclusion["statement"]:
        print(conclusion["statement"])
    return conclusion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-07-16T12:00:00-04:00")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true", help="alias kept for CLI stability")
    args = ap.parse_args()
    run(args.as_of, write=args.write, check=args.check)


if __name__ == "__main__":
    main()
