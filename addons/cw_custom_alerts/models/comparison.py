"""Release-independent event comparison."""

from __future__ import annotations

from datetime import date, datetime

from .contracts import ComparisonResult


def normalize_value(value):
    """Normalize ORM values without depending on an Odoo record implementation."""
    if hasattr(value, "ids"):
        return tuple(value.ids)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return tuple(sorted((key, normalize_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(normalize_value(item) for item in value)
    return value


def _empty(value):
    return value is None or value is False or value == ""


def _date_comparable(value):
    if isinstance(value, (date, datetime)):
        return value
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value


def compare_event(event_type, old_value=None, new_value=None, comparison_value=None):
    """Return a stable, explainable result for every approved event type."""
    old = normalize_value(old_value)
    new = normalize_value(new_value)
    target = normalize_value(comparison_value)

    if event_type == "record_created":
        return ComparisonResult(True, "record_created")
    if event_type == "record_deleted":
        return ComparisonResult(True, "record_deleted")
    if event_type == "field_changed":
        return ComparisonResult(old != new, "value_changed" if old != new else "value_unchanged")
    if event_type == "field_becomes":
        matched = old != target and new == target
        return ComparisonResult(matched, "became_target" if matched else "did_not_become_target")
    if event_type == "field_is_no_longer":
        matched = old == target and new != target
        return ComparisonResult(matched, "left_target" if matched else "did_not_leave_target")
    if event_type == "field_postponed":
        if _empty(old_value) or _empty(new_value):
            return ComparisonResult(False, "missing_date_value")
        try:
            matched = _date_comparable(new_value) > _date_comparable(old_value)
        except TypeError:
            matched = False
        return ComparisonResult(matched, "date_postponed" if matched else "date_not_postponed")
    if event_type == "field_advanced":
        if _empty(old_value) or _empty(new_value):
            return ComparisonResult(False, "missing_date_value")
        try:
            matched = _date_comparable(new_value) < _date_comparable(old_value)
        except TypeError:
            matched = False
        return ComparisonResult(matched, "date_advanced" if matched else "date_not_advanced")
    if event_type in {"date_reached", "date_relative_before", "date_relative_after"}:
        return ComparisonResult(True, "date_window_matched")
    return ComparisonResult(False, "unsupported_event")
