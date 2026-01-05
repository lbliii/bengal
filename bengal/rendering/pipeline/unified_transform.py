"""
Unified HTML Transform - Optimized content transformation for rendering.

This module provides an optimized HTML transformation approach that combines
multiple passes into an efficient sequence with quick rejection checks.

Performance:
    Benchmarked at ~27% faster than separate transform calls.
    See: scripts/benchmark_transforms.py

Architecture:
    - Step 1: Jinja escaping via str.replace() (C-optimized, very fast)
    - Step 2: .md link normalization (single regex pass with quick rejection)
    - Step 3: Internal link baseurl prefixing (single regex pass with quick rejection)

The key optimizations are:
    1. Quick rejection checks before regex operations
    2. Single transformer instance reused across pages
    3. Compiled regex patterns

Related Modules:
    - bengal.rendering.pipeline.transforms: Original separate transforms
    - bengal.rendering.pipeline.core: Uses this transformer
    - bengal.rendering.link_transformer: Link transformation patterns

RFC Reference:
    plan/drafted/rfc-rendering-package-optimizations.md
"""

from __future__ import annotations

import re
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class HybridHTMLTransformer:
    """
    Optimized HTML transformer combining multiple transformation passes.

    This transformer applies Jinja escaping and link transformations in an
    optimized sequence with quick rejection checks to skip unnecessary work.

    Creation:
        transformer = HybridHTMLTransformer(baseurl="/bengal")
        result = transformer.transform(html)

    Thread Safety:
        Thread-safe. Transformer instances are stateless after initialization
        and can be safely shared across threads.

    Performance:
        Approximately 27% faster than calling separate transform functions.
        Improvement is most significant for pages with transformable content.

    Examples:
        >>> transformer = HybridHTMLTransformer("/bengal")
        >>> transformer.transform('<a href="/docs/">Docs</a>')
        '<a href="/bengal/docs/">Docs</a>'

        >>> transformer.transform('<a href="./guide.md">Guide</a>')
        '<a href="./guide/">Guide</a>'
    """

    def __init__(self, baseurl: str = "") -> None:
        """
        Initialize the transformer.

        Args:
            baseurl: Base URL prefix for internal links (e.g., "/bengal").
                    If empty, internal link transformation is skipped.
        """
        self.baseurl = baseurl.rstrip("/") if baseurl else ""
        self.should_transform_links = bool(self.baseurl)

        # Normalize baseurl for comparison
        if self.baseurl and not self.baseurl.startswith(("http://", "https://", "file://", "/")):
            self.baseurl = "/" + self.baseurl

        # Compiled regex patterns for link transformations
        # Pattern for .md links: href="...md" or href='...md'
        self._md_pattern = re.compile(r'(href)=(["\'])([^"\']*?\.md)\2')

        # Pattern for internal links: href="/..." or src="/..."
        # Excludes external URLs (http/https) and anchors (#)
        self._internal_pattern = re.compile(r'(href|src)=(["\'])(/(?!/)[^"\'#][^"\']*)\2')

    def transform(self, html: str) -> str:
        """
        Transform HTML content with optimized multi-pass approach.

        Applies transformations in sequence:
        1. Jinja block escaping ({%, %})
        2. Markdown link normalization (.md -> /)
        3. Internal link baseurl prefixing (/ -> /baseurl/)

        Each step includes quick rejection to skip unnecessary regex work.

        Args:
            html: HTML content to transform

        Returns:
            Transformed HTML content
        """
        if not html:
            return html

        try:
            # Step 1: Jinja escaping - str.replace() is C-optimized, very fast
            result = html.replace("{%", "&#123;%").replace("%}", "%&#125;")

            # Step 2: Normalize .md links (quick rejection via substring check)
            if ".md" in result:
                result = self._md_pattern.sub(self._md_replacer, result)

            # Step 3: Transform internal links with baseurl (quick rejection)
            if self.should_transform_links and '="/' in result:
                result = self._internal_pattern.sub(self._internal_replacer, result)

            return result

        except Exception as e:
            # Never fail the build on transformation errors
            logger.debug(
                "unified_transform_error",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_original_html",
            )
            return html

    def _md_replacer(self, match: re.Match) -> str:
        """
        Transform .md link to clean URL.

        Handles special cases:
        - ./page.md -> ./page/
        - ./_index.md -> ./
        - ../other.md -> ../other/
        - path/page.md -> path/page/
        """
        attr = match.group(1)
        quote = match.group(2)
        path = match.group(3)

        # Handle _index.md and index.md special cases
        if path.endswith("/_index.md"):
            clean = path[:-10] + "/"
            if clean == "/":
                clean = "./"
        elif path.endswith("_index.md"):
            clean = "./"
        elif path.endswith("/index.md"):
            clean = path[:-9] + "/"
        elif path.endswith("index.md"):
            clean = "./"
        else:
            # Regular .md file -> strip extension, add trailing slash
            clean = path[:-3] + "/"

        return f"{attr}={quote}{clean}{quote}"

    def _internal_replacer(self, match: re.Match) -> str:
        """
        Transform internal link with baseurl prefix.

        Prepends baseurl to internal links starting with /.
        Skips links that already have the baseurl prefix.
        """
        attr = match.group(1)
        quote = match.group(2)
        path = match.group(3)

        # Skip if already has baseurl
        if path.startswith(self.baseurl + "/") or path == self.baseurl:
            return match.group(0)

        return f"{attr}={quote}{self.baseurl}{path}{quote}"


def create_transformer(config: dict[str, Any]) -> HybridHTMLTransformer:
    """
    Create a transformer instance from site config.

    Factory function that extracts baseurl from config and creates
    an appropriately configured transformer.

    Args:
        config: Site configuration dictionary

    Returns:
        Configured HybridHTMLTransformer instance
    """
    # Handle nested config structure (TOML format: [site] section)
    site_section = config.get("site", {})
    if isinstance(site_section, dict):
        baseurl = site_section.get("baseurl", "") or ""
    else:
        baseurl = config.get("baseurl", "") or ""
    return HybridHTMLTransformer(str(baseurl).rstrip("/"))
