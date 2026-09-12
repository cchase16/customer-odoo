# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError

from .security import recipient_can_read

from .alert_rule import EVENT_TYPES


class AlertNotification(models.Model):
    _name = "alert.notification"
    _description = "Custom Alert Notification"
    _rec_name = "subject"
    _order = "occurred_at desc, id desc"

    rule_id = fields.Many2one(
        "alert.rule",
        string="Source Rule",
        ondelete="set null",
        index=True,
    )
    rule_name_snapshot = fields.Char(string="Rule Name", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="Recipient",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one("res.company", string="Company", index=True, ondelete="set null")
    model_name = fields.Char(string="Source Model", required=True, index=True)
    model_label = fields.Char(string="Source Model Label")
    res_id = fields.Integer(string="Source Record", index=True)
    record_name_snapshot = fields.Char(string="Record Name")
    event_type = fields.Selection(EVENT_TYPES, string="Event", required=True, index=True)
    field_name = fields.Char(string="Field Name", index=True)
    field_label = fields.Char(string="Field Label")
    old_value_text = fields.Char(string="Old Value")
    new_value_text = fields.Char(string="New Value")
    subject = fields.Char(string="Subject", required=True, index=True)
    message = fields.Text(string="Message", required=True)
    severity = fields.Selection(
        [
            ("info", "Information"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("danger", "Danger"),
        ],
        string="Severity",
        required=True,
        default="info",
        index=True,
    )
    occurred_at = fields.Datetime(string="Occurred At", required=True, index=True)
    state = fields.Selection(
        [
            ("unread", "Unread"),
            ("read", "Read"),
            ("dismissed", "Dismissed"),
        ],
        string="State",
        required=True,
        default="unread",
        index=True,
    )
    read_at = fields.Datetime(string="Read At", index=True)
    email_state = fields.Selection(
        [
            ("not_requested", "Not requested"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        string="Email Status",
        required=True,
        default="not_requested",
        index=True,
    )
    email_error_summary = fields.Char(string="Email Error", copy=False)
    email_sent_at = fields.Datetime(string="Email Sent At", copy=False)
    occurrence_key = fields.Char(string="Occurrence Key", required=True, index=True, copy=False)

    _occurrence_key_unique = models.Constraint(
        "UNIQUE(occurrence_key)",
        "An alert occurrence can only be delivered once.",
    )

    _logger = logging.getLogger(__name__)
    _BUS_NOTIFICATION_TYPE = "cw_custom_alert.notification"

    @api.model
    def _bus_target(self, user_id):
        return "cw_custom_alerts.user.%s" % int(user_id)

    def _safe_bus_payload(self):
        """Build a recipient-safe payload; navigation is re-authorized server-side."""
        self.ensure_one()
        action = False
        if self.model_name and isinstance(self.res_id, int) and self.res_id > 0:
            action = {"model": self.model_name, "res_id": self.res_id}
        return {
            "id": self.id,
            "subject": (self.subject or "")[:256],
            "message": (self.message or "")[:4096],
            "severity": self.severity or "info",
            "occurred_at": fields.Datetime.to_string(self.occurred_at),
            "action": action,
        }

    def _schedule_live_delivery(self):
        """Publish after commit using an isolated cursor so bus failures cannot roll back events."""
        for notification in self:
            payload = notification._safe_bus_payload()
            target = self._bus_target(notification.user_id.id)
            registry = self.env.registry

            def publish(registry=registry, target=target, payload=payload):
                try:
                    with registry.cursor() as cursor:
                        env = api.Environment(cursor, SUPERUSER_ID, {})
                        env["bus.bus"]._sendone(target, self._BUS_NOTIFICATION_TYPE, payload)
                        cursor.commit()
                except Exception as error:  # pragma: no cover - infrastructure dependent
                    self._logger.warning(
                        "Custom alert live delivery failed: %s", type(error).__name__
                    )

            self.env.cr.postcommit.add(publish)

    @api.model
    def get_inbox_state(self):
        notifications = self.search(
            [("user_id", "=", self.env.user.id), ("state", "=", "unread")],
            order="occurred_at desc, id desc",
            limit=10,
        )
        count = self.search_count(
            [("user_id", "=", self.env.user.id), ("state", "=", "unread")]
        )
        return {"count": count, "notifications": [n._safe_bus_payload() for n in notifications]}

    @api.model
    def mark_read(self, notification_ids):
        if not isinstance(notification_ids, list):
            return 0
        notifications = self.browse(notification_ids).exists().filtered(
            lambda n: n.user_id == self.env.user and n.state == "unread"
        )
        notifications.write({"state": "read", "read_at": fields.Datetime.now()})
        return len(notifications)

    @api.model
    def mark_all_read(self):
        notifications = self.search(
            [("user_id", "=", self.env.user.id), ("state", "=", "unread")]
        )
        notifications.write({"state": "read", "read_at": fields.Datetime.now()})
        return len(notifications)

    def action_mark_read(self):
        """Form-view action constrained to the current recipient."""
        self.filtered(
            lambda n: n.user_id == self.env.user and n.state == "unread"
        ).write({"state": "read", "read_at": fields.Datetime.now()})
        return True

    @api.model
    def _retention_days(self, parameter, default):
        value = self.env["ir.config_parameter"].sudo().get_param(parameter, str(default))
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    @api.model
    def _run_retention(self):
        """Remove only alerts past their independently configured retention windows."""
        now = fields.Datetime.now()
        read_days = self._retention_days("cw_custom_alerts.read_retention_days", 90)
        unread_days = self._retention_days("cw_custom_alerts.unread_retention_days", 365)
        read_cutoff = fields.Datetime.subtract(now, days=read_days)
        unread_cutoff = fields.Datetime.subtract(now, days=max(read_days, unread_days))
        old_read = self.sudo().search([
            ("state", "in", ("read", "dismissed")), ("occurred_at", "<", read_cutoff),
        ])
        old_unread = self.sudo().search([
            ("state", "=", "unread"), ("occurred_at", "<", unread_cutoff),
        ])
        removed = len(old_read) + len(old_unread)
        (old_read | old_unread).unlink()
        return removed

    def action_open_source(self):
        """Open a source only after a fresh recipient access check."""
        self.ensure_one()
        if self.user_id != self.env.user:
            raise AccessError("You can open only your own alerts.")
        company = self.company_id or self.env.company
        decision = recipient_can_read(
            self.env, self.env.user, self.model_name, self.res_id, company
        )
        if decision.allowed:
            return {
                "type": "ir.actions.act_window",
                "name": self.model_label or "Alert source",
                "res_model": self.model_name,
                "view_mode": "form",
                "res_id": self.res_id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Alert details",
            "res_model": "alert.notification",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }
