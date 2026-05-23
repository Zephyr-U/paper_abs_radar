from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

from src.abstracts import enrich_missing_abstracts
from src.enrich import normalize_doi, normalize_title
from src.export import CORE_EXPORT_FIELDS
from src.models import Paper


@dataclass
class UpdateResult:
    new_count: int
    summary_written: bool
    summary_path: Path | None
    with_abstract_before: int = 0
    with_abstract_after: int = 0


@dataclass
class AbstractStateResult:
    total: int
    with_abstract_before: int
    with_abstract_after: int
    state_path: Path


def diff_new_papers(existing: list[Paper], current: list[Paper]) -> list[Paper]:
    existing_dois = {normalize_doi(paper.doi) for paper in existing if normalize_doi(paper.doi)}
    existing_titles = {normalize_title(paper.title) for paper in existing if paper.title}
    new_papers = []
    for paper in current:
        doi = normalize_doi(paper.doi)
        if doi and doi in existing_dois:
            continue
        if not doi and paper.title and normalize_title(paper.title) in existing_titles:
            continue
        if doi is None and paper.title and normalize_title(paper.title) in existing_titles:
            continue
        if doi is not None or normalize_title(paper.title) not in existing_titles:
            new_papers.append(paper)
    return new_papers


def apply_update_if_threshold_met(
    state_path: Path,
    summary_path: Path,
    current: list[Paper],
    threshold: int = 20,
    cache_path: Path | None = None,
    allow_title_search: bool = False,
    summary_profile: str = "circuits",
) -> UpdateResult:
    existing = load_papers_json(state_path)
    new_papers = diff_new_papers(existing, current)
    if len(new_papers) <= threshold:
        return UpdateResult(new_count=len(new_papers), summary_written=False, summary_path=None)

    with_abstract_before = sum(1 for paper in new_papers if paper.abstract)
    new_papers = enrich_missing_abstracts(
        new_papers,
        cache_path=cache_path,
        allow_title_search=allow_title_search,
    )
    with_abstract_after = sum(1 for paper in new_papers if paper.abstract)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(generate_issue_summary_draft(new_papers, profile=summary_profile), encoding="utf-8")
    merged = existing + new_papers
    save_papers_json(state_path, merged)
    return UpdateResult(
        new_count=len(new_papers),
        summary_written=True,
        summary_path=summary_path,
        with_abstract_before=with_abstract_before,
        with_abstract_after=with_abstract_after,
    )


def enrich_state_abstracts(
    state_path: Path,
    cache_path: Path | None = None,
    allow_title_search: bool = False,
) -> AbstractStateResult:
    papers = load_papers_json(state_path)
    with_abstract_before = sum(1 for paper in papers if paper.abstract)
    enriched = enrich_missing_abstracts(
        papers,
        cache_path=cache_path,
        allow_title_search=allow_title_search,
    )
    save_papers_json(state_path, enriched)
    with_abstract_after = sum(1 for paper in enriched if paper.abstract)
    return AbstractStateResult(
        total=len(enriched),
        with_abstract_before=with_abstract_before,
        with_abstract_after=with_abstract_after,
        state_path=state_path,
    )


def load_papers_json(path: Path) -> list[Paper]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return [_paper_from_core_row(row) for row in rows]


