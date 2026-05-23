import unittest
from unittest.mock import patch

from src.sources.springer import springer_enrich_by_doi


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
