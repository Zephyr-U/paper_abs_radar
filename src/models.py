from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Paper:
    title: str
    authors: list[str]
    venue: str
    venue_short: str
    year: Optional[int]
    publication_date: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    abstract: Optional[str]
    source_priority: list[str] = field(default_factory=list)
    openalex_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    crossref_id: Optional[str] = None
    relevance_score: float = 0.0
    relevance_tags: list[str] = field(default_factory=list)
    suggested_section: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Journal:
    name: str
    short: str
    issn: str
    family: str
