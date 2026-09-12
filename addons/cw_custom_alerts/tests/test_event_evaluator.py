# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestAlertEventEvaluator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.name_field = cls.env.ref("base.field_res_partner__name")
        cls.create_date_field = cls.env.ref("base.field_res_partner__create_date")

    def _rule_values(self, event_type, **overrides):
        values = {
            "name": f"Evaluator {event_type}",
            "model_id": self.partner_model.id,
            "event_type": event_type,
            "scope_type": "captured_domain",
            "scope_domain_json": [["name", "!=", False]],
            "subject_template": "${event_time} ${record_name}",
            "message_template": "${old_value} -> ${new_value}",
            "status": "active",
        }
        values.update(overrides)
        return values

    def test_field_change_uses_automation_old_values_and_safe_rendering(self):
        rule = self.AlertRule.create(self._rule_values(
            "field_changed", field_id=self.name_field.id,
        ))
        partner = self.env["res.partner"].create({"name": "After"})
        rule.automation_id.with_context(old_values={partner.id: {"name": "Before"}})._process(partner)
        notification = self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", partner.id),
        ])
        self.assertEqual(len(notification), 1)
        self.assertIn("Before -> After", notification.message)
        self.assertEqual(notification.record_name_snapshot, "After")

    def test_unrelated_field_does_not_run_a_watched_field_rule(self):
        rule = self.AlertRule.create(self._rule_values(
            "field_changed", field_id=self.name_field.id,
        ))
        partner = self.env["res.partner"].create({"name": "Stable"})
        rule.automation_id.with_context(old_values={partner.id: {"email": "old@example.test"}})._process(partner)
        self.assertFalse(self.AlertNotification.search([("rule_id", "=", rule.id)]))

    def test_record_deleted_uses_the_pre_unlink_record_snapshot(self):
        partner = self.env["res.partner"].create({"name": "To remove"})
        rule = self.AlertRule.create(self._rule_values(
            "record_deleted", scope_type="current_record", target_res_id=partner.id,
        ))
        rule.automation_id._process(partner)
        notification = self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", partner.id),
        ])
        self.assertEqual(len(notification), 1)
        self.assertEqual(notification.record_name_snapshot, "To remove")

    def test_alert_creation_rolls_back_with_the_business_transaction(self):
        rule = self.AlertRule.create(self._rule_values("record_created"))
        partner = self.env["res.partner"].create({"name": "Rolled back"})
        with self.assertRaises(RuntimeError):
            with self.env.cr.savepoint():
                rule.automation_id._process(partner)
                raise RuntimeError("test rollback")
        self.assertFalse(self.AlertNotification.search([("rule_id", "=", rule.id)]))

    def test_no_model_specific_branches_are_present_in_production_evaluator(self):
        source = open("addons/cw_custom_alerts/models/event_evaluator.py", encoding="utf-8").read().lower()
        self.assertNotIn("sale", source)
        self.assertNotIn("purchase", source)

