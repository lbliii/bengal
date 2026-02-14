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

from typing import TYPE_CHECKING

from .base import ContentTypeStrategy
from .utils import (
    date_key,
    has_dated_pages,
    has_page_type_metadata,
    section_name_matches,
    weight_title_key,
)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.protocols import SectionLike


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
        return sorted(pages, key=date_key, reverse=True)

    def detect_from_section(self, section: SectionLike) -> bool:
        """
        Detect blog sections by name patterns or date-heavy content.

        Returns True if section name is a blog pattern or if >60% of pages
        (sampled from first 5) have date metadata.
        """
        if section_name_matches(section, ("blog", "posts", "news", "articles")):
            return True
        return has_dated_pages(section, threshold=0.6, sample_size=5)


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
        return sorted(pages, key=weight_title_key)

    def detect_from_section(self, section: SectionLike) -> bool:
        """Detect documentation sections by common naming patterns."""
        return section_name_matches(section, ("docs", "documentation", "guides", "reference"))


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

    def detect_from_section(self, section: SectionLike) -> bool:
        """
        Detect API sections by name patterns or autodoc page metadata.

        Checks section name for API patterns and samples page metadata for
        autodoc type indicators.
        """
        if section_name_matches(section, ("api", "reference", "autodoc-python", "api-docs")):
            return True
        return has_page_type_metadata(
            section,
            ("python-module", "autodoc-python", "autodoc-rest"),
            sample_size=3,
            substring_match=True,
        )

    def _get_extra_template_prefixes(self) -> list[str] | None:
        """Include autodoc/ templates in cascade."""
        return ["autodoc"]


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

    def detect_from_section(self, section: SectionLike) -> bool:
        """
        Detect CLI sections by name patterns or command page metadata.

        Checks section name for CLI patterns and samples page metadata for
        command type indicators.
        """
        if section_name_matches(section, ("cli", "commands", "autodoc-cli", "command-line")):
            return True
        return has_page_type_metadata(
            section,
            ("cli-", "command"),
            sample_size=3,
            substring_match=True,
        )

    def _get_extra_template_prefixes(self) -> list[str] | None:
        """Include autodoc/ templates in cascade."""
        return ["autodoc"]


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
        return sorted(pages, key=weight_title_key)

    def detect_from_section(self, section: SectionLike) -> bool:
        """Detect tutorial sections by common naming patterns."""
        return section_name_matches(section, ("tutorials", "guides", "how-to"))


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
            key=lambda p: (date_key(p), p.title),
            reverse=True,
        )

    def detect_from_section(self, section: SectionLike) -> bool:
        """Detect changelog sections by common naming patterns."""
        return section_name_matches(
            section, ("changelog", "releases", "release-notes", "releasenotes", "changes")
        )


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
        return sorted(pages, key=weight_title_key)

    def detect_from_section(self, section: SectionLike) -> bool:
        """Detect track sections by exact name match."""
        return section_name_matches(section, ("tracks",))


class NotebookStrategy(ContentTypeStrategy):
    """
    Strategy for Jupyter notebook content.

    Notebooks are sorted by weight then title (like docs). Uses a dedicated
    notebook template with download badge, kernel info, and cell styling.

    Auto-Detection:
        Detected when section name matches notebook patterns
        (``notebooks``, ``notebook``, ``examples``).

    Sorting:
        Pages sorted by ``weight`` (ascending), then title alphabetically.

    Templates:
        - Single: ``notebook/single.html``

    Class Attributes:
        default_template: ``"notebook/single.html"``
        allows_pagination: ``False``

    """

    default_template = "notebook/single.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort notebook pages by weight, then title."""
        return sorted(pages, key=weight_title_key)

    def detect_from_section(self, section: SectionLike) -> bool:
        """Detect notebook sections by common naming patterns."""
        return section_name_matches(section, ("notebooks", "notebook", "examples"))


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
        return sorted(pages, key=weight_title_key)
