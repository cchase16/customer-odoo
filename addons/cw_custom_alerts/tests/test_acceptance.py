# -*- coding: utf-8 -*-

"""Repeatable acceptance fixtures for the generic alert engine.

The production module deliberately does not depend on ``sale`` or ``purchase``.
The optional business fixtures below run when those Community modules are
installed, while the res.partner fixtures keep the acceptance contract
executable on the declared four-dependency baseline.
"""

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models.comparison import compare_event


class TestAlertAcceptance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.AlertRule = cls.env["alert.rule"]
        cls.AlertNotification = cls.env["alert.notification"]
        cls.evaluator = cls.env["alert.event.evaluator"]
        cls.partner_model = cls.env.ref("base.model_res_partner")
        cls.partner_name_field = cls.env.ref("base.field_res_partner__name")
        cls.partner_write_date_field = cls.env.ref("base.field_res_partner__write_date")

    def _rule(self, **values):
        rule_values = {
            "name": "Acceptance fixture",
            "model_id": self.partner_model.id,
            "event_type": "record_created",
            "scope_type": "current_record",
            "subject_template": "Acceptance alert",
            "message_template": "Alert for ${record_name}",
            # Direct fixture evaluation intentionally uses a draft rule. The
            # managed automation path is exercised by test_automation.py.
            "active": False,
            "status": "draft",
        }
        rule_values.update(values)
        return self.AlertRule.create(rule_values)

    def _optional_model(self, model_name):
        model = self.env["ir.model"].search([("model", "=", model_name)], limit=1)
        if not model:
            self.skipTest("optional %s fixture is not installed" % model_name)
        return self.env[model_name]

    def test_filtered_create_fixture_uses_generic_engine(self):
        """A captured list scope admits matching records only."""
        rule = self._rule(
            scope_type="captured_domain",
            scope_domain_json=[["name", "ilike", "acceptance-match"]],
        )
        matching = self.env["res.partner"].create({"name": "Acceptance-match order"})
        nonmatching = self.env["res.partner"].create({"name": "Other order"})

        captured_records = self.env["res.partner"].search(rule.scope_domain_json)
        self.evaluator.evaluate_rule(rule, captured_records)

        self.assertTrue(self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", matching.id),
        ]))
        self.assertFalse(self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", nonmatching.id),
        ]))

    def test_sales_order_fixture_is_optional_and_uses_captured_domain(self):
        """Exercise the real sales model when it is present, without a dependency."""
        sale_orders = self._optional_model("sale.order")
        partner = self.env["res.partner"].create({"name": "Acceptance sales partner"})
        try:
            order = sale_orders.create({"partner_id": partner.id})
        except Exception as error:  # optional fixture configuration is deployment-owned
            self.skipTest("sale.order fixture is not creatable: %s" % type(error).__name__)
        model = self.env["ir.model"]._get("sale.order")
        state_field = model.field_id.filtered(lambda field: field.name == "state")[:1]
        self.assertTrue(state_field, "sale.order must expose a stored state field")
        rule = self._rule(
            name="Sales-order captured create fixture",
            model_id=model.id,
            field_id=False,
            scope_type="captured_domain",
            scope_domain_json=[["state", "=", order.state]],
        )
        self.evaluator.evaluate_rule(rule, sale_orders.search(rule.scope_domain_json))
        self.assertTrue(self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", order.id),
        ]))

    def test_postponed_delivery_fixture_requires_two_dates_and_a_later_value(self):
        """The purchase-delivery semantic is covered by the generic comparator."""
        partner = self.env["res.partner"].create({"name": "Delivery fixture"})
        rule = self._rule(
            name="Purchase delivery postponed fixture",
            model_id=self.partner_model.id,
            field_id=self.partner_write_date_field.id,
            event_type="field_postponed",
            scope_type="current_record",
            target_res_id=partner.id,
        )
        # Odoo may expose datetime fields as strings or datetime instances;
        # the fixture deliberately uses the canonical ORM string form.
        old_value = "2020-01-01 00:00:00"
        self.assertTrue(partner.write_date)
        self.assertTrue(compare_event("field_postponed", old_value, partner.write_date).matched)
        self.evaluator.evaluate_rule(
            rule, partner, {"old_values": {partner.id: {"write_date": old_value}}}
        )
        self.assertTrue(self.AlertNotification.search([
            ("rule_id", "=", rule.id), ("res_id", "=", partner.id),
        ]))

        equal_rule = self._rule(
            name="Purchase delivery unchanged fixture",
            model_id=self.partner_model.id,
            field_id=self.partner_write_date_field.id,
            event_type="field_postponed",
            scope_type="current_record",
            target_res_id=partner.id,
        )
        self.evaluator.evaluate_rule(
            equal_rule, partner, {"old_values": {partner.id: {"write_date": partner.write_date}}}
        )
        self.assertFalse(self.AlertNotification.search([
            ("rule_id", "=", equal_rule.id), ("res_id", "=", partner.id),
        ]))

    def test_purchase_delivery_field_fixture_selects_a_stored_date_field_when_available(self):
        """Record the deployment-specific purchase field without hard-coding production logic."""
        purchase_model = self.env["ir.model"].search([("model", "in", ["purchase.order", "purchase.order.line"])], limit=1)
        if not purchase_model:
            self.skipTest("optional purchase fixture is not installed")
        candidates = purchase_model.field_id.filtered(
            lambda field: field.name in {
                "date_planned", "date_order", "date_approve", "scheduled_date", "commitment_date",
            } and field.ttype in {"date", "datetime"} and field.store
        )
        self.assertTrue(candidates, "purchase fixture needs a stored date or datetime field")

    def test_offline_recipient_recovery_uses_persistent_inbox_state(self):
        rule = self._rule()
        notification = self.AlertNotification.create({
            "rule_id": rule.id,
            "rule_name_snapshot": rule.name,
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
            "model_name": "res.partner",
            "model_label": "Contact",
            "res_id": 1,
            "event_type": "record_created",
            "subject": "Offline fixture",
            "message": "Persistent offline alert",
            "occurred_at": fields.Datetime.now(),
            "occurrence_key": "acceptance-offline-%s" % rule.id,
        })
        state = self.AlertNotification.get_inbox_state()
        self.assertEqual(state["count"], 1)
        self.assertEqual(state["notifications"][0]["id"], notification.id)
