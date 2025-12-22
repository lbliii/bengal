"""
Per-page TXT generator for Bengal SSG.

Generates LLM-friendly plain text files alongside each HTML page. These
text files are optimized for AI/LLM discovery, RAG systems, and content
extraction by providing clean, structured plain text without HTML markup.

Output Format:
    Each page.html gets a corresponding page.txt (or index.txt for
    directory index pages) with this structure:

    ```
    # Page Title

    URL: /section/page/
    Section: docs
    Tags: python, api
    Date: 2024-01-15

    --------------------------------------------------------------------------------

    [Plain text content extracted from AST]

    --------------------------------------------------------------------------------

    Metadata:
    - Author: Jane Doe
    - Word Count: 1234
    - Reading Time: 6 minutes
    ```

Use Cases:
    - LLM context windows (clean text without HTML noise)
    - RAG (Retrieval-Augmented Generation) pipelines
    - AI-powered search and analysis
    - Content extraction for external tools
    - Accessibility (screen readers, text-only browsers)

Configuration:
    Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    enabled = true
    per_page = ["llm_txt"]  # Enable per-page LLM text
    options.llm_separator_width = 80  # Separator line width
    ```

Example:
    >>> generator = PageTxtGenerator(site, separator_width=80)
    >>> count = generator.generate(pages)
    >>> print(f"Generated {count} TXT files")

Related:
    - bengal.postprocess.output_formats: OutputFormatsGenerator facade
    - bengal.postprocess.output_formats.llm_generator: Site-wide LLM text
    - bengal.core.page: Page.plain_text for AST-based text extraction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import (
    get_page_relative_url,
    get_page_txt_path,
)
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class PageTxtGenerator:
    """
    Generates per-page LLM-friendly text files.

    Creates a .txt file alongside each HTML page in a structured format
    optimized for AI/LLM discovery, RAG pipelines, and content extraction.

    Creation:
        Direct instantiation: PageTxtGenerator(site, separator_width=80)
            - Created by OutputFormatsGenerator for TXT generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages
        separator_width: Width of separator lines in output (default: 80)

    Relationships:
        - Used by: OutputFormatsGenerator facade
        - Uses: Site for page access, Page.plain_text for content

    Output Structure:
        - Header: Title, URL, section, tags, date
        - Content: Plain text from AST (no HTML)
        - Footer: Author, word count, reading time

    Performance:
        - Parallel writes with 8-thread pool
        - Uses cached Page.plain_text (computed during rendering)

    Example:
        >>> generator = PageTxtGenerator(site, separator_width=80)
        >>> count = generator.generate(pages)
        >>> print(f"Generated {count} TXT files")
    """

    def __init__(
        self,
        site: Site,
        separator_width: int = 80,
    ) -> None:
        """
        Initialize the TXT generator.

        Args:
            site: Site instance
            separator_width: Width of separator lines in output
        """
        self.site = site
        self.separator_width = separator_width

    def generate(self, pages: list[Page]) -> int:
        """
        Generate TXT files for all pages.

        Args:
            pages: List of pages to generate TXT for

        Returns:
            Number of TXT files generated
        """
        import concurrent.futures
        from typing import Any

        # Prepare all page data first
        page_items: list[tuple[Any, str]] = []
        for page in pages:
            txt_path = get_page_txt_path(page)
            if not txt_path:
                continue
            text = self.page_to_llm_text(page)
            page_items.append((txt_path, text))

        if not page_items:
            return 0

        # Write files in parallel
        def write_txt(item: tuple[Any, str]) -> bool:
            txt_path, text = item
            try:
                txt_path.parent.mkdir(parents=True, exist_ok=True)
                with AtomicFile(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                return True
            except Exception as e:
                logger.warning("page_txt_write_failed", path=str(txt_path), error=str(e))
                return False

        # Use thread pool for I/O-bound writes
        count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = executor.map(write_txt, page_items)
            count = sum(1 for r in results if r)

        logger.info("page_txt_generated", count=count)
        return count

    def page_to_llm_text(self, page: Page) -> str:
        """
        Convert page to LLM-friendly text format.

        Args:
            page: Page object

        Returns:
            Formatted text string optimized for AI discovery
        """
        lines = []

        # Title
        lines.append(f"# {page.title}\n")

        # Metadata
        url = get_page_relative_url(page, self.site)
        lines.append(f"URL: {url}")

        section_name = (
            getattr(page._section, "name", "")
            if hasattr(page, "_section") and page._section
            else ""
        )
        if section_name:
            lines.append(f"Section: {section_name}")

        if page.tags:
            tags = page.tags
            # Ensure tags is iterable
            if isinstance(tags, list | tuple):
                tags_list = list(tags)
            else:
                try:
                    tags_list = list(tags) if tags else []
                except (TypeError, ValueError):
                    tags_list = []
            if tags_list:
                lines.append(f"Tags: {', '.join(str(tag) for tag in tags_list)}")

        if page.date:
            lines.append(f"Date: {page.date.strftime('%Y-%m-%d')}")

        lines.append("\n" + ("-" * self.separator_width) + "\n")

        # Content (plain text via AST walker)
        content = page.plain_text
        lines.append(content)

        # Footer metadata
        word_count = len(content.split())
        reading_time = max(1, round(word_count / 200))

        lines.append("\n" + ("-" * self.separator_width))
        lines.append("\nMetadata:")
        if "author" in page.metadata:
            lines.append(f"- Author: {page.metadata['author']}")
        lines.append(f"- Word Count: {word_count}")
        lines.append(f"- Reading Time: {reading_time} minutes")

        return "\n".join(lines)
