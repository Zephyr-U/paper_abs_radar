from __future__ import annotations

import re
from html import unescape
from typing import Any, Optional

from src.errors import SourceFetchError
from src.models import Paper
from src.utils import clean_text, first, get_json

CROSSREF_WORKS_URL = "https://api.crossref.org/works"


def strip_jats(raw_abstract: Optional[str]) -> Optional[str]:
    if not raw_abstract:
        return None
    raw = unescape(raw_abstract)
    try:
        from bs4 import BeautifulSoup

        text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text)
    return text or None


def search_crossref_by_issn(
    issn: str,
    from_date: str,
    to_date: str,
    rows: int = 100,
    date_field: str = "published",
) -> list[Paper]:
    papers: list[Paper] = []
    offset = 0
    total_results = None
    from_filter, until_filter = _date_filter_names(date_field)
    while True:
        params = {
            "filter": f"issn:{issn},{from_filter}:{from_date},{until_filter}:{to_date},type:journal-article",
            "rows": rows,
            "offset": offset,
            "sort": date_field,
            "order": "desc",
        }
        payload = get_json(CROSSREF_WORKS_URL, params=params)
        if payload is None:
            raise SourceFetchError(f"Crossref fetch failed for ISSN {issn} ({from_date} to {to_date})")
        message = (payload or {}).get("message") or {}
        items = message.get("items") or []
        total_results = message.get("total-results") if total_results is None else total_results
        for item in items:
            paper = _paper_from_item(item)
            if not _is_non_article_notice(paper.title):
                papers.append(paper)
        if not items:
            break
        offset += len(items)
        if total_results is not None and offset >= total_results:
            break
    return papers


def _date_filter_names(date_field: str) -> tuple[str, str]:
    if date_field == "published":
        return "from-pub-date", "until-pub-date"
    if date_field == "created":
        return "from-created-date", "until-created-date"
    raise ValueError(f"Unsupported Crossref date field: {date_field}")


def get_by_doi(doi: str) -> Optional[Paper]:
    payload = get_json(f"{CROSSREF_WORKS_URL}/{doi}")
    item = ((payload or {}).get("message") or None)
    if not item:
        return None
    return _paper_from_item(item)


def _paper_from_item(item: dict[str, Any]) -> Paper:
    title = clean_text(first(item.get("title"))) or ""
    authors = []
    for author in item.get("author", []) or []:
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        if name:
            authors.append(name)
    date_parts = first((item.get("published-online") or item.get("published-print") or item.get("issued") or {}).get("date-parts"))
    publication_date = None
    year = None
    if date_parts:
        year = date_parts[0]
        publication_date = "-".join(f"{part:02d}" if index else str(part) for index, part in enumerate(date_parts))
    return Paper(
        title=title,
        authors=authors,
        venue=clean_text(first(item.get("container-title"))) or "",
        venue_short=clean_text(first(item.get("short-container-title"))) or clean_text(first(item.get("container-title"))) or "",
        year=year,
        publication_date=publication_date,
        doi=item.get("DOI"),
        url=item.get("URL"),
        abstract=strip_jats(item.get("abstract")),
        source_priority=["Crossref"],
        crossref_id=item.get("DOI"),
    )


def _is_non_article_notice(title: str) -> bool:
    normalized = title.lower()
    skip_phrases = (
        "table of contents",
        "publication information",
        "information for authors",
        "guest editorial",
        "editorial",
        "correction",
        "corrections to",
        "new associate editor",
        "front cover",
        "back cover",
        "masthead",
        "index",
    )
    return any(phrase in normalized for phrase in skip_phrases)
