"""SourcePage-backed runtime page object for the discovery adapter boundary."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bengal.core.cascade import CascadeSnapshot, CascadeView
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.page.frontmatter import Frontmatter
from bengal.core.page.metadata_helpers import (
    coerce_weight,
    fallback_url,
    get_assigned_template,
    get_content_type_name,
    get_internal_metadata,
    get_user_metadata,
    infer_nav_title,
    infer_slug,
    infer_title,
    is_generated,
    is_in_variant,
    normalize_edition,
    normalize_keywords,
)
from bengal.core.page.utils import normalize_tags
from bengal.core.page_visibility import (
    get_content_signal_defaults,
    get_page_visibility,
    get_robots_meta,
    is_page_in_ai_input,
    is_page_in_ai_train,
    is_page_in_listings,
    is_page_in_rss,
    is_page_in_search,
    is_page_in_sitemap,
    should_render_page,
    should_render_page_in_environment,
)
from bengal.protocols import SiteLike

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from bengal.core.author import Author
    from bengal.core.page.bundle import BundleType, PageResources
    from bengal.core.page.page_core import PageCore
    from bengal.core.records import SourcePage
    from bengal.core.series import Series
    from bengal.parsing.ast.types import ASTNode
    from bengal.protocols.core import PageLike, SectionLike


@dataclass
class RuntimePage:
    """Runtime page state adapted from an immutable ``SourcePage`` record."""

    source_page: SourcePage
    source_path: Path
    _raw_content: str
    _raw_metadata: dict[str, Any]
    core: PageCore
    html_content: str | None = None
    rendered_html: str = ""
    render_time_ms: float = 0.0
    output_path: Path | None = None
    links: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str | None = None
    toc: str | None = None
    related_posts: list[PageLike] = field(default_factory=list)
    lang: str | None = None
    translation_key: str | None = None
    aliases: list[str] = field(default_factory=list)
    _site: Any | None = field(default=None, repr=False)
    _section_path: Path | None = field(default=None, repr=False)
    _section_url: str | None = field(default=None, repr=False)
    _section_obj_cache: SectionLike | object | None = field(default=None, repr=False, init=False)
    _section_obj_cache_key: tuple[int, int, Path | None, str | None] | None = field(
        default=None, repr=False, init=False
    )
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None, repr=False, init=False)
    _excerpt: str | None = field(default=None, repr=False, init=False)
    _meta_description: str | None = field(default=None, repr=False, init=False)
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)
    _init_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _metadata_view_cache: CascadeView | None = field(default=None, init=False, repr=False)
    _metadata_view_cache_key: tuple[int, str] | None = field(default=None, init=False, repr=False)
    _ast_cache: list[ASTNode] | dict[str, Any] | None = field(default=None, repr=False, init=False)
    _html_cache: str | None = field(default=None, repr=False, init=False)
    _plain_text_cache: str | None = field(default=None, repr=False, init=False)
    virtual: bool = False
    _posts: list[PageLike] | None = field(default=None, repr=False, init=False)
    _subsections: list[Any] | None = field(default=None, repr=False, init=False)
    _paginator: Any | None = field(default=None, repr=False, init=False)
    _page_num: int | None = field(default=None, repr=False, init=False)
    _autodoc_fallback_template: bool = field(default=False, repr=False, init=False)
    _autodoc_fallback_reason: str | None = field(default=None, repr=False, init=False)
    prerendered_html: str | None = field(default=None, repr=False)
    template_name: str | None = field(default=None, repr=False)
    _complexity_score: int | None = field(default=None, repr=False, init=False)
    _cascade_invalidated: bool = field(default=False, repr=False, init=False)
    _from_cache: bool = False

    _global_missing_section_warnings: ClassVar[dict[str, int]] = {}
    _warnings_lock: ClassVar[threading.Lock] = threading.Lock()
    _MAX_WARNING_KEYS: ClassVar[int] = 100
    _SECTION_NOT_FOUND: ClassVar[object] = object()

    def __post_init__(self) -> None:
        if self._raw_metadata:
            self.tags = normalize_tags(self._raw_metadata.get("tags"))
            self.version = self._raw_metadata.get("version") or self._raw_metadata.get("_version")
            self.aliases = self._raw_metadata.get("aliases", [])

    @classmethod
    def from_source_page(
        cls,
        source_page: SourcePage,
        *,
        output_path: Path | None = None,
        rendered_html: str | None = None,
        template_name: str | None = None,
        from_cache: bool = False,
    ) -> RuntimePage:
        """Create runtime page state from an immutable source record."""
        page = cls(
            source_page=source_page,
            source_path=Path(source_page.source_path),
            _raw_content=source_page.raw_content,
            _raw_metadata=source_page.raw_metadata_dict(),
            core=source_page.core,
            rendered_html=rendered_html or "",
            output_path=output_path,
            lang=source_page.lang,
            translation_key=source_page.translation_key,
            virtual=source_page.is_virtual,
            _from_cache=from_cache,
        )
        if rendered_html is not None:
            page.prerendered_html = rendered_html
        if template_name is not None:
            page.template_name = template_name
        if source_page.core.section:
            page._section_path = Path(source_page.core.section)
        return page

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Return effective page metadata, including cascade when available."""
        if self._site is None:
            return self._raw_metadata

        cascade = getattr(self._site, "cascade", None)
        if cascade is None or not isinstance(cascade, CascadeSnapshot):
            return self._raw_metadata

        section_path = ""
        if self._section_path:
            try:
                content_dir = self._site.root_path / "content"
                section_path = str(self._section_path.relative_to(content_dir))
            except ValueError, AttributeError:
                section_path = str(self._section_path)

        cache_key = (id(cascade), section_path)
        if self._metadata_view_cache is not None and self._metadata_view_cache_key == cache_key:
            return self._metadata_view_cache

        with self._init_lock:
            if self._metadata_view_cache is not None and self._metadata_view_cache_key == cache_key:
                return self._metadata_view_cache
            view = CascadeView.for_page(
                frontmatter=self._raw_metadata,
                section_path=section_path,
                snapshot=cascade,
            )
            self._metadata_view_cache = view
            self._metadata_view_cache_key = cache_key
        return view

    @property
    def title(self) -> str:
        return infer_title(self.metadata, self.source_path)

    @property
    def nav_title(self) -> str:
        return infer_nav_title(
            core_nav_title=self.core.nav_title,
            metadata=self.metadata,
            fallback_title=self.title,
        )

    @property
    def weight(self) -> float:
        return coerce_weight(self.core.weight, self.metadata)

    @property
    def date(self) -> datetime | None:
        from bengal.utils.primitives.dates import parse_date

        return parse_date(self.metadata.get("date"))

    @property
    def slug(self) -> str:
        return infer_slug(self.metadata, self.source_path)

    @property
    def name(self) -> str:
        return self.source_path.stem

    @property
    def href(self) -> str:
        from bengal.rendering.page_urls import get_href

        return get_href(self)

    @property
    def _path(self) -> str:
        from bengal.rendering.page_urls import get_path

        return get_path(self)

    @property
    def absolute_href(self) -> str:
        from bengal.rendering.page_urls import get_absolute_href

        return get_absolute_href(self)

    def _fallback_url(self) -> str:
        return fallback_url(self.slug)

    @property
    def toc_items(self) -> list[dict[str, Any]]:
        from bengal.rendering.page_content import get_toc_items

        return get_toc_items(self)

    @property
    def is_home(self) -> bool:
        return self._path == "/" or self.slug in ("index", "_index", "home")

    @property
    def is_section(self) -> bool:
        from bengal.core.section import Section

        return isinstance(self, Section)

    @property
    def is_page(self) -> bool:
        return not self.is_section

    @property
    def kind(self) -> str:
        if self.is_home:
            return "home"
        if self.is_section:
            return "section"
        return "page"

    @property
    def type(self) -> str | None:
        return self.metadata.get("type")

    @property
    def description(self) -> str:
        if self.core.description:
            return self.core.description
        return str(self.metadata.get("description", ""))

    @property
    def variant(self) -> str | None:
        return (
            self.metadata.get("variant")
            or self.metadata.get("layout")
            or self.metadata.get("hero_style")
        )

    @property
    def props(self) -> dict[str, Any]:
        return cast("dict[str, Any]", self.metadata)

    @property
    def params(self) -> dict[str, Any]:
        return cast("dict[str, Any]", self.metadata)

    @property
    def draft(self) -> bool:
        return bool(self.metadata.get("draft", False))

    @property
    def keywords(self) -> list[str]:
        return normalize_keywords(self.metadata.get("keywords", []))

    @property
    def hidden(self) -> bool:
        return bool(self.metadata.get("hidden", False))

    def _get_content_signal_defaults(self) -> dict[str, Any]:
        return get_content_signal_defaults(self)

    @property
    def visibility(self) -> dict[str, Any]:
        return get_page_visibility(self)

    @property
    def in_listings(self) -> bool:
        return is_page_in_listings(self)

    @property
    def in_sitemap(self) -> bool:
        return is_page_in_sitemap(self)

    @property
    def in_search(self) -> bool:
        return is_page_in_search(self)

    @property
    def in_rss(self) -> bool:
        return is_page_in_rss(self)

    @property
    def in_ai_train(self) -> bool:
        return is_page_in_ai_train(self)

    @property
    def in_ai_input(self) -> bool:
        return is_page_in_ai_input(self)

    @property
    def robots_meta(self) -> str:
        return get_robots_meta(self)

    @property
    def should_render(self) -> bool:
        return should_render_page(self)

    def should_render_in_environment(self, is_production: bool = False) -> bool:
        return should_render_page_in_environment(self, is_production)

    @property
    def edition(self) -> list[str]:
        return normalize_edition(self.metadata.get("edition"))

    def in_variant(self, variant: str | None) -> bool:
        return is_in_variant(self.metadata, variant)

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        return get_user_metadata(self.metadata, key, default)

    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        return get_internal_metadata(self.metadata, key, default)

    @property
    def is_generated(self) -> bool:
        return is_generated(self.metadata)

    @property
    def assigned_template(self) -> str | None:
        return get_assigned_template(self.metadata)

    @property
    def content_type_name(self) -> str | None:
        return get_content_type_name(self.metadata)

    def normalize_core_paths(self) -> None:
        """Normalize cached core paths relative to the current site root."""
        if not self._site or not self.core:
            return

        updates: dict[str, str] = {}
        source_path_str = self.core.source_path
        if Path(source_path_str).is_absolute():
            try:
                rel_path = Path(source_path_str).relative_to(self._site.root_path)
                updates["source_path"] = str(rel_path)
            except ValueError, AttributeError:
                pass

        if self._section_path is not None:
            try:
                content_dir = self._site.root_path / "content"
                updates["section"] = str(self._section_path.relative_to(content_dir))
            except ValueError, AttributeError:
                updates["section"] = str(self._section_path)

        if updates:
            self.core = replace(self.core, **updates)

    @property
    def frontmatter(self) -> Frontmatter:
        if self._frontmatter is None:
            with self._init_lock:
                if self._frontmatter is None:
                    self._frontmatter = Frontmatter.from_dict(dict(self.metadata))
        return self._frontmatter

    def __hash__(self) -> int:
        return hash(self.source_path)

    def __eq__(self, other: object) -> bool:
        if not hasattr(other, "source_path"):
            return NotImplemented
        return self.source_path == cast("Any", other).source_path

    def eq(self, other: object) -> bool:
        return bool(
            hasattr(other, "source_path") and self.source_path == cast("Any", other).source_path
        )

    def in_section(self, section: Any) -> bool:
        return bool(self._section == section)

    def is_ancestor(self, other: PageLike) -> bool:
        if not self.is_section:
            return False

        from bengal.protocols.capabilities import has_walk

        other_section = getattr(other, "_section", None)
        return other_section in self.walk() if has_walk(self) else False

    def is_descendant(self, other: object) -> bool:
        is_ancestor = getattr(other, "is_ancestor", None)
        return bool(callable(is_ancestor) and is_ancestor(self))

    def __repr__(self) -> str:
        return f"RuntimePage(title='{self.title}', source='{self.source_path}')"

    def _format_path_for_log(self, path: Path | str | None) -> str | None:
        from bengal.utils.primitives.text import format_path_for_display

        base_path = None
        if self._site is not None and isinstance(self._site, SiteLike):
            base_path = self._site.root_path

        return format_path_for_display(path, base_path)

    @property
    def _section(self) -> SectionLike | None:
        if self._section_path is None and self._section_url is None:
            return None

        if self._site is None:
            warn_key = "missing_site"
            with self._warnings_lock:
                if self._global_missing_section_warnings.get(warn_key, 0) < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_lookup_no_site",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = (
                        self._global_missing_section_warnings.get(warn_key, 0) + 1
                    )
            return None

        epoch = self._site.registry.epoch if hasattr(self._site, "registry") else 0
        cache_key = (id(self._site), epoch, self._section_path, self._section_url)
        if self._section_obj_cache_key == cache_key:
            cached = self._section_obj_cache
            return None if cached is self._SECTION_NOT_FOUND else cast("SectionLike | None", cached)

        with self._init_lock:
            if self._section_obj_cache_key == cache_key:
                cached = self._section_obj_cache
                return (
                    None
                    if cached is self._SECTION_NOT_FOUND
                    else cast("SectionLike | None", cached)
                )

            if self._section_path is not None:
                section = self._site.get_section_by_path(self._section_path)
            else:
                section = self._site.get_section_by_url(self._section_url or "")

        if section is None:
            warn_key = str(self._section_path or self._section_url)
            with self._warnings_lock:
                count = self._global_missing_section_warnings.get(warn_key, 0)
                if count < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        count=count + 1,
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1
                elif count == 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found_summary",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        total_warnings=count + 1,
                        note="Further warnings for this section will be suppressed",
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1

        with self._init_lock:
            self._section_obj_cache_key = cache_key
            self._section_obj_cache = section if section is not None else self._SECTION_NOT_FOUND
        return section

    @_section.setter
    def _section(self, value: SectionLike | None) -> None:
        if value is None:
            self._section_path = None
            self._section_url = None
        elif value.path is not None:
            self._section_path = value.path
            self._section_url = None
        else:
            self._section_path = None
            self._section_url = getattr(value, "_path", None) or f"/{value.name}/"

        self._section_obj_cache_key = None
        self._section_obj_cache = None

    @property
    def section_path(self) -> str | None:
        return str(self._section_path) if self._section_path else None

    @property
    def next(self) -> PageLike | None:
        from bengal.core.page.navigation import get_next_page

        return get_next_page(self, self._site)

    @property
    def prev(self) -> PageLike | None:
        from bengal.core.page.navigation import get_prev_page

        return get_prev_page(self, self._site)

    @property
    def next_in_section(self) -> PageLike | None:
        from bengal.core.page.navigation import get_next_in_section

        return get_next_in_section(self, self._section)

    @property
    def prev_in_section(self) -> PageLike | None:
        from bengal.core.page.navigation import get_prev_in_section

        return get_prev_in_section(self, self._section)

    @property
    def parent(self) -> SectionLike | None:
        return self._section

    @property
    def ancestors(self) -> list[SectionLike]:
        from bengal.core.page.navigation import get_ancestors

        return get_ancestors(self._section)

    @cached_property
    def bundle_type(self) -> BundleType:
        from bengal.core.page.bundle import get_bundle_type

        return get_bundle_type(self.source_path)

    @property
    def is_bundle(self) -> bool:
        from bengal.core.page.bundle import BundleType

        return self.bundle_type == BundleType.LEAF

    @property
    def is_branch_bundle(self) -> bool:
        from bengal.core.page.bundle import BundleType

        return self.bundle_type == BundleType.BRANCH

    @cached_property
    def resources(self) -> PageResources:
        from bengal.core.page.bundle import get_resources

        return get_resources(self.source_path, getattr(self, "url", "/"))

    @property
    def _source(self) -> str:
        return self._raw_content

    @property
    def content(self) -> str:
        from bengal.rendering.page_content import get_content

        return get_content(self)

    @property
    def ast(self) -> list[ASTNode] | dict[str, Any] | None:
        from bengal.rendering.page_content import get_ast

        return get_ast(self)

    @property
    def html(self) -> str:
        from bengal.rendering.page_content import get_html

        return get_html(self)

    @property
    def plain_text(self) -> str:
        from bengal.rendering.page_content import get_plain_text

        return get_plain_text(self)

    def _render_ast_to_html(self) -> str:
        from bengal.rendering.page_content import render_ast_to_html

        return render_ast_to_html(self)

    def _extract_text_from_ast(self) -> str:
        from bengal.rendering.page_content import extract_text_from_ast_cache

        return extract_text_from_ast_cache(self._ast_cache)

    def _extract_links_from_ast(self) -> list[str]:
        from bengal.rendering.page_content import extract_links_from_ast_cache

        return extract_links_from_ast_cache(self._ast_cache)

    def _strip_html_to_text(self, html: str) -> str:
        from bengal.rendering.page_content import strip_html_to_text

        return strip_html_to_text(html)

    def extract_links(self, plugin_links: list[str] | None = None) -> list[str]:
        from bengal.rendering.page_operations import extract_links

        return extract_links(self, plugin_links=plugin_links)

    def HasShortcode(self, name: str) -> bool:
        from bengal.rendering.page_operations import has_shortcode

        return has_shortcode(self, name)

    @cached_property
    def word_count(self) -> int:
        from bengal.core.page.computed import compute_word_count

        return compute_word_count(self._raw_content)

    @cached_property
    def meta_description(self) -> str:
        from bengal.rendering.page_content import get_meta_description

        return get_meta_description(self, self.metadata)

    @cached_property
    def reading_time(self) -> int:
        from bengal.core.page.computed import compute_reading_time

        return compute_reading_time(self.word_count)

    @cached_property
    def excerpt(self) -> str:
        from bengal.rendering.page_content import get_excerpt

        return get_excerpt(self)

    @cached_property
    def age_days(self) -> int:
        from bengal.core.page.computed import compute_age_days

        return compute_age_days(self.date)

    @cached_property
    def age_months(self) -> int:
        from bengal.core.page.computed import compute_age_months

        return compute_age_months(self.date)

    @cached_property
    def author(self) -> Author | None:
        from bengal.core.page.computed import get_primary_author

        return get_primary_author(self.metadata)

    @cached_property
    def authors(self) -> list[Author]:
        from bengal.core.page.computed import get_all_authors

        return get_all_authors(self.metadata)

    @cached_property
    def series(self) -> Series | None:
        from bengal.core.page.computed import get_series_info

        return get_series_info(self.metadata)

    @cached_property
    def prev_in_series(self) -> PageLike | None:
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, -1)

    @cached_property
    def next_in_series(self) -> PageLike | None:
        from bengal.core.page.computed import get_series_neighbor

        return get_series_neighbor(self.metadata, self._site, 1)
