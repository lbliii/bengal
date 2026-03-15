"""
Page Operations Mixin - Operations and transformations on pages.

Provides render, validate_links, extract_links, and apply_template.
Uses lazy imports for rendering/health to avoid core import-time deps.

Key Methods:
- render(): Render page using template engine
- validate_links(): Validate all links in the page
- extract_links(): Extract all links from page content
- apply_template(): Apply a specific template to the page

Related Modules:
- bengal.rendering.renderer: Page rendering implementation
- bengal.health.validators.links: Link validation logic

See Also:
- bengal/core/page/__init__.py: Page class that uses this mixin

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from bengal.protocols import PageRenderer
from bengal.protocols.core import PageLike

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.health.validators.links import LinkValidator


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

    def render(self, renderer: PageRenderer) -> str:
        """
        Render the page using the provided page renderer.

        Caller creates the renderer (e.g. Renderer(template_engine)) and passes it.
        This avoids core importing from rendering.

        Args:
            renderer: Page renderer instance (e.g. from bengal.rendering.Renderer)

        Returns:
            Rendered HTML content
        """
        self.rendered_html = renderer.render_page(cast(PageLike, self))
        return self.rendered_html

    def validate_links(self, validator: LinkValidator | None = None) -> list[str]:
        """
        Validate all links in the page.

        For batch validation (e.g. during health check), create a single
        LinkValidator(site) and pass it to each page to avoid O(pages^2) work.

        Args:
            validator: Optional shared LinkValidator (IPA audit Task 6).
                When provided, reuses indexes instead of rebuilding per page.

        Returns:
            List of broken link URLs
        """
        from bengal.health.validators.links import LinkValidator

        site = getattr(self, "_site", None)
        if validator is None:
            validator = LinkValidator(site)
        broken_links = validator.validate_page_links(cast(PageLike, self), site)
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
        content_without_code = self._source

        content_without_code = re.sub(
            r"`{4,}[^\n]*\n.*?`{4,}", "", content_without_code, flags=re.DOTALL
        )
        content_without_code = re.sub(
            r"```[^\n]*\n.*?```", "", content_without_code, flags=re.DOTALL
        )
        content_without_code = re.sub(r"`[^`]+`", "", content_without_code)

        markdown_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content_without_code)
        html_links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', content_without_code)

        if plugin_links is not None:
            wikilink_urls = plugin_links
            self.links = [url for _, url in markdown_links] + html_links + wikilink_urls
        elif self.html_content:
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
            if path.startswith("!"):
                url = f"#{path[1:]}"
            elif path.startswith("#"):
                url = path
            else:
                path = path.replace("\\|", "|").split("|")[0].strip()
                url = f"/{path}" if not path.startswith("/") else path
            wikilink_urls.append(url)
        return wikilink_urls
