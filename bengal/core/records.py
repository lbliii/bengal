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

from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from bengal.core.page.page_core import PageCore


class FrozenList(list[Any]):
    """List-compatible immutable sequence for record boundary payloads."""

    def __init__(self, values: Iterable[Any] = ()) -> None:
        super().__init__(values)

    def _blocked(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("FrozenList is immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    append = _blocked
    clear = _blocked
    extend = _blocked
    insert = _blocked
    pop = _blocked
    remove = _blocked
    reverse = _blocked
    sort = _blocked
    __iadd__ = _blocked
    __imul__ = _blocked


def _deep_freeze(value: Any) -> Any:
    """Recursively freeze JSON-like containers at record boundaries."""
    if isinstance(value, MappingProxyType):
        return value
    if isinstance(value, dict):
        return MappingProxyType({str(k): _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, FrozenList):
        return value
    if isinstance(value, list | tuple):
        return FrozenList(_deep_freeze(v) for v in value)
    if isinstance(value, set | frozenset):
        return frozenset(_deep_freeze(v) for v in value)
    return value


def _deep_thaw(value: Any) -> Any:
    """Return mutable JSON-like containers from frozen record payloads."""
    if isinstance(value, MappingProxyType):
        return {k: _deep_thaw(v) for k, v in value.items()}
    if isinstance(value, FrozenList | tuple | list):
        return [_deep_thaw(v) for v in value]
    if isinstance(value, frozenset | set):
        return [_deep_thaw(v) for v in value]
    return value


def _freeze_page_core(core: PageCore) -> PageCore:
    """Return a PageCore copy whose nested containers are immutable."""
    frozen_core = replace(core)
    object.__setattr__(frozen_core, "tags", FrozenList(core.tags))
    object.__setattr__(frozen_core, "aliases", FrozenList(core.aliases))
    object.__setattr__(frozen_core, "props", _deep_freeze(core.props))
    object.__setattr__(frozen_core, "cascade", _deep_freeze(core.cascade))
    return frozen_core


PAGE_CORE_MIGRATION_MAP = MappingProxyType(
    {
        "source_path": "source_path",
        "title": "metadata.title",
        "date": "metadata.date",
        "tags": "metadata.tags",
        "slug": "metadata.slug or source_path.stem",
        "weight": "metadata.weight",
        "lang": "lang override or metadata.lang",
        "nav_title": "metadata.nav_title",
        "type": "metadata.type",
        "variant": "metadata.variant or metadata.layout or props.hero_style",
        "description": "metadata.description",
        "props": "metadata minus standard/internal fields",
        "section": "section path string",
        "file_hash": "full source hash when available",
        "aliases": "metadata.aliases",
        "version": "metadata.version or metadata._version",
        "cascade": "metadata.cascade",
    }
)
"""Canonical PageCore field migration map from mutable Page/frontmatter state."""

SOURCE_PAGE_MIGRATION_MAP = MappingProxyType(
    {
        "core": "PageCore built by build_page_core()",
        "raw_content": "frontmatter-stripped source body",
        "raw_metadata": "read-only parsed frontmatter mapping",
        "content_hash": "hash of raw_content",
        "is_virtual": "generated/non-file-backed source marker",
        "lang": "lang override or PageCore.lang",
        "translation_key": "metadata.translation_key",
    }
)
"""Canonical SourcePage migration map from discovery-time mutable inputs."""

PARSED_PAGE_MIGRATION_MAP = MappingProxyType(
    {
        "html_content": "page.html_content",
        "toc": "page.toc",
        "toc_items": "rendering-supplied TOC structure or page.toc_items",
        "excerpt": "page.excerpt",
        "meta_description": "page.meta_description or page.description",
        "plain_text": "page.plain_text",
        "word_count": "page.word_count",
        "reading_time": "page.reading_time",
        "links": "page.links",
        "ast_cache": "page._ast_cache",
    }
)
"""Canonical ParsedPage migration map from parse-phase PageLike state."""

RENDERED_PAGE_MIGRATION_MAP = MappingProxyType(
    {
        "source_path": "page.source_path",
        "output_path": "page.output_path",
        "rendered_html": "rendered HTML argument or page.rendered_html",
        "render_time_ms": "measured render time",
        "dependencies": "render-time tracked asset/template dependencies",
    }
)
"""Canonical RenderedPage migration map from render-phase PageLike state."""


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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "toc_items",
            tuple(_deep_freeze(dict(item)) for item in self.toc_items),
        )
        object.__setattr__(self, "links", tuple(str(link) for link in self.links))
        object.__setattr__(self, "ast_cache", _deep_freeze(self.ast_cache))

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to a cache-storable dict.

        The returned dict is JSON-serializable and compatible with
        ``ParsedContentCacheMixin.store_parsed_content()`` storage format.
        """
        return {
            "html": self.html_content,
            "toc": self.toc,
            "toc_items": [_deep_thaw(item) for item in self.toc_items],
            "excerpt": self.excerpt,
            "meta_description": self.meta_description,
            "plain_text": self.plain_text,
            "word_count": self.word_count,
            "reading_time": self.reading_time,
            "links": list(self.links),
            "ast": _deep_thaw(self.ast_cache),
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "dependencies", frozenset(str(dep) for dep in self.dependencies))


@dataclass(frozen=True, slots=True)
class SourcePage:
    """Immutable record of discovery-phase output for a single page.

    Constructed during content discovery after reading a source file and
    parsing its frontmatter.  Composes ``PageCore`` for cache-compatible
    metadata and adds discovery-specific fields (raw content, content
    hash, i18n).

    Consumed by discovery/orchestration handoffs before the remaining mutable
    ``Page`` compatibility object is populated.  In the target architecture,
    content loading is deferred to the parse stage and ``raw_content`` becomes
    optional.

    The record itself is frozen (field reassignment raises), and nested
    metadata containers are recursively frozen when the record is constructed.
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "core", _freeze_page_core(self.core))
        object.__setattr__(self, "raw_metadata", _deep_freeze(dict(self.raw_metadata)))

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
        """Return a deep mutable copy of the frozen metadata."""
        return _deep_thaw(self.raw_metadata)


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
    meta = dict(metadata) if metadata else {}
    meta.setdefault("title", title)

    return build_source_page(
        source_path=source_id,
        raw_content=content,
        metadata=meta,
        lang=lang,
        section_path=section_path,
        content_hash=None,
        file_hash=None,
        is_virtual=True,
    )


def build_page_core(
    source_path: str | Path,
    metadata: Mapping[str, Any] | None = None,
    *,
    tags: Sequence[Any] | None = None,
    slug: str | None = None,
    lang: str | None = None,
    section_path: str | Path | None = None,
    file_hash: str | None = None,
    aliases: Sequence[Any] | None = None,
) -> PageCore:
    """Build a ``PageCore`` from canonical discovery/frontmatter inputs.

    This is the migration substrate shared by mutable ``Page`` construction,
    immutable ``SourcePage`` construction, and tests.  It intentionally accepts
    plain mappings and path strings so callers do not need the concrete
    mutable ``Page`` class.
    """
    from bengal.core.page.page_core import PageCore
    from bengal.core.page.utils import normalize_tags, separate_standard_and_custom_fields
    from bengal.utils.primitives.dates import parse_date

    meta = dict(metadata or {})
    standard_fields, custom_props = separate_standard_and_custom_fields(meta)
    source = Path(source_path)

    resolved_slug = slug if slug is not None else standard_fields.get("slug")
    if resolved_slug is None:
        resolved_slug = source.parent.name if source.stem == "_index" else source.stem

    variant = standard_fields.get("variant")
    if not variant:
        variant = standard_fields.get("layout") or custom_props.get("hero_style")

    resolved_tags = normalize_tags(tags if tags is not None else meta.get("tags"))
    resolved_aliases = list(aliases if aliases is not None else standard_fields.get("aliases", []))
    resolved_lang = lang or standard_fields.get("lang")
    resolved_section = str(section_path) if section_path is not None else None

    return PageCore(
        source_path=str(source_path),
        title=standard_fields.get("title", ""),
        date=parse_date(standard_fields.get("date")),
        tags=resolved_tags,
        slug=resolved_slug,
        weight=standard_fields.get("weight"),
        lang=resolved_lang,
        nav_title=standard_fields.get("nav_title"),
        type=standard_fields.get("type"),
        variant=variant,
        description=standard_fields.get("description"),
        props=custom_props,
        section=resolved_section,
        file_hash=file_hash,
        aliases=resolved_aliases,
        version=meta.get("version") or meta.get("_version"),
        cascade=meta.get("cascade", {}),
    )


def build_source_page(
    source_path: str | Path,
    raw_content: str,
    metadata: Mapping[str, Any] | None = None,
    *,
    lang: str | None = None,
    section_path: str | Path | None = None,
    content_hash: str | None = None,
    file_hash: str | None = None,
    is_virtual: bool = False,
) -> SourcePage:
    """Build an immutable ``SourcePage`` without requiring a mutable ``Page``.

    ``content_hash`` is the hash of the frontmatter-stripped body. ``file_hash``
    is the full source file hash for real files. Both values are computed by
    discovery/orchestration boundaries and passed in so core remains passive.
    """
    meta = dict(metadata or {})

    core = build_page_core(
        source_path,
        meta,
        lang=lang,
        section_path=section_path,
        file_hash=file_hash,
    )

    return SourcePage(
        core=core,
        raw_content=raw_content,
        raw_metadata=MappingProxyType(meta),
        content_hash=content_hash,
        is_virtual=is_virtual,
        lang=lang or core.lang,
        translation_key=meta.get("translation_key"),
    )


def parsed_page_from_page_state(
    page: Any,
    *,
    toc_items: Sequence[Mapping[str, Any]] | None = None,
    links: Sequence[Any] | None = None,
    ast_cache: Any = None,
) -> ParsedPage:
    """Build ``ParsedPage`` from parse-phase state on a Page-like object.

    Rendering owns deriving TOC structures; pass ``toc_items`` when available
    so this adapter does not import rendering helpers from core.
    """
    raw_toc_items = toc_items
    if raw_toc_items is None:
        raw_toc_items = getattr(page, "toc_items", ()) or ()

    raw_links = links
    if raw_links is None:
        raw_links = getattr(page, "links", None) or ()

    resolved_ast_cache = ast_cache if ast_cache is not None else getattr(page, "_ast_cache", None)

    return ParsedPage(
        html_content=getattr(page, "html_content", None) or "",
        toc=getattr(page, "toc", None) or "",
        toc_items=tuple(dict(item) for item in raw_toc_items),
        excerpt=getattr(page, "excerpt", "") or "",
        meta_description=getattr(page, "meta_description", "")
        or getattr(page, "description", "")
        or "",
        plain_text=getattr(page, "plain_text", "") or "",
        word_count=getattr(page, "word_count", 0) or 0,
        reading_time=getattr(page, "reading_time", 0) or 0,
        links=tuple(str(link) for link in raw_links),
        ast_cache=resolved_ast_cache,
    )


def rendered_page_from_page_state(
    page: Any,
    *,
    rendered_html: str | None = None,
    render_time_ms: float | None = None,
    dependencies: Sequence[str] | frozenset[str] | None = None,
) -> RenderedPage:
    """Build ``RenderedPage`` from render-phase state on a Page-like object."""
    output_path = getattr(page, "output_path", None)
    if output_path is None:
        raise ValueError(
            "RenderedPage requires page.output_path; call determine_output_path() before rendering."
        )

    resolved_html = (
        rendered_html if rendered_html is not None else getattr(page, "rendered_html", "")
    )
    resolved_time = (
        render_time_ms if render_time_ms is not None else getattr(page, "render_time_ms", 0.0)
    )
    resolved_dependencies = (
        dependencies if isinstance(dependencies, frozenset) else frozenset(dependencies or ())
    )

    return RenderedPage(
        source_path=page.source_path,
        output_path=output_path,
        rendered_html=resolved_html,
        render_time_ms=resolved_time,
        dependencies=resolved_dependencies,
    )
