"""Generic transactional event evaluation and persistent alert creation."""

from __future__ import annotations

from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import AccessError, MissingError
from psycopg2 import IntegrityError

from .comparison import compare_event, normalize_value
from .occurrence import OccurrenceKeyBuilder
from .security import recipient_can_read
from .validation import render_plain_text


class AlertEventEvaluator(models.AbstractModel):
    _name = "alert.event.evaluator"
    _description = "Custom Alert Event Evaluator"

    @api.model
    def _occurred_at(self):
        return self.env.cr.now()

    @api.model
    def _record_company(self, record, rule):
        if "company_id" in record._fields and record.company_id in rule.company_ids:
            return record.company_id
        return rule.company_ids[:1] or self.env.company

    @api.model
    def _safe_value_text(self, value, recipient_env):
        if hasattr(value, "display_name"):
            try:
                return str(value.with_env(recipient_env).display_name)
            except (AccessError, MissingError):
                return ""
        if isinstance(value, (datetime,)):
            return fields.Datetime.to_string(value)
        return "" if value is None or value is False else str(value)

    @api.model
    def _record_name(self, record, recipient_env):
        try:
            return str(record.with_env(recipient_env).display_name)
        except (AccessError, MissingError):
            return ""

    @api.model
    def _create_notification(self, rule, record, *, old_value, new_value, occurred_at, recipient_env):
        recipient = rule.recipient_user_id
        company = self._record_company(record, rule)
        event = rule.event_type
        field = rule.field_id
        field_name = field.name if field else False
        record_name = self._record_name(record, recipient_env)
        old_text = self._safe_value_text(old_value, recipient_env)
        new_text = self._safe_value_text(new_value, recipient_env)
        values = {
            "rule_name": rule.name,
            "model_name": rule.model_id.name,
            "record_name": record_name,
            "field_name": field.field_description if field else "",
            "old_value": old_text,
            "new_value": new_text,
            "event_time": fields.Datetime.to_string(occurred_at),
        }
        subject = render_plain_text(rule.subject_template, values)
        message = render_plain_text(rule.message_template, values)
        if event in {"date_reached", "date_relative_before", "date_relative_after"}:
            occurrence_key = OccurrenceKeyBuilder.for_date(
                rule, record, normalize_value(new_value),
                f"{rule.date_offset_amount}:{rule.date_offset_unit}:{rule.date_offset_direction}",
            )
        else:
            occurrence_key = OccurrenceKeyBuilder.for_event(
                rule, record, event, old_value=old_value, new_value=new_value, occurred_at=occurred_at,
            )
        notification_values = {
            "rule_id": rule.id,
            "rule_name_snapshot": rule.name,
            "user_id": recipient.id,
            "company_id": company.id if company else False,
            "model_name": record._name,
            "model_label": rule.model_id.name,
            "res_id": record.id,
            "record_name_snapshot": record_name,
            "event_type": event,
            "field_name": field_name,
            "field_label": field.field_description if field else False,
            "old_value_text": old_text,
            "new_value_text": new_text,
            "severity": rule.severity or "info",
            "subject": subject,
            "message": message,
            "occurred_at": occurred_at,
            "occurrence_key": occurrence_key,
        }
        Notification = self.env["alert.notification"].sudo()
        try:
            with self.env.cr.savepoint():
                notification = Notification.create(notification_values)
        except IntegrityError:
            # Uniqueness is the expected scheduler/concurrency retry signal.
            notification = Notification.search([("occurrence_key", "=", occurrence_key)], limit=1)
            if not notification:
                raise
        else:
            notification._schedule_live_delivery()
            if rule.send_email:
                self.env["alert.email.delivery"].queue(notification)
        return notification

    @api.model
    def _expire_if_needed(self, rule):
        if rule.expires_at and rule.expires_at <= self._occurred_at():
            rule.write({"active": False, "status": "expired"})
            return True
        return False

    @api.model
    def evaluate_rule(self, rule, records, eval_context=None):
        old_values = (eval_context or {}).get("old_values") or {}
        for record in records:
            if self._expire_if_needed(rule):
                break
            if rule.scope_type == "current_record" and record.id != rule.target_res_id:
                continue
            field = rule.field_id
            old_value = None
            new_value = None
            if field:
                new_value = record[field.name]
                old_value = old_values.get(record.id, {}).get(field.name)
            result = compare_event(rule.event_type, old_value, new_value, rule.comparison_value_json)
            if not result.matched:
                continue
            company = self._record_company(record, rule)
            decision = recipient_can_read(self.env, rule.recipient_user_id, record._name, record.id, company)
            if not decision.allowed:
                rule.sudo().write({"suppressed_count": rule.suppressed_count + 1})
                continue
            recipient_env = self.env(user=rule.recipient_user_id, context={
                **self.env.context,
                "allowed_company_ids": [company.id] if company else self.env.companies.ids,
            }, su=False)
            notification = self._create_notification(
                rule, record, old_value=old_value, new_value=new_value,
                occurred_at=self._occurred_at(), recipient_env=recipient_env,
            )
            rule.sudo().write({
                "last_triggered_at": notification.occurred_at,
                "trigger_count": rule.trigger_count + 1,
            })
        return True
