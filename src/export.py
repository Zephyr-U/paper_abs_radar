from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from src.models import Paper

CORE_EXPORT_FIELDS = [
    "title",
    "authors",
    "venue",
    "venue_short",
    "year",
    "publication_date",
    "doi",
    "url",
    "abstract",
]


def export_outputs(
    papers: Iterable[Paper],
    output_dir: str,
    run_label: str,
    markdown_filename: str,
    csv_filename: str,
    json_filename: str,
) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sorted_papers = sort_papers(list(papers))

    paths = {
        "csv": out_dir / f"{run_label}_{csv_filename}",
        "json": out_dir / f"{run_label}_{json_filename}",
        "markdown": out_dir / f"{run_label}_{markdown_filename}",
    }
    _write_csv(paths["csv"], sorted_papers)
    _write_json(paths["json"], sorted_papers)
    _write_markdown(paths["markdown"], sorted_papers, run_label)
    return paths


def sort_papers(papers: list[Paper]) -> list[Paper]:
    return sorted(
        papers,
        key=lambda paper: (
            paper.relevance_score,
            paper.publication_date or "",
            paper.venue_short,
        ),
        reverse=True,
    )


def _write_csv(path: Path, papers: list[Paper]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EXPORT_FIELDS)
        writer.writeheader()
        for paper in papers:
            writer.writerow(_core_row(paper))


def _write_json(path: Path, papers: list[Paper]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump([_core_row(paper) for paper in papers], handle, indent=2, ensure_ascii=False)


def _write_markdown(path: Path, papers: list[Paper], run_label: str) -> None:
    lines = [f"# Paper Metadata Backfill - {run_label}", ""]
    if not papers:
        lines.extend(["_No papers._", ""])
    for paper in papers:
        lines.extend(
            [
                f"## {paper.title}",
                f"- Authors: {'; '.join(paper.authors)}",
                f"- Venue: {paper.venue}",
                f"- Venue short: {paper.venue_short}",
                f"- Year: {paper.year or ''}",
                f"- Publication date: {paper.publication_date or ''}",
                f"- DOI: {paper.doi or ''}",
                f"- URL: {paper.url or ''}",
                "- Abstract:",
                "",
                paper.abstract or "_No abstract available._",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _core_row(paper: Paper) -> dict[str, object]:
    return {
        "title": paper.title,
        "authors": "; ".join(paper.authors),
        "venue": paper.venue,
        "venue_short": paper.venue_short,
        "year": paper.year,
        "publication_date": paper.publication_date,
        "doi": paper.doi,
        "url": paper.url,
        "abstract": paper.abstract,
    }
