"""
Renderer for converting pages to final HTML output.

Handles individual page rendering using templates, markdown processing, and
content transformation. Integrates with template engine for template rendering (Kida default)
and provides error handling with graceful degradation.

Key Concepts:
- Template rendering: Template rendering with page context (Kida default)
- Markdown processing: Markdown to HTML conversion
- Content transformation: Link rewriting, image processing, etc.
- Error handling: Graceful error handling with error pages

Related Modules:
- bengal.rendering.template_engine: Template engine for rendering (Kida default)
- bengal.parsing: Markdown parser implementations (Patitas default)
- bengal.rendering.link_transformer: Link transformation logic

See Also:
- bengal/rendering/renderer.py:Renderer class for rendering logic
- plan/active/rfc-template-performance-optimization.md: Performance RFC

"""

from __future__ import annotations

import re
from typing import Any

from bengal.core.page import Page
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


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
        self, template_engine: Any, build_stats: Any = None, block_cache: Any = None
    ) -> None:
        """
        Initialize the renderer.

        Args:
            template_engine: Template engine instance
            build_stats: Optional BuildStats object for error collection
            block_cache: Optional BlockCache for KIDA template block caching
        """
        self.template_engine = template_engine
        self.site = template_engine.site  # Access to site config for strict mode
        self.build_stats = build_stats  # For collecting template errors
        self.block_cache = block_cache  # Block cache for KIDA introspection optimization
        # PERF: Cache for top-level content (computed once per build)
        self._top_level_cache: tuple[list[Page], list[Any]] | None = None
        # PERF: Cache for resolved tag pages (computed once per build)
        # Maps tag_slug -> list of filtered, resolved Page objects
        self._tag_pages_cache: dict[str, list[Page]] | None = None

    def _get_top_level_content(self) -> tuple[list[Page], list[Any]]:
        """
        Get top-level pages and sections (not nested in any section).

        PERF: Uses O(n) algorithm with set-based filtering instead of O(n²).
        Result is cached for the lifetime of the Renderer instance.

        Returns:
            Tuple of (top_level_pages, top_level_subsections)
        """
        if self._top_level_cache is not None:
            return self._top_level_cache

        # Build set of all pages that are in any section (O(sections × pages_per_section))
        pages_in_sections: set[int] = set()
        for section in self.site.sections:
            for p in section.pages:
                pages_in_sections.add(id(p))

        # Build set of all sections that are subsections of another (O(sections × subsections))
        nested_sections: set[int] = set()
        for parent in self.site.sections:
            for s in parent.subsections:
                nested_sections.add(id(s))

        # Filter using O(1) set membership
        top_level_pages = [p for p in self.site.regular_pages if id(p) not in pages_in_sections]
        top_level_subsections = [s for s in self.site.sections if id(s) not in nested_sections]

        self._top_level_cache = (top_level_pages, top_level_subsections)
        return self._top_level_cache

    def _get_resolved_tag_pages(self, tag_slug: str) -> list[Page]:
        """
        Get resolved and filtered pages for a tag (cached).

        Cache is built once per Renderer instance (per build). This eliminates
        repeated O(P) filtering per tag page render.

        PERF: O(T × P) total once, then O(1) lookups per tag page render.
        Previously: O(P) per render × R pagination pages per tag.

        Args:
            tag_slug: The tag slug to get pages for

        Returns:
            List of filtered, resolved Page objects for the tag
        """
        if self._tag_pages_cache is None:
            self._tag_pages_cache = self._build_all_tag_pages_cache()

        return self._tag_pages_cache.get(tag_slug, [])

    def _build_all_tag_pages_cache(self) -> dict[str, list[Page]]:
        """
        Build complete cache of resolved tag pages.

        Filters and resolves all tag pages once per build:
        - Excludes generated pages
        - Excludes API/CLI documentation pages
        - Resolves stale Page references via site's page path map

        Returns:
            Dict mapping tag_slug -> list of resolved Page objects
        """
        cache: dict[str, list[Page]] = {}
        str_page_map = self.site.get_page_path_map()
        tags_data = self.site.taxonomies.get("tags", {})

        for tag_slug, tag_info in tags_data.items():
            resolved_pages: list[Page] = []

            for tax_page in tag_info.get("pages", []):
                resolved_page = None
                if hasattr(tax_page, "source_path"):
                    # Use cached string-keyed map for O(1) lookup
                    resolved_page = str_page_map.get(str(tax_page.source_path))

                page_to_check = resolved_page if resolved_page else tax_page

                if page_to_check and hasattr(page_to_check, "source_path"):
                    source_str = str(page_to_check.source_path)
                    # Apply filtering rules: exclude generated, API, and CLI pages
                    if (
                        not page_to_check.metadata.get("_generated")
                        and "content/api" not in source_str
                        and "content/cli" not in source_str
                    ):
                        resolved_pages.append(page_to_check)

            cache[tag_slug] = resolved_pages

        logger.debug(
            "tag_pages_cache_built",
            total_tags=len(cache),
            total_pages=sum(len(pages) for pages in cache.values()),
        )

        return cache

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

        Args:
            content: HTML content

        Returns:
            Content with first H1 tag removed
        """
        # Pattern matches: <h1>...</h1> or <h1 id="...">...</h1>
        # Uses non-greedy matching to get just the first H1
        pattern = r"<h1[^>]*>.*?</h1>"

        # Remove only the first occurrence
        result = re.sub(pattern, "", content, count=1, flags=re.DOTALL | re.IGNORECASE)

        return result

    def render_page(self, page: Page, content: str | None = None) -> str:
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
            content: Optional pre-rendered content (uses page.parsed_ast if not provided)

        Returns:
            Fully rendered HTML page
        """
        from bengal.rendering.context import build_page_context

        if content is None:
            content = page.parsed_ast or ""
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

        # Mark active menu items for this page
        if hasattr(self.site, "mark_active_menu_items"):
            self.site.mark_active_menu_items(page)

        # Determine which template to use
        template_name = self._get_template_name(page)

        # Build base context using unified context builder
        # This handles: site/config/theme wrappers, params cascade, section context,
        # versioning, content, toc, meta_desc, reading_time, excerpt
        context = build_page_context(
            page=page,
            site=self.site,
            content=content,
        )

        # Inject cached blocks for KIDA templates (RFC: kida-template-introspection)
        # This enables site-wide block caching for nav, footer, etc.
        # The block cache was pre-warmed with site-scoped blocks from base.html
        if self.block_cache and self.block_cache._site_blocks:
            # Get all cached blocks from base.html (the primary parent template)
            # We use the cache directly - no introspection needed during rendering
            cached_blocks = {}
            for key, html in self.block_cache._site_blocks.items():
                # Keys are formatted as "template:block", e.g., "base.html:site_footer"
                if ":" in key:
                    cached_template, block_name = key.split(":", 1)
                    # Only inject blocks from parent templates (base.html)
                    # Skip empty cached blocks (they'd just add overhead)
                    if cached_template == "base.html" and html:
                        cached_blocks[block_name] = html

            # Inject cached blocks into context for template to use
            if cached_blocks:
                context["_cached_blocks"] = cached_blocks
                # Inject stats object so CachedBlocksDict can record hits
                if hasattr(self.block_cache, "_stats"):
                    context["_cached_stats"] = self.block_cache._stats

                logger.debug(
                    "renderer_using_cached_blocks",
                    template=template_name,
                    cached_blocks=list(cached_blocks.keys()),
                )

        # Add special context for generated pages (tags, archives, etc.)
        # These need additional pagination and tag-specific data
        if page.metadata.get("_generated"):
            self._add_generated_page_context(page, context)

        # Handle root index pages (top-level _index.md without enclosing section)
        # Provide context for ALL root index pages, regardless of type
        # EXCLUDE generated pages (tags, archives) which have their own context logic
        page_type = page.metadata.get("type")
        is_index_page = page.source_path.stem in ("_index", "index")

        if (
            is_index_page
            and page._section is None
            and not page.metadata.get("_generated")
            and page_type not in ("tag", "tag-index")
        ):
            # For root home page, provide site-level context as fallback
            # Filter to top-level items only (exclude nested sections/pages)
            # PERF: Use cached sets for O(n) instead of O(n²) filtering
            top_level_pages, top_level_subsections = self._get_top_level_content()

            # Wrap subsections in SectionContext so subsection.params works correctly
            # This prevents 'str' object has no attribute 'get' errors when accessing
            # subsection?.params?.type in templates
            from bengal.rendering.context import SectionContext

            context.update(
                {
                    "posts": top_level_pages,
                    "pages": top_level_pages,  # Alias
                    "subsections": [
                        SectionContext(sub) for sub in top_level_subsections if sub is not None
                    ],
                }
            )

        # Render with template
        try:
            result = self.template_engine.render(template_name, context)
            return str(result) if result else ""
        except Exception as e:
            from bengal.rendering.errors import TemplateRenderError, display_template_error

            # Create rich error object
            rich_error = TemplateRenderError.from_jinja2_error(
                e, template_name, page.source_path, self.template_engine
            )

            # In strict mode, display and fail immediately
            # Access from build section (supports both Config and dict)
            config = self.site.config
            if hasattr(config, "build"):
                strict_mode = config.build.strict_mode
                debug_mode = config.build.debug
            else:
                build_section = config.get("build", {})
                strict_mode = (
                    build_section.get("strict_mode", False)
                    if isinstance(build_section, dict)
                    else config.get("strict_mode", False)
                )
                debug_mode = (
                    build_section.get("debug", False)
                    if isinstance(build_section, dict)
                    else config.get("debug", False)
                )

            if strict_mode:
                display_template_error(rich_error)
                if debug_mode:
                    # Use configured traceback renderer for consistency
                    try:
                        from bengal.errors.traceback import TracebackConfig

                        TracebackConfig.from_environment().get_renderer().display_exception(e)
                    except Exception as traceback_error:
                        logger.debug(
                            "traceback_renderer_failed",
                            error=str(traceback_error),
                            error_type=type(traceback_error).__name__,
                        )
                        pass
                # Raise TemplateRenderError directly (now extends Exception)
                raise rich_error from e

            # In production mode, collect error and continue
            if self.build_stats:
                self.build_stats.add_template_error(rich_error)
            else:
                # No build stats available, display immediately
                display_template_error(rich_error)

            if debug_mode:
                # Show exception using the configured renderer
                try:
                    from bengal.errors.traceback import TracebackConfig

                    TracebackConfig.from_environment().get_renderer().display_exception(e)
                except Exception as traceback_error:
                    logger.debug(
                        "traceback_renderer_failed",
                        error=str(traceback_error),
                        error_type=type(traceback_error).__name__,
                    )
                    pass

            # Fallback to simple HTML
            return self._render_fallback(page, content)

    def _add_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
        """
        Add special context variables for generated pages (archives, tags, etc.).

        Args:
            page: Page being rendered
            context: Template context to update
        """
        page_type = page.metadata.get("type")

        archive_like_types = {
            "archive",
            "blog",
            "autodoc/python",
            "autodoc-cli",
            "tutorial",
            "changelog",
        }

        if page_type in archive_like_types:
            self._add_archive_like_generated_page_context(page, context)
            return

        if page_type == "tag":
            self._add_tag_generated_page_context(page, context)
            return

        if page_type == "tag-index":
            self._add_tag_index_generated_page_context(page, context)
            return

    def _add_archive_like_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
        """
        Add context for archive/reference/blog-like generated pages.

        Note: Posts are already filtered and sorted by the content type strategy
        in the SectionOrchestrator, so we do not re-sort here.
        """
        from bengal.rendering.context import SectionContext

        section = page.metadata.get("_section") if page.metadata is not None else None
        all_posts = (
            page.metadata.get("_posts", []) if page.metadata is not None else []
        )  # Already filtered & sorted!
        page_metadata = page.metadata if page.metadata is not None else {}
        subsections = page_metadata.get("_subsections", [])
        paginator = page_metadata.get("_paginator")
        page_num = page_metadata.get("_page_num", 1)

        if paginator:
            posts = paginator.page(page_num)
            section_name = section.name if section is not None else ""
            pagination = paginator.page_context(page_num, f"/{section_name}/")
        else:
            posts = all_posts
            pagination = {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
                "base_url": f"/{section.name}/" if section else "/",
            }

        context.update(
            {
                "section": SectionContext(section),
                "posts": posts,
                "pages": posts,  # Alias
                "subsections": subsections,
                "total_posts": len(all_posts),
                **pagination,
            }
        )

    def _add_tag_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
        """Add context for an individual tag page."""
        tag_name = page.metadata.get("_tag")
        tag_slug = page.metadata.get("_tag_slug")
        page_num = page.metadata.get("_page_num", 1)

        # PERF: Use cached resolved tag pages instead of filtering on each render.
        # Cache is built once per Renderer instance and reused across all tag page renders.
        # Complexity: O(T × P) once at cache build, then O(1) lookup per render.
        all_posts = self._get_resolved_tag_pages(tag_slug) if tag_slug else []

        # Fallback: Try to resolve from stored metadata if cache yielded nothing
        if not all_posts and page.metadata is not None:
            stored_posts = page.metadata.get("_posts", [])
            if stored_posts:
                str_page_map = self.site.get_page_path_map()
                for stored_item in stored_posts:
                    resolved_page = None
                    if hasattr(stored_item, "source_path"):
                        resolved_page = str_page_map.get(str(stored_item.source_path))
                        if resolved_page:
                            all_posts.append(resolved_page)
                        else:
                            all_posts.append(stored_item)
                    elif isinstance(stored_item, str):
                        resolved_page = str_page_map.get(stored_item)
                        if resolved_page:
                            all_posts.append(resolved_page)

        page_metadata = page.metadata if page.metadata is not None else {}
        paginator = page_metadata.get("_paginator")

        if all_posts:
            total_posts_count = len(all_posts)

            if paginator and hasattr(paginator, "per_page"):
                from bengal.utils.pagination import Paginator

                per_page = paginator.per_page
                fresh_paginator = Paginator(all_posts, per_page=per_page)
                try:
                    posts = fresh_paginator.page(page_num)
                    pagination = fresh_paginator.page_context(page_num, f"/tags/{tag_slug}/")
                except ValueError:
                    posts = all_posts
                    pagination = {
                        "current_page": 1,
                        "total_pages": 1,
                        "has_next": False,
                        "has_prev": False,
                        "base_url": f"/tags/{tag_slug}/",
                    }
            else:
                posts = all_posts
                pagination = {
                    "current_page": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False,
                    "base_url": f"/tags/{tag_slug}/",
                }
        elif paginator and hasattr(paginator, "items") and paginator.items:
            resolved_items = []
            str_page_map = self.site.get_page_path_map()
            for item in paginator.items:
                if hasattr(item, "source_path"):
                    resolved = str_page_map.get(str(item.source_path))
                    if resolved:
                        resolved_items.append(resolved)
                    elif item and hasattr(item, "title"):
                        resolved_items.append(item)

            if resolved_items:
                all_posts = resolved_items
                from bengal.utils.pagination import Paginator

                fresh_paginator = Paginator(all_posts, per_page=paginator.per_page)
                posts = fresh_paginator.page(page_num)
                total_posts_count = len(all_posts)
                pagination = fresh_paginator.page_context(page_num, f"/tags/{tag_slug}/")
            else:
                posts = []
                total_posts_count = 0
                pagination = {
                    "current_page": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False,
                    "base_url": f"/tags/{tag_slug}/",
                }
        else:
            posts = []
            total_posts_count = 0
            pagination = {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
                "base_url": f"/tags/{tag_slug}/",
            }

        logger.debug(
            "tag_page_context",
            tag_slug=tag_slug,
            posts_count=len(posts) if posts else 0,
            total_posts=total_posts_count,
            all_posts_count=len(all_posts) if all_posts else 0,
            page_num=page_num,
        )

        context.update(
            {
                "tag": tag_name,
                "tag_slug": tag_slug,
                "posts": posts,
                "total_posts": total_posts_count,
                **pagination,
            }
        )

    def _add_tag_index_generated_page_context(self, page: Page, context: dict[str, Any]) -> None:
        """Add context for the tag index page."""
        tags = page.metadata.get("_tags", {})

        tags_list = [
            {
                "name": data["name"],
                "slug": data["slug"],
                "count": len(data["pages"]),
                "pages": data["pages"],
            }
            for data in tags.values()
        ]
        tags_list.sort(key=lambda t: (-t["count"], t["name"].lower()))

        context.update(
            {
                "tags": tags_list,
                "total_tags": len(tags_list),
            }
        )

    def _get_template_name(self, page: Page) -> str:
        """
        Determine which template to use for a page.

        Priority order:
        1. Explicit template in frontmatter (`template: doc.html`)
        2. Content type strategy (delegates to strategy.get_template())
        3. Section-based auto-detection (e.g., `docs.html`, `docs/single.html`)
        4. Default fallback (`page.html` or `index.html`)

        Note: We use a simple, explicit template selection strategy without
        complex type/kind/layout hierarchies.

        Args:
            page: Page to get template for

        Returns:
            Template name
        """
        # 1. Explicit template (highest priority)
        if "template" in page.metadata:
            return str(page.metadata["template"])

        # 2. Get content type strategy and delegate
        page_type = page.metadata.get("type")
        content_type = None

        if hasattr(page, "_section") and page._section and hasattr(page._section, "metadata"):
            content_type = page._section.metadata.get("content_type")

        # Determine which strategy to use
        from bengal.content_types.registry import (
            CONTENT_TYPE_REGISTRY,
            get_strategy,
            normalize_page_type_to_content_type,
        )

        # Normalize page type to content type (handles special cases like python-module)
        strategy_type = None
        if page_type:
            strategy_type = normalize_page_type_to_content_type(page_type)
        elif content_type and content_type in CONTENT_TYPE_REGISTRY:
            strategy_type = content_type

        if strategy_type:
            strategy = get_strategy(strategy_type)
            # Delegate to strategy
            template_name = strategy.get_template(page, self.template_engine)
            if template_name:
                return template_name

        # 3. Section-based auto-detection (fallback)
        is_section_index = page.source_path.stem == "_index"
        if hasattr(page, "_section") and page._section:
            section_name = page._section.name

            if is_section_index:
                # Try section index templates in order of specificity
                templates_to_try = [
                    f"{section_name}/list.html",  # Section directory structure
                    f"{section_name}/index.html",  # Alternative directory
                    f"{section_name}-list.html",  # Flat with suffix
                    f"{section_name}.html",  # Flat simple
                ]
            else:
                # Try section page templates in order of specificity
                templates_to_try = [
                    f"{section_name}/single.html",  # Section directory structure
                    f"{section_name}/page.html",  # Alternative directory
                    f"{section_name}.html",  # Flat
                ]

            # Check if any template exists
            for template_name in templates_to_try:
                if self._template_exists(template_name):
                    return template_name

        # 4. Simple default fallback (no type/kind complexity)
        if is_section_index:
            # Section index without custom template
            return "index.html"

        # Regular page - just use page.html
        return "page.html"

    def _template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists in any template directory.

        Args:
            template_name: Template filename or path

        Returns:
            True if template exists, False otherwise
        """
        try:
            self.template_engine.env.get_template(template_name)
            return True
        except Exception as e:
            logger.debug(
                "template_check_failed",
                template=template_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def _get_site_title(self) -> str:
        """Get site title from config, supporting both Config and dict."""
        config = self.site.config
        if hasattr(config, "site"):
            return config.site.title or "Site"
        site_section = config.get("site", {})
        if isinstance(site_section, dict):
            return site_section.get("title", "Site")
        return config.get("title", "Site")

    def _render_fallback(self, page: Page, content: str) -> str:
        """
        Render a fallback HTML page with basic styling.

        When the main template fails, we still try to produce a usable page
        with basic CSS and structure (though without partials/navigation).

        Args:
            page: Page to render
            content: Page content

        Returns:
            Fallback HTML page with minimal styling
        """
        # Try to include CSS if available
        css_link = ""
        if hasattr(self.site, "output_dir"):
            css_file = self.site.output_dir / "assets" / "css" / "style.css"
            if css_file.exists():
                css_link = '<link rel="stylesheet" href="/assets/css/style.css">'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title} - {self._get_site_title()}</title>
    {css_link}
    <style>
        /* Emergency fallback styling */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        .fallback-notice {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 2rem;
        }}
        article {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
        }}
        h1 {{ color: #2c3e50; }}
        code {{ background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="fallback-notice">
        <strong>⚠️ Notice:</strong> This page is displayed in fallback mode due to a template error.
        Some features (navigation, sidebars, etc.) may be missing.
    </div>
    <article>
        <h1>{page.title}</h1>
        {content}
    </article>
</body>
</html>
"""
