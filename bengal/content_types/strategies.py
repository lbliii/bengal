"""
Concrete content type strategies.

This module provides concrete implementations of ContentTypeStrategy for
Bengal's built-in content types. Each strategy encapsulates type-specific
behavior for sorting, filtering, pagination, and template selection.

Built-in Strategies:
    - BlogStrategy: Chronological blog posts (newest first, paginated)
    - ArchiveStrategy: Archive pages (similar to blog, simpler template)
    - DocsStrategy: Documentation pages (weight-sorted, no pagination)
    - ApiReferenceStrategy: Python API reference (autodoc-python)
    - CliReferenceStrategy: CLI command reference (autodoc-cli)
    - TutorialStrategy: Step-by-step tutorials (weight-sorted)
    - ChangelogStrategy: Release notes and changelogs (date-sorted)
    - TrackStrategy: Learning tracks (weight-sorted)
    - PageStrategy: Generic pages (default fallback)

Strategy Selection:
    Content types are typically set in section ``_index.md`` frontmatter:

    .. code-block:: yaml

        ---
        content_type: blog
        ---

    Alternatively, auto-detection uses ``detect_from_section()`` heuristics.

Example:
    >>> from bengal.content_types.strategies import BlogStrategy
    >>> strategy = BlogStrategy()
    >>> sorted_posts = strategy.sort_pages(section.pages)
    >>> template = strategy.get_template(page, template_engine)

Related:
    - bengal/content_types/base.py: ContentTypeStrategy base class
    - bengal/content_types/registry.py: Strategy registration and lookup
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
    """
    Strategy for blog/news content with chronological ordering.

    Optimized for time-based content like blog posts, news articles, and
    announcements. Pages are sorted by date (newest first) and pagination
    is enabled by default for long lists.

    Auto-Detection:
        Detected when section name matches blog patterns (``blog``, ``posts``,
        ``news``, ``articles``) or when >60% of pages have date metadata.

    Templates:
        - Home: ``blog/home.html`` → ``home.html`` → ``index.html``
        - List: ``blog/list.html``
        - Single: ``blog/single.html``

    Class Attributes:
        default_template: ``"blog/list.html"``
        allows_pagination: ``True``
    """

    default_template = "blog/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages by date, newest first.

        Pages without dates are sorted to the end (using ``datetime.min``).
        """
        return sorted(pages, key=lambda p: p.date if p.date else datetime.min, reverse=True)

    def detect_from_section(self, section: Section) -> bool:
        """
        Detect blog sections by name patterns or date-heavy content.

        Returns True if section name is a blog pattern or if >60% of pages
        (sampled from first 5) have date metadata.
        """
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

        is_home = page.is_home or page._path == "/"
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

    Inherits chronological sorting from BlogStrategy but uses a simpler
    archive template. Suitable for date-based archives, historical records,
    or simplified blog views.

    Templates:
        Uses ``archive.html`` as the default template.

    Class Attributes:
        default_template: ``"archive.html"``
        allows_pagination: ``True`` (inherited from BlogStrategy)
    """

    default_template = "archive.html"


class DocsStrategy(ContentTypeStrategy):
    """
    Strategy for documentation with weight-based ordering.

    Optimized for structured documentation where page order is manually
    controlled via ``weight`` frontmatter. Pagination is disabled since
    documentation sections typically show all pages in a structured nav.

    Auto-Detection:
        Detected when section name matches documentation patterns
        (``docs``, ``documentation``, ``guides``, ``reference``).

    Sorting:
        Pages sorted by ``weight`` (ascending), then title (alphabetical).
        Use ``weight`` in frontmatter to control order:

        .. code-block:: yaml

            ---
            title: Getting Started
            weight: 10
            ---

    Templates:
        - Home: ``doc/home.html`` → ``home.html`` → ``index.html``
        - List: ``doc/list.html``
        - Single: ``doc/single.html``

    Class Attributes:
        default_template: ``"doc/list.html"``
        allows_pagination: ``False``
    """

    default_template = "doc/list.html"
    allows_pagination = False  # Docs should not be paginated

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages by weight, then title alphabetically.

        Pages without explicit weight default to 999999 (sorted last).
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect documentation sections by common naming patterns."""
        name = section.name.lower()
        return name in ("docs", "documentation", "guides", "reference")

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """Docs-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page._path == "/"
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
    """
    Strategy for Python API reference documentation.

    Designed for auto-generated API documentation (autodoc) from Python
    source code. Preserves alphabetical discovery order and uses specialized
    API reference templates.

    Auto-Detection:
        Detected when section name matches API patterns (``api``, ``reference``,
        ``autodoc-python``, ``api-docs``) or when pages have ``python-module``
        or ``autodoc-python`` type metadata.

    Sorting:
        Preserves original discovery order (typically alphabetical by module).

    Templates:
        - Home: ``autodoc/python/home.html``
        - List: ``autodoc/python/list.html``
        - Single: ``autodoc/python/single.html``

    Class Attributes:
        default_template: ``"autodoc/python/list.html"``
        allows_pagination: ``False``

    See Also:
        - bengal/autodoc/: Python autodoc generation
    """

    default_template = "autodoc/python/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Preserve original discovery order (typically alphabetical).

        API reference pages are usually discovered in module alphabetical order,
        which is the desired display order.
        """
        return list(pages)  # No resorting

    def detect_from_section(self, section: Section) -> bool:
        """
        Detect API sections by name patterns or autodoc page metadata.

        Checks section name for API patterns and samples page metadata for
        autodoc type indicators.
        """
        name = section.name.lower()

        if name in ("api", "reference", "autodoc-python", "api-docs"):
            return True

        # Check page metadata
        if section.pages:
            for page in section.pages[:3]:
                page_type = page.metadata.get("type", "")
                if "python-module" in page_type or page_type in (
                    "autodoc-python",
                    "autodoc-rest",
                ):
                    return True

        return False

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """API reference-specific template selection."""
        # Backward compatibility
        if page is None:
            return self.default_template

        is_home = page.is_home or page._path == "/"
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
            # Try autodoc/python/home.html first
            if template_exists("autodoc/python/home.html"):
                return "autodoc/python/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "autodoc/python/list.html"
        else:
            return "autodoc/python/single.html"


