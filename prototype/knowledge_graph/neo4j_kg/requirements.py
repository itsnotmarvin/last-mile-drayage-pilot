"""Static, source-backed requirement intake for synthetic trip assessments.

The catalog says which facts and verification steps a scoped conversation needs.
Except for the existing induction check, it does not decide compliance.  Source
clause IDs point into the pinned Neo4j release; limits retain the source's
jurisdiction, currentness, and interpretation boundaries.
"""

from __future__ import annotations

import copy

from .common import digest


_CANONICAL_REQUIREMENTS = (
    {
        "id": "trip_context",
        "label": "Trip, terminal, and timing context",
        "family": "shared_trip_context",
        "source_clause_ids": [
            "reg_nj_single_trip_route_review_13_18_portal_copy",
            "reg_apm_safety_induction",
        ],
        "required_fields": ["terminal_id", "trip_at"],
        "verification_fields": [],
        "owner": "dispatcher",
        "question_templates": {
            "terminal_id": "Which terminal is this trip going to?",
            "trip_at": "What date and time is the trip planned for, including the time zone?",
        },
        "limits": [
            "These facts select assessment scope; they do not establish dispatch, route, or entry clearance.",
            "The catalog's terminal-specific evidence supports APM Elizabeth only. A missing terminal leaves applicability unresolved, and another terminal creates an unsupported-terminal coverage gap rather than an exemption.",
            "The NJPASS-hosted route-review clause is retained evidence, but its official code-of-record currentness was not independently verified.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": [],
    },
    {
        "id": "axle_weight_evidence",
        "label": "Gross, axle, and spacing evidence",
        "family": "axle_weight",
        "source_clause_ids": [
            "reg_federal_interstate_weight",
            "reg_nj_noninterstate_single_axle",
            "reg_nj_tandem_gross_bridge",
            "reg_nj_single_trip_route_review_13_18_portal_copy",
        ],
        "required_fields": [
            "gross_weight",
            "axle_weights",
            "axle_spacings",
            "axle_count",
            "route_id",
        ],
        "verification_fields": [
            "gross_weight",
            "axle_weights",
            "axle_spacings",
            "route_id",
        ],
        "owner": "carrier",
        "question_templates": {
            "gross_weight": "What is the loaded gross weight, including the unit?",
            "axle_weights": "What is the loaded weight on each axle or axle group, including the unit?",
            "axle_spacings": "What are the axle spacings, including the unit?",
            "axle_count": "How many axles does the tractor-trailer combination have?",
            "route_id": "What exact route is planned for this trip?",
        },
        "limits": [
            "The federal clause is limited to the Interstate system and reasonable access; the New Jersey single-axle clause is limited to non-Interstate New Jersey roads.",
            "Which limit applies depends on the exact roadway jurisdiction and route. This catalog implements no bridge-formula, axle-group, tire-load, or legal-weight calculator.",
            "Gross weight, axle count, and reported axle weights or spacings do not by themselves establish compliance.",
            "The NJPASS-hosted route-review clause is excluded from the verified graph because official code-of-record currentness was not independently verified.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["trip_context"],
    },
    {
        "id": "dimensions_and_route",
        "label": "Loaded dimensions and exact route access",
        "family": "dimensions_route",
        "source_clause_ids": [
            "reg_nj_width_limit",
            "reg_nj_height_limit",
            "reg_nj_semitrailer_length",
            "reg_nj_truck_access_local_rule_preservation",
            "reg_nj_access_network_600_series",
            "reg_nj_terminal_access_102_inch_standard_truck",
        ],
        "required_fields": [
            "width",
            "height",
            "overall_length",
            "semitrailer_length",
            "route_id",
            "route_description",
            "terminal_id",
        ],
        "verification_fields": [
            "width",
            "height",
            "overall_length",
            "semitrailer_length",
            "route_id",
            "route_description",
        ],
        "owner": "carrier",
        "question_templates": {
            "width": "What is the loaded overall width, including the unit?",
            "height": "What is the loaded overall height, including the unit?",
            "overall_length": "What is the loaded overall vehicle length, including the unit?",
            "semitrailer_length": "What is the semitrailer length, including the unit?",
            "route_id": "What exact route is planned for this trip?",
            "route_description": "Please list the planned roads and terminal-access sequence in travel order.",
            "terminal_id": "Which terminal is this route intended to access?",
        },
        "limits": [
            "Width limits depend on route-network status, and the cited local-access rule is expressly limited to a 102-inch-wide standard truck using unrestricted local roads by the direct route.",
            "A road's absence from a listed network or restriction table establishes neither permission nor prohibition. Current local postings and every segment still require verification.",
            "Published terminal directions and stored route topology are not legal route designation, bridge-clearance evidence, or navigable truck-route approval.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["trip_context"],
    },
    {
        "id": "permit_eligibility",
        "label": "Permit type and load eligibility evidence",
        "family": "permit_coverage",
        "source_clause_ids": [
            "reg_nj_osow_permit_requirement_13_18_portal_copy",
            "reg_nj_single_trip_osow_permit",
            "reg_nj_ocean_container_permit",
        ],
        "required_fields": [
            "permit_type",
            "container_sealed",
            "load_divisible",
            "trip_at",
        ],
        "verification_fields": ["permit_type", "permit_route_reported"],
        "owner": "carrier",
        "question_templates": {
            "permit_type": "What permit type, if any, is reported for this specific truck and load?",
            "container_sealed": "Is the container sealed, unknown, or not a sealed container?",
            "load_divisible": "Is the load divisible, non-divisible, or still unknown?",
            "trip_at": "What date and time is the permitted movement planned for, including the time zone?",
            "permit_route_reported": "Does the reported permit identify this exact route and trip?",
        },
        "limits": [
            "Permit applicability depends on the load, dimensions, axle facts, trip time, and permit terms; no legal interpretation or permit-validity check is implemented.",
            "The ocean-container sources concern sealed ocean-borne containers and do not make every container move eligible for that permit type.",
            "The NJPASS-hosted permit clause is retained but excluded from the verified graph because official code-of-record currentness was not independently archived and compared.",
            "A reported permit, including a reported-valid permit, is user-reported evidence and does not establish approval or route coverage.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["axle_weight_evidence", "dimensions_and_route"],
    },
    {
        "id": "cross_authority_coverage",
        "label": "Cross-authority route and permit coverage",
        "family": "permit_coverage",
        "source_clause_ids": [
            "reg_nj_toll_authority_approval_13_18_portal_copy",
            "reg_nj_truck_access_local_rule_preservation",
            "reg_panynj_terminal_traffic",
        ],
        "required_fields": [
            "route_id",
            "route_description",
            "permit_route_reported",
            "turnpike_approval_reported",
            "local_approval_reported",
            "port_approval_reported",
            "terminal_approval_reported",
        ],
        "verification_fields": [
            "permit_route_reported",
            "turnpike_approval_reported",
            "local_approval_reported",
            "port_approval_reported",
            "terminal_approval_reported",
        ],
        "owner": "authority",
        "question_templates": {
            "route_id": "What exact route is planned for this trip?",
            "route_description": "Which State, toll, county, local, Port Authority, and terminal roads will the move use?",
            "permit_route_reported": "Does the reported permit identify this exact route and trip?",
            "turnpike_approval_reported": "Is separate approval from the toll-road authority reported for this route?",
            "local_approval_reported": "Are the required county or local approvals reported for every local segment?",
            "port_approval_reported": "Is Port Authority approval reported for this movement?",
            "terminal_approval_reported": "Is terminal handling approval reported for this movement?",
        },
        "limits": [
            "A New Jersey State permit does not establish approval for toll, county, local, Port Authority, or terminal-controlled segments.",
            "Every reported approval requires verification from the responsible authority; a complete set of user reports is not cross-authority clearance.",
            "The retained toll-road approval clause is excluded from the verified graph because official code-of-record currentness was not independently verified.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["permit_eligibility", "dimensions_and_route"],
    },
    {
        "id": "current_route_conditions",
        "label": "Current route postings and operating conditions",
        "family": "current_route_conditions",
        "source_clause_ids": [
            "reg_nj_truck_access_local_rule_preservation",
            "reg_panynj_terminal_traffic",
        ],
        "required_fields": [
            "trip_at",
            "route_id",
            "route_description",
            "port_street_in_route",
            "route_conditions_checked_at",
        ],
        "verification_fields": ["route_conditions_checked_at"],
        "owner": "authority",
        "question_templates": {
            "trip_at": "What date and time is the trip planned for, including the time zone?",
            "route_id": "What exact route needs a current-condition check?",
            "route_description": "Please list the planned roads in travel order so each segment can be rechecked.",
            "port_street_in_route": "Does the planned route use Port Street?",
            "route_conditions_checked_at": "When were current postings, closures, lanes, detours, escorts, and restrictions last checked with the responsible authorities?",
        },
        "limits": [
            "No live current-policy, posting, closure, lane, detour, escort, or route-condition integration is implemented.",
            "The archived Port Street bulletin is a quarantined dated observation, not a source clause or proof of conditions on the trip date; it must be rechecked before operational use.",
            "A user-reported check time does not verify the result, authority, route coverage, or continued currentness of that check.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["dimensions_and_route"],
    },
    {
        "id": "dtr_registration_and_rfid",
        "label": "DTR registration and vehicle RFID evidence",
        "family": "dtr",
        "source_clause_ids": ["reg_panynj_dtr", "reg_panynj_rfid"],
        "required_fields": ["vehicle_id", "dtr_reported", "rfid_reported"],
        "verification_fields": ["dtr_reported", "rfid_reported"],
        "owner": "carrier",
        "question_templates": {
            "vehicle_id": "Which synthetic truck is assigned to this move?",
            "dtr_reported": "Is this truck reported as currently registered in the DTR?",
            "rfid_reported": "Is a valid, properly mounted RFID tag reported for this truck?",
        },
        "limits": [
            "No live PortTruckPass, DTR, ownership-amendment, or RFID lookup is implemented.",
            "Reported DTR or RFID status is not registry verification and does not establish terminal entry.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["trip_context"],
    },
    {
        "id": "dtr_engine_policy",
        "label": "DTR engine-policy evidence and retained tariff conflict",
        "family": "dtr",
        "source_clause_ids": [
            "reg_panynj_dtr_engine",
            "reg_panynj_drayage_truck_deadline_34_1140",
        ],
        "required_fields": ["vehicle_id", "engine_model_year", "dtr_reported", "trip_at"],
        "verification_fields": ["dtr_reported"],
        "owner": "carrier",
        "question_templates": {
            "vehicle_id": "Which synthetic truck is assigned to this move?",
            "engine_model_year": "What is the truck engine model year?",
            "dtr_reported": "Can an active DTR record for this truck be verified?",
            "trip_at": "What date and time is terminal entry planned for, including the time zone?",
        },
        "limits": [
            "The release preserves an unresolved internal tension between Subrules 34-1101 and 34-1140; the deadline clause is explicitly excluded from verified use.",
            "This catalog does not reconcile the tariff, infer enforcement, or categorically approve or deny a truck from engine model year alone.",
            "The 2014 engine language concerns completing DTR registration and must not be silently converted into a universal terminal-entry rule.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["dtr_registration_and_rfid"],
    },
    {
        "id": "driver_twic",
        "label": "Driver TWIC evidence",
        "family": "terminal_access",
        "source_clause_ids": ["reg_federal_twic", "reg_panynj_sealink_twic"],
        "required_fields": ["driver_id", "twic_reported"],
        "verification_fields": ["twic_reported"],
        "owner": "driver",
        "question_templates": {
            "driver_id": "Which synthetic driver is assigned to this move?",
            "twic_reported": "Does the assigned driver report a current TWIC for the intended access?",
        },
        "limits": [
            "The federal clause concerns unescorted access to regulated secure areas and retains its stated exceptions; this catalog does not determine whether an exception applies.",
            "No live TSA or Port Authority credential verification is implemented. A reported TWIC is not verified access authorization.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["trip_context"],
    },
    {
        "id": "sealink_registration",
        "label": "SeaLink and TWIC registration evidence",
        "family": "terminal_access",
        "source_clause_ids": ["reg_panynj_sealink_twic"],
        "required_fields": [
            "driver_id",
            "current_sealink_id",
            "sealink_registered_reported",
            "twic_reported",
        ],
        "verification_fields": ["sealink_registered_reported", "twic_reported"],
        "owner": "driver",
        "question_templates": {
            "driver_id": "Which synthetic driver is assigned to this move?",
            "current_sealink_id": "What synthetic SeaLink alias is current for that driver?",
            "sealink_registered_reported": "Is the driver's current SeaLink reported as active with the TWIC registered to it?",
            "twic_reported": "Does the assigned driver report a current TWIC for the intended access?",
        },
        "limits": [
            "No live SeaLink or TWIC-registration lookup is implemented.",
            "Possession of an identifier and a reported registration do not establish current validity or terminal entry.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["driver_twic"],
    },
    {
        "id": "apm_induction",
        "label": "APM safety induction tied to the current SeaLink",
        "family": "terminal_access",
        "source_clause_ids": [
            "reg_apm_safety_induction",
            "prototype_clause_induction_sealink_change",
        ],
        "required_fields": [
            "terminal_id",
            "subject_role",
            "driver_id",
            "current_sealink_id",
            "trip_at",
        ],
        "verification_fields": ["induction_reported"],
        "owner": "driver",
        "question_templates": {
            "terminal_id": "Is this trip going to APM Elizabeth?",
            "subject_role": "Is the assessed person the truck driver for this move?",
            "driver_id": "Which synthetic driver is assigned to this move?",
            "current_sealink_id": "What synthetic SeaLink alias is current for that driver?",
            "trip_at": "What date and time is terminal entry planned for, including the time zone?",
            "induction_reported": "Does the driver report completing APM's induction for that current SeaLink?",
        },
        "limits": [
            "This is the only catalog requirement with an implemented check, and it uses server-owned synthetic evidence rather than a live training provider.",
            "A matching synthetic result addresses only induction for the current SeaLink; it is not dispatch, route, permit, or terminal-entry clearance.",
            "Archived policy is not verified as current for the trip, and synthetic assessment dates do not create a training-expiry rule.",
        ],
        "implementation": "induction_identifier_match_v1",
        "dependencies": ["trip_context"],
    },
    {
        "id": "apm_appointment",
        "label": "APM gate appointment evidence",
        "family": "terminal_access",
        "source_clause_ids": ["reg_apm_appointment"],
        "required_fields": ["terminal_id", "appointment_reported"],
        "verification_fields": ["appointment_reported"],
        "owner": "dispatcher",
        "question_templates": {
            "terminal_id": "Is this gate move going to APM Elizabeth?",
            "appointment_reported": "Is an appointment reported for this specific APM gate move?",
        },
        "limits": [
            "No live TERMPoint or terminal appointment lookup is implemented.",
            "A reported appointment does not establish that it is current, matches this movement, or will be accepted at the gate.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["trip_context"],
    },
    {
        "id": "transaction_release",
        "label": "Same-day transaction and gate release evidence",
        "family": "terminal_access",
        "source_clause_ids": [],
        "required_fields": ["terminal_id", "trip_at", "transaction_release_reported"],
        "verification_fields": ["transaction_release_reported"],
        "owner": "dispatcher",
        "question_templates": {
            "terminal_id": "Which terminal must release this transaction?",
            "trip_at": "What date and time is the intended gate move, including the time zone?",
            "transaction_release_reported": "Is this specific transaction reported as released for the intended gate move?",
        },
        "limits": [
            "The pinned release contains no retained source clause that establishes same-day transaction or gate-release requirements.",
            "No live terminal transaction, gate, cargo-release, or admission integration is implemented. Reported release status cannot establish entry.",
        ],
        "implementation": "evidence_readiness_only",
        "dependencies": ["apm_appointment"],
    },
)


# Public catalog data is intentionally ordinary JSON-like data for callers and
# serialization.  The selector uses the private canonical snapshot so mutation
# of a returned result (or even accidental mutation of this convenience copy)
# cannot change later selection or the version identity.
REQUIREMENTS = copy.deepcopy(list(_CANONICAL_REQUIREMENTS))
CATALOG_VERSION = digest(_CANONICAL_REQUIREMENTS)


_SCOPE_REQUIREMENT_IDS = {
    "induction": ("trip_context", "apm_induction"),
    "terminal_entry": (
        "trip_context",
        "dtr_registration_and_rfid",
        "dtr_engine_policy",
        "driver_twic",
        "sealink_registration",
        "apm_induction",
        "apm_appointment",
        "transaction_release",
    ),
    "route": (
        "trip_context",
        "axle_weight_evidence",
        "dimensions_and_route",
        "permit_eligibility",
        "cross_authority_coverage",
        "current_route_conditions",
    ),
}
_ALL_REQUIREMENT_IDS = tuple(item["id"] for item in _CANONICAL_REQUIREMENTS)


def _fact_value(facts: dict, field: str):
    """Return a normalized fact value without accepting raw-value shortcuts."""
    if not isinstance(facts, dict):
        return None
    record = facts.get(field)
    if not isinstance(record, dict):
        return None
    return record.get("value")


def applicable_requirements(facts: dict, question_scope: str) -> list[dict]:
    """Select catalog records conservatively for a normalized trip fact set.

    Selection is deliberately narrow: question scope and the one explicit
    synthetic unsupported-terminal fixture choose records.  Fact values never
    make an evidence-readiness requirement pass, and missing applicability
    facts retain requirements for unresolved assessment.
    """
    selected_ids = _SCOPE_REQUIREMENT_IDS.get(question_scope, _ALL_REQUIREMENT_IDS)

    # This fixture explicitly represents a terminal outside this catalog.  The
    # shared context record carries the unsupported-domain limit; the assessment
    # layer reports the coverage gap.  Missing or arbitrary terminal values do
    # not take this branch and therefore cannot make requirements disappear.
    if _fact_value(facts, "terminal_id") == "synthetic_other_terminal":
        selected_ids = ("trip_context",)

    selected = set(selected_ids)
    return [copy.deepcopy(item) for item in _CANONICAL_REQUIREMENTS
            if item["id"] in selected]


def _validate_catalog() -> None:
    ids = _ALL_REQUIREMENT_IDS
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate requirement ID")
    allowed_owners = {"driver", "dispatcher", "carrier", "authority"}
    allowed_implementations = {"induction_identifier_match_v1", "evidence_readiness_only"}
    for requirement in _CANONICAL_REQUIREMENTS:
        if requirement["owner"] not in allowed_owners:
            raise RuntimeError("Unsupported requirement owner")
        if requirement["implementation"] not in allowed_implementations:
            raise RuntimeError("Unsupported requirement implementation")
        fields = set(requirement["required_fields"]) | set(requirement["verification_fields"])
        if fields - set(requirement["question_templates"]):
            raise RuntimeError("Every requested field needs a question template")
        if set(requirement["dependencies"]) - set(ids):
            raise RuntimeError("Requirement dependency is missing")


_validate_catalog()
