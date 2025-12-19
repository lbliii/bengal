"""
API Documentation Enhancer - Post-processes API docs to inject badges and visual indicators.

This module operates on parsed HTML after Markdown rendering but before template application.
It's designed to work around Mistune's HTML escaping while maintaining clean, maintainable code.

Architecture:
    - Operates at the rendering pipeline stage (after Markdown → HTML)
    - Uses marker syntax in templates (@async, @property, etc.)
    - Injects HTML badges via regex replacement
    - Opt-in via page type (python-module, autodoc/python)

Usage:

```python
from bengal.rendering.api_doc_enhancer import APIDocEnhancer

enhancer = APIDocEnhancer()
enhanced_html = enhancer.enhance(html, page_type='python-module')
```
"""

from __future__ import annotations

import re

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class APIDocEnhancer:
    """
    Post-processes API documentation HTML to inject badges and visual enhancements.

    This enhancer transforms marker syntax (e.g., @async, @property) into styled
    HTML badges. It operates on already-parsed HTML, avoiding Mistune's escaping issues.

    Markers are placed in templates after method names and get replaced with proper
    HTML during post-processing.

    Example:
        Input:  <h4>build @async</h4>
        Output: <h4>build <span class="api-badge api-badge-async">async</span></h4>
    """

    # Badge patterns: (marker_pattern, replacement)
    # Note: These need to handle headerlink anchors that come before the closing tag
    BADGE_PATTERNS = [
        # Async methods/functions (h3 or h4 headings)
        (
            r"(<h[34][^>]*>)([^<@]+)\s*@async\s*(<a[^>]*headerlink[^>]*>.*?</a>)(\s*</h[34]>)",
            r'\1\2 <span class="api-badge api-badge-async">async</span>\3\4',
        ),
        # Properties (h4 headings only)
        (
            r"(<h4[^>]*>)([^<@]+)\s*@property\s*(<a[^>]*headerlink[^>]*>.*?</a>)(\s*</h4>)",
            r'\1\2 <span class="api-badge api-badge-property">property</span>\3\4',
        ),
        # Class methods (h4 headings only)
        (
            r"(<h4[^>]*>)([^<@]+)\s*@classmethod\s*(<a[^>]*headerlink[^>]*>.*?</a>)(\s*</h4>)",
            r'\1\2 <span class="api-badge api-badge-classmethod">classmethod</span>\3\4',
        ),
        # Static methods (h4 headings only)
        (
            r"(<h4[^>]*>)([^<@]+)\s*@staticmethod\s*(<a[^>]*headerlink[^>]*>.*?</a>)(\s*</h4>)",
            r'\1\2 <span class="api-badge api-badge-staticmethod">staticmethod</span>\3\4',
        ),
        # Deprecated (any heading level)
        (
            r"(<h[2-6][^>]*>)([^<@]+)\s*@deprecated\s*(<a[^>]*headerlink[^>]*>.*?</a>)(\s*</h[2-6]>)",
            r'\1\2 <span class="api-badge api-badge-deprecated">deprecated</span>\3\4',
        ),
    ]

    # Page types that should be enhanced
    SUPPORTED_PAGE_TYPES = {
        "python-module",
        "autodoc/python",
        "cli-command",
        "autodoc-cli",
    }

    def __init__(self) -> None:
        """Initialize the enhancer."""
        # Compile patterns for performance
        self._compiled_patterns = [
            (re.compile(pattern, re.MULTILINE), replacement)
            for pattern, replacement in self.BADGE_PATTERNS
        ]

    def should_enhance(self, page_type: str | None) -> bool:
        """
        Check if a page should be enhanced based on its type.

        Args:
            page_type: The page type from frontmatter

        Returns:
            True if the page should be enhanced
        """
        return page_type in self.SUPPORTED_PAGE_TYPES

    def enhance(self, html: str, page_type: str | None = None) -> str:
        """
        Enhance HTML with API documentation badges.

        This method applies all badge transformations to the HTML if the page
        type indicates it's an API documentation page.

        Args:
            html: Parsed HTML from markdown rendering
            page_type: Page type from frontmatter (optional)

        Returns:
            Enhanced HTML with badges injected (or unchanged HTML if not applicable)

        Example:
            >>> enhancer = APIDocEnhancer()
            >>> html = '<h4>render @async</h4>'
            >>> enhancer.enhance(html, 'python-module')
            '<h4>render <span class="api-badge api-badge-async">async</span></h4>'
        """
        # Only enhance API documentation pages
        if not self.should_enhance(page_type):
            return html

        # Apply all badge patterns
        enhanced = html
        replacements_made = 0
        for pattern, replacement in self._compiled_patterns:
            before = enhanced
            enhanced = pattern.sub(replacement, enhanced)
            if len(enhanced) != len(before):
                replacements_made += 1

        # Debug: Report if badges were added (only in dev mode)
        if replacements_made > 0:
            from bengal.utils.profile import should_show_debug

            if should_show_debug():
                logger.debug("api_doc_badge_replacements", replacements_made=replacements_made)

        return enhanced

    def strip_markers(self, html: str) -> str:
        """
        Remove all marker syntax from HTML without adding badges.

        Useful for pages that want to show API documentation without badges,
        or for debugging purposes.

        Args:
            html: HTML with marker syntax

        Returns:
            HTML with markers removed
        """
        # Simple pattern to match all @marker syntax
        marker_pattern = re.compile(
            r"\s+@(?:async|property|classmethod|staticmethod|deprecated)\s*"
        )
        return marker_pattern.sub(" ", html)


# Singleton instance for reuse across pages
_enhancer = None


def get_enhancer() -> APIDocEnhancer:
    """
    Get or create the singleton APIDocEnhancer instance.

    Returns:
        Shared APIDocEnhancer instance
    """
    global _enhancer
    if _enhancer is None:
        _enhancer = APIDocEnhancer()
    return _enhancer
