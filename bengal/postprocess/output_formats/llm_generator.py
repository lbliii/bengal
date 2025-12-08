"""
Site-wide LLM text generator for Bengal SSG.

Generates a single llm-full.txt file containing all site content
in an AI/LLM-friendly format for training, context, and analysis.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import (
    get_page_relative_url,
)
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class SiteLlmTxtGenerator:
    """
    Generates site-wide llm-full.txt for AI discovery.

    Creates a single text file containing all site content in a format
    optimized for AI/LLM consumption with clear page separators.

    Example:
        >>> generator = SiteLlmTxtGenerator(site, separator_width=80)
        >>> path = generator.generate(pages)
    """

    def __init__(
        self,
        site: Site,
        separator_width: int = 80,
    ) -> None:
        """
        Initialize the LLM text generator.

        Args:
            site: Site instance
            separator_width: Width of separator lines
        """
        self.site = site
        self.separator_width = separator_width

    def generate(self, pages: list[Page]) -> Path:
        """
        Generate site-wide llm-full.txt.

        Args:
            pages: List of pages to include

        Returns:
            Path to the generated llm-full.txt file
        """
        separator = "=" * self.separator_width
        lines = []

        # Site header
        title = self.site.config.get("title", "Bengal Site")
        baseurl = self.site.config.get("baseurl", "")
        lines.append(f"# {title}\n")
        if baseurl:
            lines.append(f"Site: {baseurl}")

        # Only include build date in production
        if not self.site.config.get("dev_server", False):
            lines.append(f"Build Date: {datetime.now().isoformat()}")

        lines.append(f"Total Pages: {len(pages)}\n")
        lines.append(separator + "\n")

        # Add each page
        for idx, page in enumerate(pages, 1):
            lines.append(f"\n## Page {idx}/{len(pages)}: {page.title}\n")

            # Page metadata
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

            lines.append("")  # Blank line before content

            # Page content (plain text via AST walker)
            content = page.plain_text
            lines.append(content)

            lines.append("\n" + separator + "\n")

        # Write to output directory
        llm_path = self.site.output_dir / "llm-full.txt"
        new_text = "\n".join(lines)

        self._write_if_changed(llm_path, new_text)

        logger.info("site_llm_txt_generated", path=str(llm_path), page_count=len(pages))

        return llm_path

    def _write_if_changed(self, path: Path, content: str) -> None:
        """Write content only if it differs from existing file."""
        try:
            if path.exists():
                existing = path.read_text(encoding="utf-8")
                if existing == content:
                    return
        except Exception as e:
            # If we can't read existing file, proceed to write new content
            logger.debug(
                "postprocess_llm_existing_file_read_failed",
                path=str(path),
                error=str(e),
                error_type=type(e).__name__,
                action="writing_new_content",
            )

        with AtomicFile(path, "w", encoding="utf-8") as f:
            f.write(content)
