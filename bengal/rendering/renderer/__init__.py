"""
Renderer for converting pages to final HTML output.

Handles individual page rendering using templates, markdown processing, and
content transformation. Integrates with template engine for template rendering (Kida default)
and provides error handling with graceful degradation.

Context assembly, template selection, tag-page membership, and fallback HTML
live in sibling modules. Renderer remains the public facade so
``from bengal.rendering.renderer import Renderer`` is unchanged.

There is no menu-state or batch helper in this magnet: render must not mutate
shared menu active state (see tests/unit/rendering/test_renderer_menu_state.py).

Related Modules:
- bengal.rendering.template_engine: Template engine for rendering (Kida default)
- bengal.parsing: Markdown parser implementations (Patitas default)
- bengal.rendering.link_transformer: Link transformation logic

See Also:
- bengal/rendering/renderer/context.py: Renderer-owned context helpers
- bengal/rendering/renderer/template_select.py: Template selection
- bengal/rendering/renderer/tag_pages.py: Tag membership and tag context
- bengal/rendering/renderer/fallback.py: Strict-mode / overlay / fallback HTML
"""

from __future__ import annotations

import re
import threading
from typing import TYPE_CHECKING, Any

from bengal.rendering.context import build_page_context
from bengal.rendering.renderer.context import (
    add_archive_like_generated_page_context,
    add_generated_page_context,
    add_root_index_context,
    coerce_pagination_ints,
    default_pagination,
    get_top_level_content,
    inject_cached_blocks,
    to_section_snapshot,
    to_section_snapshots,
)
from bengal.rendering.renderer.fallback import (
    get_site_title,
    handle_render_error,
    render_fallback,
)
from bengal.rendering.renderer.tag_pages import (
    add_tag_generated_page_context,
    add_tag_index_generated_page_context,
    build_all_tag_pages_cache,
    compute_per_language_taxonomies,
    get_resolved_tag_pages,
)
from bengal.rendering.renderer.template_select import get_template_name, template_exists
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.orchestration.build_context import BuildContext
    from bengal.orchestration.stats.models import BuildStats
    from bengal.protocols import PageLike, SectionLike, TemplateEngine
    from bengal.rendering.block_cache import BlockCache
    from bengal.snapshots.types import SectionSnapshot, SiteSnapshot

logger = get_logger(__name__)

__all__ = ["Renderer"]


