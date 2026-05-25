import unittest
from datetime import date
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.errors import SourceFetchError
from src.models import Journal
from src.main import (
    crossref_date_field_for_journal_short,
    fetch_update_candidates,
    main,
    seed_window_bounds_for_journal_short,
    summary_profile_for_journal_short,
    update_settings_for_journal_short,
)


class MainTests(unittest.TestCase):
    def test_jssc_l_uses_created_date_for_crossref_windows(self):
        self.assertEqual(crossref_date_field_for_journal_short("JSSC-L"), "created")

    def test_other_journals_use_published_date_for_crossref_windows(self):
        self.assertEqual(crossref_date_field_for_journal_short("JSSC"), "published")

    def test_jssc_l_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("JSSC-L", None, None), (90, 9))

    def test_nature_sensors_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("Nature Sensors", None, None), (90, 9))

    def test_tbicas_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("TBioCAS", None, None), (90, 9))

    def test_nature_bme_uses_article_count_update_defaults(self):
        self.assertEqual(update_settings_for_journal_short("Nature BME", None, None), (90, 9))

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

    def test_tbicas_seed_window_defaults_to_article_count_lookback(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("TBioCAS", date(2026, 5, 23), None, None, None),
            ("2026-02-22", "2026-05-23"),
        )

    def test_nature_bme_seed_window_defaults_to_article_count_lookback(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("Nature BME", date(2026, 5, 23), None, None, None),
            ("2026-02-22", "2026-05-23"),
        )

    def test_nature_bme_uses_filtered_summary_profile(self):
        self.assertEqual(summary_profile_for_journal_short("Nature BME"), "nature_bme")

    def test_nature_bme_update_candidates_use_nature_research_articles(self):
        journal = Journal("Nature Biomedical Engineering", "Nature BME", "2157-846X", "nature")

        with patch("src.main.search_nature_research_articles", return_value=["paper"]) as nature_search:
            with patch("src.main.search_crossref_by_issn") as crossref_search:
                papers = fetch_update_candidates(journal, "2026-02-22", "2026-05-23")

        self.assertEqual(papers, ["paper"])
        nature_search.assert_called_once_with("Nature BME", from_date="2026-02-22", to_date="2026-05-23")
        crossref_search.assert_not_called()

    def test_explicit_seed_window_dates_override_defaults(self):
        self.assertEqual(
            seed_window_bounds_for_journal_short("JSSC-L", date(2026, 5, 23), "2026-03-01", "2026-04-30", None),
            ("2026-03-01", "2026-04-30"),
        )

    def test_check_update_source_fetch_failure_returns_2_and_preserves_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            summary_dir = Path(tmpdir) / "summaries"
            state_dir.mkdir()
            state_path = state_dir / "Nature Sensors_papers.json"
            original_state = [
                {
                    "title": "Existing Paper",
                    "authors": "A. Author",
                    "venue": "Nature Sensors",
                    "venue_short": "Nature Sensors",
                    "year": 2026,
                    "publication_date": "2026-05-01",
                    "doi": "10.1038/existing",
                    "url": "https://doi.org/10.1038/existing",
                    "abstract": "Existing abstract.",
                }
            ]
            state_path.write_text(json.dumps(original_state), encoding="utf-8")

            with patch("src.main.fetch_update_candidates", side_effect=SourceFetchError("Crossref unavailable")):
                with self.assertLogs(level="ERROR") as logs:
                    result = main(
                        [
                            "--config",
                            "config.yaml",
                            "--mode",
                            "check-update",
                            "--journal",
                            "Nature Sensors",
                            "--state-dir",
                            str(state_dir),
                            "--summary-dir",
                            str(summary_dir),
                        ]
                    )

            self.assertEqual(result, 2)
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), original_state)
            self.assertFalse(summary_dir.exists())
            self.assertIn("Fetch failed for Nature Sensors", "\n".join(logs.output))
            self.assertIn("state unchanged", "\n".join(logs.output))
