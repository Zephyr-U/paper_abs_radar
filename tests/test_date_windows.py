import unittest
from datetime import date

from src.date_windows import build_run_label, compact_date_label, resolve_date_window


class DateWindowTests(unittest.TestCase):
    def test_backfill_uses_last_n_years_inclusive(self):
        start, end = resolve_date_window("backfill", today=date(2026, 5, 23), backfill_years=5)

        self.assertEqual(start, "2021-05-23")
        self.assertEqual(end, "2026-05-23")

    def test_weekly_is_not_supported(self):
        with self.assertRaises(ValueError):
            resolve_date_window("weekly", today=date(2026, 5, 23), backfill_years=5)

    def test_monthly_is_not_supported_by_backfill_date_window(self):
        with self.assertRaises(ValueError):
            resolve_date_window("monthly", today=date(2026, 5, 23), backfill_years=5)

    def test_build_run_label_includes_mode_and_range(self):
        self.assertEqual(
            build_run_label("backfill", "2021-05-23", "2026-05-23"),
            "260523_backfill_2021-05-23_to_2026-05-23",
        )

    def test_compact_date_label_converts_iso_date_to_yymmdd(self):
        self.assertEqual(compact_date_label("2026-05-23"), "260523")
