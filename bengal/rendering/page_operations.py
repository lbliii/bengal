"""
Page Operations Mixin - Operations and transformations on pages.

This mixin provides methods for page rendering, link extraction, and template
application. It handles the operational aspects of page processing.

Key Methods:
- render(): Render page using template engine
- validate_links(): Validate all links in the page
- extract_links(): Extract all links from page content
- apply_template(): Apply a specific template to the page

Related Modules:
- bengal.rendering.renderer: Page rendering implementation
- bengal.health.validators.links: Link validation logic
- bengal.rendering.template_engine: Template application

See Also:
- bengal/core/page/__init__.py: Page class that uses this mixin

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from bengal.protocols.core import PageLike

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.rendering.template_engine import TemplateEngine


class PageOperationsMixin:
    """
    Mixin providing operations for pages.

    This mixin handles:
    - Rendering with templates
    - Link validation and extraction
    - Template application

    Attributes:
        content: Raw page content (markdown)
        rendered_html: Rendered HTML output
        links: List of links extracted from the page
        source_path: Path to the source content file

    """

    # Declare attributes that will be provided by the dataclass this mixin is mixed into
    content: str
    rendered_html: str
    links: list[str]
    source_path: Path

    def render(self, template_engine: TemplateEngine) -> str:
        """
        Render the page using the provided template engine.

        Args:
            template_engine: Template engine instance

        Returns:
            Rendered HTML content
        """
        from bengal.rendering.renderer import Renderer

        renderer = Renderer(template_engine)
        self.rendered_html = renderer.render_page(cast(PageLike, self))
        return self.rendered_html

    def validate_links(self) -> list[str]:
        """
        Validate all links in the page.

        Returns:
            List of broken link URLs
        """
        from bengal.health.validators.links import LinkValidator

        validator = LinkValidator()
        broken_links = validator.validate_page_links(cast(PageLike, self))
        return broken_links

    def apply_template(self, template_name: str, context: dict[str, object] | None = None) -> str:
        """
        Apply a specific template to this page.

        Args:
            template_name: Name of the template to apply
            context: Additional context variables

        Returns:
            Rendered content with template applied
        """

        # Template application will be handled by the template engine
        return self.rendered_html

    def extract_links(self, plugin_links: list[str] | None = None) -> list[str]:
        """
        Extract all links from the page content.

        When plugin_links is provided (from CrossReferencePlugin during parse),
        uses those for wikilinks (single source of truth). Otherwise falls back
        to html_content extraction or regex on source.

        Skips content inside fenced code blocks to avoid false positives
        from code examples in documentation.

        Args:
            plugin_links: Resolved wikilink URLs from CrossReferencePlugin, or None
                         when plugin did not run (e.g. cache restore, generated pages).

        Returns:
            List of link URLs found in the page
        """
        # Regex-based extraction from raw markdown source
        # Remove fenced code blocks before extracting links
        # Process larger fences first (4+ backticks) to handle nested code blocks
        content_without_code = self._source

        # Remove 4+ backtick fences first (handles nested 3-backtick blocks)
        content_without_code = re.sub(
            r"`{4,}[^\n]*\n.*?`{4,}", "", content_without_code, flags=re.DOTALL
        )

        # Then remove 3-backtick fences
        content_without_code = re.sub(
            r"```[^\n]*\n.*?```", "", content_without_code, flags=re.DOTALL
        )

        # Also remove inline code spans
        content_without_code = re.sub(r"`[^`]+`", "", content_without_code)

        # Extract Markdown links [text](url)
        markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content_without_code)

        # Extract HTML links <a href="url">
        html_links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', content_without_code)

        # Wikilinks: use plugin-collected when available, else fallback
        if plugin_links is not None:
            wikilink_urls = plugin_links
            self.links = [url for _, url in markdown_links] + html_links + wikilink_urls
        elif self.html_content:
            # Fallback: extract all links from html_content (resolved hrefs + broken-ref)
            self.links = self._extract_all_links_from_html()
        else:
            wikilink_urls = self._extract_wikilinks_from_source(content_without_code)
            self.links = [url for _, url in markdown_links] + html_links + wikilink_urls

        return self.links

    def _extract_all_links_from_html(self) -> list[str]:
        """Extract all links from html_content (fallback when plugin didn't run)."""
        urls: list[str] = []
        urls.extend(re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', self.html_content))
        urls.extend(
            match.group(1)
            for match in re.finditer(
                r'<span\s+class="broken-ref"[^>]*data-ref="([^"]+)"', self.html_content
            )
        )
        return urls

    def _extract_wikilinks_from_source(self, content: str) -> list[str]:
        """Extract wikilinks from source via regex (last-resort fallback)."""
        wikilink_matches = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", content)
        wikilink_urls = []
        for path in wikilink_matches:
            path = path.strip()
            if path.startswith("ext:"):
                continue
            # Fix edge cases: [[!id]] -> #id, [[#heading]] -> #heading, [[path\|label]] -> path
            if path.startswith("!"):
                url = f"#{path[1:]}"
            elif path.startswith("#"):
                url = path
            else:
                path = path.replace("\\|", "|").split("|")[0].strip()
                url = f"/{path}" if not path.startswith("/") else path
            wikilink_urls.append(url)
        return wikilink_urls