class CliReferenceStrategy(ContentTypeStrategy):
    """
    Strategy for CLI command reference documentation.

    Designed for auto-generated CLI documentation showing commands, arguments,
    and options. Preserves alphabetical discovery order and uses specialized
    CLI reference templates.

    Auto-Detection:
        Detected when section name matches CLI patterns (``cli``, ``commands``,
        ``autodoc-cli``, ``command-line``) or when pages have CLI-related
        type metadata.

    Sorting:
        Preserves original discovery order (typically alphabetical by command).

    Templates:
        - Home: ``autodoc/cli/home.html``
        - List: ``autodoc/cli/list.html``
        - Single: ``autodoc/cli/single.html``

    Class Attributes:
        default_template: ``"autodoc/cli/list.html"``
        allows_pagination: ``False``

    See Also:
        - bengal/autodoc/: CLI autodoc generation
    """

    default_template = "autodoc/cli/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Preserve original discovery order (typically alphabetical).

        CLI commands are usually discovered in alphabetical order, which is
        the desired display order.
        """
        return list(pages)

    def detect_from_section(self, section: Section) -> bool:
        """
        Detect CLI sections by name patterns or command page metadata.

        Checks section name for CLI patterns and samples page metadata for
        command type indicators.
        """
        name = section.name.lower()

        if name in ("cli", "commands", "autodoc-cli", "command-line"):
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

        is_home = page.is_home or page._path == "/"
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
            # Try autodoc/cli/home.html first
            if template_exists("autodoc/cli/home.html"):
                return "autodoc/cli/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "autodoc/cli/list.html"
        else:
            return "autodoc/cli/single.html"


class TutorialStrategy(ContentTypeStrategy):
    """
    Strategy for tutorial/how-to content.

    Optimized for step-by-step learning content where order matters. Pages
    are sorted by weight to maintain sequential flow through tutorials.

    Auto-Detection:
        Detected when section name matches tutorial patterns
        (``tutorials``, ``guides``, ``how-to``).

    Sorting:
        Pages sorted by ``weight`` (ascending), then title. Use ``weight``
        to control tutorial sequence:

        .. code-block:: yaml

            ---
            title: Step 1 - Setup
            weight: 10
            ---

    Templates:
        - List: ``tutorial/list.html``
        - Single: (inherits from base strategy)

    Class Attributes:
        default_template: ``"tutorial/list.html"``
        allows_pagination: ``False``
    """

    default_template = "tutorial/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages by weight for sequential tutorial ordering.

        Tutorial steps should have explicit weights to ensure correct order.
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect tutorial sections by common naming patterns."""
        name = section.name.lower()
        return name in ("tutorials", "guides", "how-to")


