"""Immutable pipeline records for Bengal SSG.

Frozen dataclasses representing the output of each pipeline stage.
These replace mutable Page field mutations with typed, immutable records
that flow through the pipeline.

Sprint 1: ParsedPage — captures all parse-phase output.

See Also:
    plan/epic-immutable-page-pipeline.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Immutable record of parsing-phase output for a single page.

    Constructed after markdown parsing, API-doc enhancement, and link
    extraction.  Consumed by the rendering phase and cache layer.

    All container fields use immutable types (tuple, not list) so the
    record is safe to share across threads without synchronization.
    """

    html_content: str
    toc: str
    toc_items: tuple[dict[str, Any], ...]
    excerpt: str
    meta_description: str
    plain_text: str
    word_count: int
    reading_time: int
    links: tuple[str, ...]
    ast_cache: dict[str, Any] | list[Any] | None = None
