from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from src.models import Paper
from src.utils import clean_text, get_json

FIELDS = "title,abstract,year,venue,publicationVenue,authors,externalIds,url,citationCount,publicationDate"
BASE_URL = "https://api.semanticscholar.org/graph/v1"


def get_by_doi(doi: str) -> Optional[Paper]:
    payload = get_json(f"{BASE_URL}/paper/DOI:{quote(doi)}", params={"fields": FIELDS})
    if not payload:
        return None
    return _paper_from_payload(payload)


def search_by_title(title: str) -> Optional[Paper]:
    payload = get_json(
        f"{BASE_URL}/paper/search",
        params={"query": title, "limit": 1, "fields": FIELDS},
    )
    if not payload or not payload.get("data"):
        return None
    return _paper_from_payload(payload["data"][0])


def _paper_from_payload(payload: dict[str, Any]) -> Paper:
    external_ids = payload.get("externalIds") or {}
    venue = payload.get("venue") or ((payload.get("publicationVenue") or {}).get("name")) or ""
    authors = [author.get("name") for author in payload.get("authors", []) if author.get("name")]
    return Paper(
        title=clean_text(payload.get("title")) or "",
        authors=authors,
        venue=venue,
        venue_short=venue,
        year=payload.get("year"),
        publication_date=payload.get("publicationDate"),
        doi=external_ids.get("DOI"),
        url=payload.get("url"),
        abstract=clean_text(payload.get("abstract")),
        source_priority=["Semantic Scholar"],
        semantic_scholar_id=payload.get("paperId"),
    )
