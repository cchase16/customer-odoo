"""Deterministic occurrence keys for alert delivery."""

from __future__ import annotations

import hashlib
import json

from .contracts import OccurrenceIdentity


def _canonical(value):
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "ids"):
        return list(value.ids)
    return value


class OccurrenceKeyBuilder:
    """Build opaque SHA-256 keys; business values never appear in the key."""

    @staticmethod
    def build(identity: OccurrenceIdentity) -> str:
        payload = {
            "rule_id": identity.rule_id,
            "model_name": identity.model_name,
            "record_id": identity.record_id,
            "event_type": identity.event_type,
            "normalized_target": identity.normalized_target,
            "offset": identity.offset,
        }
        encoded = json.dumps(_canonical(payload), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def for_event(cls, rule, record, event_type, *, old_value=None, new_value=None, occurred_at=None):
        payload = {
            "old": _canonical(old_value),
            "new": _canonical(new_value),
            "occurred_at": _canonical(occurred_at),
        }
        return cls.build(OccurrenceIdentity(
            rule_id=rule.id,
            model_name=record._name,
            record_id=record.id,
            event_type=event_type,
            normalized_target=json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")),
            offset="event",
        ))

    @classmethod
    def for_date(cls, rule, record, target, offset):
        return cls.build(OccurrenceIdentity(
            rule_id=rule.id,
            model_name=record._name,
            record_id=record.id,
            event_type=rule.event_type,
            normalized_target=_canonical(target),
            offset=str(offset),
        ))
