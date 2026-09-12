import unittest

from ..models.contracts import (
    CapturedContext,
    ContextAdapter,
    DeliverySink,
    RuleSpec,
    SUPPORTED_EVENT_TYPES,
)


class ContractsTest(unittest.TestCase):
    def test_contracts_are_importable_without_odoo(self):
        self.assertIsNotNone(RuleSpec)
        self.assertIsNotNone(CapturedContext)
        self.assertIsNotNone(ContextAdapter)
        self.assertIsNotNone(DeliverySink)

    def test_context_transfer_is_json_safe_by_shape(self):
        context = CapturedContext(
            model_name="res.partner",
            action_id=1,
            view_id=2,
            record_id=None,
            company_id=1,
            resolved_domain=[],
            visible_fields=("name",),
        )
        self.assertEqual(context.model_name, "res.partner")
        self.assertEqual(context.visible_fields, ("name",))

    def test_event_contract_covers_record_field_and_date_events(self):
        self.assertEqual(
            SUPPORTED_EVENT_TYPES,
            {
                "record_created",
                "record_deleted",
                "field_changed",
                "field_becomes",
                "field_is_no_longer",
                "field_postponed",
                "field_advanced",
                "date_reached",
                "date_relative_before",
                "date_relative_after",
            },
        )


if __name__ == "__main__":
    unittest.main()
