from __future__ import annotations

import re
import string
from typing import Iterable, Optional

from src.models import Paper
from src.sources import crossref, semantic_scholar, springer


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    cleaned = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://dx.doi.org/", "http://doi.org/", "doi:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned.replace(prefix, "", 1)
    return cleaned or None


def normalize_title(title: str) -> str:
    lower = title.lower().strip()
    translation = str.maketrans({char: " " for char in string.punctuation})
    return re.sub(r"\s+", " ", lower.translate(translation)).strip()


def deduplicate_and_merge(papers: Iterable[Paper]) -> list[Paper]:
    merged: list[Paper] = []
    by_doi: dict[str, Paper] = {}
    by_title: dict[str, Paper] = {}

    for paper in papers:
        doi_key = normalize_doi(paper.doi)
        title_key = normalize_title(paper.title) if paper.title else None
        target = by_doi.get(doi_key) if doi_key else None
        if target is None and title_key:
            target = by_title.get(title_key)
        if target is None:
            paper.doi = doi_key or paper.doi
            merged.append(paper)
            if doi_key:
                by_doi[doi_key] = paper
            if title_key:
                by_title[title_key] = paper
            continue
        merge_paper(target, paper)
        if doi_key:
            by_doi[doi_key] = target
        if title_key:
            by_title[title_key] = target

    return merged


def merge_paper(base: Paper, enrichment: Paper) -> Paper:
    for field_name in (
        "abstract",
        "doi",
        "publication_date",
        "year",
        "url",
        "venue",
        "venue_short",
        "openalex_id",
        "semantic_scholar_id",
        "crossref_id",
    ):
        if getattr(base, field_name) in (None, "", []):
            value = getattr(enrichment, field_name)
            if value not in (None, "", []):
                setattr(base, field_name, value)
    if not base.authors and enrichment.authors:
        base.authors = enrichment.authors
    for source in enrichment.source_priority:
        if source not in base.source_priority:
            base.source_priority.append(source)
    base.doi = normalize_doi(base.doi)
    return base


def enrich_papers(papers: Iterable[Paper], use_springer: bool = True) -> list[Paper]:
    enriched: list[Paper] = []
    for paper in papers:
        candidates = [paper]
        doi = normalize_doi(paper.doi)
        if doi:
            s2 = semantic_scholar.get_by_doi(doi)
            cr = crossref.get_by_doi(doi)
            if s2:
                candidates.append(s2)
            if cr:
                candidates.append(cr)
            if use_springer and _looks_springer_nature(paper, doi):
                sp = springer.springer_enrich_by_doi(doi)
                if sp:
                    candidates.append(sp)
        else:
            s2 = semantic_scholar.search_by_title(paper.title)
            if s2:
                candidates.append(s2)
        enriched.extend(candidates)
    return deduplicate_and_merge(enriched)


def _looks_springer_nature(paper: Paper, doi: str) -> bool:
    text = f"{paper.venue} {paper.venue_short}".lower()
    return doi.startswith("10.1038/") or "nature" in text or "springer" in text
