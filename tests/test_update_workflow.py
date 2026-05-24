import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.models import Paper
from src.update import (
    apply_update_if_threshold_met,
    diff_new_papers,
    enrich_state_abstracts,
    filter_papers_for_profile,
    generate_issue_summary_draft,
    load_papers_json,
    save_papers_json,
)


def paper(title, doi=None):
    return Paper(
        title=title,
        authors=["A. Author"],
        venue="IEEE Journal of Solid-State Circuits",
        venue_short="JSSC",
        year=2026,
        publication_date="2026-05",
        doi=doi,
        url=f"https://doi.org/{doi}" if doi else None,
        abstract=None,
        source_priority=["Crossref"],
    )


class UpdateWorkflowTests(unittest.TestCase):
    def test_diff_new_papers_uses_doi_first(self):
        existing = [paper("Old title", "10.1109/a")]
        current = [paper("Renamed title", "10.1109/a"), paper("New ADC", "10.1109/b")]

        new_papers = diff_new_papers(existing, current)

        self.assertEqual([p.title for p in new_papers], ["New ADC"])

    def test_diff_new_papers_falls_back_to_title(self):
        existing = [paper("A Known Paper")]
        current = [paper("A Known Paper"), paper("A New Paper")]

        new_papers = diff_new_papers(existing, current)

        self.assertEqual([p.title for p in new_papers], ["A New Paper"])

    def test_save_papers_json_writes_core_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "papers.json"
            save_papers_json(path, [paper("New ADC", "10.1109/b")])
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data[0]["title"], "New ADC")
        self.assertEqual(data[0]["doi"], "10.1109/b")
        self.assertNotIn("source_priority", data[0])

    def test_summarize_distribution_groups_major_topics(self):
        papers = [
            paper("A SAR ADC With Noise Shaping"),
            paper("A Compute-in-Memory Accelerator for AI"),
            paper("A 70-GHz RF Transmitter"),
            paper("A Low-Dropout Voltage Regulator"),
        ]

        summary = generate_issue_summary_draft(papers)

        self.assertIn("Data converters: 1", summary)
        self.assertIn("AI / compute accelerators: 1", summary)
        self.assertIn("RF / wireless circuits: 1", summary)
        self.assertIn("Power management: 1", summary)

    def test_summarize_distribution_includes_application_view(self):
        papers = [
            paper("A Wireless Neural Implant SoC"),
            paper("A Bandgap Voltage Reference With Temperature Sensor"),
            paper("A 500-nW Always-On Wake-Up Receiver for IoT"),
            paper("A Compute-in-Memory Accelerator for AI"),
        ]

        summary = generate_issue_summary_draft(papers)

        self.assertIn("## Circuit Topic Distribution", summary)
        self.assertIn("## Application Distribution", summary)
        self.assertIn("Implantable / neural / biomedical: 1", summary)
        self.assertIn("Precision analog / references / sensors: 1", summary)
        self.assertIn("Ultra-low-power / always-on / IoT: 1", summary)

    def test_summarize_distribution_omits_circuit_representative_section(self):
        summary = generate_issue_summary_draft([paper("A SAR ADC With Noise Shaping")])

        self.assertNotIn("## Representative Papers by Circuit Topic", summary)
        self.assertNotIn("## Representative Papers by Application", summary)

    def test_summarize_distribution_classifies_by_title_not_abstract(self):
        abstract_only = paper("A General Purpose Processor")
        abstract_only.abstract = "This abstract mentions neural sensors, low-power operation, and biomedical front-end circuits."

        summary = generate_issue_summary_draft([abstract_only])

        self.assertNotIn("Implantable / neural / biomedical: 1", summary)
        self.assertNotIn("Precision analog / references / sensors: 1", summary)
        self.assertNotIn("Ultra-low-power / always-on / IoT: 1", summary)
        self.assertIn("Other: 1", summary)

    def test_summary_draft_adds_focused_candidates_with_abstracts(self):
        focused = paper("A Wireless Neural Implant SoC")
        focused.abstract = (
            "Implantable neural interfaces require secure low-power operation. "
            "This work presents a mixed-signal SoC using adaptive stimulation and telemetry. "
            "Measurements show improved energy efficiency and reliable neural operation."
        )

        summary = generate_issue_summary_draft([focused])

        self.assertIn("# Issue Summary Draft", summary)
        self.assertIn("Counts are title-keyword based and non-exclusive", summary)
        self.assertIn("## Focused Summary Candidates", summary)
        self.assertIn("### Implantable / neural / biomedical", summary)
        self.assertIn("- Abstract: Implantable neural interfaces require", summary)
        self.assertNotIn("針對問題", summary)
        self.assertNotIn("技術/方法", summary)
        self.assertNotIn("達到效果", summary)

    def test_summary_draft_uses_additional_sample_label(self):
        summary = generate_issue_summary_draft([paper("A SAR ADC With Noise Shaping")])

        self.assertIn("### Additional sample", summary)
        self.assertNotIn("Random sample", summary)

    def test_nature_sensors_summary_uses_wearable_ml_focused_buckets(self):
        papers = [
            paper("Wireless and Battery-Free Implantable Sensing Technologies"),
            paper("Wearable Skin Sensor for Sweat Monitoring"),
            paper("Self-Powered Wireless Sensor Patch"),
            paper("In-Sensor Neuromorphic Computing for Edge AI"),
        ]

        summary = generate_issue_summary_draft(papers, profile="nature_sensors")

        self.assertIn("## Focused Topic Distribution", summary)
        self.assertIn("Implantable / bioelectronic / neural: 1", summary)
        self.assertIn("Wearable / epidermal / sweat / skin: 1", summary)
        self.assertIn("Self-powered / wireless / battery-free: 2", summary)
        self.assertIn("AI / in-sensor / neuromorphic computing: 1", summary)
        self.assertIn("### Implantable / bioelectronic / neural", summary)

    def test_tbicas_summary_uses_biomedical_circuit_focused_buckets(self):
        papers = [
            paper("A Wireless Neural Implant SoC"),
            paper("A Wearable Multimodal Biosignal Acquisition ASIC"),
            paper("A Low-Power ECG PPG AFE"),
            paper("An Edge-AI Processor for Biomedical Signals"),
        ]

        summary = generate_issue_summary_draft(papers, profile="tbicas")

        self.assertIn("## Focused Topic Distribution", summary)
        self.assertIn("Implantable / neural interface: 1", summary)
        self.assertIn("Wearable / biosignal acquisition: 2", summary)
        self.assertIn("Biomedical AFE / sensor interface: 2", summary)
        self.assertIn("Edge AI / biomedical signal processing: 1", summary)
        self.assertIn("### Implantable / neural interface", summary)

    def test_nature_bme_filter_keeps_only_relevant_research_topics(self):
        papers = [
            paper("Wireless and in situ regenerable multimodal wearable bioelectronic sweat sensor"),
            paper("Fundamental limitations of kilohertz-frequency carriers in transcutaneous spinal cord stimulation"),
            paper("A three-dimensional multi-modal foundation model for optical coherence tomography"),
            paper("A cuffless vascular hemodynamics sensor for cardiovascular monitoring"),
            paper("Polymer-mRNA complexes for protein expression"),
            paper("CAR-neutrophils for tumour immunotherapy"),
            paper("Towards generalizable AI for medical diagnosis"),
            paper("A deep learning system for non-invasive breast cancer diagnosis with multimodal data"),
            paper("DeepDrugDiscovery identifies blood-brain barrier permeable autophagy enhancers"),
            paper("High-resolution functional mapping of androgen receptor variants"),
            paper("Three-dimensional quantitative tissue clearing reveals differences in osteovascular niche"),
            paper("Single-nucleus transcriptomics of an engineered pig model reveals neurodegeneration"),
        ]

        filtered = filter_papers_for_profile(papers, "nature_bme")

        self.assertEqual(
            [item.title for item in filtered],
            [
                "Wireless and in situ regenerable multimodal wearable bioelectronic sweat sensor",
                "Fundamental limitations of kilohertz-frequency carriers in transcutaneous spinal cord stimulation",
                "A three-dimensional multi-modal foundation model for optical coherence tomography",
                "A cuffless vascular hemodynamics sensor for cardiovascular monitoring",
            ],
        )

    def test_nature_bme_summary_uses_bioengineering_focused_buckets(self):
        papers = [
            paper("Wireless and in situ regenerable multimodal wearable bioelectronic sweat sensor"),
            paper("Geometry-aware noninvasive mapping of whole human brain dynamics"),
            paper("Whole cross-sectional human ultrasound tomography"),
            paper("Human inflammatory bowel disease-on-a-chip"),
            paper("Cardiovascular hemodynamics monitoring with vascular ultrasound"),
        ]

        summary = generate_issue_summary_draft(papers, profile="nature_bme")

        self.assertIn("Wearable / bioelectronic sensing: 1", summary)
        self.assertIn("Neural / neuromodulation / brain mapping: 1", summary)
        self.assertIn("Biomedical imaging / sensing hardware: 2", summary)
        self.assertIn("Organ/tissue-on-chip / microphysiological systems: 1", summary)
        self.assertIn("Cardiovascular / hemodynamics / vascular monitoring: 1", summary)

    def test_update_below_threshold_does_not_change_baseline(self):
        existing = [paper("Old ADC", "10.1109/old")]
        current = existing + [paper(f"New Paper {idx}", f"10.1109/new{idx}") for idx in range(20)]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            summary_path = Path(tmpdir) / "summary.md"
            save_papers_json(state_path, existing)

            result = apply_update_if_threshold_met(state_path, summary_path, current, threshold=20)
            updated = load_papers_json(state_path)

        self.assertFalse(result.summary_written)
        self.assertEqual(result.new_count, 20)
        self.assertFalse(summary_path.exists())
        self.assertEqual([p.doi for p in updated], ["10.1109/old"])

    def test_update_above_threshold_enriches_writes_draft_and_merges_baseline(self):
        existing = [paper("Old ADC", "10.1109/old")]
        current = existing + [paper(f"New Paper {idx}", f"10.1109/new{idx}") for idx in range(21)]

        def fill(papers, cache_path=None, allow_title_search=False):
            for item in papers:
                item.abstract = f"Abstract for {item.title}"
            return papers

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            summary_path = Path(tmpdir) / "summary_draft.md"
            cache_path = Path(tmpdir) / "cache.json"
            save_papers_json(state_path, existing)

            with patch("src.update.enrich_missing_abstracts", side_effect=fill) as enrich:
                result = apply_update_if_threshold_met(
                    state_path,
                    summary_path,
                    current,
                    threshold=20,
                    cache_path=cache_path,
                )
            updated = load_papers_json(state_path)
            summary_text = summary_path.read_text(encoding="utf-8")

        self.assertTrue(result.summary_written)
        self.assertEqual(result.new_count, 21)
        self.assertEqual(result.with_abstract_after, 21)
        self.assertIn("# Issue Summary Draft", summary_text)
        self.assertIn("Abstract for New Paper", summary_text)
        self.assertEqual(len(updated), 22)
        self.assertTrue(all(p.abstract for p in updated if p.doi != "10.1109/old"))
        enrich.assert_called_once()

    def test_enrich_state_abstracts_saves_filled_state(self):
        existing = [paper("Old ADC", "10.1109/old")]

        def fill(papers, cache_path=None, allow_title_search=False):
            papers[0].abstract = "Filled abstract."
            return papers

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            cache_path = Path(tmpdir) / "cache.json"
            save_papers_json(state_path, existing)

            with patch("src.update.enrich_missing_abstracts", side_effect=fill) as enrich:
                result = enrich_state_abstracts(state_path, cache_path=cache_path)
            updated = load_papers_json(state_path)

        self.assertEqual(result.total, 1)
        self.assertEqual(result.with_abstract_before, 0)
        self.assertEqual(result.with_abstract_after, 1)
        self.assertEqual(updated[0].abstract, "Filled abstract.")
        enrich.assert_called_once()
