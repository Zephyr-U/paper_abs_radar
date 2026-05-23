from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from src.enrich import normalize_doi
from src.models import Paper
from src.sources import crossref, openalex, semantic_scholar

LOGGER = logging.getLogger(__name__)


def enrich_missing_abstracts(
    papers: Iterable[Paper],
    cache_path: Optional[Path] = None,
    allow_title_search: bool = False,
) -> list[Paper]:
    paper_list = list(papers)
    cache = _load_cache(cache_path)
    changed = False

    for index, paper in enumerate(paper_list, start=1):
        if paper.abstract:
            continue
        cache_key = _cache_key(paper)
        if cache_key and cache_key in cache:
            paper.abstract = cache[cache_key] or None
            continue

        abstract = _fetch_abstract(paper, allow_title_search=allow_title_search)
        if abstract:
            paper.abstract = abstract
            LOGGER.info("Filled abstract %s/%s: %s", index, len(paper_list), paper.title[:80])
        if cache_key:
            cache[cache_key] = abstract
            changed = True
            if cache_path:
                _save_cache(cache_path, cache)
    return paper_list


def _fetch_abstract(paper: Paper, allow_title_search: bool = False) -> Optional[str]:
    doi = normalize_doi(paper.doi)
    if doi:
        openalex_paper = openalex.get_by_doi(doi)
        if openalex_paper and openalex_paper.abstract:
            return openalex_paper.abstract
        crossref_paper = crossref.get_by_doi(doi)
        if crossref_paper and crossref_paper.abstract:
            return crossref_paper.abstract
        semantic_paper = semantic_scholar.get_by_doi(doi)
        if semantic_paper and semantic_paper.abstract:
            return semantic_paper.abstract

    if allow_title_search:
        semantic_paper = semantic_scholar.search_by_title(paper.title)
        if semantic_paper and semantic_paper.abstract:
            return semantic_paper.abstract
    return None


def _cache_key(paper: Paper) -> Optional[str]:
    doi = normalize_doi(paper.doi)
    if doi:
        return f"doi:{doi}"
    if paper.title:
        return f"title:{paper.title.strip().lower()}"
    return None


def _load_cache(cache_path: Optional[Path]) -> dict[str, Optional[str]]:
    if not cache_path or not cache_path.exists():
        return {}
    with cache_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _save_cache(cache_path: Path, cache: dict[str, Optional[str]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False, sort_keys=True)
