"""
Asset extraction utilities for tracking page-to-asset dependencies.

Extracts references to assets (images, stylesheets, scripts, fonts) from
rendered HTML to populate the AssetDependencyMap cache. This enables
incremental builds to discover only the assets needed for changed pages.

Asset types tracked:
- Images: <img src>, <picture> <source srcset>
- Stylesheets: <link href> with rel=stylesheet
- Scripts: <script src>
- Fonts: <link href> with rel=preload type=font
- Data URLs, IFrames, and other embedded resources
"""

from __future__ import annotations

import re
from html.parser import HTMLParser


class AssetExtractorParser(HTMLParser):
    """HTML parser for extracting asset references from rendered content."""

    def __init__(self) -> None:
        """Initialize the asset extractor parser."""
        super().__init__()
        self.assets: set[str] = set()
        self.in_style_tag = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Extract asset references from opening tags.

        Handles:
        - <img src>, <img srcset>
        - <script src>
        - <link href>
        - <source srcset>
        - <iframe src>
        - <picture> with sources
        """
        tag = tag.lower()
        attrs_dict = dict(attrs) if attrs else {}

        if tag == "img":
            # Extract src and srcset
            if "src" in attrs_dict and attrs_dict["src"]:
                self.assets.add(attrs_dict["src"])
            if "srcset" in attrs_dict and attrs_dict["srcset"]:
                # srcset can contain multiple URLs: "url1 1x, url2 2x"
                for item in attrs_dict["srcset"].split(","):
                    url = item.strip().split()[0]
                    if url:
                        self.assets.add(url)

        elif tag == "script":
            # Extract script src
            if "src" in attrs_dict and attrs_dict["src"]:
                self.assets.add(attrs_dict["src"])

        elif tag == "link":
            # Extract link href (stylesheets, fonts, etc.)
            if "href" in attrs_dict and attrs_dict["href"]:
                href = attrs_dict["href"]
                rel_value = attrs_dict.get("rel", "")
                if rel_value is not None:
                    rel = rel_value.lower()
                    # Track stylesheets, preloads, etc.
                    if "stylesheet" in rel or "preload" in rel or "prefetch" in rel:
                        self.assets.add(href)

        elif tag == "source":
            # Extract srcset from picture/video sources
            if "srcset" in attrs_dict and attrs_dict["srcset"]:
                for item in attrs_dict["srcset"].split(","):
                    url = item.strip().split()[0]
                    if url:
                        self.assets.add(url)
            if "src" in attrs_dict and attrs_dict["src"]:
                self.assets.add(attrs_dict["src"])

        elif tag == "iframe":
            # Extract iframe src
            if "src" in attrs_dict and attrs_dict["src"]:
                self.assets.add(attrs_dict["src"])

        elif tag == "style":
            # Mark that we're in a style tag (for parsing @import)
            self.in_style_tag = True

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags."""
        if tag.lower() == "style":
            self.in_style_tag = False

    def handle_data(self, data: str) -> None:
        """
        Extract @import URLs from style tag content.

        Handles:
        - @import url('...')
        - @import url("...")
        - @import url(...) - without quotes
        """
        if self.in_style_tag:
            # Match @import url(...) patterns
            import_pattern = r"@import\s+url\(['\"]?([^'\")\s]+)['\"]?\)"
            for match in re.finditer(import_pattern, data):
                url = match.group(1)
                if url:
                    self.assets.add(url)

    def feed(self, data: str) -> AssetExtractorParser:  # type: ignore[override]
        """
        Parse HTML and return self for chaining.

        Returns:
            self to allow parser(html).get_assets() pattern

        Note:
            HTMLParser.feed returns None, but we return self for chaining.
            Type ignore is needed for this intentional override.
        """
        from contextlib import suppress

        with suppress(Exception):
            # Gracefully handle malformed HTML
            super().feed(data)
        return self

    def get_assets(self) -> set[str]:
        """
        Get all extracted asset URLs.

        Filters out empty strings and returns normalized set.

        Returns:
            Set of asset URLs/paths
        """
        return {url.strip() for url in self.assets if url and url.strip()}


def extract_assets_from_html(html_content: str) -> set[str]:
    """
    Extract all asset references from rendered HTML.

    Args:
        html_content: Rendered HTML content

    Returns:
        Set of asset URLs/paths referenced in the HTML

    Example:
        >>> html = '<img src="/images/logo.png" /><script src="/js/app.js"></script>'
        >>> assets = extract_assets_from_html(html)
        >>> assert "/images/logo.png" in assets
        >>> assert "/js/app.js" in assets
    """
    if not html_content:
        return set()

    parser = AssetExtractorParser()
    return parser.feed(html_content).get_assets()
