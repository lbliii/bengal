"""Immutable pipeline records for Bengal SSG.

Frozen dataclasses representing the output of each pipeline stage.
These replace mutable Page field mutations with typed, immutable records
that flow through the pipeline.

Sprint 1: ParsedPage — captures all parse-phase output.
Sprint 2: RenderedPage — captures all render-phase output.
Sprint 4: SourcePage — captures all discovery-phase output.

See Also:
    plan/epic-immutable-page-pipeline.md
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page.page_core import PageCore


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

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to a cache-storable dict.

        The returned dict is JSON-serializable and compatible with
        ``ParsedContentCacheMixin.store_parsed_content()`` storage format.
        """
        return {
            "html": self.html_content,
            "toc": self.toc,
            "toc_items": list(self.toc_items),
            "excerpt": self.excerpt,
            "meta_description": self.meta_description,
            "plain_text": self.plain_text,
            "word_count": self.word_count,
            "reading_time": self.reading_time,
            "links": list(self.links),
            "ast": self.ast_cache,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> ParsedPage:
        """Reconstruct a ``ParsedPage`` from a cache dict.

        Accepts the dict format stored by ``ParsedContentCacheMixin``.
        Missing fields fall back to safe defaults.
        """
        toc_items = data.get("toc_items", [])
        links = data.get("links", [])
        return cls(
            html_content=data.get("html", ""),
            toc=data.get("toc", ""),
            toc_items=tuple(toc_items) if toc_items else (),
            excerpt=data.get("excerpt", "") or "",
            meta_description=data.get("meta_description", "") or "",
            plain_text=data.get("plain_text", ""),
            word_count=data.get("word_count", 0) or 0,
            reading_time=data.get("reading_time", 0) or 0,
            links=tuple(str(x) for x in links) if links else (),
            ast_cache=data.get("ast"),
        )


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


@dataclass(frozen=True, slots=True)
class SourcePage:
    """Immutable record of discovery-phase output for a single page.

    Constructed during content discovery after reading a source file and
    parsing its frontmatter.  Composes ``PageCore`` for cache-compatible
    metadata and adds discovery-specific fields (raw content, content
    hash, i18n).

    Consumed by the orchestration and rendering phases via the
    ``page._source_page`` dual-write bridge.  In the target architecture
    (Sprint 5+) content loading is deferred to the parse stage and
    ``raw_content`` becomes optional.

    The record itself is frozen (field reassignment raises).  Composed
    ``PageCore`` contains mutable containers (``tags``, ``props``,
    ``cascade``) and ``raw_metadata`` is a shallow read-only view —
    callers must not mutate nested values.  Full deep-freeze is deferred
    to Sprint 6 when ``PageCore`` is replaced.
    """

    # Composed cache-compatible metadata (same contract as Page.core)
    core: PageCore

    # Markdown body with frontmatter stripped
    raw_content: str

    # Read-only view of parsed frontmatter
    raw_metadata: MappingProxyType[str, Any]

    # SHA-256 hex digest of the markdown body (frontmatter stripped).
    # Distinct from ``PageCore.file_hash`` which covers the full source file.
    # None for virtual pages.
    content_hash: str | None = None

    # True for generated pages (taxonomy, autodoc, archive)
    is_virtual: bool = False

    # i18n enrichment
    lang: str | None = None
    translation_key: str | None = None

    # ------------------------------------------------------------------
    # Convenience delegates (avoid core.field in hot paths)
    # ------------------------------------------------------------------

    @property
    def source_path(self) -> str:
        """Source path (delegated to core for single source of truth)."""
        return self.core.source_path

    @property
    def title(self) -> str:
        """Title (delegated to core)."""
        return self.core.title

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def raw_metadata_dict(self) -> dict[str, Any]:
        """Return a shallow mutable copy of the frozen metadata.

        Only the top-level mapping is copied; nested mutable values remain
        shared with ``raw_metadata`` and must not be mutated in place.
        """
        return dict(self.raw_metadata)


def create_virtual_source_page(
    source_id: str,
    title: str,
    content: str = "",
    metadata: dict[str, Any] | None = None,
    *,
    section_path: str | None = None,
    lang: str | None = None,
) -> SourcePage:
    """Factory for virtual SourcePage records (taxonomy, autodoc, archive).

    Virtual pages have no disk file, no content_hash, and
    ``is_virtual=True``.
    """
    from bengal.core.page.page_core import PageCore
    from bengal.core.page.utils import normalize_tags, separate_standard_and_custom_fields
    from bengal.utils.primitives.dates import parse_date

    meta = dict(metadata) if metadata else {}
    meta.setdefault("title", title)

    standard_fields, custom_props = separate_standard_and_custom_fields(meta)

    core = PageCore(
        source_path=source_id,
        title=title,
        date=parse_date(standard_fields.get("date")),
        tags=normalize_tags(meta.get("tags")),
        slug=standard_fields.get("slug"),
        weight=standard_fields.get("weight"),
        lang=lang or standard_fields.get("lang"),
        nav_title=standard_fields.get("nav_title"),
        type=standard_fields.get("type"),
        variant=standard_fields.get("variant"),
        description=standard_fields.get("description"),
        props=custom_props,
        section=section_path,
        aliases=meta.get("aliases", []),
        version=meta.get("version"),
        cascade=meta.get("cascade", {}),
    )

    return SourcePage(
        core=core,
        raw_content=content,
        raw_metadata=MappingProxyType(meta),
        content_hash=None,
        is_virtual=True,
        lang=core.lang,
        translation_key=meta.get("translation_key"),
    )
