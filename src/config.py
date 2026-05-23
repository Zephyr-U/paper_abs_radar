from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.models import Journal


@dataclass
class AppConfig:
    from_date: str
    to_date: str
    output_dir: str
    markdown_filename: str
    csv_filename: str
    json_filename: str
    journals: list[Journal]
    positive_keywords: list[str]
    negative_keywords: list[str]


def load_config(path: str, from_override: Optional[str] = None, to_override: Optional[str] = None) -> AppConfig:
    raw = _load_yaml_subset(Path(path))

    date_range = raw.get("date_range", {})
    output = raw.get("output", {})
    journals = []
    for family, entries in (raw.get("journals") or {}).items():
        for entry in entries or []:
            journals.append(
                Journal(
                    name=entry["name"],
                    short=entry["short"],
                    issn=entry["issn"],
                    family=family,
                )
            )

    keywords: dict[str, Any] = raw.get("keywords", {})
    return AppConfig(
        from_date=from_override or date_range["from"],
        to_date=to_override or date_range["to"],
        output_dir=output.get("dir", "output"),
        markdown_filename=output.get("markdown_filename", "paper_metadata.md"),
        csv_filename=output.get("csv_filename", "papers.csv"),
        json_filename=output.get("json_filename", "papers.json"),
        journals=journals,
        positive_keywords=list(keywords.get("positive", [])),
        negative_keywords=list(keywords.get("negative", [])),
    )


def _load_yaml_subset(path: Path) -> dict[str, Any]:
    try:
        import yaml

        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except ImportError:
        return _parse_known_config_shape(path)


def _parse_known_config_shape(path: Path) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "date_range": {},
        "output": {},
        "journals": {},
        "keywords": {"positive": [], "negative": []},
    }
    section: Optional[str] = None
    family: Optional[str] = None
    keyword_kind: Optional[str] = None
    current_journal: Optional[dict[str, str]] = None

    for original in path.read_text(encoding="utf-8").splitlines():
        if not original.strip() or original.lstrip().startswith("#"):
            continue
        indent = len(original) - len(original.lstrip(" "))
        line = original.strip()

        if indent == 0 and line.endswith(":"):
            section = line[:-1]
            family = None
            keyword_kind = None
            continue

        if section in {"date_range", "output"} and indent == 2 and ":" in line:
            key, value = _split_key_value(line)
            raw[section][key] = value
            continue

        if section == "journals":
            if indent == 2 and line.endswith(":"):
                family = line[:-1]
                raw["journals"][family] = []
                continue
            if indent == 4 and line.startswith("- "):
                key, value = _split_key_value(line[2:])
                current_journal = {key: value}
                raw["journals"][family].append(current_journal)
                continue
            if indent == 6 and current_journal is not None:
                key, value = _split_key_value(line)
                current_journal[key] = value
                continue

        if section == "keywords":
            if indent == 2 and line.endswith(":"):
                keyword_kind = line[:-1]
                raw["keywords"][keyword_kind] = []
                continue
            if indent == 4 and line.startswith("- ") and keyword_kind:
                raw["keywords"][keyword_kind].append(_unquote(line[2:]))

    return raw


def _split_key_value(line: str) -> tuple[str, str]:
    key, value = line.split(":", 1)
    return key.strip(), _unquote(value.strip())


def _unquote(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value
