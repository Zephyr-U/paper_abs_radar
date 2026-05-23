from __future__ import annotations

import logging
import os
from typing import Any, Optional

from src.models import Paper
from src.utils import clean_text, get_json

LOGGER = logging.getLogger(__name__)
SPRINGER_URL = "https://api.springernature.com/metadata/v1/articles"


def springer_enrich_by_doi(doi: str) -> Optional[Paper]:
    api_key = os.getenv("SPRINGER_API_KEY")
    if not api_key:
        LOGGER.warning("SPRINGER_API_KEY is not set; skipping Springer enrichment")
        return None
    payload = get_json(SPRINGER_URL, params={"api_key": api_key, "q": f"doi:{doi}"})
    records = (payload or {}).get("records") or []
    if not records:
        return None
    return _paper_from_record(records[0])


def _paper_from_record(record: dict[str, Any]) -> Paper:
    authors = []
    creators = record.get("creators") or []
    for creator in creators:
        name = creator.get("creator")
        if name:
            authors.append(name)
    return Paper(
        title=clean_text(record.get("title")) or "",
        authors=authors,
        venue=record.get("publicationName") or "",
        venue_short=record.get("publicationName") or "",
        year=_year_from_date(record.get("publicationDate")),
        publication_date=record.get("publicationDate"),
        doi=record.get("doi"),
        url=record.get("url") or record.get("webUrl"),
        abstract=clean_text(record.get("abstract")),
        source_priority=["Springer"],
    )


def _year_from_date(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
