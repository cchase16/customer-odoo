import unittest
from datetime import date

from ..models.comparison import compare_event, normalize_value


class ComparisonTest(unittest.TestCase):
    def test_record_events_always_match_their_event(self):
        self.assertTrue(compare_event("record_created").matched)
        self.assertTrue(compare_event("record_deleted").matched)

    def test_transition_events_use_old_and_new_values(self):
        self.assertTrue(compare_event("field_changed", "draft", "confirmed").matched)
        self.assertFalse(compare_event("field_changed", "draft", "draft").matched)
        self.assertTrue(compare_event("field_becomes", "draft", "confirmed", "confirmed").matched)
        self.assertFalse(compare_event("field_becomes", "confirmed", "confirmed", "confirmed").matched)
        self.assertTrue(compare_event("field_is_no_longer", "confirmed", "draft", "confirmed").matched)

    def test_date_transitions_require_two_values_and_use_direction(self):
        self.assertTrue(compare_event("field_postponed", date(2026, 9, 1), date(2026, 9, 2)).matched)
        self.assertTrue(compare_event("field_advanced", "2026-09-02", "2026-09-01").matched)
        self.assertFalse(compare_event("field_postponed", None, "2026-09-02").matched)
        self.assertFalse(compare_event("field_advanced", "2026-09-02", False).matched)

    def test_normalization_is_orm_shape_independent(self):
        self.assertEqual(normalize_value([1, "x"]), (1, "x"))
        self.assertEqual(normalize_value({"b": 2, "a": 1}), (("a", 1), ("b", 2)))

