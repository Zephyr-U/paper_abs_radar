import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.abstracts import enrich_missing_abstracts
from src.models import Paper


def make_paper(**overrides):
    data = {
        "title": "A Missing Abstract Paper",
        "authors": ["A. Author"],
        "venue": "IEEE Journal of Solid-State Circuits",
        "venue_short": "JSSC",
        "year": 2026,
        "publication_date": "2026-01-01",
        "doi": "10.1109/example",
        "url": "https://doi.org/10.1109/example",
        "abstract": None,
        "source_priority": ["OpenAlex"],
    }
    data.update(overrides)
    return Paper(**data)


class AbstractEnrichTests(unittest.TestCase):
    def test_skips_papers_that_already_have_abstract(self):
        paper = make_paper(abstract="Already present")

        enriched = enrich_missing_abstracts([paper])

        self.assertEqual(enriched[0].abstract, "Already present")

    def test_fills_missing_abstract_from_openalex_first(self):
        openalex_paper = make_paper(abstract="OpenAlex abstract.", source_priority=["OpenAlex"])

        with patch("src.abstracts.openalex.get_by_doi", return_value=openalex_paper) as openalex_get:
            with patch("src.abstracts.crossref.get_by_doi") as crossref_get:
                with patch("src.abstracts.semantic_scholar.get_by_doi") as semantic_get:
                    enriched = enrich_missing_abstracts([make_paper()])

        self.assertEqual(enriched[0].abstract, "OpenAlex abstract.")
        openalex_get.assert_called_once_with("10.1109/example")
        crossref_get.assert_not_called()
        semantic_get.assert_not_called()

    def test_falls_back_to_crossref_when_openalex_has_no_abstract(self):
        openalex_paper = make_paper(abstract=None, source_priority=["OpenAlex"])
        crossref_paper = make_paper(abstract="Crossref abstract.", source_priority=["Crossref"])

        with patch("src.abstracts.openalex.get_by_doi", return_value=openalex_paper):
            with patch("src.abstracts.crossref.get_by_doi", return_value=crossref_paper) as crossref_get:
                with patch("src.abstracts.semantic_scholar.get_by_doi") as semantic_get:
                    enriched = enrich_missing_abstracts([make_paper()])

        self.assertEqual(enriched[0].abstract, "Crossref abstract.")
        crossref_get.assert_called_once_with("10.1109/example")
        semantic_get.assert_not_called()

    def test_falls_back_to_semantic_scholar_when_openalex_and_crossref_have_no_abstract(self):
        openalex_paper = make_paper(abstract=None, source_priority=["OpenAlex"])
        crossref_paper = make_paper(abstract=None, source_priority=["Crossref"])
        semantic_paper = make_paper(abstract="Semantic Scholar abstract.", source_priority=["Semantic Scholar"])

        with patch("src.abstracts.openalex.get_by_doi", return_value=openalex_paper):
            with patch("src.abstracts.crossref.get_by_doi", return_value=crossref_paper):
                with patch("src.abstracts.semantic_scholar.get_by_doi", return_value=semantic_paper):
                    enriched = enrich_missing_abstracts([make_paper()])

        self.assertEqual(enriched[0].abstract, "Semantic Scholar abstract.")

    def test_uses_cache_for_repeated_doi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "abstract_cache.json"
            cache_path.write_text('{"doi:10.1109/example": "Cached abstract."}', encoding="utf-8")

            with patch("src.abstracts.openalex.get_by_doi") as openalex_get:
                enriched = enrich_missing_abstracts([make_paper()], cache_path=cache_path)

        self.assertEqual(enriched[0].abstract, "Cached abstract.")
        openalex_get.assert_not_called()

    def test_writes_cache_after_new_lookup(self):
        openalex_paper = make_paper(abstract="OpenAlex abstract.", source_priority=["OpenAlex"])
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "abstract_cache.json"
            with patch("src.abstracts.openalex.get_by_doi", return_value=openalex_paper):
                enrich_missing_abstracts([make_paper()], cache_path=cache_path)

            self.assertIn("OpenAlex abstract.", cache_path.read_text(encoding="utf-8"))

    def test_does_not_search_by_title_by_default(self):
        with patch("src.abstracts.openalex.get_by_doi", return_value=None):
            with patch("src.abstracts.crossref.get_by_doi", return_value=None):
                with patch("src.abstracts.semantic_scholar.get_by_doi", return_value=None):
                    with patch("src.abstracts.semantic_scholar.search_by_title") as title_search:
                        enriched = enrich_missing_abstracts([make_paper(doi=None)])

        self.assertIsNone(enriched[0].abstract)
        title_search.assert_not_called()

    def test_can_search_by_title_when_enabled(self):
        semantic_paper = make_paper(abstract="Title search abstract.", source_priority=["Semantic Scholar"])

        with patch("src.abstracts.openalex.get_by_doi") as openalex_get:
            with patch("src.abstracts.crossref.get_by_doi") as crossref_get:
                with patch("src.abstracts.semantic_scholar.search_by_title", return_value=semantic_paper):
                    enriched = enrich_missing_abstracts([make_paper(doi=None)], allow_title_search=True)

        self.assertEqual(enriched[0].abstract, "Title search abstract.")
        openalex_get.assert_not_called()
        crossref_get.assert_not_called()

    def test_fallbacks_use_doi_before_optional_title_search(self):
        semantic_paper = make_paper(abstract="Semantic Scholar abstract.", source_priority=["Semantic Scholar"])

        with patch("src.abstracts.openalex.get_by_doi", return_value=None):
            with patch("src.abstracts.crossref.get_by_doi", return_value=None):
                with patch("src.abstracts.semantic_scholar.get_by_doi", return_value=semantic_paper):
                    with patch("src.abstracts.semantic_scholar.search_by_title") as title_search:
                        enriched = enrich_missing_abstracts([make_paper()], allow_title_search=True)

        self.assertEqual(enriched[0].abstract, "Semantic Scholar abstract.")
        title_search.assert_not_called()
