"""Immutable pipeline records for Bengal SSG.

Frozen dataclasses representing the output of each pipeline stage.
These replace mutable Page field mutations with typed, immutable records
that flow through the pipeline.

Sprint 1: ParsedPage — captures all parse-phase output.
Sprint 2: RenderedPage — captures all render-phase output.

See Also:
    plan/epic-immutable-page-pipeline.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


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


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """Immutable record of render-phase output for a single page.

    Constructed after template rendering and HTML formatting.
    Consumed by the write phase and post-processing.

    All fields are immutable so the record is safe to share across
    threads without synchronization.
    """

    source_path: Path
    output_path: Path
    rendered_html: str
    render_time_ms: float
    dependencies: frozenset[str] = frozenset()
