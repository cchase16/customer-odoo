# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAlertRuleManagement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env.ref("base.model_res_partner")
        cls.rule = cls.env["alert.rule"].create({
            "name": "Managed rule",
            "model_id": cls.model.id,
            "event_type": "record_created",
            "scope_type": "captured_domain",
            "scope_domain_json": [["is_company", "=", True]],
            "subject_template": "Subject",
            "message_template": "Message",
        })

    def test_lifecycle_actions_pause_resume_and_archive(self):
        self.rule.action_activate()
        self.assertEqual(self.rule.status, "active")
        self.assertTrue(self.rule.automation_id)
        self.rule.action_pause()
        self.assertEqual(self.rule.status, "paused")
        self.assertFalse(self.rule.active)
        self.assertFalse(self.rule.automation_id.active)
        self.rule.action_activate()
        self.assertEqual(self.rule.status, "active")
        self.rule.action_archive()
        self.assertEqual(self.rule.status, "paused")
        self.assertFalse(self.rule.active)

    def test_recapture_is_explicit_and_preserves_validated_snapshot(self):
        original = self.rule.scope_domain_json
        self.rule.action_recapture()
        self.assertEqual(self.rule.scope_domain_json, original)

    def test_structural_sync_failure_records_sanitized_error(self):
        self.rule.action_activate()
        with patch.object(type(self.env["alert.automation.mapper"]), "synchronize", side_effect=RuntimeError("secret value")):
            self.rule.write({"name": "Edited managed rule"})
        self.assertEqual(self.rule.status, "error")
        self.assertFalse(self.rule.active)
        self.assertEqual(self.rule.last_error_summary, "Managed automation synchronization failed: RuntimeError")
        self.assertNotIn("secret value", self.rule.last_error_summary)
        self.assertTrue(self.rule.last_error_at)
