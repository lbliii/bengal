"""
Native HTML parser for build-time validation and health checks.

This parser is used during `bengal build` for:
- Health check validation (detecting unrendered directives, Jinja templates)
- Text extraction from rendered HTML (excluding code blocks)
- Performance-optimized alternative to BeautifulSoup4

Design:
- Uses Python's stdlib html.parser (fast, zero dependencies)
- Tracks state for code/script/style blocks to exclude from text extraction
- Optimized for build-time validation, not complex DOM manipulation

Performance:
- ~5-10x faster than BeautifulSoup4 for text extraction
- Suitable for high-volume build-time validation
"""

from __future__ import annotations

from html.parser import HTMLParser


class NativeHTMLParser(HTMLParser):
    """
    Fast HTML parser for build-time validation and text extraction.

    This parser is the production parser used during `bengal build` for health
    checks and validation. It's optimized for speed over features, using Python's
    stdlib html.parser without external dependencies.

    **Primary use cases:**
    - Health check validation (unrendered directives, Jinja templates)
    - Text extraction for search indexing
    - Link validation and content analysis

    **Performance:**
    - ~5-10x faster than BeautifulSoup4 for text extraction
    - Zero external dependencies (uses stdlib only)

    **Example:**
        >>> parser = NativeHTMLParser()
        >>> result = parser.feed("<p>Hello <code>world</code></p>")
        >>> result.get_text()
        'Hello'  # Code block excluded
    """

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []  # Collect text content
        self.in_code_block = False  # Toggle for <code>/<pre> tags
        self.in_script = False  # Track <script> tags
        self.in_style = False  # Track <style> tags

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle opening tags."""
        if tag.lower() in ("code", "pre"):
            self.in_code_block = True
        elif tag.lower() == "script":
            self.in_script = True
        elif tag.lower() == "style":
            self.in_style = True

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags."""
        if tag.lower() in ("code", "pre"):
            self.in_code_block = False
        elif tag.lower() == "script":
            self.in_script = False
        elif tag.lower() == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        """Handle text data."""
        # Only collect text if not in code/script/style blocks
        if not self.in_code_block and not self.in_script and not self.in_style:
            self.text_parts.append(data)

    def feed(self, data: str) -> NativeHTMLParser:  # type: ignore[override]
        """
        Parse HTML content and return self for chaining.

        Returns:
            self to allow parser(html).get_text() pattern

        Note:
            HTMLParser.feed returns None, but we return self for chaining.
            Type ignore is needed for this intentional override.
        """
        super().feed(data)
        return self

    def get_text(self) -> str:
        """
        Get extracted text content (excluding code/script/style blocks).

        Returns:
            Text content with whitespace normalized
        """
        return " ".join(" ".join(self.text_parts).split())

    def reset(self) -> None:
        """Reset parser state for reuse."""
        super().reset()
        self.text_parts = []
        self.in_code_block = False
        self.in_script = False
        self.in_style = False
