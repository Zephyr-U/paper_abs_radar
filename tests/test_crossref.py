import unittest
from unittest.mock import patch

from src.errors import SourceFetchError
from src.sources.crossref import search_crossref_by_issn


class CrossrefSearchTests(unittest.TestCase):
    def test_search_crossref_paginates_and_skips_front_matter(self):
        def fake_get_json(_url, params):
            offset = params["offset"]
            if offset == 0:
                return {
                    "message": {
                        "total-results": 5,
                        "items": [
                            {
                                "DOI": "10.1109/a",
                                "title": ["A Research Article"],
                                "container-title": ["IEEE Journal of Solid-State Circuits"],
                                "published-print": {"date-parts": [[2026, 5]]},
                            },
                            {
                                "DOI": "10.1109/toc",
                                "title": ["Table of Contents"],
                                "container-title": ["IEEE Journal of Solid-State Circuits"],
                                "published-print": {"date-parts": [[2026, 5]]},
                            },
                            {
                                "DOI": "10.1109/editor",
                                "title": ["New Associate Editor"],
                                "container-title": ["IEEE Journal of Solid-State Circuits"],
                                "published-print": {"date-parts": [[2026, 5]]},
                            },
                            {
                                "DOI": "10.1109/correction",
                                "title": ["Corrections to “A Research Article”"],
                                "container-title": ["IEEE Solid-State Circuits Letters"],
                                "published-print": {"date-parts": [[2026]]},
                            },
                        ],
                    }
                }
            return {
                "message": {
                    "total-results": 5,
                    "items": [
                        {
                            "DOI": "10.1109/b",
                            "title": ["Another Research Article"],
                            "container-title": ["IEEE Journal of Solid-State Circuits"],
                            "published-print": {"date-parts": [[2026, 5]]},
                        }
                    ],
                }
            }

        with patch("src.sources.crossref.get_json", side_effect=fake_get_json) as mocked:
            papers = search_crossref_by_issn("0018-9200", "2026-05-01", "2026-05-31", rows=2)

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual([p.title for p in papers], ["A Research Article", "Another Research Article"])

    def test_search_crossref_can_filter_by_created_date(self):
        def fake_get_json(_url, params):
            return {"message": {"total-results": 0, "items": []}}

        with patch("src.sources.crossref.get_json", side_effect=fake_get_json) as mocked:
            search_crossref_by_issn("2573-9603", "2026-05-01", "2026-05-31", date_field="created")

        self.assertIn("from-created-date:2026-05-01", mocked.call_args.kwargs["params"]["filter"])
        self.assertIn("until-created-date:2026-05-31", mocked.call_args.kwargs["params"]["filter"])
        self.assertEqual(mocked.call_args.kwargs["params"]["sort"], "created")

    def test_search_crossref_raises_when_api_fetch_fails(self):
        with patch("src.sources.crossref.get_json", return_value=None):
            with self.assertRaises(SourceFetchError):
                search_crossref_by_issn("0018-9200", "2026-05-01", "2026-05-31")

    def test_search_crossref_returns_empty_list_for_successful_empty_response(self):
        with patch("src.sources.crossref.get_json", return_value={"message": {"total-results": 0, "items": []}}):
            papers = search_crossref_by_issn("0018-9200", "2026-05-01", "2026-05-31")

        self.assertEqual(papers, [])
