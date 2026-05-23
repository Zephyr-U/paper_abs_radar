import unittest
from datetime import date

from src.main import crossref_date_field_for_journal_short, seed_window_bounds_for_journal_short, update_settings_for_journal_short


class MainTests(unittest.TestCase):
    def test_jssc_l_uses_created_date_for_crossref_windows(self):
        self.assertEqual(crossref_date_field_for_journal_short("JSSC-L"), "created")

    def test_other_journals_use_published_date_for_crossref_windows(self):
        self.assertEqual(crossref_date_field_for_journal_short("JSSC"), "published")

    def test_jssc_l_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("JSSC-L", None, None), (90, 9))

    def test_nature_sensors_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("Nature Sensors", None, None), (90, 9))

    def test_jssc_uses_issue_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("JSSC", None, None), (30, 20))

    def test_explicit_update_settings_override_journal_defaults(self):
        self.assertEqual(update_settings_for_journal_short("JSSC-L", 45, 4), (45, 4))

    def test_jssc_l_seed_window_defaults_to_article_count_lookback(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("JSSC-L", date(2026, 5, 23), None, None, None),
            ("2026-02-22", "2026-05-23"),
        )

    def test_nature_sensors_seed_window_defaults_to_article_count_lookback(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("Nature Sensors", date(2026, 5, 23), None, None, None),
            ("2026-02-22", "2026-05-23"),
        )

    def test_explicit_seed_window_dates_override_defaults(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("JSSC-L", date(2026, 5, 23), "2026-03-01", "2026-04-30", None),
            ("2026-03-01", "2026-04-30"),
        )
