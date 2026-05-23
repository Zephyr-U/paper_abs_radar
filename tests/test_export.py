import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.export import CORE_EXPORT_FIELDS, export_outputs
from src.models import Paper


class ExportTests(unittest.TestCase):
    def test_csv_and_json_export_only_core_metadata_fields(self):
        paper = Paper(
            title="A JSSC Article",
            authors=["A. Author", "B. Writer"],
            venue="IEEE Journal of Solid-State Circuits",
            venue_short="JSSC",
            year=2026,
            publication_date="2026-01-01",
            doi="10.1109/example",
            url="https://doi.org/10.1109/example",
            abstract="Abstract text.",
            source_priority=["OpenAlex"],
            openalex_id="W1",
            relevance_score=9,
            relevance_tags=["rf"],
            suggested_section="IV-A(i) TX architectures",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_outputs([paper], tmpdir, "run", "watch.md", "papers.csv", "papers.json")

            with paths["csv"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            with paths["json"].open(encoding="utf-8") as handle:
                data = json.load(handle)

        self.assertEqual(list(rows[0].keys()), CORE_EXPORT_FIELDS)
        self.assertEqual(list(data[0].keys()), CORE_EXPORT_FIELDS)
        self.assertEqual(rows[0]["authors"], "A. Author; B. Writer")
        self.assertNotIn("relevance_score", data[0])