class Renderer:
    """
    Renders individual pages using templates and content processing.

    Handles template rendering, content processing (H1 stripping), and error
    collection. Integrates with template engine for rendering (Kida default) and
    provides graceful error handling.

    Creation:
        Direct instantiation: Renderer(template_engine, build_stats=None)
            - Created by RenderingPipeline for page rendering
            - Requires TemplateEngine instance

    Attributes:
        template_engine: TemplateEngine instance for rendering (Kida default)
        site: Site instance (accessed via template_engine.site)
        build_stats: Optional BuildStats for error collection

    Relationships:
        - Uses: TemplateEngine for template rendering
        - Uses: BuildStats for error collection
        - Used by: RenderingPipeline for page rendering

    Thread Safety:
        Thread-safe. Each thread should have its own Renderer instance.

    Examples:
        renderer = Renderer(template_engine, build_stats=stats)
        html = renderer.render_page(page)

    """

    def __init__(
        self,
        template_engine: TemplateEngine,
        build_stats: BuildStats | None = None,
        block_cache: BlockCache | None = None,
        build_context: BuildContext | None = None,
    ) -> None:
        """
        Initialize the renderer.

        Args:
            template_engine: Template engine instance
            build_stats: Optional BuildStats object for error collection
            block_cache: Optional BlockCache for KIDA template block caching
            build_context: Optional BuildContext for accessing snapshot (RFC: rfc-bengal-snapshot-engine)
        """
        self.template_engine = template_engine
        self.site = template_engine.site  # Access to site config for strict mode
        self.build_stats = build_stats  # For collecting template errors
        self.block_cache = block_cache  # Block cache for KIDA introspection optimization
        self.build_context = build_context  # For accessing snapshot
        # PERF: Cache for top-level content (computed once per build)
        self._top_level_cache: tuple[list[PageLike], list[SectionLike]] | None = None
        # PERF: Cache for resolved tag pages (computed once per build)
        # Maps tag_slug -> list of filtered, resolved PageLike objects
        self._tag_pages_cache: dict[str, list[PageLike]] | None = None
        # Thread-safety: Lock for initializing caches under free-threading (PEP 703)
        self._cache_lock = threading.Lock()
        # i18n: when taxonomies are per-language (i18n enabled + share_taxonomies=False),
        # each generated tag page carries its own language-narrowed membership in its
        # _posts metadata. The snapshot/instance tag-page cache is language-blind, so the
        # tag-page renderer must defer to that per-page path (#354). Computed lazily on the
        # first tag-page render (None = not yet computed); the value is a deterministic
        # bool, so a concurrent recompute under free-threading is benign.
        self._per_language_taxonomies: bool | None = None

    @staticmethod
    def _default_pagination(base_url: str) -> dict[str, Any]:
        """Return default single-page pagination dict."""
        return default_pagination(base_url)

    @staticmethod
    def _coerce_pagination_ints(pagination: dict[str, Any]) -> dict[str, Any]:
        """Coerce YAML string pagination values to int."""
        return coerce_pagination_ints(pagination)

    def _get_top_level_content(self) -> tuple[list[PageLike], list[SectionLike]]:
        """Get top-level pages and sections (not nested in any section)."""
        return get_top_level_content(self)

    def _to_section_snapshot(
        self, section: SectionLike | SectionSnapshot | None, snapshot: SiteSnapshot | None
    ) -> SectionSnapshot | None:
        """Convert a mutable Section to its SectionSnapshot equivalent."""
        return to_section_snapshot(self, section, snapshot)

    def _to_section_snapshots(
        self, sections: Sequence[SectionLike | SectionSnapshot], snapshot: SiteSnapshot | None
    ) -> list[SectionSnapshot]:
        """Convert a list of mutable Sections to SectionSnapshots."""
        return to_section_snapshots(self, sections, snapshot)

    def _compute_per_language_taxonomies(self) -> bool:
        """Whether taxonomies are per-language (i18n enabled, taxonomies not shared)."""
        return compute_per_language_taxonomies(self)

    def _get_resolved_tag_pages(self, tag_slug: str) -> list[PageLike]:
        """Get resolved and filtered pages for a tag (cached)."""
        return get_resolved_tag_pages(self, tag_slug)

    def _build_all_tag_pages_cache(self) -> dict[str, list[PageLike]]:
        """Build complete cache of resolved tag pages."""
        return build_all_tag_pages_cache(self)

    def render_content(self, content: str) -> str:
        """
        Render raw content (already parsed HTML).

        Automatically strips the first H1 tag to avoid duplication with
        the template-rendered title.

        Args:
            content: Parsed HTML content

        Returns:
            Content with first H1 removed
        """
        return self._strip_first_h1(content)

    def _strip_first_h1(self, content: str) -> str:
        """
        Remove the first H1 tag from HTML content.

        This prevents duplication when templates render {{ page.title }} as H1
        and the markdown also contains an H1 heading.
        """
        # Pattern matches: <h1>...</h1> or <h1 id="...">...</h1>
        # Uses non-greedy matching to get just the first H1
        pattern = r"<h1[^>]*>.*?</h1>"

        # Remove only the first occurrence
        result = re.sub(pattern, "", content, count=1, flags=re.DOTALL | re.IGNORECASE)

        return result

    def render_page(
        self,
        page: PageLike,
        content: str | None = None,
        parsed_page: Any = None,
    ) -> str:
        """
        Render a complete page with template.

        Architecture:
        1. Uses build_page_context() for unified context building
        2. Adds specialized context based on page type:
           - Generated pages (tags/archives): Adds filtered `posts` list
           - Root index: Adds top-level pages
        3. Renders using Jinja2 template

        Conflict Prevention:
        Logic strictly separates "Root Index" (home page) from "Generated Index" (tag pages).
        Tag pages often have source paths like `tags/foo/index.md` (is_index_page=True)
        but must NOT use the root home page logic which overwrites their `posts` list.

        Args:
            page: Page to render
            content: Optional pre-rendered content (uses page.html_content if not provided)

        Returns:
            Fully rendered HTML page
        """
        if content is None:
            content = page.html_content or ""
            # Debug: Check core/page specifically
            if hasattr(page, "source_path") and "core/page.md" in str(page.source_path):
                has_badges = "api-badge" in content
                has_markers = "@property" in content
                logger.debug(
                    "renderer_content_check",
                    source_path=str(page.source_path),
                    content_length=len(content),
                    has_badges=has_badges,
                    has_markers=has_markers,
                )

        # Determine which template to use
        template_name = self._get_template_name(page)

        # Build base context using unified context builder
        # This handles: site/config/theme wrappers, params cascade, section context,
        # versioning, content, toc, meta_desc, reading_time, excerpt
        # Get snapshot from build_context if available (RFC: rfc-bengal-snapshot-engine)
        snapshot = None
        if hasattr(self, "build_context") and self.build_context:
            snapshot = getattr(self.build_context, "snapshot", None)

        # Build context using unified context builder
        context = build_page_context(
            page=page,
            site=self.site,
            content=content,
            snapshot=snapshot,
            build_context=self.build_context,  # PERF: O(1) section lookup
            parsed_page=parsed_page,
        )

        # Inject cached blocks for KIDA templates (RFC: kida-template-introspection)
        inject_cached_blocks(self, context, template_name)

        # Add special context for generated pages (tags, archives, etc.)
        # These need additional pagination and tag-specific data
        if page.metadata.get("_generated"):
            self._add_generated_page_context(page, context)

        # Handle root index pages (top-level _index.md without enclosing section)
        add_root_index_context(self, page, context, snapshot)

        # Render with template
        try:
            result = self.template_engine.render(template_name, context)
            return str(result) if result else ""
        except Exception as e:
            return handle_render_error(self, page, content, template_name, e)

    def _add_generated_page_context(self, page: PageLike, context: dict[str, Any]) -> None:
        """Add special context variables for generated pages (archives, tags, etc.)."""
        add_generated_page_context(self, page, context)

    def _add_archive_like_generated_page_context(
        self, page: PageLike, context: dict[str, Any]
    ) -> None:
        """Add context for archive/reference/blog-like generated pages."""
        add_archive_like_generated_page_context(self, page, context)

    def _add_tag_generated_page_context(self, page: PageLike, context: dict[str, Any]) -> None:
        """Add context for an individual tag page."""
        add_tag_generated_page_context(self, page, context)

    def _add_tag_index_generated_page_context(
        self, page: PageLike, context: dict[str, Any]
    ) -> None:
        """Add context for the tag index page."""
        add_tag_index_generated_page_context(self, page, context)

    def _get_template_name(self, page: PageLike) -> str:
        """Determine which template to use for a page."""
        return get_template_name(self, page)

    def _template_exists(self, template_name: str) -> bool:
        """Check if a template exists in any template directory."""
        return template_exists(self, template_name)

    def _get_site_title(self) -> str:
        """Get site title from config, supporting both Config and dict."""
        return get_site_title(self)

    def _render_fallback(self, page: PageLike, content: str) -> str:
        """Render a fallback HTML page with basic styling."""
        return render_fallback(self, page, content)
