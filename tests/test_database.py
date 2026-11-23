"""Tests for database.py. Run from the project folder with:

    python -m unittest discover tests
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        # Use a throwaway database so tests never touch your real data in AppData.
        self.tmp = tempfile.TemporaryDirectory()
        self.original = database.DATABASE
        database.DATABASE = os.path.join(self.tmp.name, "test.db")
        database.create_database()

    def tearDown(self):
        database.DATABASE = self.original
        self.tmp.cleanup()

    def test_empty_totals_are_zero(self):
        self.assertEqual(database.get_totals(), (0, 0, 0))

    def test_totals(self):
        database.add_transaction("Income", "Allowance", 1000.0, "2026-11-01")
        database.add_transaction("Expense", "Food", 250.5, "2026-11-02")
        database.add_transaction("Expense", "Transport", 49.5, "2026-11-03")
        self.assertEqual(database.get_totals(), (1000.0, 300.0, 700.0))

    def test_sorted_by_date_newest_first(self):
        database.add_transaction("Expense", "Later entry, older date", 10, "2026-10-01")
        database.add_transaction("Expense", "Newest date", 10, "2026-11-20")
        dates = [row[4] for row in database.get_transactions()]
        self.assertEqual(dates, ["2026-11-20", "2026-10-01"])

    def test_limit(self):
        for day in range(1, 11):
            database.add_transaction("Expense", "Food", 1, f"2026-11-{day:02d}")
        self.assertEqual(len(database.get_transactions(limit=7)), 7)
        self.assertEqual(len(database.get_transactions()), 10)

    def test_delete(self):
        database.add_transaction("Expense", "Food", 5, "2026-11-01")
        tid = database.get_transactions()[0][0]
        database.delete_transaction(tid)
        self.assertEqual(database.get_transactions(), [])

    def test_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            database.add_transaction("Refund", "Food", 5, "2026-11-01")
        self.assertEqual(database.get_transactions(), [])


if __name__ == "__main__":
    unittest.main()
