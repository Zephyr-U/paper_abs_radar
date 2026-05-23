from __future__ import annotations

import re
from dataclasses import replace
from typing import Optional

from src.models import Paper

DEFAULT_RULES = [
    (3, "implantable", [r"\bimplantable\b", r"\bimplant\b", r"\bin-body\b"]),
    (3, "wireless power", [r"wireless power", r"\bwpt\b", r"\brectifier\b", r"energy harvesting"]),
    (3, "rf", [r"\brf\b", r"\btelemetry\b", r"\bbackscatter\b", r"\bantenna\b"]),
    (2, "soc", [r"\bsoc\b", r"\basic\b", r"\bcmos\b", r"integrated circuit"]),
    (2, "analog front-end", [r"analog front[- ]end", r"\bafe\b", r"sensor interface"]),
    (2, "biomedical", [r"\bbiomedical\b", r"\bbioelectronics\b", r"\bneural\b"]),
    (2, "ultrasound", [r"\bultrasound\b", r"\bcmut\b", r"\bpzt\b"]),
    (2, "voltage reference", [r"voltage reference", r"\bbandgap\b", r"temperature sensor"]),
]

NEGATIVE_RULES = [
    (-3, "review", [r"\breview\b"]),
    (-3, "editorial", [r"\beditorial\b"]),
    (-3, "correction", [r"\bcorrection\b", r"\berratum\b"]),
]

SECTION_RULES = [
    ("IV-A(i) TX architectures", [r"\btx\b", r"\btransmitter\b", r"power amplifier", r"\boscillator\b", r"\book\b", r"\bfsk\b", r"\bpsk\b"]),
    ("IV-A(ii) RX architectures", [r"\brx\b", r"\breceiver\b", r"\bdemodulator\b", r"wake-up receiver", r"\bsensitivity\b"]),
    ("IV-A(iii) Passive and hybrid telemetry", [r"\bbackscatter\b", r"load modulation", r"\bpassive\b", r"semi-passive"]),
    ("IV-B External RF interfaces", [r"\bantenna\b", r"\bmatching\b", r"\bpackaging\b", r"\btissue\b", r"\bdetuning\b", r"\binterface\b"]),
    ("IV-C Mixed-signal integration and process technology", [r"\bsoc\b", r"\bprocessor\b", r"\bafe\b", r"digital control", r"mixed-signal", r"\bintegration\b"]),
    ("Precision analog / sensor circuits", [r"\bbandgap\b", r"voltage reference", r"temperature sensor"]),
    ("Ultrasound biomedical interface", [r"\bultrasound\b", r"\bpzt\b", r"\bcmut\b", r"acoustic link"]),
]


def score_paper(paper: Paper, positive_keywords: list[str], negative_keywords: list[str]) -> Paper:
    text = _paper_text(paper)
    score = 0
    tags: list[str] = []

    for points, tag, patterns in DEFAULT_RULES:
        if _matches_any(text, patterns):
            score += points
            tags.append(tag)
    for keyword in positive_keywords:
        if keyword and re.search(re.escape(keyword.lower()), text):
            score += 1
            if keyword.lower() not in tags:
                tags.append(keyword.lower())
    for points, tag, patterns in NEGATIVE_RULES:
        if _matches_any(text, patterns):
            score += points
            tags.append(tag)
    for keyword in negative_keywords:
        if keyword and re.search(re.escape(keyword.lower()), text):
            score -= 3
            if keyword.lower() not in tags:
                tags.append(keyword.lower())

    return replace(
        paper,
        relevance_score=float(score),
        relevance_tags=tags,
        suggested_section=suggest_section(paper.title, paper.abstract),
    )


def suggest_section(title: str, abstract: Optional[str]) -> Optional[str]:
    text = f"{title} {abstract or ''}".lower()
    for section, patterns in SECTION_RULES:
        if _matches_any(text, patterns):
            return section
    return None


def _paper_text(paper: Paper) -> str:
    return f"{paper.title} {paper.abstract or ''} {paper.venue} {paper.venue_short}".lower()


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)
