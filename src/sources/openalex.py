from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from src.models import Paper
from src.utils import clean_text, get_json

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def restore_openalex_abstract(inv: Optional[dict[str, list[int]]]) -> Optional[str]:
    if not inv:
        return None
    pos_to_word = {}
    for word, positions in inv.items():
        for pos in positions:
            pos_to_word[pos] = word
    return " ".join(pos_to_word[i] for i in sorted(pos_to_word))


def search_openalex_by_issn(
    issn: str,
    from_date: str,
    to_date: str,
    per_page: int = 200,
    venue_short: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> list[Paper]:
    filters = ",".join(
        [
            f"primary_location.source.issn:{issn}",
            f"from_publication_date:{from_date}",
            f"to_publication_date:{to_date}",
        ]
    )
    all_papers: list[Paper] = []
    page = 1
    total_count: Optional[int] = None
    while True:
        params = {
            "filter": filters,
            "per-page": per_page,
            "page": page,
            "sort": "publication_date:desc",
        }
        payload = get_json(OPENALEX_WORKS_URL, params=params)
        if not payload:
            break

        results = payload.get("results", [])
        total_count = ((payload.get("meta") or {}).get("count")) if total_count is None else total_count
        papers = [paper_from_openalex_work(work, venue_short=venue_short) for work in results]
        all_papers.extend(paper for paper in papers if paper is not None)

        if not results:
            break
        if total_count is not None and page * per_page >= total_count:
            break
        if max_pages is not None and page >= max_pages:
            break
        page += 1

    return all_papers


def get_by_doi(doi: str) -> Optional[Paper]:
    payload = get_json(f"{OPENALEX_WORKS_URL}/{quote('doi:' + doi, safe=':')}")
    if not payload:
        return None
    return paper_from_openalex_work(payload, venue_short=None)


def paper_from_openalex_work(work: dict[str, Any], venue_short: Optional[str]) -> Optional[Paper]:
    title = clean_text(work.get("title")) or ""
    if work.get("is_paratext") or _is_non_article_notice(title):
        return None
    source = (((work.get("primary_location") or {}).get("source")) or {})
    authorships = work.get("authorships") or []
    authors = [
        author.get("display_name")
        for author in ((item.get("author") or {}) for item in authorships)
        if author.get("display_name")
    ]
    doi = work.get("doi")
    if doi and doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "", 1)

    return Paper(
        title=title,
        authors=authors,
        venue=source.get("display_name") or "",
        venue_short=venue_short or source.get("display_name") or "",
        year=work.get("publication_year"),
        publication_date=work.get("publication_date"),
        doi=doi,
        url=(work.get("primary_location") or {}).get("landing_page_url") or work.get("id"),
        abstract=restore_openalex_abstract(work.get("abstract_inverted_index")),
        source_priority=["OpenAlex"],
        openalex_id=work.get("id"),
    )


def _is_non_article_notice(title: str) -> bool:
    normalized = title.lower()
    skip_phrases = (
        "table of contents",
        "publication information",
        "information for authors",
        "front cover",
        "back cover",
        "masthead",
        "index",
    )
    return any(phrase in normalized for phrase in skip_phrases)
