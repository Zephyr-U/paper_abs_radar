import unittest
from unittest.mock import patch

from src.sources.openalex import paper_from_openalex_work, search_openalex_by_issn


class OpenAlexMappingTests(unittest.TestCase):
    def test_paratext_records_are_skipped(self):
        work = {
            "title": "Table of Contents",
            "is_paratext": True,
            "primary_location": {"source": {"display_name": "IEEE Journal of Solid-State Circuits"}},
        }

        self.assertIsNone(paper_from_openalex_work(work, venue_short="JSSC"))

    def test_publication_information_records_are_skipped(self):
        work = {
            "title": "IEEE Journal of Solid-State Circuits Publication Information",
            "primary_location": {"source": {"display_name": "IEEE Journal of Solid-State Circuits"}},
        }

        self.assertIsNone(paper_from_openalex_work(work, venue_short="JSSC"))

    def test_search_openalex_by_issn_paginates_until_count_is_fetched(self):
        def fake_get_json(_url, params):
            page = params["page"]
            if page == 1:
                return {
                    "meta": {"count": 3},
                    "results": [
                        {
                            "id": "W1",
                            "title": "First JSSC Article",
                            "publication_year": 2026,
                            "publication_date": "2026-01-02",
                            "primary_location": {"source": {"display_name": "IEEE Journal of Solid-State Circuits"}},
                        },
                        {
                            "id": "W2",
                            "title": "Table of Contents",
                            "is_paratext": True,
                            "primary_location": {"source": {"display_name": "IEEE Journal of Solid-State Circuits"}},
                        },
                    ],
                }
            return {
                "meta": {"count": 3},
                "results": [
                    {
                        "id": "W3",
                        "title": "Second JSSC Article",
                        "publication_year": 2026,
                        "publication_date": "2026-01-01",
                        "primary_location": {"source": {"display_name": "IEEE Journal of Solid-State Circuits"}},
                    }
                ],
            }

        with patch("src.sources.openalex.get_json", side_effect=fake_get_json) as mocked:
            papers = search_openalex_by_issn("0018-9200", "2026-01-01", "2026-01-02", per_page=2)

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual([paper.title for paper in papers], ["First JSSC Article", "Second JSSC Article"])
