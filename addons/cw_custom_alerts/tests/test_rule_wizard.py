# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAlertRuleWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("base.partner_admin")

    def _payload(self, record_id=None):
        return {
            "modelName": "res.partner",
            "actionId": None,
            "viewId": None,
            "recordId": record_id,
            "companyId": 1,
            "resolvedDomain": [] if record_id else [["is_company", "=", True]],
            "visibleFields": ["name", "email"],
        }

    def test_list_context_previews_reviews_and_activates(self):
        action = self.env["alert.rule"].action_open_wizard_from_context(self._payload())
        wizard = self.env["alert.rule.wizard"].browse(action["res_id"])
        self.assertEqual(wizard.model_name, "res.partner")
        self.assertEqual(wizard.scope_type, "captured_domain")
        wizard.action_preview()
        self.assertGreaterEqual(wizard.preview_count, 0)
        wizard.action_review()
        self.assertEqual(wizard.step, "review")
        wizard.action_activate()
        rule = self.env["alert.rule"].search([("name", "=", wizard.name)], order="id desc", limit=1)
        self.assertTrue(rule)
        self.assertEqual(rule.status, "active")
        self.assertEqual(rule.scope_domain_json, [["is_company", "=", True]])

    def test_form_context_defaults_to_current_record(self):
        action = self.env["alert.rule"].action_open_wizard_from_context(self._payload(self.partner.id))
        wizard = self.env["alert.rule.wizard"].browse(action["res_id"])
        self.assertEqual(wizard.scope_type, "current_record")
        self.assertEqual(wizard.source_record_id, self.partner.id)
        wizard.action_review()
        wizard.action_activate()
        rule = self.env["alert.rule"].search([("target_res_id", "=", self.partner.id)], order="id desc", limit=1)
        self.assertTrue(rule)
        self.assertEqual(rule.scope_type, "current_record")

    def test_activation_revalidates_tampered_wizard_context(self):
        action = self.env["alert.rule"].action_open_wizard_from_context(self._payload(self.partner.id))
        wizard = self.env["alert.rule.wizard"].browse(action["res_id"])
        wizard.source_record_id = 999999999
        with self.assertRaises(ValidationError):
            wizard.action_activate()
