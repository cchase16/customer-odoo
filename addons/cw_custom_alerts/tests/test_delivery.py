# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import fields
from odoo.tests.common import TransactionCase


class TestAlertDelivery(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")

    def _rule(self):
        return self.AlertRule.create({
            "name": "Delivery rule",
            "model_id": self.partner_model.id,
            "event_type": "record_created",
            "subject_template": "Subject",
            "message_template": "Message",
        })

    def _notification(self, rule, key, **values):
        vals = {
            "rule_id": rule.id,
            "rule_name_snapshot": rule.name,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "model_name": "res.partner",
            "model_label": "Contact",
            "res_id": 1,
            "event_type": "record_created",
            "subject": "Subject",
            "message": "Message",
            "occurred_at": "2026-09-12 12:00:00",
            "occurrence_key": key,
        }
        vals.update(values)
        return self.AlertNotification.create(vals)

    def test_payload_is_minimal_and_safe(self):
        notification = self._notification(
            self._rule(), "delivery-payload", severity="warning"
        )
        self.assertEqual(
            set(notification._safe_bus_payload()),
            {"id", "subject", "message", "severity", "occurred_at", "action"},
        )
        self.assertEqual(notification._safe_bus_payload()["severity"], "warning")
        self.assertEqual(
            notification._safe_bus_payload()["action"],
            {"model": "res.partner", "res_id": 1},
        )

    def test_inbox_state_and_read_operations_are_recipient_owned(self):
        rule = self._rule()
        first = self._notification(rule, "delivery-first")
        second = self._notification(rule, "delivery-second")
        state = self.AlertNotification.get_inbox_state()
        self.assertEqual(state["count"], 2)
        self.assertEqual([item["id"] for item in state["notifications"]], [second.id, first.id])
        self.assertEqual(self.AlertNotification.mark_read([first.id, 999999]), 1)
        self.assertEqual(first.state, "read")
        self.assertEqual(self.AlertNotification.mark_all_read(), 1)
        self.assertEqual(second.state, "read")
        self.assertFalse(self.AlertNotification.get_inbox_state()["notifications"])

    def test_live_delivery_is_registered_for_after_commit(self):
        notification = self._notification(self._rule(), "delivery-after-commit")
        callback_count = len(self.env.cr.postcommit)
        notification._schedule_live_delivery()
        self.assertEqual(len(self.env.cr.postcommit), callback_count + 1)

    def test_source_open_rechecks_access_and_falls_back_to_alert_details(self):
        rule = self._rule()
        partner = self.env["res.partner"].create({"name": "Accessible source"})
        notification = self._notification(
            rule, "delivery-source", res_id=partner.id, record_name_snapshot=partner.name
        )
        action = notification.action_open_source()
        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["res_id"], partner.id)

        notification.write({"res_id": 999999999})
        fallback = notification.action_open_source()
        self.assertEqual(fallback["res_model"], "alert.notification")
        self.assertEqual(fallback["res_id"], notification.id)

    def test_source_open_rejects_foreign_notification(self):
        other = self.env["res.users"].search(
            [("id", "!=", self.env.user.id)], limit=1
        )
        if not other:
            self.skipTest("database has no second internal user")
        notification = self._notification(self._rule(), "delivery-foreign", user_id=other.id)
        with self.assertRaises(AccessError):
            notification.action_open_source()

    def test_enabled_email_is_queued_from_escaped_rendered_text(self):
        rule = self._rule()
        self.env.user.partner_id.email = "alert-recipient@example.test"
        notification = self._notification(
            rule, "delivery-email", subject="<subject>", message="<script>alert(1)</script>"
        )
        self.env["alert.email.delivery"].queue(notification)
        self.assertEqual(notification.email_state, "queued")
        mail = self.env["mail.mail"].search(
            [("alert_notification_id", "=", notification.id)], limit=1
        )
        self.assertTrue(mail)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", mail.body_html)
        self.assertNotIn("<script>", mail.body_html)

    def test_email_channel_status_is_independent_from_inbox_status(self):
        rule = self._rule()
        self.env.user.partner_id.email = "alert-recipient@example.test"
        notification = self._notification(rule, "delivery-email-status")
        self.env["alert.email.delivery"].queue(notification)
        mail = self.env["mail.mail"].search(
            [("alert_notification_id", "=", notification.id)], limit=1
        )
        mail._postprocess_sent_message([], [])
        self.assertEqual(notification.state, "unread")
        self.assertEqual(notification.email_state, "sent")
        self.assertTrue(notification.email_sent_at)

    def test_retention_removes_old_read_alerts_before_longer_lived_unread_alerts(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "cw_custom_alerts.read_retention_days", "0"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "cw_custom_alerts.unread_retention_days", "365"
        )
        rule = self._rule()
        read_notification = self._notification(rule, "delivery-retention-read")
        unread_notification = self._notification(rule, "delivery-retention-unread")
        read_notification.write({
            "state": "read",
            "read_at": fields.Datetime.now(),
            "occurred_at": "2020-01-01 00:00:00",
        })
        removed = self.AlertNotification._run_retention()
        self.assertEqual(removed, 1)
        self.assertFalse(read_notification.exists())
        self.assertTrue(unread_notification.exists())
