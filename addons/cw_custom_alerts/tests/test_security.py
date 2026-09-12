# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from ..models.security import recipient_can_read


class TestAlertSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.alert_user_group = cls.env.ref("cw_custom_alerts.group_alert_user")
        cls.alert_manager_group = cls.env.ref("cw_custom_alerts.group_alert_manager")

    def _make_user(self, login, group):
        return self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": f"{login}@example.test",
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id, group.id])],
        })

    def _rule_values(self):
        return {
            "name": "Owned alert",
            "model_id": self.partner_model.id,
            "event_type": "record_created",
            "subject_template": "Subject",
            "message_template": "Message",
        }

    def _notification_values(self, user, key):
        return {
            "rule_name_snapshot": "Rule",
            "user_id": user.id,
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

    def test_alert_user_is_limited_to_owned_recipient_and_company(self):
        user = self._make_user("alert-user", self.alert_user_group)
        other = self._make_user("other-user", self.alert_user_group)
        restricted_company = self.env["res.company"].create({"name": "Restricted Alert Company"})
        user_env = self.env(user=user)
        rule = user_env["alert.rule"].create(self._rule_values())
        self.assertEqual(rule.creator_user_id, user)
        self.assertEqual(rule.recipient_user_id, user)
        with self.assertRaises(ValidationError):
            user_env["alert.rule"].create({**self._rule_values(), "recipient_user_id": other.id})
        with self.assertRaises(ValidationError):
            user_env["alert.rule"].create({**self._rule_values(), "organization_wide": True})
        with self.assertRaises(AccessError):
            user_env["alert.rule"].create({
                **self._rule_values(),
                "company_ids": [(6, 0, [restricted_company.id])],
            })
        self.assertEqual(user_env["alert.rule"].search([]), rule)

    def test_alert_manager_can_select_recipient_and_manager_rule_is_broader(self):
        manager = self._make_user("alert-manager", self.alert_manager_group)
        recipient = self._make_user("alert-recipient", self.alert_user_group)
        manager_env = self.env(user=manager)
        rule = manager_env["alert.rule"].create({
            **self._rule_values(),
            "recipient_user_id": recipient.id,
            "organization_wide": True,
        })
        self.assertEqual(rule.recipient_user_id, recipient)
        self.assertTrue(rule.organization_wide)

    def test_notifications_are_recipient_owned_and_access_decision_contains_no_values(self):
        user = self._make_user("notification-user", self.alert_user_group)
        other = self._make_user("notification-other", self.alert_user_group)
        self.AlertNotification.create(self._notification_values(user, "security-1"))
        self.AlertNotification.create(self._notification_values(other, "security-2"))
        visible = self.env(user=user)["alert.notification"].search([])
        self.assertEqual(visible.mapped("occurrence_key"), ["security-1"])

        partner = self.env["res.partner"].create({"name": "Access test contact"})
        allowed = recipient_can_read(self.env, user, "res.partner", partner.id, self.env.company)
        denied = recipient_can_read(self.env, user, "res.partner", 999999999, self.env.company)
        self.assertTrue(allowed.allowed)
        self.assertFalse(denied.allowed)
        self.assertIn(denied.reason, {"record_missing", "access_denied"})
        self.assertEqual(set(vars(denied)), {"allowed", "reason"})
        with self.assertRaises(AccessError):
            self.env(user=user)["alert.notification"].create(self._notification_values(user, "security-3"))
