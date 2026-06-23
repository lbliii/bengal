"""Per-page discovery facts used by warm-build cache and orchestration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from bengal.content.page_source import get_raw_source

if TYPE_CHECKING:
    from bengal.protocols import PageLike


class DiscoveryFactsExtractor:
    """Extract CSS features and target anchors from page source."""

    PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "mermaid": re.compile(r"```mermaid", re.IGNORECASE),
        "data_tables": re.compile(
            r"(tabulator|DataTable|data-table|\.datatable)",
            re.IGNORECASE,
        ),
        "graph": re.compile(
            r"(graph[-_]?vis|d3[-.]|force[-_]?graph|network[-_]?graph)", re.IGNORECASE
        ),
        "interactive": re.compile(r"(interactive|widget|marimo)", re.IGNORECASE),
        "holo_cards": re.compile(r"(holo[-_]?card|holographic)", re.IGNORECASE),
    }

    DIRECTIVE_PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "mermaid": re.compile(r":::\{mermaid\}", re.IGNORECASE),
        "data_tables": re.compile(r":::\{(datatable|tabulator)\}", re.IGNORECASE),
    }

    @classmethod
    def detect_features_in_content(cls, content: str) -> set[str]:
        features: set[str] = set()
        if not content:
            return features
        for feature, pattern in cls.PATTERNS.items():
            if pattern.search(content):
                features.add(feature)
        for feature, pattern in cls.DIRECTIVE_PATTERNS.items():
            if pattern.search(content):
                features.add(feature)
        return features

    @classmethod
    def detect_features_in_page(cls, page: PageLike) -> set[str]:
        features: set[str] = set()
        source = get_raw_source(page)
        if source:
            features.update(cls.detect_features_in_content(source))
        else:
            plain_text = getattr(page, "_plain_text_cache", None)
            if isinstance(plain_text, str) and plain_text:
                features.update(cls.detect_features_in_content(plain_text))

        metadata = page.metadata or {}
        if metadata.get("mermaid"):
            features.add("mermaid")
        if metadata.get("interactive"):
            features.add("interactive")
        if metadata.get("graph"):
            features.add("graph")
        return features


def extract_target_directives_from_content(content: str) -> list[str]:
    """Extract target directive anchor IDs from markdown content."""
    anchor_ids: list[str] = []
    pattern = r"^(\s*):{3,}\{(?:target|anchor)\}([^\n]*)$"
    for line in content.split("\n"):
        match = re.match(pattern, line)
        if not match:
            continue
        indent = len(match.group(1))
        if indent >= 4:
            continue
        title = match.group(2).strip()
        if title and re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", title):
            anchor_ids.append(title)
    return anchor_ids


def collect_parsed_discovery_facts(page: PageLike) -> dict[str, list[str]]:
    """Collect per-page facts to persist alongside parsed content cache."""
    raw_source = get_raw_source(page)
    return {
        "detected_features": sorted(DiscoveryFactsExtractor.detect_features_in_page(page)),
        "target_anchors": extract_target_directives_from_content(raw_source) if raw_source else [],
    }
