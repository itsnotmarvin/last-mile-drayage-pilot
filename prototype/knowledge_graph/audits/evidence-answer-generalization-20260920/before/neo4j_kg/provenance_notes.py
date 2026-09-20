"""Non-destructive extraction review notes for the audited evidence release.

These are development review annotations, not amendments or legal interpretations.
The archive's text and locator remain available unchanged. Notes are scoped to the
exact release reviewed in audits/evidence-2026-09-10/source-manual-review.json.
"""
import copy

_REVIEWED_RELEASE = "f5dffe0f7a32b5144920efb5a644f8c4dc9f20def76b4217c38b0cdbc454cf5c"
_NOTES = {
    "reg_nj_single_trip_route_review_13_18_portal_copy": {
        "issue": "incomplete_archive_page_locator",
        "recommended_locator": "PDF pages 2-3, N.J.A.C. 13:18-1.5(b)(3)-(7), (d), and (e)",
        "quotation_form": "retained_passages",
        "note": "Items (b)(3) and (b)(4) occur on PDF page 2; remaining retained items and (d)/(e) occur on page 3. The archive locator remains unchanged for reproducibility.",
    },
    "reg_nj_ocean_container_permit": {
        "issue": "table_linearization_labeled_verbatim",
        "recommended_locator": "PDF page 43, section 3.4 and Table 5",
        "quotation_form": "prose_and_linearized_table",
        "note": "The Table 5 entry is a linearized three-column table, not a continuous verbatim sentence. Gross 90,000 lb, tandem 38,000 lb and tri-axle 56,400 lb values match the PDF. Preserve surrounding scope and qualifications; these numbers alone do not establish permit eligibility.",
    },
}


def provenance_review(revision, clause_id):
    if revision != _REVIEWED_RELEASE or clause_id not in _NOTES:
        return None
    return {"review_status": "development_visual_review_not_policy_approval",
            "reviewed_release": _REVIEWED_RELEASE,
            "review_record": "audits/evidence-2026-09-10/source-manual-review.json",
            **copy.deepcopy(_NOTES[clause_id])}