def save_papers_json(path: Path, papers: list[Paper]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([_core_row(paper) for paper in papers], handle, indent=2, ensure_ascii=False)


def generate_issue_summary_draft(papers: list[Paper], profile: str = "circuits") -> str:
    if profile == "nature_sensors":
        return _generate_nature_sensors_summary_draft(papers)
    if profile == "tbicas":
        return _generate_tbicas_summary_draft(papers)
    if profile != "circuits":
        raise ValueError(f"Unsupported summary profile: {profile}")
    circuit_buckets = {
        "Data converters": ["adc", "dac", "converter", "sar", "delta-sigma", "pipeline"],
        "AI / compute accelerators": ["accelerator", "compute", "memory", "cim", "imc", "ai", "llm", "processor"],
        "RF / wireless circuits": ["rf", "ghz", "transmitter", "receiver", "pll", "vco", "mixer", "phased-array"],
        "Power management": ["ldo", "regulator", "converter", "dc-dc", "ac-dc", "power"],
        "Sensors / biomedical": ["sensor", "biosignal", "biomedical", "neural", "implant"],
    }
    application_buckets = {
        "Implantable / neural / biomedical": ["implant", "neural", "biosignal", "biomedical", "bio", "in-vivo", "wearable"],
        "Precision analog / references / sensors": ["bandgap", "voltage reference", "reference", "temperature sensor", "sensor", "readout", "front-end", "afe"],
        "Ultra-low-power / always-on / IoT": ["ultra-low", "low-power", "nw", "nanowatt", "uw", "microwatt", "always-on", "wake-up", "iot", "energy-efficient"],
        "AI / edge compute": ["ai", "accelerator", "compute-in-memory", "cim", "imc", "llm", "transformer", "inference"],
        "Communication / RF / optical I/O": ["rf", "wireless", "transmitter", "receiver", "optical", "serdes", "beamformer", "phased-array"],
    }
    circuit_counts, _circuit_examples = _bucket_papers(papers, circuit_buckets)
    application_counts, _application_examples = _bucket_papers(papers, application_buckets)

    lines = [
        "# Issue Summary Draft",
        "",
        f"New articles: {len(papers)}",
        "",
        "Counts are title-keyword based and non-exclusive; abstracts are used only for focused summary drafting.",
        "",
    ]
    _append_distribution(lines, "Circuit Topic Distribution", circuit_counts)
    _append_distribution(lines, "Application Distribution", application_counts)
    _append_focused_summary_candidates(
        lines,
        papers,
        application_buckets,
        focused_bucket_names=[
            "Implantable / neural / biomedical",
            "Precision analog / references / sensors",
            "Ultra-low-power / always-on / IoT",
        ],
    )
    return "\n".join(lines).strip() + "\n"


def summarize_distribution(papers: list[Paper]) -> str:
    return generate_issue_summary_draft(papers)


def _generate_nature_sensors_summary_draft(papers: list[Paper]) -> str:
    focused_buckets = {
        "Implantable / bioelectronic / neural": [
            "implant",
            "implantable",
            "intracranial",
            "neural",
            "bioelectronic",
            "biodegradable",
            "microneedle",
            "organ",
            "piezo1",
            "ecog",
            "neurostimulation",
            "in vivo",
            "medical device",
        ],
        "Wearable / epidermal / sweat / skin": [
            "wearable",
            "skin",
            "epidermal",
            "sweat",
            "tattoo",
            "shoulder",
            "on-body",
            "clothing",
            "gesture",
            "haptic",
            "mask",
            "breath",
            "cortisol",
            "motion tracking",
            "biopotential",
            "biomechanical",
            "electrodermal",
        ],
        "Self-powered / wireless / battery-free": [
            "self-powered",
            "wireless",
            "battery-free",
            "chip-less",
            "passive",
            "remote sensing",
            "standoff",
            "triboelectric",
            "piezoelectric-powered",
        ],
        "AI / in-sensor / neuromorphic computing": [
            "ai",
            "deep learning",
            "machine learning",
            "agentic",
            "neuromorphic",
            "in-sensor",
            "sensing-as-computation",
            "computing",
            "memristor",
            "gan",
            "perception",
            "slam",
            "intelligent",
            "codesign",
            "analogue",
            "analog sensing-as-computation",
            "edge",
        ],
    }
    focused_counts, _focused_examples = _bucket_papers_by_title_and_abstract(papers, focused_buckets)
    lines = [
        "# Issue Summary Draft",
        "",
        f"New articles: {len(papers)}",
        "",
        "Counts are title/abstract-keyword based and non-exclusive; abstracts are used for focused summary drafting.",
        "",
    ]
    _append_distribution(lines, "Focused Topic Distribution", focused_counts)
    _append_focused_summary_candidates(
        lines,
        papers,
        focused_buckets,
        focused_bucket_names=list(focused_buckets),
        match_abstract=True,
    )
    return "\n".join(lines).strip() + "\n"


def _generate_tbicas_summary_draft(papers: list[Paper]) -> str:
    focused_buckets = {
        "Implantable / neural interface": [
            "implant",
            "implantable",
            "neural",
            "brain",
            "eeg",
            "ecog",
            "bci",
            "neuro",
            "stimulation",
            "prosthesis",
            "intracranial",
        ],
        "Wearable / biosignal acquisition": [
            "wearable",
            "biosignal",
            "ecg",
            "emg",
            "eeg",
            "ppg",
            "epilepsy",
            "seizure",
            "body",
            "motion",
            "health",
            "multimodal",
        ],
        "Biomedical AFE / sensor interface": [
            "afe",
            "front-end",
            "readout",
            "sensor interface",
            "acquisition",
            "bioimpedance",
            "impedance",
            "amplifier",
            "adc",
            "analog",
            "mixed-signal",
        ],
        "Edge AI / biomedical signal processing": [
            "edge-ai",
            "edge ai",
            "machine learning",
            "deep learning",
            "neural network",
            "spiking",
            "processor",
            "accelerator",
            "classification",
            "detection",
            "signal processing",
            "on-device",
        ],
        "Wireless / power / closed-loop systems": [
            "wireless",
            "power",
            "energy",
            "battery",
            "harvesting",
            "telemetry",
            "closed-loop",
            "closed loop",
            "stimulator",
            "stimulation",
        ],
    }
    focused_counts, _focused_examples = _bucket_papers_by_title_and_abstract(papers, focused_buckets)
    lines = [
        "# Issue Summary Draft",
        "",
        f"New articles: {len(papers)}",
        "",
        "Counts are title/abstract-keyword based and non-exclusive; abstracts are used for focused summary drafting.",
        "",
    ]
    _append_distribution(lines, "Focused Topic Distribution", focused_counts)
    _append_focused_summary_candidates(
        lines,
        papers,
        focused_buckets,
        focused_bucket_names=list(focused_buckets),
        match_abstract=True,
    )
    return "\n".join(lines).strip() + "\n"


def _bucket_papers(papers: list[Paper], buckets: dict[str, list[str]]) -> tuple[dict[str, int], dict[str, list[str]]]:
    counts = {name: 0 for name in buckets}
    examples = {name: [] for name in buckets}
    for paper in papers:
        text = paper.title.lower()
        matched = False
        for name, keywords in buckets.items():
            if any(keyword in text for keyword in keywords):
                counts[name] += 1
                if len(examples[name]) < 3:
                    examples[name].append(paper.title)
                matched = True
        if not matched:
            counts.setdefault("Other", 0)
            examples.setdefault("Other", [])
            counts["Other"] += 1
            if len(examples["Other"]) < 3:
                examples["Other"].append(paper.title)
    return counts, examples


def _bucket_papers_by_title_and_abstract(
    papers: list[Paper],
    buckets: dict[str, list[str]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    counts = {name: 0 for name in buckets}
    examples = {name: [] for name in buckets}
    for paper in papers:
        text = f"{paper.title} {paper.abstract or ''}".lower()
        matched = False
        for name, keywords in buckets.items():
            if any(keyword in text for keyword in keywords):
                counts[name] += 1
                if len(examples[name]) < 3:
                    examples[name].append(paper.title)
                matched = True
        if not matched:
            counts.setdefault("Other", 0)
            examples.setdefault("Other", [])
            counts["Other"] += 1
            if len(examples["Other"]) < 3:
                examples["Other"].append(paper.title)
    return counts, examples


def _append_focused_summary_candidates(
    lines: list[str],
    papers: list[Paper],
    application_buckets: dict[str, list[str]],
    focused_bucket_names: list[str],
    match_abstract: bool = False,
) -> None:
    focused_entries: list[tuple[str, Paper]] = []
    focused_ids: set[int] = set()
    for bucket_name in focused_bucket_names:
        keywords = application_buckets[bucket_name]
        bucket_papers = [paper for paper in papers if _matches_keywords(paper, keywords, include_abstract=match_abstract)]
        if bucket_papers:
            focused_entries.extend((bucket_name, paper) for paper in bucket_papers)
            focused_ids.update(id(paper) for paper in bucket_papers)

    random_pool = [paper for paper in papers if id(paper) not in focused_ids]
    if random_pool:
        focused_entries.append(("Additional sample", random.Random(23).choice(random_pool)))

    if not focused_entries:
        return

    lines.extend(["## Focused Summary Candidates", ""])
    current_bucket = None
    for bucket_name, paper in focused_entries:
        if bucket_name != current_bucket:
            lines.extend([f"### {bucket_name}", ""])
            current_bucket = bucket_name
        lines.append(f"#### {paper.title}")
        lines.append(f"- DOI: {paper.doi or ''}")
        lines.append(f"- URL: {paper.url or ''}")
        lines.append(f"- Abstract: {paper.abstract or ''}")
        lines.append("")


def _matches_title(paper: Paper, keywords: list[str]) -> bool:
    text = paper.title.lower()
    return any(keyword in text for keyword in keywords)


def _matches_keywords(paper: Paper, keywords: list[str], include_abstract: bool = False) -> bool:
    text = paper.title.lower()
    if include_abstract:
        text = f"{text} {(paper.abstract or '').lower()}"
    return any(keyword in text for keyword in keywords)


def _extract_problem_method_effect(abstract: str | None) -> tuple[str, str, str]:
    if not abstract:
        missing = "Abstract 未提供，暫時只能依 title 判斷。"
        return missing, missing, missing
    sentences = _split_sentences(abstract)
    problem = _first_matching_sentence(
        sentences,
        ["challenge", "require", "need", "limitation", "bottleneck", "difficult", "issue", "problem"],
        default_index=0,
    )
    method = _first_matching_sentence(
        sentences,
        ["present", "propose", "introduce", "using", "based", "employ", "utiliz", "designed", "implemented"],
        default_index=1,
    )
    effect = _first_matching_sentence(
        sentences,
        ["achiev", "measur", "demonstrat", "show", "result", "improv", "reduce", "efficien", "accuracy"],
        default_index=-1,
    )
    return problem, method, effect


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]


def _first_matching_sentence(sentences: list[str], needles: list[str], default_index: int) -> str:
    if not sentences:
        return "Abstract 未提供足夠資訊。"
    for sentence in sentences:
        lowered = sentence.lower()
        if any(needle in lowered for needle in needles):
            return sentence
    try:
        return sentences[default_index]
    except IndexError:
        return sentences[-1]


def _append_distribution(lines: list[str], heading: str, counts: dict[str, int]) -> None:
    lines.extend([f"## {heading}", ""])
    for name, count in counts.items():
        if count:
            lines.append(f"- {name}: {count}")
    lines.append("")


def _append_examples(lines: list[str], heading: str, examples: dict[str, list[str]]) -> None:
    lines.extend([f"## {heading}", ""])
    for name, titles in examples.items():
        if titles:
            lines.append(f"### {name}")
            for title in titles:
                lines.append(f"- {title}")
            lines.append("")


def _core_row(paper: Paper) -> dict[str, object]:
    return {field: ("; ".join(paper.authors) if field == "authors" else getattr(paper, field)) for field in CORE_EXPORT_FIELDS}


def _paper_from_core_row(row: dict[str, object]) -> Paper:
    authors = row.get("authors") or ""
    return Paper(
        title=str(row.get("title") or ""),
        authors=[author.strip() for author in str(authors).split(";") if author.strip()],
        venue=str(row.get("venue") or ""),
        venue_short=str(row.get("venue_short") or ""),
        year=row.get("year"),
        publication_date=row.get("publication_date"),
        doi=row.get("doi"),
        url=row.get("url"),
        abstract=row.get("abstract"),
    )
