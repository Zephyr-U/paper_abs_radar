import unittest
from unittest.mock import patch

from src.sources.crossref import search_crossref_by_issn


class CrossrefSearchTests(unittest.TestCase):
    def test_search_crossref_paginates_and_skips_front_matter(self):
        def fake_get_json(_url, params):
            offset = params["offset"]
            if offset == 0:
                return {
                    "message": {
                        "total-results": 4,
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
                        ],
                    }
                }
            return {
                "message": {
                    "total-results": 4,
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
