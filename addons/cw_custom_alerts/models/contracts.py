"""Release-independent contracts for the custom-alerts engine.

This module intentionally contains no Odoo imports. Odoo ORM, automation, and
web-client adapters must implement these contracts from their isolated adapter
packages so the rule, comparison, security, and delivery boundaries remain
portable and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Mapping, Protocol, Sequence

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = Mapping[str, JsonValue]
Scalar = str | int | float | bool | date | datetime | None
EventType = Literal[
    "record_created",
    "record_deleted",
    "field_changed",
    "field_becomes",
    "field_is_no_longer",
    "field_postponed",
    "field_advanced",
    "date_reached",
    "date_relative_before",
    "date_relative_after",
]
SUPPORTED_EVENT_TYPES = frozenset(
    {
        "record_created",
        "record_deleted",
        "field_changed",
        "field_becomes",
        "field_is_no_longer",
        "field_postponed",
        "field_advanced",
        "date_reached",
        "date_relative_before",
        "date_relative_after",
    }
)


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """Canonical rule configuration passed to engine services."""

    rule_id: int
    owner_id: int
    model_name: str
    event_type: EventType
    watched_field: str | None
    domain_snapshot: JsonValue
    condition_snapshot: JsonValue | None
    company_id: int | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class EventContext:
    """Normalized event input; ORM-specific records stay outside the contract."""

    model_name: str
    record_id: int | None
    event_type: EventType
    field_name: str | None
    old_value: Scalar
    new_value: Scalar
    occurred_at: datetime
    company_id: int | None
    record_snapshot: JsonObject


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Comparison outcome without prescribing an ORM or field implementation."""

    matched: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class RecipientContext:
    """Recipient identity and execution context used for fresh access checks."""

    user_id: int
    company_id: int | None
    language: str | None
    timezone: str | None
    can_read_source: bool


@dataclass(frozen=True, slots=True)
class NotificationDraft:
    """Safe, already-rendered notification content ready for delivery."""

    recipient: RecipientContext
    rule_id: int
    severity: str
    plain_text: str
    action_metadata: JsonObject | None
    occurrence_key: str | None


@dataclass(frozen=True, slots=True)
class OccurrenceIdentity:
    """Stable inputs for a date-event uniqueness key."""

    rule_id: int
    model_name: str
    record_id: int
    event_type: str
    normalized_target: str
    offset: str


@dataclass(frozen=True, slots=True)
class CapturedContext:
    """JSON-safe page context transferred to the server for revalidation."""

    model_name: str
    action_id: int | None
    view_id: int | None
    record_id: int | None
    company_id: int | None
    resolved_domain: list[JsonValue]
    visible_fields: Sequence[str]


@dataclass(frozen=True, slots=True)
class AutomationBinding:
    """Opaque links to the managed automation records owned by one rule."""

    automation_id: int
    server_action_id: int


class Comparator(Protocol):
    """Compare normalized event values under a validated rule."""

    def compare(self, rule: RuleSpec, event: EventContext) -> ComparisonResult:
        ...


class SecurityPolicy(Protocol):
    """Authorize recipients and source-record access without rendering values."""

    def authorize(self, rule: RuleSpec, recipient: RecipientContext, event: EventContext) -> bool:
        ...


class OccurrenceKeyBuilder(Protocol):
    """Build a deterministic key for scheduler retries and overlapping windows."""

    def build(self, identity: OccurrenceIdentity) -> str:
        ...


class NotificationRenderer(Protocol):
    """Render only approved plain-text placeholders after authorization."""

    def render(self, rule: RuleSpec, event: EventContext, recipient: RecipientContext) -> NotificationDraft:
        ...


class AutomationMapper(Protocol):
    """Synchronize exactly one managed automation and trusted action per rule."""

    def synchronize(self, rule: RuleSpec) -> AutomationBinding:
        ...

    def disable(self, rule: RuleSpec, binding: AutomationBinding) -> None:
        ...


class DeliverySink(Protocol):
    """Persist and publish recipient-safe notifications using transaction boundaries."""

    def deliver(self, draft: NotificationDraft) -> Any:
        ...


class ContextAdapter(Protocol):
    """Capture supported view context without exposing controller internals."""

    def capture(self) -> CapturedContext | None:
        ...
