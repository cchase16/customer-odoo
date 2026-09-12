# -*- coding: utf-8 -*-

from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase


class TestAlertPersistence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.partner_model = cls.env.ref("base.model_res_partner")

    def _rule_values(self, name="Test alert rule"):
        return {
            "name": name,
            "model_id": self.partner_model.id,
            "event_type": "record_created",
            "subject_template": "Subject",
            "message_template": "Message",
        }

    def _notification_values(self, rule, occurrence_key=None):
        return {
            "rule_id": rule.id,
            "rule_name_snapshot": rule.name,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "model_name": "res.partner",
            "model_label": "Contact",
            "res_id": 1,
            "record_name_snapshot": "A contact",
            "event_type": "record_created",
            "subject": "Subject",
            "message": "Message",
            "occurred_at": "2026-09-12 12:00:00",
            "occurrence_key": occurrence_key,
        }

    def test_rule_and_notification_persist_full_history_shape(self):
        rule = self.AlertRule.create(self._rule_values())
        notification = self.AlertNotification.create(self._notification_values(rule, "occurrence-1"))

        self.assertEqual(rule.status, "draft")
        self.assertTrue(rule.active)
        self.assertEqual(rule.creator_user_id, self.env.user)
        self.assertEqual(rule.recipient_user_id, self.env.user)
        self.assertEqual(rule.model_id, self.partner_model)
        self.assertEqual(rule.company_ids, self.env.company)
        self.assertEqual(notification.state, "unread")
        self.assertFalse(notification.read_at)
        self.assertEqual(notification.rule_id, rule)

        rule.write({"active": False, "status": "paused", "last_error_summary": "safe diagnostic"})
        self.assertFalse(rule.active)
        self.assertEqual(rule.status, "paused")
        self.assertEqual(rule.last_error_summary, "safe diagnostic")
        self.assertTrue(notification.exists(), "archiving a rule must retain its alert history")
        self.assertEqual(notification.rule_id, rule)

    def test_occurrence_key_is_unique_when_present(self):
        rule = self.AlertRule.create(self._rule_values())
        self.AlertNotification.create(self._notification_values(rule, "duplicate-key"))
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.AlertNotification.create(self._notification_values(rule, "duplicate-key"))

    def test_required_indexes_and_unique_constraint_exist(self):
        self.env.cr.execute(
            """
            SELECT DISTINCT a.attname
              FROM pg_class table_ref
              JOIN pg_index idx ON idx.indrelid = table_ref.oid
              JOIN pg_attribute a ON a.attrelid = table_ref.oid AND a.attnum = ANY(idx.indkey)
             WHERE table_ref.relname IN ('alert_rule', 'alert_notification')
            """
        )
        indexed_columns = {row[0] for row in self.env.cr.fetchall()}
        self.assertTrue({"status", "expires_at", "model_id"}.issubset(indexed_columns))
        self.assertTrue(
            {"user_id", "state", "rule_id", "occurred_at", "model_name", "res_id"}.issubset(indexed_columns)
        )

        self.env.cr.execute(
            """
            SELECT 1
              FROM pg_constraint
             WHERE conrelid = 'alert_notification'::regclass
               AND conname = 'alert_notification_occurrence_key_unique'
            """
        )
        self.assertTrue(self.env.cr.fetchone(), "the occurrence-key uniqueness constraint must be installed")
