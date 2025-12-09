"""
Concrete content type strategies.

Implements specific strategies for different content types like blog, docs, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

from .base import ContentTypeStrategy

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


class BlogStrategy(ContentTypeStrategy):
    """Strategy for blog/news content with chronological ordering."""

    default_template = "blog/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by date (newest first)."""
        return sorted(pages, key=lambda p: p.date if p.date else datetime.min, reverse=True)

    def detect_from_section(self, section: Section) -> bool:
        """Detect blog sections by name or date-heavy content."""
        name = section.name.lower()

        # Check section name patterns
        if name in ("blog", "posts", "news", "articles"):
            return True

        # Check if most pages have dates
        if section.pages:
            pages_with_dates = sum(1 for p in section.pages[:5] if p.metadata.get("date") or p.date)
            return pages_with_dates >= len(section.pages[:5]) * 0.6

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Blog-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        # Helper to check template existence
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            try:
                template_engine.env.get_template(name)
                return True
            except Exception as e:
                logger.debug(
                    "template_check_failed",
                    template=name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False

        if is_home:
            # Try blog/home.html first
            if template_exists("blog/home.html"):
                return "blog/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "blog/list.html"
        else:
            return "blog/single.html"


class ArchiveStrategy(BlogStrategy):
    """
    Strategy for archive/chronological content.

    Similar to blog but uses simpler archive template.
    """

    default_template = "archive.html"


class DocsStrategy(ContentTypeStrategy):
    """Strategy for documentation with weight-based ordering."""

    default_template = "doc/list.html"
    allows_pagination = False  # Docs should not be paginated

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by weight, then title (keeps manual ordering)."""
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect docs sections by name."""
        name = section.name.lower()
        return name in ("docs", "documentation", "guides", "reference")

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Docs-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        # Helper to check template existence
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            try:
                template_engine.env.get_template(name)
                return True
            except Exception as e:
                logger.debug(
                    "template_check_failed",
                    template=name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False

        if is_home:
            # Try doc/home.html first
            if template_exists("doc/home.html"):
                return "doc/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "doc/list.html"
        else:
            return "doc/single.html"


class ApiReferenceStrategy(ContentTypeStrategy):
    """Strategy for API reference documentation."""

    default_template = "api-reference/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Keep original discovery order (alphabetical)."""
        return list(pages)  # No resorting

    def detect_from_section(self, section: Section) -> bool:
        """Detect API sections by name or content."""
        name = section.name.lower()

        if name in ("api", "reference", "api-reference", "api-docs"):
            return True

        # Check page metadata
        if section.pages:
            for page in section.pages[:3]:
                page_type = page.metadata.get("type", "")
                if "python-module" in page_type or "api-reference" in page_type:
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """API reference-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        # Helper to check template existence
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            try:
                template_engine.env.get_template(name)
                return True
            except Exception as e:
                logger.debug(
                    "template_check_failed",
                    template=name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False

        if is_home:
            # Try api-reference/home.html first
            if template_exists("api-reference/home.html"):
                return "api-reference/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "api-reference/list.html"
        else:
            return "api-reference/single.html"


class CliReferenceStrategy(ContentTypeStrategy):
    """Strategy for CLI reference documentation."""

    default_template = "cli-reference/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Keep original discovery order (alphabetical)."""
        return list(pages)

    def detect_from_section(self, section: Section) -> bool:
        """Detect CLI sections by name or content."""
        name = section.name.lower()

        if name in ("cli", "commands", "cli-reference", "command-line"):
            return True

        # Check page metadata
        if section.pages:
            for page in section.pages[:3]:
                page_type = page.metadata.get("type", "")
                if "cli-" in page_type or page_type == "command":
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """CLI reference-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        # Helper to check template existence
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            try:
                template_engine.env.get_template(name)
                return True
            except Exception as e:
                logger.debug(
                    "template_check_failed",
                    template=name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False

        if is_home:
            # Try cli-reference/home.html first
            if template_exists("cli-reference/home.html"):
                return "cli-reference/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "cli-reference/list.html"
        else:
            return "cli-reference/single.html"


class TutorialStrategy(ContentTypeStrategy):
    """Strategy for tutorial content."""

    default_template = "tutorial/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by weight (for sequential tutorials)."""
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect tutorial sections by name."""
        name = section.name.lower()
        return name in ("tutorials", "guides", "how-to")


class ChangelogStrategy(ContentTypeStrategy):
    """Strategy for changelog/release notes with chronological timeline."""

    default_template = "changelog/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by date (newest first) or by version number."""
        return sorted(pages, key=lambda p: p.date if p.date else datetime.min, reverse=True)

    def detect_from_section(self, section: Section) -> bool:
        """Detect changelog sections by name."""
        name = section.name.lower()
        return name in ("changelog", "releases", "release-notes", "releasenotes", "changes")


class PageStrategy(ContentTypeStrategy):
    """Default strategy for generic pages."""

    default_template = "index.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by weight, then title."""
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))
