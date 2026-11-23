"""Tests for reports.py (pure logic, no GUI needed)."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports import (  # noqa: E402
    category_choices,
    month_key,
    month_label,
    monthly_totals,
    normalize_category,
    records_in_month,
    shift_month,
)


class MonthTests(unittest.TestCase):
    def test_shift_within_year(self):
        self.assertEqual(shift_month(date(2026, 11, 1), 1), date(2026, 12, 1))

    def test_shift_across_year_boundary(self):
        self.assertEqual(shift_month(date(2026, 12, 1), 1), date(2027, 1, 1))
        self.assertEqual(shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))
        self.assertEqual(shift_month(date(2026, 3, 1), -14), date(2025, 1, 1))

    def test_labels(self):
        self.assertEqual(month_key(date(2026, 3, 1)), "2026-03")
        self.assertEqual(month_label(date(2026, 3, 1)), "March 2026")


class ReportTests(unittest.TestCase):
    records = [
        (1, "Income", "Allowance", 1000.0, "2026-11-02"),
        (2, "Expense", "Food", 150.0, "2026-11-05"),
        (3, "Expense", "Food", 50.0, "2026-10-15"),
        (4, "Expense", "Bills", 300.0, "2026-01-10"),  # outside a 6-month window
    ]

    def test_records_in_month(self):
        ids = [r[0] for r in records_in_month(self.records, date(2026, 11, 1))]
        self.assertEqual(ids, [1, 2])

    def test_monthly_totals(self):
        result = monthly_totals(self.records, date(2026, 11, 1), count=6)
        self.assertEqual([m for m, _, _ in result],
                         [date(2026, m, 1) for m in range(6, 12)])
        self.assertEqual(result[-1][1:], (1000.0, 150.0))  # November
        self.assertEqual(result[-2][1:], (0.0, 50.0))      # October
        self.assertEqual(sum(e for _, _, e in result), 200.0)  # January excluded


class CategoryTests(unittest.TestCase):
    def test_reuses_existing_spelling(self):
        self.assertEqual(normalize_category("  food ", ["Food"]), "Food")

    def test_cleans_new_category(self):
        self.assertEqual(normalize_category("  load   wallet ", []), "Load wallet")

    def test_choices_have_no_duplicates(self):
        choices = category_choices(["food", "Gym"])
        self.assertEqual(choices.count("Food"), 1)
        self.assertNotIn("food", choices)
        self.assertIn("Gym", choices)


if __name__ == "__main__":
    unittest.main()
