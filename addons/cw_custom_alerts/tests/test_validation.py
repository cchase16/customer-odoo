# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from types import SimpleNamespace

from odoo.tests.common import TransactionCase

from ..models.validation import (
    AlertConfigurationError,
    canonicalize_domain,
    combine_domains,
    render_plain_text,
    validate_rule_configuration,
)


class TestAlertValidation(TransactionCase):
    def test_domain_is_copied_and_combined_without_executable_values(self):
        scope = [["state", "=", "sale"]]
        condition = [["amount_total", ">", 10]]
        canonical = canonicalize_domain(scope)
        self.assertEqual(canonical, scope)
        self.assertIsNot(canonical, scope)
        self.assertEqual(combine_domains(scope, condition), scope + condition)
        with self.assertRaises(AlertConfigurationError):
            canonicalize_domain([["state", "=", "__import__('os')"]])

    def test_domain_rejects_unsafe_shape_operator_and_complexity(self):
        with self.assertRaises(AlertConfigurationError):
            canonicalize_domain({"field": "state"})
        with self.assertRaises(AlertConfigurationError):
            canonicalize_domain([["state", "=", {"call": "eval"}]])
        with self.assertRaises(AlertConfigurationError):
            canonicalize_domain([["state", "regex", "sale"]])
        with self.assertRaises(AlertConfigurationError):
            canonicalize_domain(["|", ["state", "=", "sale"]])

    def test_domain_rejects_unknown_nonstored_collection_and_deep_paths(self):
        class FakeField:
            def __init__(self, field_type, store=True, comodel_name=None):
                self.type = field_type
                self.store = store
                self.comodel_name = comodel_name

        class FakeEnv(dict):
            def __getitem__(self, key):
                return super().__getitem__(key)

        related = SimpleNamespace(
            _fields={"name": FakeField("char")},
            env=FakeEnv(),
            _transient=False,
            _abstract=False,
            _auto=True,
        )
        model = SimpleNamespace(
            _fields={
                "name": FakeField("char"),
                "partner_id": FakeField("many2one", comodel_name="res.partner"),
                "tags": FakeField("many2many"),
                "computed": FakeField("char", store=False),
            },
            env=FakeEnv({"res.partner": related}),
            _transient=False,
            _abstract=False,
            _auto=True,
        )
        self.assertEqual(canonicalize_domain([["partner_id.name", "=", "A"]], model), [["partner_id.name", "=", "A"]])
        for domain in (
            [["missing", "=", "A"]],
            [["tags", "=", "A"]],
            [["computed", "=", "A"]],
            [["partner_id.name.x.y", "=", "A"]],
        ):
            with self.assertRaises(AlertConfigurationError):
                canonicalize_domain(domain, model)

    def test_placeholder_whitelist_and_plain_text_rendering(self):
        template = "${rule_name}: ${record_name} at ${event_time}"
        self.assertEqual(
            render_plain_text(
                template,
                {"rule_name": "Late order", "record_name": "SO-1", "event_time": "12:00"},
            ),
            "Late order: SO-1 at 12:00",
        )
        with self.assertRaises(AlertConfigurationError):
            render_plain_text("${unknown}", {"unknown": "value"})
        with self.assertRaises(AlertConfigurationError):
            render_plain_text("{{ dangerous }}", {})
        with self.assertRaises(AlertConfigurationError):
            render_plain_text("<script>alert(1)</script>", {})

    def test_record_and_field_event_rules_have_compatible_configuration(self):
        base = {
            "event_type": "record_created",
            "scope_type": "captured_domain",
            "scope_domain_json": [["state", "=", "sale"]],
            "condition_domain_json": [["amount_total", ">", 0]],
            "subject_template": "${model_name}",
            "message_template": "${record_name}",
        }
        canonical = validate_rule_configuration(base, at_activation=True)
        self.assertEqual(canonical["scope_domain_json"], base["scope_domain_json"])
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration({**base, "field_id": 2}, at_activation=True)
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration(
                {**base, "event_type": "field_postponed"},
                watched_field=SimpleNamespace(type="char", store=True),
            )
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration(
                {**base, "event_type": "field_becomes", "comparison_value_json": 4},
                watched_field=SimpleNamespace(type="char", store=True),
            )

    def test_expiry_and_relative_date_constraints(self):
        base = {
            "event_type": "date_relative_before",
            "scope_type": "current_record",
            "target_res_id": 7,
            "subject_template": "Alert",
            "message_template": "Message",
            "date_offset_amount": 2,
            "date_offset_unit": "days",
            "date_offset_direction": "before",
        }
        future = datetime(2026, 9, 13, tzinfo=timezone.utc)
        field = SimpleNamespace(type="date", store=True)
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration(
                {**base, "expires_at": "2026-09-12T00:00:00+00:00"},
                watched_field=field,
                at_activation=True,
                now=future,
            )
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration({**base, "date_offset_amount": 0}, watched_field=field)
        with self.assertRaises(AlertConfigurationError):
            validate_rule_configuration({**base, "event_type": "record_created", "date_offset_amount": 1})
