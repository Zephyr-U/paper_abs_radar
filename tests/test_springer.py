import unittest
from unittest.mock import patch

from src.errors import SourceFetchError
from src.sources.springer import search_nature_research_articles, springer_enrich_by_doi


class SpringerTests(unittest.TestCase):
    def test_meta_api_v2_lookup_by_doi(self):
        payload = {
            "records": [
                {
                    "title": "Nature Sensors Article",
                    "doi": "10.1038/s44460-026-00076-6",
                    "abstract": "Springer Nature abstract.",
                    "publicationDate": "2026-05-22",
                    "journalTitle": "Nature Sensors",
                    "url": [{"value": "https://www.nature.com/articles/s44460-026-00076-6"}],
                    "creators": [{"creator": "A. Author"}],
                }
            ]
        }

        with patch.dict("os.environ", {"SPRINGER_API_KEY": "test-key"}):
            with patch("src.sources.springer.get_json", return_value=payload) as get_json:
                paper = springer_enrich_by_doi("10.1038/s44460-026-00076-6")

        self.assertEqual(paper.abstract, "Springer Nature abstract.")
        self.assertEqual(paper.venue, "Nature Sensors")
        self.assertEqual(paper.url, "https://www.nature.com/articles/s44460-026-00076-6")
        self.assertEqual(get_json.call_args.args[0], "https://api.springernature.com/meta/v2/json")
        self.assertEqual(get_json.call_args.kwargs["params"]["q"], "doi:10.1038/s44460-026-00076-6")

    def test_search_nature_research_articles_parses_article_page_and_enriches_dois(self):
        html = """
        <html><body>
          <a href="/articles/s41551-026-01670-2">Wearable sensor</a>
          <a href="https://www.nature.com/articles/s41551-026-01684-w">Spinal stimulation</a>
          <a href="/articles/s41552-026-00001-1">Wrong journal</a>
        </body></html>
        """

        def enrich(doi):
            return {
                "10.1038/s41551-026-01670-2": _paper(
                    "Wireless wearable bioelectronic sweat sensor",
                    "10.1038/s41551-026-01670-2",
                    "2026-05-01",
                ),
                "10.1038/s41551-026-01684-w": _paper(
                    "Transcutaneous spinal cord stimulation",
                    "10.1038/s41551-026-01684-w",
                    "2026-04-20",
                ),
            }.get(doi)

        with patch("src.sources.springer.get_text", return_value=html):
            with patch("src.sources.springer.springer_enrich_by_doi", side_effect=enrich):
                papers = search_nature_research_articles(
                    "Nature BME",
                    from_date="2026-04-01",
                    to_date="2026-05-31",
                    limit=10,
                )

        self.assertEqual([paper.doi for paper in papers], ["10.1038/s41551-026-01670-2", "10.1038/s41551-026-01684-w"])
        self.assertTrue(all(paper.venue_short == "Nature BME" for paper in papers))

    def test_search_nature_research_articles_raises_when_listing_fetch_fails(self):
        with patch("src.sources.springer.get_text", return_value=None):
            with self.assertRaises(SourceFetchError):
                search_nature_research_articles("Nature BME", from_date="2026-04-01", to_date="2026-05-31")


def _paper(title, doi, publication_date):
    from src.models import Paper

    return Paper(
        title=title,
        authors=["A. Author"],
        venue="Nature Biomedical Engineering",
        venue_short="Nature Biomedical Engineering",
        year=2026,
        publication_date=publication_date,
        doi=doi,
        url=f"https://www.nature.com/articles/{doi.split('/')[-1]}",
        abstract="Abstract.",
        source_priority=["Springer"],
    )
