import unittest

from src.enrich import deduplicate_and_merge, normalize_doi, normalize_title
from src.models import Paper


def make_paper(**overrides):
    data = {
        "title": "Implantable RF SoC",
        "authors": ["A. Author"],
        "venue": "IEEE Journal of Solid-State Circuits",
        "venue_short": "JSSC",
        "year": 2026,
        "publication_date": "2026-05-10",
        "doi": "https://doi.org/10.1109/example",
        "url": "https://example.org/paper",
        "abstract": None,
        "source_priority": ["OpenAlex"],
        "openalex_id": "https://openalex.org/W1",
        "semantic_scholar_id": None,
        "crossref_id": None,
        "relevance_score": 0.0,
        "relevance_tags": [],
        "suggested_section": None,
    }
    data.update(overrides)
    return Paper(**data)


class DedupTests(unittest.TestCase):
    def test_normalize_doi_removes_common_prefixes_and_lowercases(self):
        self.assertEqual(normalize_doi(" https://doi.org/10.1109/ABC.Def "), "10.1109/abc.def")
        self.assertEqual(normalize_doi("http://dx.doi.org/10.1038/XYZ"), "10.1038/xyz")
        self.assertIsNone(normalize_doi(None))

    def test_normalize_title_removes_punctuation_and_spacing_noise(self):
        self.assertEqual(normalize_title(" A  Low-Power, RF SoC! "), "a low power rf soc")

    def test_deduplicate_and_merge_prefers_base_and_fills_missing_fields(self):
        base = make_paper(abstract=None, semantic_scholar_id=None)
        enrichment = make_paper(
            doi="10.1109/EXAMPLE",
            abstract="A restored abstract.",
            semantic_scholar_id="S2-1",
            source_priority=["Semantic Scholar"],
            openalex_id=None,
        )

        merged = deduplicate_and_merge([base, enrichment])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].abstract, "A restored abstract.")
        self.assertEqual(merged[0].openalex_id, "https://openalex.org/W1")
        self.assertEqual(merged[0].semantic_scholar_id, "S2-1")
        self.assertEqual(merged[0].source_priority, ["OpenAlex", "Semantic Scholar"])


if __name__ == "__main__":
    unittest.main()
