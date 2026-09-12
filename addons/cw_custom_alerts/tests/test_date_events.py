# -*- coding: utf-8 -*-

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models.occurrence import OccurrenceKeyBuilder


class TestAlertDateEvents(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.write_date_field = cls.env.ref("base.field_res_partner__write_date")

    def _date_rule(self, **overrides):
        values = {
            "name": "Date alert",
            "model_id": self.partner_model.id,
            "field_id": self.write_date_field.id,
            "event_type": "date_reached",
            "scope_type": "captured_domain",
            "scope_domain_json": [["name", "!=", False]],
            "subject_template": "Date alert",
            "message_template": "Date window reached for ${record_name}",
            "status": "active",
        }
        values.update(overrides)
        return self.AlertRule.create(values)

    def test_time_activation_initializes_last_run_without_backlog(self):
        old_partner = self.env["res.partner"].create({"name": "Existing before rule"})
        before = fields.Datetime.now()
        rule = self._date_rule()
        after = fields.Datetime.now()
        self.assertTrue(rule.automation_id.last_run)
        self.assertGreaterEqual(rule.automation_id.last_run, before)
        self.assertLessEqual(rule.automation_id.last_run, after)
        records = rule.automation_id._search_time_based_automation_records(until=fields.Datetime.now())
        self.assertFalse(self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", old_partner.id),
        ]))
        self.assertNotIn(old_partner, records)

    def test_scheduler_window_evaluates_date_fields_and_new_target_is_distinct(self):
        partner = self.env["res.partner"].create({"name": "Scheduler fixture"})
        rule = self._date_rule(
            scope_type="current_record", target_res_id=partner.id, scope_domain_json=None,
        )
        rule.automation_id.write({"last_run": "2020-01-01 00:00:00"})
        rule.automation_id._process(partner)
        self.assertEqual(self.AlertNotification.search_count([("rule_id", "=", rule.id)]), 1)

    def test_changed_normalized_target_has_a_distinct_occurrence_key(self):
        rule = self._date_rule()
        partner = self.env["res.partner"].create({"name": "Target fixture"})
        first = OccurrenceKeyBuilder.for_date(rule, partner, "2026-09-12 10:00:00", "0:days:after")
        second = OccurrenceKeyBuilder.for_date(rule, partner, "2026-09-13 10:00:00", "0:days:after")
        self.assertNotEqual(first, second)

    def test_repeated_date_windows_create_one_alert_for_one_occurrence(self):
        rule = self._date_rule()
        partner = self.env["res.partner"].create({"name": "Date fixture"})
        # The controlled replay uses the same watched value and therefore the
        # same deterministic occurrence key on both scheduler passes.
        rule.automation_id._process(partner)
        rule.automation_id._process(partner)
        alerts = self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", partner.id),
        ])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(rule.automation_id.action_server_ids.ids, [rule.server_action_id.id])

    def test_expired_rules_are_disabled_and_retain_their_links(self):
        expiry = fields.Datetime.now() + timedelta(days=1)
        rule = self._date_rule(expires_at=expiry)
        automation_id = rule.automation_id.id
        with patch.object(
            self.env["alert.event.evaluator"].__class__,
            "_occurred_at",
            return_value=expiry + timedelta(seconds=1),
        ):
            partner = self.env["res.partner"].create({"name": "Expired fixture"})
            self.env["alert.event.evaluator"].evaluate_rule(rule, partner)
        rule.invalidate_recordset()
        self.assertEqual(rule.status, "expired")
        self.assertFalse(rule.active)
        self.assertEqual(rule.automation_id.id, automation_id)
        self.assertFalse(rule.automation_id.active)

    def test_unexpected_evaluator_failure_does_not_advance_time_window(self):
        rule = self._date_rule()
        old_last_run = rule.automation_id.last_run
        partner = self.env["res.partner"].create({"name": "Failure fixture"})
        with patch.object(
            self.env["alert.event.evaluator"].__class__,
            "evaluate_rule",
            side_effect=RuntimeError("unexpected evaluator failure"),
        ):
            with self.assertRaises(RuntimeError):
                rule.automation_id._process(partner)
        self.assertEqual(rule.automation_id.last_run, old_last_run)