class ChangelogStrategy(ContentTypeStrategy):
    """
    Strategy for changelog/release notes with chronological timeline.

    Designed for version history and release notes where entries are
    organized by release date. Shows newest releases first.

    Auto-Detection:
        Detected when section name matches changelog patterns
        (``changelog``, ``releases``, ``release-notes``, ``releasenotes``, ``changes``).

    Sorting:
        Pages sorted by date (newest first), then title descending for
        same-day releases (e.g., v1.1.0 before v1.0.1 on same day).

    Templates:
        - List: ``changelog/list.html``
        - Single: (inherits from base strategy)

    Class Attributes:
        default_template: ``"changelog/list.html"``
        allows_pagination: ``False``
    """

    default_template = "changelog/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort releases by date (newest first), then title descending.

        Same-day releases are sorted by title descending (v1.1.0 before v1.0.1).
        """
        return sorted(
            pages,
            key=lambda p: (p.date if p.date else datetime.min, p.title),
            reverse=True,
        )

    def detect_from_section(self, section: Section) -> bool:
        """Detect changelog sections by common naming patterns."""
        name = section.name.lower()
        return name in ("changelog", "releases", "release-notes", "releasenotes", "changes")


class TrackStrategy(ContentTypeStrategy):
    """
    Strategy for learning track content.

    Designed for structured learning paths or course-like content where
    users progress through a sequence of lessons or modules. Pages are
    sorted by weight to maintain learning sequence.

    Auto-Detection:
        Detected when section name is exactly ``tracks``.

    Sorting:
        Pages sorted by ``weight`` (ascending), then title alphabetically.

    Templates:
        - List: ``tracks/list.html``
        - Single: ``tracks/single.html``

    Class Attributes:
        default_template: ``"tracks/list.html"``
        allows_pagination: ``False``
    """

    default_template = "tracks/list.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort track pages by weight for sequential learning order.

        Learning modules should have explicit weights to ensure correct
        progression through the track.
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def detect_from_section(self, section: Section) -> bool:
        """Detect track sections by exact name match."""
        name = section.name.lower()
        return name == "tracks"

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """
        Track-specific template selection.

        Uses dedicated track templates without fallback chain since tracks
        have specific layout requirements.
        """
        # Backward compatibility
        if page is None:
            return self.default_template

        is_section_index = page.source_path.stem == "_index"

        if is_section_index:
            return "tracks/list.html"
        else:
            return "tracks/single.html"


class PageStrategy(ContentTypeStrategy):
    """
    Default strategy for generic pages.

    The fallback strategy used when no specific content type is detected
    or configured. Provides sensible defaults for miscellaneous content.

    Sorting:
        Pages sorted by ``weight`` (ascending), then title alphabetically.

    Templates:
        Uses base strategy template resolution with ``index.html`` as fallback.

    Class Attributes:
        default_template: ``"index.html"``
        allows_pagination: ``False``

    Note:
        This strategy is also registered as ``"list"`` for generic section
        listings that don't fit other content types.
    """

    default_template = "index.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages by weight, then title alphabetically.

        Default ordering for generic pages without specialized requirements.
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))
