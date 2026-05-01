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
from bengal.rendering.html_markdown import rendered_html_to_markdown
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
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

    def generate(self, pages: Sequence[PageLike]) -> int:
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

        Uses the page's raw markdown source content when it provides good
        coverage of the rendered HTML content. Falls back to plain_text
        when raw content is incomplete (e.g., shortcodes or includes
        expanded significant additional content during rendering).

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
        lines.append(self._agent_directive())
        lines.append("")

        content = self._get_best_content(page)
        lines.append(content)
        lines.append("")

        return "\n".join(lines)

    def _agent_directive(self) -> str:
        """Return the page-level directive that points agents to llms.txt."""
        baseurl = (getattr(self.site, "baseurl", "") or "").rstrip("/")
        llms_url = f"{baseurl}/llms.txt" if baseurl else "/llms.txt"
        return f"> For a complete page index, fetch {llms_url}."

    def _get_best_content(self, page: PageLike) -> str:
        """Select the best content source for markdown parity.

        Prefers raw markdown when it covers the rendered page well, because
        it preserves author formatting. Uses the rendered primary content
        when templates generated substantial additional content, then falls
        back to plain_text for parser-expanded content without full rendered
        HTML.

        Args:
            page: Page to get content for.

        Returns:
            Best available content string.
        """
        raw = getattr(page, "_raw_content", None) or ""
        plain = getattr(page, "plain_text", "") or ""
        rendered = getattr(page, "rendered_html", "") or ""
        rendered_markdown = rendered_html_to_markdown(rendered) if isinstance(rendered, str) else ""

        if not raw:
            return rendered_markdown or plain

        content = raw.strip()

        # Strip leading H1 if it duplicates the title we already wrote
        if content.startswith("# "):
            first_line_end = content.find("\n")
            h1_text = (
                content[2:first_line_end].strip() if first_line_end != -1 else content[2:].strip()
            )
            if h1_text == page.title:
                content = content[first_line_end:].lstrip("\n") if first_line_end != -1 else ""

        # Check content parity: if plain_text is significantly longer
        # than raw content, shortcodes/includes added substantial content.
        # Use plain_text for better parity with the rendered HTML.
        raw_len = len(content)
        plain_len = len(plain)
        rendered_len = len(rendered_markdown)
        reference_len = max(raw_len, plain_len)
        if rendered_len > 0 and (reference_len == 0 or rendered_len / reference_len > 1.15):
            return rendered_markdown

        if plain_len > 0 and raw_len > 0:
            coverage = raw_len / plain_len
            if coverage < 0.75:
                # Raw markdown covers <75% of rendered content — fall back
                # to plain text for better parity with HTML output
                return plain

        return content
