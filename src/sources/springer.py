from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional
from urllib.parse import urljoin

from src.models import Paper
from src.utils import clean_text, get_json, get_text

LOGGER = logging.getLogger(__name__)
SPRINGER_URL = "https://api.springernature.com/meta/v2/json"
NATURE_RESEARCH_ARTICLES = {
    "NATURE BME": {
        "url": "https://www.nature.com/natbiomedeng/research-articles",
        "doi_prefix": "10.1038/s41551",
        "venue_short": "Nature BME",
    },
}


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


def search_nature_research_articles(
    journal_short: str,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 80,
) -> list[Paper]:
    source = NATURE_RESEARCH_ARTICLES.get(journal_short.upper())
    if not source:
        return []

    doi_prefix = source["doi_prefix"]
    venue_short = source["venue_short"]
    dois = _collect_nature_research_dois(source["url"], doi_prefix, limit)
    papers = []
    for doi in dois:
        paper = springer_enrich_by_doi(doi)
        if paper is None:
            paper = Paper(
                title="",
                authors=[],
                venue="Nature Biomedical Engineering",
                venue_short=venue_short,
                year=None,
                publication_date=None,
                doi=doi,
                url=f"https://www.nature.com/articles/{doi.split('/')[-1]}",
                abstract=None,
                source_priority=["Nature"],
            )
        paper.venue_short = venue_short
        if _date_in_window(paper.publication_date, from_date, to_date):
            papers.append(paper)
    return papers


def _collect_nature_research_dois(base_url: str, doi_prefix: str, limit: int) -> list[str]:
    dois: list[str] = []
    seen: set[str] = set()
    for page_number in range(1, 8):
        params = {"sort": "PubDate", "type": "article"}
        if page_number > 1:
            params["page"] = str(page_number)
        html = get_text(base_url, params=params)
        if not html:
            break
        page_dois = _extract_nature_dois(html, doi_prefix)
        if not page_dois:
            break
        for doi in page_dois:
            if doi not in seen:
                seen.add(doi)
                dois.append(doi)
                if len(dois) >= limit:
                    return dois
    return dois


def _extract_nature_dois(html: str, doi_prefix: str) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        LOGGER.warning("beautifulsoup4 is required to parse Nature research-article pages")
        return []

    soup = BeautifulSoup(html, "html.parser")
    dois: list[str] = []
    for link in soup.find_all("a", href=True):
        url = urljoin("https://www.nature.com", link["href"])
        match = re.search(r"/articles/([^/?#]+)", url)
        if not match:
            continue
        article_id = match.group(1)
        doi = f"10.1038/{article_id}"
        if doi.startswith(doi_prefix):
            dois.append(doi)
    return dois


def _date_in_window(value: str | None, from_date: str | None, to_date: str | None) -> bool:
    if not value:
        return True
    if from_date and value < from_date:
        return False
    if to_date and value > to_date:
        return False
    return True


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
        venue=record.get("journalTitle") or record.get("publicationName") or "",
        venue_short=record.get("journalTitle") or record.get("publicationName") or "",
        year=_year_from_date(record.get("publicationDate")),
        publication_date=record.get("publicationDate"),
        doi=record.get("doi"),
        url=_url_from_record(record),
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


def _url_from_record(record: dict[str, Any]) -> Optional[str]:
    url = record.get("url")
    if isinstance(url, str):
        return url
    if isinstance(url, list) and url:
        first_url = url[0]
        if isinstance(first_url, dict):
            return first_url.get("value")
        if isinstance(first_url, str):
            return first_url
    return record.get("webUrl")
