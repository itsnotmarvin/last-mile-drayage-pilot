"""Strict synthetic trip-fact normalization with statement provenance.

The normalizer accepts only the small, documented intake vocabulary.  Its
output is safe to persist as JSON, but it is still a collection of user
statements: normalization never upgrades a report into verified evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import re

from .service import InputError, timestamp
from .axle_layout import INPUT_SCHEMA as AXLE_LAYOUT_SCHEMA, normalize_layout


REPORTER_ROLES = ("driver", "dispatcher", "other", "unknown")
SUBJECT_ROLES = ("truck_driver", "other")
TERMINAL_IDS = ("facility_apm_elizabeth", "synthetic_other_terminal")
ROUTE_IDS = ("path_a_exit13a_to_apm", "path_b_us1_9_to_apm", "other")
PERMIT_TYPES = ("none", "nj_single_trip", "nj_ocean_container_annual", "other")
MOVE_TYPES = ("import_pickup", "empty_pickup", "export_dropoff", "empty_return", "unknown")

MAX_SOURCE_TEXT = 8_000
MAX_ROUTE_DESCRIPTION = 2_000
MAX_AXLES = 32
MAX_WEIGHT_LB = Decimal("10000000")
MAX_DIMENSION_INCH = Decimal("1000000")
KG_TO_LB = Decimal("2.2046226218487757")
FT_TO_INCH = Decimal("12")

_ID_PATTERNS = {
    "load_id": re.compile(r"syn-load-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?\Z"),
    "move_id": re.compile(r"syn-move-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?\Z"),
    "driver_id": re.compile(r"syn-driver-[a-z-]{1,40}\Z"),
    "vehicle_id": re.compile(r"syn-vehicle-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?\Z"),
    "trailer_id": re.compile(r"syn-trailer-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?\Z"),
    "current_sealink_id": re.compile(r"SYN-SL-[A-Z]{1,8}\Z"),
}

_WEIGHT_FIELDS = frozenset(("gross_weight", "axle_weights"))
_DIMENSION_FIELDS = frozenset((
    "axle_spacings", "width", "height", "overall_length", "semitrailer_length",
))
_ARRAY_QUANTITY_FIELDS = frozenset(("axle_weights", "axle_spacings"))
_BOOLEAN_FIELDS = frozenset((
    "cargo_hazardous", "container_sealed", "load_divisible", "company_changed",
    "twic_reported", "sealink_registered_reported", "induction_reported",
    "dtr_reported", "rfid_reported", "appointment_reported",
    "transaction_release_reported", "permit_route_reported",
    "turnpike_approval_reported", "local_approval_reported",
    "port_approval_reported", "terminal_approval_reported", "port_street_in_route",
))
_TIMESTAMP_FIELDS = frozenset(("trip_at", "route_conditions_checked_at"))

FACT_FIELDS = (
    "load_id", "move_id", "move_type",
    "terminal_id", "subject_role", "driver_id", "vehicle_id", "trailer_id",
    "current_sealink_id", "trip_at", "gross_weight", "axle_weights",
    "axle_spacings", "axle_count", "axle_layout", "width", "height", "overall_length",
    "semitrailer_length", "cargo_hazardous", "container_sealed", "load_divisible",
    "route_id", "route_description", "twic_reported",
    "sealink_registered_reported", "induction_reported", "dtr_reported",
    "rfid_reported", "appointment_reported", "transaction_release_reported",
    "company_changed", "engine_model_year", "permit_type", "permit_route_reported",
    "turnpike_approval_reported", "local_approval_reported",
    "port_approval_reported", "terminal_approval_reported", "port_street_in_route",
    "route_conditions_checked_at",
)


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def _quantity_schema(units: tuple[str, ...]) -> dict:
    return {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": list(units)},
        },
        "required": ["value", "unit"],
        "additionalProperties": False,
    }


_WEIGHT_SCHEMA = _quantity_schema(("lb", "kg"))
_DIMENSION_SCHEMA = _quantity_schema(("in", "ft"))

FACTS_SCHEMA = {
    "type": "object",
    "description": (
        "Partial synthetic trip facts. Null means explicitly unknown. Quantities "
        "must always include a numeric value and one of the listed units."
    ),
    "properties": {
        "terminal_id": _nullable({"type": "string", "enum": list(TERMINAL_IDS)}),
        "subject_role": _nullable({"type": "string", "enum": list(SUBJECT_ROLES)}),
        "driver_id": _nullable({"type": "string", "pattern": r"^syn-driver-[a-z-]{1,40}$"}),
        "vehicle_id": _nullable({"type": "string", "pattern": r"^syn-vehicle-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$"}),
        "trailer_id": _nullable({"type": "string", "pattern": r"^syn-trailer-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$"}),
        "current_sealink_id": _nullable({"type": "string", "pattern": r"^SYN-SL-[A-Z]{1,8}$"}),
        "trip_at": _nullable({
            "type": "string",
            "description": "ISO 8601 timestamp with seconds and an explicit timezone.",
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$",
        }),
        "gross_weight": _nullable(_WEIGHT_SCHEMA),
        "axle_weights": _nullable({
            "type": "array", "items": _WEIGHT_SCHEMA, "minItems": 1, "maxItems": MAX_AXLES,
        }),
        "axle_spacings": _nullable({
            "type": "array", "items": _DIMENSION_SCHEMA, "minItems": 1,
            "maxItems": MAX_AXLES,
        }),
        "axle_count": _nullable({"type": "integer", "minimum": 1, "maximum": MAX_AXLES}),
        "axle_layout": _nullable(AXLE_LAYOUT_SCHEMA),
        "width": _nullable(_DIMENSION_SCHEMA),
        "height": _nullable(_DIMENSION_SCHEMA),
        "overall_length": _nullable(_DIMENSION_SCHEMA),
        "semitrailer_length": _nullable(_DIMENSION_SCHEMA),
        "cargo_hazardous": _nullable({"type": "boolean"}),
        "container_sealed": _nullable({"type": "boolean"}),
        "load_divisible": _nullable({"type": "boolean"}),
        "route_id": _nullable({"type": "string", "enum": list(ROUTE_IDS)}),
        "route_description": _nullable({
            "type": "string", "minLength": 1, "maxLength": MAX_ROUTE_DESCRIPTION,
            "pattern": r"^(?=[\s\S]*\S)[^\x00]*$",
        }),
        "twic_reported": _nullable({"type": "boolean"}),
        "sealink_registered_reported": _nullable({"type": "boolean"}),
        "induction_reported": _nullable({"type": "boolean"}),
        "dtr_reported": _nullable({"type": "boolean"}),
        "rfid_reported": _nullable({"type": "boolean"}),
        "appointment_reported": _nullable({"type": "boolean"}),
        "transaction_release_reported": _nullable({"type": "boolean"}),
        "company_changed": _nullable({"type": "boolean"}),
        "engine_model_year": _nullable({
            "type": "integer", "minimum": 1886, "maximum": 2100,
        }),
        "permit_type": _nullable({"type": "string", "enum": list(PERMIT_TYPES)}),
        "permit_route_reported": _nullable({"type": "boolean"}),
        "turnpike_approval_reported": _nullable({"type": "boolean"}),
        "local_approval_reported": _nullable({"type": "boolean"}),
        "port_approval_reported": _nullable({"type": "boolean"}),
        "terminal_approval_reported": _nullable({"type": "boolean"}),
        "port_street_in_route": _nullable({"type": "boolean"}),
        "route_conditions_checked_at": _nullable({
            "type": "string",
            "description": "ISO 8601 timestamp with seconds and an explicit timezone.",
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$",
        }),
    },
    "additionalProperties": False,
}


for _identity in ("load_id", "move_id"):
    FACTS_SCHEMA["properties"][_identity] = _nullable({"type": "string", "pattern": "^" + _ID_PATTERNS[_identity].pattern.replace("\\Z", "$")})
FACTS_SCHEMA["properties"]["move_type"] = _nullable({"type": "string", "enum": list(MOVE_TYPES)})

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _bounded_decimal(value, field: str, maximum: Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{field} quantity value must be a finite JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise InputError(f"{field} quantity value must be a finite JSON number")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InputError(f"{field} quantity value must be a finite JSON number") from exc
    if not parsed.is_finite():
        raise InputError(f"{field} quantity value must be a finite JSON number")
    if parsed < 0 or parsed > maximum:
        raise InputError(f"{field} quantity value is outside the supported prototype bounds")
    return parsed


def _quantity(value, field: str, *, weight: bool) -> tuple[int | float, str]:
    units = ("lb", "kg") if weight else ("in", "ft")
    example = "{'value': number, 'unit': 'lb' or 'kg'}" if weight else (
        "{'value': number, 'unit': 'in' or 'ft'}"
    )
    if not isinstance(value, dict) or set(value) != {"value", "unit"}:
        raise InputError(
            f"{field} must be {example}; unitless or extra-field quantities are ambiguous"
        )
    if value["unit"] not in units:
        raise InputError(f"{field} unit must be one of: {', '.join(units)}")

    if weight:
        raw_limit = MAX_WEIGHT_LB if value["unit"] == "lb" else MAX_WEIGHT_LB / KG_TO_LB
        normalized = _bounded_decimal(value["value"], field, raw_limit)
        if value["unit"] == "kg":
            normalized *= KG_TO_LB
        return _json_number(normalized), "lb"

    raw_limit = MAX_DIMENSION_INCH if value["unit"] == "in" else MAX_DIMENSION_INCH / FT_TO_INCH
    normalized = _bounded_decimal(value["value"], field, raw_limit)
    if value["unit"] == "ft":
        normalized *= FT_TO_INCH
    return _json_number(normalized), "inch"


def _quantity_array(value, field: str, *, weight: bool) -> tuple[list[int | float], str]:
    if not isinstance(value, list):
        unit_text = "lb/kg" if weight else "in/ft"
        raise InputError(
            f"{field} must be an array of {{value: number, unit: {unit_text}}} objects; "
            "raw numeric arrays are ambiguous"
        )
    if not value or len(value) > MAX_AXLES:
        raise InputError(f"{field} must contain between 1 and {MAX_AXLES} quantities")
    if any(not isinstance(item, dict) for item in value):
        raise InputError(
            f"{field} raw numeric arrays are ambiguous; every item must include value and unit"
        )
    normalized = [_quantity(item, field, weight=weight)[0] for item in value]
    return normalized, "lb" if weight else "inch"


def _enum(value, field: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise InputError(f"{field} must be one of: {', '.join(allowed)}, or null")
    return value


def _synthetic_id(value, field: str) -> str:
    if not isinstance(value, str) or _ID_PATTERNS[field].fullmatch(value) is None:
        prefix = {
            "driver_id": "syn-driver-*",
            "vehicle_id": "syn-vehicle-*",
            "trailer_id": "syn-trailer-*",
            "load_id": "syn-load-*",
            "move_id": "syn-move-*",
            "current_sealink_id": "SYN-SL-*",
        }[field]
        raise InputError(
            f"{field} accepts only a short {prefix} synthetic alias; never submit a real identifier"
        )
    return value


def _normalize_value(field: str, value) -> tuple[object, str | None]:
    if value is None:
        return None, None
    if field == 'axle_layout':
        return normalize_layout(value, _quantity)
    if field in _WEIGHT_FIELDS:
        if field in _ARRAY_QUANTITY_FIELDS:
            return _quantity_array(value, field, weight=True)
        return _quantity(value, field, weight=True)
    if field in _DIMENSION_FIELDS:
        if field in _ARRAY_QUANTITY_FIELDS:
            return _quantity_array(value, field, weight=False)
        return _quantity(value, field, weight=False)
    if field in _BOOLEAN_FIELDS:
        if type(value) is not bool:
            raise InputError(f"{field} must be boolean or null")
        return value, None
    if field in _TIMESTAMP_FIELDS:
        try:
            return timestamp(value).isoformat(), None
        except InputError as exc:
            raise InputError(
                f"{field} must be a valid ISO timestamp with seconds and an explicit timezone, or null"
            ) from exc
    if field in _ID_PATTERNS:
        return _synthetic_id(value, field), None
    if field == "terminal_id":
        return _enum(value, field, TERMINAL_IDS), None
    if field == "subject_role":
        return _enum(value, field, SUBJECT_ROLES), None
    if field == "route_id":
        return _enum(value, field, ROUTE_IDS), None
    if field == "permit_type":
        return _enum(value, field, PERMIT_TYPES), None
    if field == "move_type":
        return _enum(value, field, MOVE_TYPES), None
    if field == "route_description":
        if (not isinstance(value, str) or not value.strip()
                or len(value) > MAX_ROUTE_DESCRIPTION or "\x00" in value):
            raise InputError(
                f"route_description must be nonblank text of at most {MAX_ROUTE_DESCRIPTION} characters, or null"
            )
        return value, None
    if field == "axle_count":
        if type(value) is not int or not 1 <= value <= MAX_AXLES:
            raise InputError(f"axle_count must be an integer from 1 through {MAX_AXLES}, or null")
        return value, None
    if field == "engine_model_year":
        if type(value) is not int or not 1886 <= value <= 2100:
            raise InputError("engine_model_year must be an integer from 1886 through 2100, or null")
        return value, None
    raise AssertionError(f"Normalizer missing implementation for {field}")


def normalize_facts(facts: dict, reported_by: str, source_message: str) -> dict:
    """Validate partial raw facts and attach user-statement provenance.

    Null is retained as an explicit unknown.  The function deliberately rejects
    prebuilt provenance/evidence envelopes and unitless quantities so a client
    cannot assert that its own report was independently verified.
    """
    if not isinstance(facts, dict):
        raise InputError("facts must be an object")
    unknown = set(facts) - set(FACT_FIELDS)
    if unknown:
        raise InputError(
            "Unexpected fact fields; callers cannot supply evidence, verification, or rule overrides: "
            + ", ".join(sorted(str(field) for field in unknown))
        )
    if reported_by not in REPORTER_ROLES or not isinstance(reported_by, str):
        raise InputError(f"reported_by must be one of: {', '.join(REPORTER_ROLES)}")
    if (not isinstance(source_message, str) or not source_message.strip()
            or len(source_message) > MAX_SOURCE_TEXT or "\x00" in source_message):
        raise InputError(
            f"source_message must be nonblank text of at most {MAX_SOURCE_TEXT} characters"
        )

    recorded_at = _utc_now()
    normalized = {}
    for field, raw_value in facts.items():
        value, unit = _normalize_value(field, raw_value)
        normalized[field] = {
            "value": value,
            "unit": unit,
            "basis": "user_reported",
            "reported_by": reported_by,
            "source_text": source_message,
            "recorded_at": recorded_at,
        }
    from .input_review import reject_inconsistent_facts
    reject_inconsistent_facts(normalized)
    return normalized
