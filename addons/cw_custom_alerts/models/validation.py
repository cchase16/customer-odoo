# -*- coding: utf-8 -*-
"""Safe, deterministic validation for alert configuration."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import math
import re
from typing import Any, Mapping

from .contracts import SUPPORTED_EVENT_TYPES


class AlertConfigurationError(ValueError):
    """Raised when a rule contains unsupported or unsafe configuration."""


SUPPORTED_DOMAIN_OPERATORS = frozenset({
    "=", "!=", ">", ">=", "<", "<=", "=?", "=like", "like", "not like",
    "=ilike", "ilike", "not ilike", "in", "not in", "child_of", "parent_of",
})
LOGICAL_OPERATORS = frozenset({"&", "|", "!"})
DOMAIN_MAX_TOKENS = 100
DOMAIN_MAX_LEAVES = 50
DOMAIN_MAX_TRAVERSAL = 3
DOMAIN_MAX_IN_VALUES = 100
ELIGIBLE_SCALAR_TYPES = frozenset({
    "boolean", "char", "text", "integer", "float", "monetary", "selection",
    "date", "datetime", "many2one",
})
DATE_EVENT_TYPES = frozenset({
    "field_postponed", "field_advanced", "date_reached", "date_relative_before", "date_relative_after",
})
FIELD_EVENT_TYPES = frozenset({
    "field_changed", "field_becomes", "field_is_no_longer", "field_postponed", "field_advanced",
})
RECORD_EVENT_TYPES = frozenset({"record_created", "record_deleted"})
COMPARISON_EVENT_TYPES = frozenset({"field_becomes", "field_is_no_longer"})
RELATIVE_DATE_EVENT_TYPES = frozenset({"date_relative_before", "date_relative_after"})
ALLOWED_SCOPE_TYPES = frozenset({"current_record", "captured_domain"})
ALLOWED_OFFSET_UNITS = frozenset({"minutes", "hours", "days", "months"})
ALLOWED_OFFSET_DIRECTIONS = frozenset({"before", "after"})
PLACEHOLDER_NAMES = frozenset({
    "rule_name", "model_name", "record_name", "field_name", "old_value", "new_value", "event_time",
})
PLACEHOLDER_PATTERN = re.compile(r"\$\{([^{}]+)\}")
UNSAFE_TEXT_PATTERN = re.compile(
    r"(?:\{\{|\}\}|<%|%>|<\s*/?\s*[A-Za-z][^>]*>|__\w+__|"
    r"\b(?:eval|exec|lambda|import)\s*\b|\benv\s*[\[(.]|\bsudo\s*\()",
    re.IGNORECASE,
)


def _fail(message: str) -> None:
    raise AlertConfigurationError(message)


def _is_safe_literal(value: Any, *, depth: int = 0) -> bool:
    if depth > 2:
        return False
    if value is None or isinstance(value, (bool, int, str)):
        return not isinstance(value, str) or not UNSAFE_TEXT_PATTERN.search(value)
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_safe_literal(item, depth=depth + 1) for item in value)
    return False


def _validate_domain_leaf(leaf: Any, target_model: Any, leaf_count: list[int]) -> None:
    if not isinstance(leaf, list) or len(leaf) != 3:
        _fail("Each domain condition must be a JSON list of field, operator, and value.")
    field_path, operator, value = leaf
    if not isinstance(field_path, str) or not field_path or field_path.startswith(".") or field_path.endswith("."):
        _fail("Domain field paths must be non-empty strings.")
    if not isinstance(operator, str) or operator not in SUPPORTED_DOMAIN_OPERATORS:
        _fail(f"Unsupported domain operator: {operator!r}.")
    if not _is_safe_literal(value):
        _fail("Domain values must contain only safe JSON literals.")
    if operator in {"in", "not in"}:
        if not isinstance(value, list) or not value or len(value) > DOMAIN_MAX_IN_VALUES:
            _fail("The 'in' and 'not in' operators require 1 to 100 literal values.")
    elif isinstance(value, list):
        _fail("List literals are only supported with 'in' and 'not in'.")
    if operator in {"like", "not like", "=like", "ilike", "not ilike", "=ilike"} and not isinstance(value, str):
        _fail("Pattern operators require a string literal.")

    parts = field_path.split(".")
    if len(parts) > DOMAIN_MAX_TRAVERSAL:
        _fail("Domain field traversal is limited to three components.")
    if target_model is None:
        leaf_count[0] += 1
        return
    model = target_model
    for index, part in enumerate(parts):
        if part in {"id", "create_uid", "create_date", "write_uid", "write_date"} and index == len(parts) - 1:
            continue
        field = getattr(model, "_fields", {}).get(part)
        if field is None:
            _fail(f"Unknown domain field: {field_path}.")
        if not getattr(field, "store", True):
            _fail(f"Domain field must be stored: {field_path}.")
        field_type = getattr(field, "type", None)
        if index < len(parts) - 1:
            if field_type != "many2one" or not getattr(field, "comodel_name", None):
                _fail("Only many-to-one fields may be traversed in a domain.")
            try:
                model = model.env[field.comodel_name]
            except (KeyError, ValueError):
                _fail(f"Unknown related model in domain field: {field_path}.")
        elif field_type not in ELIGIBLE_SCALAR_TYPES:
            _fail(f"Domain field type is not supported: {field_path}.")
    leaf_count[0] += 1


def _parse_prefix_domain(tokens: list[Any], index: int, target_model: Any, leaf_count: list[int], depth: int) -> int:
    if depth > DOMAIN_MAX_TRAVERSAL:
        _fail("Domain logical complexity is too deep.")
    if index >= len(tokens):
        _fail("Domain logical operators do not have enough operands.")
    token = tokens[index]
    if isinstance(token, str) and token in LOGICAL_OPERATORS:
        operand_count = 1 if token == "!" else 2
        index += 1
        for _ in range(operand_count):
            index = _parse_prefix_domain(tokens, index, target_model, leaf_count, depth + 1)
        return index
    if isinstance(token, str):
        _fail(f"Unknown domain token: {token!r}.")
    _validate_domain_leaf(token, target_model, leaf_count)
    if leaf_count[0] > DOMAIN_MAX_LEAVES:
        _fail("Domain complexity is limited to 50 conditions.")
    return index + 1


def canonicalize_domain(domain: Any, target_model: Any = None) -> list[Any] | None:
    """Validate and copy an Odoo-style JSON domain snapshot."""
    if domain is None:
        return None
    if not isinstance(domain, list):
        _fail("Domains must be JSON arrays.")
    if len(domain) > DOMAIN_MAX_TOKENS:
        _fail("Domain complexity is limited to 100 tokens.")
    if not domain:
        return []
    leaf_count = [0]
    logical_present = any(isinstance(token, str) and token in LOGICAL_OPERATORS for token in domain)
    if logical_present:
        if not isinstance(domain[0], str) or domain[0] not in LOGICAL_OPERATORS:
            _fail("Logical domain operators must use Odoo prefix notation.")
        end = _parse_prefix_domain(domain, 0, target_model, leaf_count, 0)
        if end != len(domain):
            _fail("Domain contains unused or ambiguously placed tokens.")
    else:
        for leaf in domain:
            _validate_domain_leaf(leaf, target_model, leaf_count)
            if leaf_count[0] > DOMAIN_MAX_LEAVES:
                _fail("Domain complexity is limited to 50 conditions.")
    return deepcopy(domain)


def combine_domains(*domains: Any, target_model: Any = None) -> list[Any]:
    """Return the validated implicit-AND combination of domain snapshots."""
    combined: list[Any] = []
    for domain in domains:
        canonical = canonicalize_domain(domain, target_model)
        if canonical:
            combined.extend(canonical)
    return combined


def validate_templates(*templates: str | None) -> None:
    for template in templates:
        if template is None:
            continue
        if not isinstance(template, str):
            _fail("Alert subject and message must be plain text.")
        if UNSAFE_TEXT_PATTERN.search(template):
            _fail("Alert text cannot contain executable or HTML template syntax.")
        for match in PLACEHOLDER_PATTERN.finditer(template):
            if match.group(1) not in PLACEHOLDER_NAMES:
                _fail(f"Unknown alert placeholder: ${{{match.group(1)}}}.")


def render_plain_text(template: str, values: Mapping[str, Any]) -> str:
    validate_templates(template)
    missing = [name for name in PLACEHOLDER_NAMES if f"${{{name}}}" in template and name not in values]
    if missing:
        _fail(f"Missing values for alert placeholders: {', '.join(sorted(missing))}.")
    return PLACEHOLDER_PATTERN.sub(lambda match: str(values.get(match.group(1), match.group(0))), template)


def validate_field_eligibility(field: Any, event_type: str) -> None:
    if field is None:
        _fail("This event requires a watched field.")
    if not getattr(field, "store", False):
        _fail("The watched field must be stored.")
    field_type = getattr(field, "type", getattr(field, "ttype", None))
    if field_type not in ELIGIBLE_SCALAR_TYPES:
        _fail("Binary, HTML, collection, and unsupported field types cannot be watched.")
    if event_type in DATE_EVENT_TYPES and field_type not in {"date", "datetime"}:
        _fail("Date events require a stored date or datetime field.")


def _validate_comparison_value(value: Any, field: Any) -> None:
    field_type = getattr(field, "type", getattr(field, "ttype", None))
    valid = {
        "boolean": isinstance(value, bool),
        "char": isinstance(value, str),
        "text": isinstance(value, str),
        "selection": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "float": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "monetary": isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
        "many2one": isinstance(value, int) and not isinstance(value, bool) and value > 0,
        "date": isinstance(value, str),
        "datetime": isinstance(value, str),
    }.get(field_type, False)
    if not valid:
        _fail("The comparison value does not match the watched field type.")
    if field_type == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            _fail("Date comparison values must use ISO date format.")
    if field_type == "datetime":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _fail("Datetime comparison values must use ISO datetime format.")


def _validate_expiry(value: Any, at_activation: bool, now: datetime | None) -> None:
    if value in (None, False) or not at_activation:
        return
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _fail("Expiry must be a valid datetime.")
    if not isinstance(value, datetime):
        _fail("Expiry must be a valid datetime.")
    comparison_now = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        comparison_now = comparison_now.replace(tzinfo=None)
    if value <= comparison_now:
        _fail("Expiry must be in the future when a rule is activated.")


def validate_rule_configuration(
    values: Mapping[str, Any], *, target_model: Any = None, watched_field: Any = None,
    at_activation: bool = False, now: datetime | None = None,
) -> dict[str, Any]:
    """Validate a rule payload and return canonical domain snapshots."""
    event_type = values.get("event_type")
    if event_type not in SUPPORTED_EVENT_TYPES:
        _fail(f"Unsupported alert event: {event_type!r}.")
    if target_model is not None and (
        getattr(target_model, "_transient", False)
        or getattr(target_model, "_abstract", False)
        or not getattr(target_model, "_auto", True)
    ):
        _fail("Alerts can only watch persistent concrete models.")
    if event_type in RECORD_EVENT_TYPES:
        if values.get("field_id") or watched_field is not None or values.get("comparison_value_json") not in (None, False):
            _fail("Record events cannot specify a watched field or comparison value.")
    else:
        validate_field_eligibility(watched_field, event_type)
        comparison = values.get("comparison_value_json")
        if event_type in COMPARISON_EVENT_TYPES and comparison is None:
            _fail("This field transition event requires a comparison value.")
        if event_type not in COMPARISON_EVENT_TYPES and comparison is not None:
            _fail("A comparison value is only valid for 'becomes' and 'is no longer' events.")
        if comparison is not None and not _is_safe_literal(comparison):
            _fail("Comparison values must contain only safe JSON literals.")
        if comparison is not None:
            _validate_comparison_value(comparison, watched_field)
    scope_type = values.get("scope_type", "current_record")
    if scope_type not in ALLOWED_SCOPE_TYPES:
        _fail("Unsupported alert scope.")
    target_res_id = values.get("target_res_id")
    if at_activation and scope_type == "current_record" and (
        not isinstance(target_res_id, int) or isinstance(target_res_id, bool) or target_res_id <= 0
    ):
        _fail("Current-record rules require a positive persistent record ID.")
    if at_activation and scope_type == "captured_domain" and values.get("scope_domain_json") is None:
        _fail("Captured-domain rules require a stored domain snapshot.")
    scope_domain = canonicalize_domain(values.get("scope_domain_json"), target_model)
    condition_domain = canonicalize_domain(values.get("condition_domain_json"), target_model)
    if values.get("scope_domain_json") is not None and scope_domain is None:
        _fail("The captured domain cannot be null.")
    combine_domains(scope_domain, condition_domain, target_model=target_model)
    amount = values.get("date_offset_amount", 0)
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        _fail("Date offsets must be non-negative integers.")
    if values.get("date_offset_unit", "days") not in ALLOWED_OFFSET_UNITS:
        _fail("Unsupported date offset unit.")
    if values.get("date_offset_direction", "after") not in ALLOWED_OFFSET_DIRECTIONS:
        _fail("Unsupported date offset direction.")
    if event_type not in RELATIVE_DATE_EVENT_TYPES and amount:
        _fail("A non-zero date offset is only valid for relative date events.")
    if event_type in RELATIVE_DATE_EVENT_TYPES and amount == 0:
        _fail("Relative date events require a non-zero date offset.")
    _validate_expiry(values.get("expires_at"), at_activation, now)
    validate_templates(values.get("subject_template"), values.get("message_template"))
    return {"scope_domain_json": scope_domain, "condition_domain_json": condition_domain}
