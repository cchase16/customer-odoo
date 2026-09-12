# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestAlertAutomation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.name_field = cls.env.ref("base.field_res_partner__name")
        cls.write_date_field = cls.env.ref("base.field_res_partner__write_date")

    def _rule_values(self, **overrides):
        values = {
            "name": "Managed alert",
            "model_id": self.partner_model.id,
            "event_type": "record_created",
            "scope_type": "captured_domain",
            "scope_domain_json": [["name", "!=", False]],
            "subject_template": "Alert ${record_name}",
            "message_template": "A record event occurred.",
            "status": "active",
        }
        values.update(overrides)
        return values

    def test_managed_records_have_one_trusted_action_and_automation(self):
        rule = self.AlertRule.create(self._rule_values())
        self.assertTrue(rule.automation_id)
        self.assertTrue(rule.server_action_id)
        self.assertEqual(rule.automation_id.alert_rule_id, rule)
        self.assertEqual(rule.server_action_id.alert_rule_id, rule)
        self.assertEqual(rule.automation_id.action_server_ids.ids, [rule.server_action_id.id])
        self.assertEqual(rule.server_action_id.state, "cw_alert_dispatch")
        self.assertFalse(rule.server_action_id.code)
        self.assertEqual(rule.automation_id.trigger, "on_create")
        self.assertEqual(rule.automation_id.filter_domain, "[['name', '!=', False]]")

    def test_trigger_mapping_covers_write_unlink_and_time_events(self):
        cases = [
            ("field_changed", {"field_id": self.name_field.id}, "on_create_or_write"),
            ("record_deleted", {}, "on_unlink"),
            (
                "date_relative_after",
                {
                    "field_id": self.write_date_field.id,
                    "date_offset_amount": 2,
                    "date_offset_unit": "hours",
                    "date_offset_direction": "after",
                },
                "on_time",
            ),
        ]
        for event_type, values, expected_trigger in cases:
            rule = self.AlertRule.create(self._rule_values(
                name=f"Managed {event_type}", event_type=event_type, **values,
            ))
            automation = rule.automation_id
            self.assertEqual(automation.trigger, expected_trigger)
            self.assertEqual(automation.action_server_ids.ids, [rule.server_action_id.id])
            if expected_trigger == "on_create_or_write":
                self.assertEqual(automation.trigger_field_ids.ids, [self.name_field.id])
            if expected_trigger == "on_time":
                self.assertEqual(automation.trg_date_id, self.write_date_field)
                self.assertEqual(automation.trg_date_range, 2)
                self.assertEqual(automation.trg_date_range_type, "hour")

    def test_watched_field_is_triggered_even_when_scope_uses_another_field(self):
        rule = self.AlertRule.create(self._rule_values(
            event_type="field_changed",
            field_id=self.name_field.id,
            scope_domain_json=[["email", "!=", False]],
        ))
        self.assertIn(self.name_field.id, rule.automation_id.trigger_field_ids.ids)

    def test_activation_edits_are_idempotent_and_pause_disables_execution(self):
        rule = self.AlertRule.create(self._rule_values())
        automation_id = rule.automation_id.id
        action_id = rule.server_action_id.id
        rule.write({"name": "Renamed managed alert"})
        rule.invalidate_recordset()
        self.assertEqual(rule.automation_id.id, automation_id)
        self.assertEqual(rule.server_action_id.id, action_id)
        self.assertEqual(self.env["base.automation"].with_context(active_test=False).search_count([
            ("alert_rule_id", "=", rule.id),
        ]), 1)
        self.assertEqual(self.env["ir.actions.server"].with_context(active_test=False).search_count([
            ("alert_rule_id", "=", rule.id),
        ]), 1)

        rule.write({"active": False, "status": "paused"})
        self.assertFalse(rule.automation_id.active)
        rule.write({"active": True, "status": "active"})
        self.assertTrue(rule.automation_id.active)

    def test_create_automation_runs_generic_runner_and_persists_alert(self):
        rule = self.AlertRule.create(self._rule_values())
        self.assertTrue(rule.automation_id.active)
        self.assertEqual(rule.automation_id.model_name, "res.partner")
        self.assertIn(rule.automation_id, self.env["base.automation"]._get_actions(
            self.env["res.partner"], ["on_create"],
        ))
        self.assertIsNotNone(rule.server_action_id._get_runner()[0])
        partner = self.env["res.partner"].create({"name": "Automation fixture"})
        # At-install tests run while the registry is still being assembled;
        # invoke the same automation processor that the registry hook calls.
        rule.automation_id._process(partner)
        alert = self.AlertNotification.search([
            ("rule_id", "=", rule.id),
            ("res_id", "=", partner.id),
        ])
        self.assertEqual(len(alert), 1)
        self.assertEqual(alert.state, "unread")
        self.assertEqual(alert.record_name_snapshot, "Automation fixture")
        self.assertEqual(rule.trigger_count, 1)
