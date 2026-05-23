import unittest

from src.models import Paper
from src.rank import score_paper, suggest_section


def make_paper(title, abstract=None):
    return Paper(
        title=title,
        authors=[],
        venue="IEEE Journal of Solid-State Circuits",
        venue_short="JSSC",
        year=2026,
        publication_date="2026-05-10",
        doi=None,
        url=None,
        abstract=abstract,
        source_priority=["OpenAlex"],
        openalex_id=None,
        semantic_scholar_id=None,
        crossref_id=None,
        relevance_score=0.0,
        relevance_tags=[],
        suggested_section=None,
    )


class RankTests(unittest.TestCase):
    def test_implantable_rf_soc_paper_gets_high_score(self):
        paper = make_paper(
            "Implantable RF SoC for biomedical telemetry",
            "A CMOS ASIC with wireless power and an analog front-end.",
        )

        scored = score_paper(paper, [], [])

        self.assertGreaterEqual(scored.relevance_score, 10)
        self.assertIn("implantable", scored.relevance_tags)
        self.assertIn("rf", scored.relevance_tags)
        self.assertIn("soc", scored.relevance_tags)

    def test_editorial_review_correction_gets_low_score(self):
        paper = make_paper("Editorial review and correction")

        scored = score_paper(paper, [], ["review", "editorial", "correction"])

        self.assertLessEqual(scored.relevance_score, -6)

    def test_backscatter_maps_to_passive_and_hybrid_telemetry(self):
        self.assertEqual(
            suggest_section("Backscatter telemetry for implants", None),
            "IV-A(iii) Passive and hybrid telemetry",
        )

    def test_antenna_tissue_matching_maps_to_external_rf_interfaces(self):
        self.assertEqual(
            suggest_section("Antenna matching in tissue", None),
            "IV-B External RF interfaces",
        )

    def test_bandgap_maps_to_precision_analog_sensor_circuits(self):
        self.assertEqual(
            suggest_section("Low-power bandgap voltage reference", None),
            "Precision analog / sensor circuits",
        )

    def test_ultrasound_maps_to_ultrasound_biomedical_interface(self):
        self.assertEqual(
            suggest_section("Ultrasound PZT acoustic link", None),
            "Ultrasound biomedical interface",
        )


if __name__ == "__main__":
    unittest.main()
