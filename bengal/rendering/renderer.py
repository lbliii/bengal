"""
Renderer for converting pages to final HTML output.
"""

from __future__ import annotations

import re
from typing import Any

from markupsafe import Markup

from bengal.core.page import Page
from bengal.utils.logger import get_logger, truncate_error

logger = get_logger(__name__)


class Renderer:
    """
    Renders pages using templates.
    """

    def __init__(self, template_engine: Any, build_stats: Any = None) -> None:
        """
        Initialize the renderer.

        Args:
            template_engine: Template engine instance
            build_stats: Optional BuildStats object for error collection
        """
        self.template_engine = template_engine
        self.site = template_engine.site  # Access to site config for strict mode
        self.build_stats = build_stats  # For collecting template errors

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

        Args:
            page: Page to render
            content: Optional pre-rendered content (uses page.parsed_ast if not provided)

        Returns:
            Fully rendered HTML page
        """
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

        # Build base context
        # Note: Content and TOC are marked as safe HTML to prevent auto-escaping
        # (they're already sanitized during markdown parsing)
        context = {
            "page": page,
            "content": Markup(content),  # Mark as safe HTML
            "title": page.title,
            "metadata": page.metadata,
            "toc": Markup(page.toc) if page.toc else "",  # Mark TOC as safe HTML
            "toc_items": page.toc_items,  # Structured TOC data
            # Pre-computed cached properties (computed once, reused in templates)
            # Templates can use these directly or access via page.meta_description, etc.
            "meta_desc": page.meta_description,  # From cached_property
            "reading_time": page.reading_time,  # From cached_property
            "excerpt": page.excerpt,  # From cached_property
        }

        # Add special context for generated pages
        if page.metadata.get("_generated"):
            self._add_generated_page_context(page, context)

        # Add section context for reference documentation types, doc types, and index pages
        # This allows manual reference pages, doc pages, and section index pages to access section data
        page_type = page.metadata.get("type")
        is_index_page = page.source_path.stem in ("_index", "index")

        if (
            hasattr(page, "_section")
            and page._section
            and (
                page_type
                in (
                    "api-reference",
                    "cli-reference",
                    "tutorial",
                    "doc",
                    "blog",
                    "archive",
                    "changelog",
                )
                or is_index_page
            )
        ):
            # Add section context if:
            # 1. It's a reference documentation type (api-reference, cli-reference, tutorial)
            # 2. It's a doc type page (for doc/list.html templates)
            # 3. It's a blog or archive type page (for blog/list.html templates)
            # 4. It's an index page (_index.md or index.md)
            section = page._section

            # Use pre-filtered/sorted _posts if available (from SectionOrchestrator),
            # otherwise fall back to section.pages
            posts = page.metadata.get("_posts", section.pages)
            subsections = page.metadata.get("_subsections", section.subsections)

            context.update(
                {
                    "section": section,
                    "posts": posts,
                    "pages": posts,  # Alias for templates expecting 'pages'
                    "subsections": subsections,
                }
            )

        # Handle root index pages (top-level _index.md without enclosing section)
        # Provide context for ALL root index pages, regardless of type
        elif is_index_page and page._section is None:
            # For root home page, provide site-level context as fallback
            # Filter to top-level items only (exclude nested sections/pages)
            top_level_pages = [
                p
                for p in self.site.regular_pages
                if not any(p in s.pages for s in self.site.sections)
            ]
            top_level_subsections = [
                s
                for s in self.site.sections
                if not any(s in parent.subsections for parent in self.site.sections)
            ]

            context.update(
                {
                    "section": None,  # Root has no section
                    "posts": top_level_pages,
                    "pages": top_level_pages,  # Alias
                    "subsections": top_level_subsections,
                }
            )

        # Render with template
        try:
            return self.template_engine.render(template_name, context)
        except Exception as e:
            from bengal.rendering.errors import TemplateRenderError, display_template_error

            # Create rich error object
            rich_error = TemplateRenderError.from_jinja2_error(
                e, template_name, page.source_path, self.template_engine
            )

            # In strict mode, display and fail immediately
            strict_mode = self.site.config.get("strict_mode", False)
            debug_mode = self.site.config.get("debug", False)

            if strict_mode:
                display_template_error(rich_error)
                if debug_mode:
                    # Use configured traceback renderer for consistency
                    try:
                        from bengal.utils.traceback_config import TracebackConfig

                        TracebackConfig.from_environment().get_renderer().display_exception(e)
                    except Exception:
                        pass
                # Wrap in RuntimeError for consistent error handling
                raise RuntimeError(
                    f"Template error in strict mode: {truncate_error(rich_error.message)}"
                ) from e

            # In production mode, collect error and continue
            if self.build_stats:
                self.build_stats.add_template_error(rich_error)
            else:
                # No build stats available, display immediately
                display_template_error(rich_error)

            if debug_mode:
                # Show exception using the configured renderer
                try:
                    from bengal.utils.traceback_config import TracebackConfig

                    TracebackConfig.from_environment().get_renderer().display_exception(e)
                except Exception:
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

        if page_type in (
            "archive",
            "blog",
            "api-reference",
            "cli-reference",
            "tutorial",
            "changelog",
        ):
            # Archive/Reference/Blog page context
            # Note: Posts are already filtered and sorted by the content type strategy
            # in the SectionOrchestrator, so we don't need to re-sort here
            section = page.metadata.get("_section")
            all_posts = page.metadata.get("_posts", [])  # Already filtered & sorted!
            subsections = page.metadata.get("_subsections", [])
            paginator = page.metadata.get("_paginator")
            page_num = page.metadata.get("_page_num", 1)

            # Get posts for this page
            if paginator:
                posts = paginator.page(page_num)
                pagination = paginator.page_context(page_num, f"/{section.name}/")
            else:
                # Use pre-sorted posts directly (no re-sorting needed)
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
                    "section": section,
                    "posts": posts,
                    "pages": posts,  # Alias for templates expecting 'pages'
                    "subsections": subsections,
                    "total_posts": len(all_posts),
                    **pagination,
                }
            )

        elif page_type == "tag":
            # Individual tag page context
            tag_name = page.metadata.get("_tag")
            tag_slug = page.metadata.get("_tag_slug")
            all_posts = page.metadata.get("_posts", [])
            paginator = page.metadata.get("_paginator")
            page_num = page.metadata.get("_page_num", 1)

            # Get posts for this page
            if paginator:
                posts = paginator.page(page_num)
                pagination = paginator.page_context(page_num, f"/tags/{tag_slug}/")
            else:
                posts = all_posts
                pagination = {
                    "current_page": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False,
                    "base_url": f"/tags/{tag_slug}/",
                }

            context.update(
                {
                    "tag": tag_name,
                    "tag_slug": tag_slug,
                    "posts": posts,
                    "total_posts": len(all_posts),
                    **pagination,
                }
            )

        elif page_type == "tag-index":
            # Tag index page context
            tags = page.metadata.get("_tags", {})

            # Convert to sorted list for template
            tags_list = [
                {
                    "name": data["name"],
                    "slug": data["slug"],
                    "count": len(data["pages"]),
                    "pages": data["pages"],
                }
                for data in tags.values()
            ]
            # Sort by count (descending) then name
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
        2. Type-based template selection (e.g., `type: api-reference`)
        3. Section-based auto-detection (e.g., `docs.html`, `docs/single.html`)
        4. Default fallback (`page.html` or `index.html`)

        Note: We intentionally avoid Hugo's confusing type/kind/layout hierarchy.

        Args:
            page: Page to get template for

        Returns:
            Template name
        """
        # 1. Explicit template (highest priority)
        if "template" in page.metadata:
            return page.metadata["template"]

        # 2. Type-based or content_type-based template selection
        # Page's explicit type has priority over section's content_type
        page_type = page.metadata.get("type")
        content_type = None

        if hasattr(page, "_section") and page._section and hasattr(page._section, "metadata"):
            content_type = page._section.metadata.get("content_type")

        is_section_index = page.source_path.stem == "_index"

        # Try type-based templates (for pages with explicit type) - HIGHER PRIORITY
        if page_type:
            # Map common types to content types
            type_mappings = {
                "python-module": "api-reference",
                "cli-command": "cli-reference",
                "api-reference": "api-reference",
                "cli-reference": "cli-reference",
                "doc": "doc",
                "tutorial": "tutorial",
                "blog": "blog",
                "changelog": "changelog",
            }

            if page_type in type_mappings:
                mapped_type = type_mappings[page_type]

                if is_section_index:
                    # Index pages: try list-style templates
                    templates_to_try = [
                        f"{mapped_type}/list.html",
                        f"{mapped_type}/index.html",
                    ]
                else:
                    # Regular pages: try single-style templates
                    templates_to_try = [
                        f"{mapped_type}/single.html",
                        f"{mapped_type}/page.html",
                    ]

                for template_name in templates_to_try:
                    if self._template_exists(template_name):
                        return template_name

        # Try content_type-based templates (for autodoc pages) - LOWER PRIORITY
        # Only used if page doesn't have explicit type
        if content_type and not is_section_index and not page_type:
            # For pages in api-reference or cli-reference sections
            templates_to_try = [
                f"{content_type}/single.html",
                f"{content_type}/page.html",
            ]
            for template_name in templates_to_try:
                if self._template_exists(template_name):
                    return template_name

        # 3. Section-based auto-detection
        if hasattr(page, "_section") and page._section:
            section_name = page._section.name

            if is_section_index:
                # Try section index templates in order of specificity
                templates_to_try = [
                    f"{section_name}/list.html",  # Hugo-style directory
                    f"{section_name}/index.html",  # Alternative directory
                    f"{section_name}-list.html",  # Flat with suffix
                    f"{section_name}.html",  # Flat simple
                ]
            else:
                # Try section page templates in order of specificity
                templates_to_try = [
                    f"{section_name}/single.html",  # Hugo-style directory
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
        except Exception:
            return False

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
    <title>{page.title} - {self.site.config.get("title", "Site")}</title>
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
