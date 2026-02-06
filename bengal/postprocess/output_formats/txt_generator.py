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
    parallel_write_files,
)
from bengal.postprocess.utils import get_section_name, tags_to_list
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike

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
        site: SiteLike,
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

    def generate(self, pages: list[PageLike]) -> int:
        """
        Generate TXT files for all pages.

        Args:
            pages: List of pages to generate TXT for

        Returns:
            Number of TXT files generated
        """
        from pathlib import Path

        # Prepare all page data first
        page_items: list[tuple[Path, str]] = []
        for page in pages:
            txt_path = get_page_txt_path(page)
            if not txt_path:
                continue
            text = self.page_to_llm_text(page)
            page_items.append((txt_path, text))

        if not page_items:
            return 0

        # Write function for parallel execution
        def write_txt(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with AtomicFile(path, "w", encoding="utf-8") as f:
                f.write(content)

        # Use parallel write utility
        count = parallel_write_files(page_items, write_txt, operation_name="page_txt_write")

        logger.info("page_txt_generated", count=count)
        return count

    def page_to_llm_text(self, page: PageLike) -> str:
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

        section_name = get_section_name(page)
        if section_name:
            lines.append(f"Section: {section_name}")

        tags_list = tags_to_list(page.tags)
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
