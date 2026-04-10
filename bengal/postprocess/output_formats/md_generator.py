"""
Per-page Markdown generator for Bengal SSG.

Generates .md files alongside each HTML page so that AI agents can
request structured markdown content at .md URLs (e.g.,
``/docs/getting-started/index.md``). This enables the "Markdown URL
Support" check in agent-readiness scorecards.

Output Format:
Each page.html gets a corresponding page.md (or index.md for
directory index pages) containing the page's source markdown with
a minimal metadata header:

    ```markdown
    # Page Title

    URL: /bengal/docs/getting-started/
    Section: docs

    ---

    [Original markdown content]
    ```

Configuration:
Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    per_page = ["json", "llm_txt", "markdown"]
    ```

Or via the features shorthand:

    ```yaml
    features:
      markdown: true
    ```

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.txt_generator: Per-page plain text
- bengal.postprocess.output_formats.llms_txt_generator: Site-wide llms.txt

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import (
    get_page_md_path,
    get_page_url,
    parallel_write_files,
)
from bengal.postprocess.utils import get_section_name
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


class PageMarkdownGenerator:
    """Generate per-page .md files for agent markdown URL support.

    Creates a .md file alongside each HTML page containing the page's
    source markdown content with a minimal metadata header.

    Attributes:
        site: Site instance with pages and configuration.
    """

    def __init__(self, site: SiteLike) -> None:
        self.site = site

    def generate(self, pages: list[PageLike]) -> int:
        """Generate .md files for all pages.

        Args:
            pages: List of pages to generate markdown files for.

        Returns:
            Number of .md files generated.
        """
        page_items: list[tuple[Path, str]] = []
        for page in pages:
            md_path = get_page_md_path(page)
            if not md_path:
                continue

            content = self._page_to_markdown(page)
            if content:
                page_items.append((md_path, content))

        if not page_items:
            return 0

        def write_md(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with AtomicFile(path, "w", encoding="utf-8") as f:
                f.write(content)

        count = parallel_write_files(
            page_items,
            write_md,
            max_workers=8,
            operation_name="markdown_write",
        )
        logger.info("markdown_files_generated", count=count, total=len(page_items))
        return count

    def _page_to_markdown(self, page: PageLike) -> str:
        """Convert a page to its markdown output format.

        Uses the page's raw markdown source content. Falls back to
        plain_text if raw source is unavailable.

        Args:
            page: Page to convert.

        Returns:
            Markdown string with metadata header.
        """
        lines: list[str] = []

        # Header
        lines.append(f"# {page.title}")
        lines.append("")

        # Minimal metadata
        url = get_page_url(page, self.site)
        lines.append(f"URL: {url}")

        section_name = get_section_name(page)
        if section_name:
            lines.append(f"Section: {section_name}")

        if page.description:
            lines.append(f"Description: {page.description}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Raw markdown content (preferred) or plain text fallback
        raw = getattr(page, "_raw_content", None) or ""
        if raw:
            # Strip leading H1 if it duplicates the title we already wrote
            content = raw.strip()
            if content.startswith("# "):
                first_line_end = content.find("\n")
                content = content[first_line_end:].lstrip("\n") if first_line_end != -1 else ""
        else:
            # Fallback to plain text
            content = getattr(page, "plain_text", "") or ""

        lines.append(content)
        lines.append("")

        return "\n".join(lines)
