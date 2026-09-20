"""Bounded terminal predicates over admitted synthetic verification receipts.

Admission binds every receipt to the case, release, assignment and trip interval
before this module runs.  These predicates decide only the narrow source-backed
questions named below; none of them issues entry or dispatch permission.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .common import digest
from .service import InputError, timestamp


NY = ZoneInfo("America/New_York")

_LIMITS = {
    "dtr_registration_and_rfid": (
        "The DTR branch applies to a verified drayage truck; the RFID branch applies only when that truck is also Class 8.",
        "Registration, amendment and RFID predicates do not establish terminal entry or current policy outside the retained clauses.",
    ),
    "dtr_engine_policy": (
        "Subrules 34-1101 and 34-1140 remain in unresolved internal tension; neither branch can produce an overall met or not-met result.",
        "Engine model year is used only where 34-1140 states a year cutoff. It does not prove the 34-1101 emissions standard.",
        "The 34-1101 effective date is compared with the registration event, while 34-1140 is compared with terminal entry time.",
    ),
    "driver_twic": (
        "This predicate covers unescorted access to a regulated secure area. Any claimed exception requires separate review.",
        "A valid credential record does not establish other driver, terminal or dispatch requirements.",
    ),
    "sealink_registration": (
        "This predicate checks only an active SeaLink record and TWIC registration on that record.",
        "TWIC validity, physical possession and all other terminal requirements remain separate.",
    ),
    "apm_appointment": (
        "This predicate checks one case-bound APM move against one confirmed start-inclusive, end-exclusive slot.",
        "A confirmed appointment does not establish transaction availability, gate acceptance or terminal entry.",
    ),
    "transaction_release": (
        "This draft predicate is limited to import pickup and the retained fully-available/no-holds source text.",
        "The five receipt hold fields do not exhaust every possible hold, and this result does not establish gate acceptance or terminal entry.",
        "The supporting supplement is draft, not human approved and not operational source promotion.",
    ),
}


def _check(checks, check_id, predicate, detail):
    checks.append({
        "id": check_id,
        "status": "unresolved" if predicate is None else "met" if predicate else "not_met",
        "detail": detail,
    })


def _result(checks, ids=(), limits=(), reason_codes=(), force_status=None):
    statuses = [check["status"] for check in checks]
    status = force_status or (
        "not_met" if "not_met" in statuses
        else "unresolved" if not statuses or "unresolved" in statuses
        else "met"
    )
    derived = [check["id"].upper() for check in checks if check["status"] != "met"]
    return {
        "status": status,
        "reason_codes": list(dict.fromkeys([*reason_codes, *derived])),
        "checks": checks,
        "limits": list(limits),
        "used_receipt_ids": sorted(set(ids)),
    }


def _one(evidence, kind, checks, ids):
    records = evidence.get(kind, [])
    if not records:
        _check(
            checks,
            kind + "_verification_required",
            None,
            "No admitted " + kind + " verification receipt is available for this trip.",
        )
        return None, "missing"
    if len({digest(record["payload"]) for record in records}) > 1:
        _check(
            checks,
            kind + "_verification_conflict",
            None,
            "Current admitted " + kind + " receipts disagree.",
        )
        return None, "conflict"
    ids.extend(record["id"] for record in records)
    return records[0]["payload"], "ok"


def _trip_time(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        return timestamp(value)
    except InputError:
        return None


def _local_date(value):
    parsed = _trip_time(value)
    return parsed.astimezone(NY).date() if parsed else None


def _fact_value(facts, field):
    record = facts.get(field) if isinstance(facts, dict) else None
    return record.get("value") if isinstance(record, dict) else None


def _apm_scope(facts, checks):
    terminal = _fact_value(facts, "terminal_id")
    if terminal != "facility_apm_elizabeth":
        _check(
            checks,
            "apm_terminal_scope",
            None,
            "The APM terminal scope is missing or unsupported; no appointment or import-availability result is inferred.",
        )
        return False
    _check(checks, "apm_terminal_scope", True, "The saved trip is assigned to APM Elizabeth.")
    return True


def _amendment_check(payload, trip):
    event = payload["registration_event"]
    changed_raw = payload["registration_changed_at"]
    amended_raw = payload["registration_amended_at"]

    if event == "unknown" and changed_raw is None and amended_raw is None:
        return None, "The receipt does not establish whether registered information, including ownership, changed."
    if event != "ownership_change" and changed_raw is None and amended_raw is None:
        return True, "No ownership-change or other registration-change event is asserted by this receipt."
    if changed_raw is None or amended_raw is None:
        return None, "A registration change requires both the change and amendment dates; missing ownership-change information stays unresolved."

    changed = _trip_time(changed_raw)
    amended = _trip_time(amended_raw)
    if changed is None or amended is None:
        return None, "The registration change or amendment timestamp is invalid."
    if trip is not None and (changed > trip or amended > trip):
        return None, "A future change or amendment cannot establish the registration state at the trip time."
    registered = _trip_time(payload["registered_at"])
    if registered is not None and changed < registered:
        return None, "The registration change predates registration, so the sequence cannot be resolved."
    if amended < changed:
        return None, "The amendment predates the registration change, so the sequence cannot be resolved."

    changed_date = changed.astimezone(NY).date()
    amended_date = amended.astimezone(NY).date()
    elapsed_days = (amended_date - changed_date).days
    return elapsed_days <= 10, (
        "The amendment occurred " + str(elapsed_days)
        + " calendar day(s) after the registration change; the retained limit is 10."
    )


def _dtr_registration(facts, evidence, trip_at):
    checks, ids = [], []
    payload, state = _one(evidence, "dtr", checks, ids)
    extra = (
        ["CONFLICTING_VERIFICATION_RECEIPTS"] if state == "conflict"
        else ["VERIFICATION_RECEIPT_MISSING"] if state == "missing"
        else []
    )
    if payload is None:
        return _result(checks, ids, _LIMITS["dtr_registration_and_rfid"], extra)

    if payload["drayage_truck"] is not True:
        _check(
            checks,
            "dtr_drayage_truck_scope",
            None,
            "The retained DTR clauses apply to drayage trucks; this receipt leaves that status unknown or outside the bounded scope.",
        )
        return _result(
            checks,
            ids,
            _LIMITS["dtr_registration_and_rfid"],
            ["DTR_APPLICABILITY_UNRESOLVED"],
        )
    _check(checks, "dtr_drayage_truck_scope", True, "The receipt identifies the vehicle as a drayage truck.")

    _check(
        checks,
        "dtr_registered",
        payload["registered"],
        "The truck must have a DTR registration record.",
    )
    _check(
        checks,
        "dtr_active",
        payload["active"],
        "The DTR registration must be active for the admitted trip interval.",
    )

    trip_date = _local_date(trip_at)
    registered_date = _local_date(payload["registered_at"])
    _check(
        checks,
        "dtr_registered_before_entry_date",
        None if trip_date is None or registered_date is None else registered_date < trip_date,
        "DTR registration must predate the local calendar date of entry; an earlier timestamp on the same date is insufficient.",
    )

    amendment, detail = _amendment_check(payload, _trip_time(trip_at))
    _check(checks, "dtr_change_amended_within_ten_days", amendment, detail)

    if payload["class_8"] is None:
        _check(
            checks,
            "rfid_class_8_scope",
            None,
            "Class 8 status is unknown, so applicability of the retained RFID clause is unresolved.",
        )
    elif payload["class_8"] is False:
        _check(
            checks,
            "rfid_class_8_scope",
            True,
            "The receipt establishes that the truck is not Class 8, so the bounded Class 8 RFID branch is not applied.",
        )
    else:
        _check(checks, "rfid_class_8_scope", True, "The receipt places this drayage truck in the Class 8 RFID scope.")
        _check(checks, "rfid_assigned", payload["rfid_assigned"], "A current RFID tag must be assigned to the truck.")
        _check(checks, "rfid_valid", payload["rfid_valid"], "The assigned RFID tag must be valid.")
        _check(checks, "rfid_properly_mounted", payload["rfid_mounted"], "The valid RFID tag must be properly mounted on the vehicle.")

    return _result(checks, ids, _LIMITS["dtr_registration_and_rfid"], extra)


def _subrule_34_1101(payload, trip):
    if payload is None:
        return None, "No single current DTR receipt is available for the 34-1101 registration branch."
    if payload["drayage_truck"] is not True:
        return None, "34-1101 is limited to drayage trucks, and that applicability is not established."

    registered = _trip_time(payload["registered_at"])
    if registered is None:
        return None, "The DTR registration event time is missing; terminal entry time cannot substitute for it."
    if trip is not None and registered > trip:
        return None, "The stated registration event is after the trip and cannot establish the trip-time record."

    effective = datetime(2023, 7, 2, 0, 1, tzinfo=NY).astimezone(timezone.utc)
    if registered < effective:
        return None, (
            "The registration event predates 34-1101's July 2, 2023 12:01 AM threshold; "
            "the later trip date does not turn it into a new registration event."
        )

    standard = payload["meets_2014_emissions_standard"]
    year = payload["engine_model_year"]
    return standard, (
        "The registration event falls within 34-1101. The adapter's emissions-standard field is "
        + ("true" if standard is True else "false" if standard is False else "unknown")
        + "; engine model year " + str(year) + " alone cannot establish that emissions standard."
    )


def _subrule_34_1140(payload, trip):
    if payload is None:
        return None, "No single current DTR receipt is available for the 34-1140 terminal-entry branch."
    if payload["drayage_truck"] is not True:
        return None, "34-1140 is limited to drayage trucks, and that applicability is not established."
    if trip is None:
        return None, "Trip time is missing, so the applicable 34-1140 deadline block cannot be selected."

    thresholds = (
        (datetime(2028, 5, 1, 0, 1, tzinfo=NY).astimezone(timezone.utc), 2000),
        (datetime(2027, 5, 1, 0, 1, tzinfo=NY).astimezone(timezone.utc), 1999),
        (datetime(2023, 7, 2, 0, 1, tzinfo=NY).astimezone(timezone.utc), 1998),
    )
    selected = next(((start, cutoff) for start, cutoff in thresholds if trip >= start), None)
    if selected is None:
        return None, "Trip time predates the first retained 34-1140 deadline block."

    _, cutoff = selected
    registry_ok = None if payload["registered"] is None or payload["active"] is None else (
        payload["registered"] and payload["active"]
    )
    year_ok = payload["engine_model_year"] > cutoff
    detail = (
        "For this trip, 34-1140 checks a compliant active DTR record and blocks engine model year "
        + str(cutoff) + " or older. The contract has no reviewed Alternative Drayage Truck predicate for clause (c)."
    )
    if registry_ok is False or year_ok is False:
        return False, detail
    return None, detail


def _dtr_engine(facts, evidence, trip_at):
    checks, ids = [], []
    payload, state = _one(evidence, "dtr", checks, ids)
    trip = _trip_time(trip_at)

    first, first_detail = _subrule_34_1101(payload, trip)
    second, second_detail = _subrule_34_1140(payload, trip)
    _check(checks, "subrule_34_1101_registration_branch", first, first_detail)
    _check(checks, "subrule_34_1140_entry_branch", second, second_detail)
    _check(
        checks,
        "subrules_34_1101_34_1140_reconciliation",
        None,
        "The retained release expressly leaves the two tariff branches in unresolved internal tension.",
    )

    reasons = ["UNRESOLVED_DTR_TARIFF_CONFLICT"]
    if state == "conflict":
        reasons.insert(0, "CONFLICTING_VERIFICATION_RECEIPTS")
    elif state == "missing":
        reasons.insert(0, "VERIFICATION_RECEIPT_MISSING")

    return _result(
        checks,
        ids,
        _LIMITS["dtr_engine_policy"],
        reasons,
        force_status="unresolved",
    )


def _twic(facts, evidence, trip_at):
    checks, ids = [], []
    payload, state = _one(evidence, "twic", checks, ids)
    extra = (
        ["CONFLICTING_VERIFICATION_RECEIPTS"] if state == "conflict"
        else ["VERIFICATION_RECEIPT_MISSING"] if state == "missing"
        else []
    )
    if payload is None:
        return _result(checks, ids, _LIMITS["driver_twic"], extra)

    if payload["unescorted_secure_access"] is not True:
        _check(
            checks,
            "twic_unescorted_secure_scope",
            None,
            "The retained federal predicate is limited to unescorted secure-area access; that scope is unknown or not established here.",
        )
        return _result(checks, ids, _LIMITS["driver_twic"], ["TWIC_APPLICABILITY_UNRESOLVED"])
    _check(checks, "twic_unescorted_secure_scope", True, "The intended access is unescorted access to a regulated secure area.")

    if payload["exception_claimed"]:
        _check(
            checks,
            "twic_exception_review",
            None,
            "An exception is claimed, but the retained source and contract do not decide whether it applies.",
        )
        return _result(checks, ids, _LIMITS["driver_twic"], ["TWIC_EXCEPTION_REQUIRES_REVIEW"])
    _check(checks, "twic_exception_review", True, "No exception is claimed for this bounded predicate.")

    status = {
        "valid": True,
        "revoked": False,
        "expired": False,
        "not_found": False,
        "unknown": None,
    }[payload["status"]]
    _check(checks, "twic_status", status, "The credential-verifier record must report a valid TWIC.")

    if payload["status"] == "valid":
        trip = _trip_time(trip_at)
        expiry = _trip_time(payload["credential_expires_at"])
        _check(
            checks,
            "twic_unexpired_at_trip",
            None if trip is None or expiry is None else trip < expiry,
            "The trip must occur strictly before credential expiry; equality is expired for this predicate.",
        )
    _check(
        checks,
        "twic_physically_present",
        payload["physically_present"],
        "The driver must physically possess the credential for the intended access.",
    )
    return _result(checks, ids, _LIMITS["driver_twic"], extra)


def _sealink(facts, evidence, trip_at):
    checks, ids = [], []
    payload, state = _one(evidence, "sealink", checks, ids)
    extra = (
        ["CONFLICTING_VERIFICATION_RECEIPTS"] if state == "conflict"
        else ["VERIFICATION_RECEIPT_MISSING"] if state == "missing"
        else []
    )
    if payload is not None:
        _check(checks, "sealink_active", payload["active"], "The driver's current case-bound SeaLink record must be active.")
        _check(checks, "sealink_twic_registered", payload["twic_registered"], "The TWIC must be registered with the Port Authority on that SeaLink record.")
    return _result(checks, ids, _LIMITS["sealink_registration"], extra)


def _appointment(facts, evidence, trip_at):
    checks, ids = [], []
    if not _apm_scope(facts, checks):
        return _result(
            checks,
            ids,
            _LIMITS["apm_appointment"],
            ["APM_APPLICABILITY_UNRESOLVED"],
        )
    payload, state = _one(evidence, "appointment", checks, ids)
    extra = (
        ["CONFLICTING_VERIFICATION_RECEIPTS"] if state == "conflict"
        else ["VERIFICATION_RECEIPT_MISSING"] if state == "missing"
        else []
    )
    if payload is not None:
        status = {
            "confirmed": True,
            "cancelled": False,
            "not_found": False,
            "unknown": None,
        }[payload["status"]]
        _check(checks, "appointment_confirmed", status, "The case-bound APM move must have a confirmed appointment.")
        trip = _trip_time(trip_at)
        start = _trip_time(payload["slot_start"])
        end = _trip_time(payload["slot_end"])
        _check(
            checks,
            "appointment_slot",
            None if trip is None or start is None or end is None else start <= trip < end,
            "The confirmed slot is start-inclusive and end-exclusive for the admitted move.",
        )
    return _result(checks, ids, _LIMITS["apm_appointment"], extra)


def _transaction(facts, evidence, trip_at):
    checks, ids = [], []
    if not _apm_scope(facts, checks):
        return _result(
            checks,
            ids,
            _LIMITS["transaction_release"],
            ["APM_APPLICABILITY_UNRESOLVED"],
        )
    payload, state = _one(evidence, "transaction", checks, ids)
    extra = (
        ["CONFLICTING_VERIFICATION_RECEIPTS"] if state == "conflict"
        else ["VERIFICATION_RECEIPT_MISSING"] if state == "missing"
        else []
    )
    if payload is None:
        return _result(checks, ids, _LIMITS["transaction_release"], extra)

    if payload["move_type"] != "import_pickup":
        _check(
            checks,
            "transaction_import_pickup_scope",
            None,
            "The retained draft source text covers import pickup only; no result is inferred for " + payload["move_type"] + ".",
        )
        return _result(checks, ids, _LIMITS["transaction_release"], ["TRANSACTION_MOVE_TYPE_UNRESOLVED"])
    _check(checks, "transaction_import_pickup_scope", True, "This move is an import pickup within the narrow draft predicate.")
    _check(
        checks,
        "transaction_fully_available",
        payload["fully_available"],
        "The terminal transaction record must explicitly report the import container as fully available.",
    )
    _check(
        checks,
        "transaction_hold_coverage_complete",
        True if payload["holds_complete"] else None,
        "All five modeled hold fields must be explicit before their absence can be established.",
    )
    for field in ("freight_hold", "customer_hold", "demurrage_hold", "customs_hold", "other_hold"):
        hold = payload[field]
        _check(
            checks,
            "transaction_no_" + field,
            None if hold is None else not hold,
            field.replace("_", " ").capitalize() + " must be explicitly false for this import pickup.",
        )
    return _result(checks, ids, _LIMITS["transaction_release"], extra)


EVALUATORS = {
    "dtr_registration_and_rfid": _dtr_registration,
    "dtr_engine_policy": _dtr_engine,
    "driver_twic": _twic,
    "sealink_registration": _sealink,
    "apm_appointment": _appointment,
    "transaction_release": _transaction,
}


def evaluate_terminal(requirement_id, facts, evidence, trip_at):
    """Evaluate one supported terminal requirement against admitted receipts."""

    try:
        evaluator = EVALUATORS[requirement_id]
    except KeyError as exc:
        raise ValueError("Unsupported terminal requirement: " + str(requirement_id)) from exc
    return evaluator(facts, evidence, trip_at)
