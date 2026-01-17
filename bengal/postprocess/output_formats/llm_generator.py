"""
Site-wide LLM text generator for Bengal SSG.

Generates a single llm-full.txt file containing all site content in an
AI/LLM-friendly format. This consolidated text file is ideal for:
- LLM fine-tuning and training data
- RAG (Retrieval-Augmented Generation) context
- Documentation analysis and summarization
- Content auditing and quality review

Output Format:
The llm-full.txt contains all pages concatenated with clear separators:

    ```
    # Site Title

    Site: https://example.com
    Build Date: 2024-01-15T10:30:00
    Total Pages: 150

    ================================================================================

    ## Page 1/150: Getting Started

    URL: /docs/getting-started/
    Section: docs
    Tags: tutorial, quickstart
    Date: 2024-01-10

    [Plain text content]

    ================================================================================

    ## Page 2/150: API Reference
    ...
    ```

Use Cases:
- Feed entire site to LLM for comprehensive context
- Generate site summaries and documentation audits
- Create training data for custom models
- Content migration and analysis

Configuration:
Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    site_wide = ["llm_full"]
    options.llm_separator_width = 80
    ```

Example:
    >>> generator = SiteLlmTxtGenerator(site, separator_width=80)
    >>> path = generator.generate(pages)
    >>> print(f"Generated: {path}")

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.txt_generator: Per-page LLM text

"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import (
    get_page_relative_url,
)
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


class SiteLlmTxtGenerator:
    """
    Generates site-wide llm-full.txt for AI/LLM consumption.
    
    Creates a single consolidated text file containing all site content,
    formatted for easy parsing by LLMs with clear page separators and
    structured metadata headers.
    
    Creation:
        Direct instantiation: SiteLlmTxtGenerator(site, separator_width=80)
            - Created by OutputFormatsGenerator for LLM text generation
            - Requires Site instance with rendered pages
    
    Attributes:
        site: Site instance with pages and configuration
        separator_width: Width of separator lines (default: 80)
    
    Relationships:
        - Used by: OutputFormatsGenerator facade
        - Uses: Site for pages, Page.plain_text for content
    
    Output Structure:
        - Site header: Title, URL, build date, page count
        - Per-page sections: Numbered pages with metadata and content
        - Separator lines between pages for clear boundaries
    
    Optimizations:
        - Streaming write: O(c) memory instead of O(n×c) for large sites
        - Hash-based change detection: Skip regeneration if content unchanged
        - Uses cached Page.plain_text (computed during rendering)
    
    Example:
            >>> generator = SiteLlmTxtGenerator(site, separator_width=80)
            >>> path = generator.generate(pages)
            >>> print(f"Generated: {path}")
        
    """

    def __init__(
        self,
        site: SiteLike,
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
        Generate site-wide llm-full.txt with streaming write.

        Uses streaming write to reduce memory from O(n×c) to O(c), where n is
        page count and c is average content size. For 10K pages at 5KB each,
        this reduces peak memory from ~100MB to ~5KB.

        Args:
            pages: List of pages to include

        Returns:
            Path to the generated llm-full.txt file
        """
        llm_path = self.site.output_dir / "llm-full.txt"
        hash_path = self.site.output_dir / ".llm-full.hash"

        # OPTIMIZATION: Compute content hash incrementally to detect changes
        # without loading entire file into memory. O(n) time but O(1) memory.
        hasher = hashlib.sha256()
        for page in pages:
            hasher.update(page.plain_text.encode("utf-8"))
        new_hash = hasher.hexdigest()

        # Check if content unchanged via hash comparison (O(1) instead of O(n))
        if self._is_unchanged(hash_path, new_hash):
            logger.debug(
                "site_llm_txt_skipped",
                reason="content_unchanged",
                path=str(llm_path),
            )
            return llm_path

        # OPTIMIZATION: Stream directly to file instead of building in memory
        # Reduces memory from O(n×c) to O(c) (single page at a time)
        separator = "=" * self.separator_width
        title = self.site.title or "Bengal Site"
        baseurl = self.site.baseurl or ""

        with AtomicFile(llm_path, "w", encoding="utf-8") as f:
            # Site header
            f.write(f"# {title}\n\n")
            if baseurl:
                f.write(f"Site: {baseurl}\n")

            # Only include build date in production
            # Use site.build_time for deterministic output (matches index_generator behavior)
            if not self.site.dev_mode:
                build_time = getattr(self.site, "build_time", None)
                if isinstance(build_time, datetime):
                    f.write(f"Build Date: {build_time.isoformat()}\n")
                else:
                    f.write(f"Build Date: {datetime.now().isoformat()}\n")

            f.write(f"Total Pages: {len(pages)}\n\n")
            f.write(separator + "\n")

            # Stream each page
            for idx, page in enumerate(pages, 1):
                f.write(f"\n## Page {idx}/{len(pages)}: {page.title}\n\n")

                # Page metadata
                url = get_page_relative_url(page, self.site)
                f.write(f"URL: {url}\n")

                section_name = (
                    getattr(page._section, "name", "")
                    if hasattr(page, "_section") and page._section
                    else ""
                )
                if section_name:
                    f.write(f"Section: {section_name}\n")

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
                        f.write(f"Tags: {', '.join(str(tag) for tag in tags_list)}\n")

                if page.date:
                    f.write(f"Date: {page.date.strftime('%Y-%m-%d')}\n")

                f.write("\n")  # Blank line before content

                # Page content (plain text via AST walker)
                content = page.plain_text
                f.write(content)
                f.write("\n\n" + separator + "\n")

        # Save hash for next build
        hash_path.write_text(new_hash, encoding="utf-8")

        logger.info("site_llm_txt_generated", path=str(llm_path), page_count=len(pages))
        return llm_path

    def _is_unchanged(self, hash_path: Path, new_hash: str) -> bool:
        """Check if content hash matches stored hash."""
        try:
            if hash_path.exists():
                existing_hash = hash_path.read_text(encoding="utf-8").strip()
                return existing_hash == new_hash
        except Exception as e:
            logger.debug(
                "llm_hash_check_failed",
                path=str(hash_path),
                error=str(e),
                error_type=type(e).__name__,
            )
        return False
