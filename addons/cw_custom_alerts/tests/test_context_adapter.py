# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestAlertContextAdapter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.adapter = cls.env["alert.context.adapter"]
        cls.partner = cls.env.ref("base.partner_admin")

    def _payload(self, **overrides):
        payload = {
            "modelName": "res.partner",
            "actionId": None,
            "viewId": None,
            "recordId": None,
            "companyId": 999999,
            "resolvedDomain": [["name", "!=", False]],
            "visibleFields": ["name", "email", "category_id", "image_1920", "missing_field", "name"],
        }
        payload.update(overrides)
        return payload

    def test_capture_rebuilds_company_and_filters_visible_fields(self):
        captured = self.adapter.capture(self._payload())
        self.assertEqual(captured["model_name"], "res.partner")
        self.assertEqual(captured["company_id"], self.env.company.id)
        self.assertEqual(captured["resolved_domain"], [["name", "!=", False]])
        self.assertEqual(captured["visible_fields"], ["name", "email"])
        self.assertEqual(captured["scope_type"], "captured_domain")

    def test_capture_limits_context_menu_input_to_the_selected_eligible_field(self):
        captured = self.adapter.capture(self._payload(
            visibleFields=["name", "email"],
            selectedFieldName="email",
        ))
        self.assertEqual(captured["visible_fields"], ["email"])
        self.assertEqual(captured["selected_field_name"], "email")

        unsupported = self.adapter.capture(self._payload(
            visibleFields=["category_id"],
            selectedFieldName="category_id",
        ))
        self.assertEqual(unsupported["visible_fields"], [])
        self.assertIsNone(unsupported["selected_field_name"])

        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(selectedFieldName=42))

    def test_capture_form_requires_existing_readable_record(self):
        captured = self.adapter.capture(self._payload(recordId=self.partner.id, resolvedDomain=[]))
        self.assertEqual(captured["record_id"], self.partner.id)
        self.assertEqual(captured["scope_type"], "current_record")
        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(recordId="not-an-id"))
        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(recordId=999999999, resolvedDomain=[]))

    def test_capture_rejects_tampered_action_view_and_unsupported_model(self):
        wrong_action = self.env["ir.actions.act_window"].create({
            "name": "Wrong model action",
            "res_model": "res.users",
            "view_mode": "list",
        })
        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(actionId=wrong_action.id))
        wrong_view = self.env["ir.ui.view"].create({
            "name": "Wrong model view",
            "model": "res.users",
            "arch": "<list><field name='name'/></list>",
        })
        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(viewId=wrong_view.id))
        with self.assertRaises(UserError):
            self.adapter.capture(self._payload(modelName="res.users.settings"))

    def test_capture_validates_matching_action_groups_with_odoo_19_fields(self):
        action = self.env["ir.actions.act_window"].create({
            "name": "Matching partner action",
            "res_model": "res.partner",
            "view_mode": "list,form",
        })
        captured = self.adapter.capture(self._payload(actionId=action.id))
        self.assertEqual(captured["action_id"], action.id)

        restricted_group = self.env["res.groups"].create({"name": "Restricted partner action"})
        action.group_ids = [Command.link(restricted_group.id)]
        user = self.env["res.users"].create({
            "name": "Alert action tester",
            "login": "alert-action-tester",
            "email": "alert-action-tester@example.com",
            "group_ids": [Command.link(self.env.ref("base.group_system").id)],
        })
        with self.assertRaises(AccessError):
            self.adapter.with_user(user).capture(self._payload(actionId=action.id))

        user.group_ids = [Command.link(restricted_group.id)]
        captured = self.adapter.with_user(user).capture(self._payload(actionId=action.id))
        self.assertEqual(captured["action_id"], action.id)
