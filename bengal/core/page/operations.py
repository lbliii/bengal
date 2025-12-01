"""
Page Operations Mixin - Operations and transformations on pages.
"""

from __future__ import annotations

import re
from typing import Any


class PageOperationsMixin:
    """
    Mixin providing operations for pages.

    This mixin handles:
    - Rendering with templates
    - Link validation and extraction
    - Template application
    """

    def render(self, template_engine: Any) -> str:
        """
        Render the page using the provided template engine.

        Args:
            template_engine: Template engine instance

        Returns:
            Rendered HTML content
        """
        from bengal.rendering.renderer import Renderer

        renderer = Renderer(template_engine)
        self.rendered_html = renderer.render_page(self)
        return self.rendered_html

    def validate_links(self) -> list[str]:
        """
        Validate all links in the page.

        Returns:
            List of broken link URLs
        """
        from bengal.rendering.link_validator import LinkValidator

        validator = LinkValidator()
        broken_links = validator.validate_page_links(self)
        return broken_links

    def apply_template(self, template_name: str, context: dict[str, Any] | None = None) -> str:
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

    def extract_links(self) -> list[str]:
        """
        Extract all links from the page content.

        Skips content inside fenced code blocks to avoid false positives
        from code examples in documentation.

        Returns:
            List of link URLs found in the page
        """
        # Remove fenced code blocks before extracting links
        # Process larger fences first (4+ backticks) to handle nested code blocks
        content_without_code = self.content

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

        self.links = [url for _, url in markdown_links] + html_links
        return self.links
