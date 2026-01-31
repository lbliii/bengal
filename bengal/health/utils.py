"""
Shared utilities for health check validators.

This module extracts common patterns to reduce code duplication across validators.
All utilities are designed to be defensive and handle edge cases gracefully.

Utilities:
    iter_pages_with_output: Iterate pages with valid, existing output_path
    relative_path: Convert absolute path to project-relative for display
    get_section_pages: Safely get pages from section (handles .pages/.children)
    get_health_config: Safely retrieve health_check config values
    read_output_content: Safely read page output file content

Related:
    - bengal.health.validators: Validators that use these utilities
    - bengal.health.base: BaseValidator interface

"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


def iter_pages_with_output(
    site: SiteLike,
    *,
    limit: int | None = None,
    exclude_generated: bool = False,
) -> Iterator[Any]:
    """
    Iterate over pages with valid output_path that exists on disk.

    This is a common pattern in validators that need to inspect rendered output.
    Handles type narrowing and existence checks in one place.

    Args:
        site: Site instance containing pages
        limit: Maximum pages to yield (None for all)
        exclude_generated: Skip pages with _generated metadata

    Yields:
        Page objects with valid, existing output_path

    Example:
        >>> for page in iter_pages_with_output(site, limit=10):
        ...     content = page.output_path.read_text()

    """
    count = 0
    for page in site.pages:
        if exclude_generated and page.metadata.get("_generated"):
            continue
        output_path = getattr(page, "output_path", None)
        if output_path and hasattr(output_path, "exists") and output_path.exists():
            yield page
            count += 1
            if limit is not None and count >= limit:
                break


def relative_path(path: Path | str, root: Path) -> str:
    """
    Convert absolute path to project-relative path for display.

    Used consistently across validators for error messages and reports.
    Falls back to original path string if conversion fails.

    Args:
        path: Absolute path to convert
        root: Project root to make path relative to

    Returns:
        Relative path string, or original if conversion fails

    Example:
        >>> relative_path("/project/content/page.md", Path("/project"))
        "content/page.md"

    """
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return str(path)


def get_section_pages(section: Any) -> list[Any]:
    """
    Get pages from a section, handling both .pages and .children attributes.

    Supports both full Section objects and lightweight test mocks that may
    use `children` instead of `pages`.

    Args:
        section: Section-like object

    Returns:
        List of pages in the section (empty list if none found)

    Example:
        >>> pages = get_section_pages(section)
        >>> for page in pages:
        ...     validate(page)

    """
    return getattr(section, "pages", getattr(section, "children", []))


def get_health_config(site: SiteLike, key: str, default: Any = None) -> Any:
    """
    Safely get a value from health_check config section.

    Handles both dict-based and object-based config access patterns,
    and gracefully handles missing or malformed config.

    Args:
        site: Site instance with config
        key: Config key to retrieve from health_check section
        default: Default value if key not found

    Returns:
        Config value or default

    Example:
        >>> threshold = get_health_config(site, "orphan_threshold", 5)
        >>> verbose = get_health_config(site, "verbose", False)

    """
    health_config = site.config.get("health_check", {})
    if isinstance(health_config, dict):
        return health_config.get(key, default)
    # Object-style config access
    return getattr(health_config, key, default)


def read_output_content(page: Any, encoding: str = "utf-8") -> str | None:
    """
    Safely read output file content with error handling.

    Common pattern for validators that inspect rendered HTML output.
    Returns None on any error (missing file, encoding issues, etc.).

    Args:
        page: Page with output_path attribute
        encoding: File encoding (default utf-8)

    Returns:
        File content as string, or None if read fails

    Example:
        >>> content = read_output_content(page)
        >>> if content:
        ...     check_html_structure(content)

    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None
    try:
        return output_path.read_text(encoding=encoding)
    except Exception:
        return None


def sample_pages(
    site: SiteLike,
    count: int = 10,
    *,
    exclude_generated: bool = False,
    require_output: bool = True,
) -> list[Any]:
    """
    Get a sample of pages for validation checks.

    Many validators only need to check a subset of pages (e.g., first 10)
    for performance. This utility standardizes that sampling.

    Args:
        site: Site instance containing pages
        count: Maximum pages to return
        exclude_generated: Skip pages with _generated metadata
        require_output: Only include pages with existing output_path

    Returns:
        List of up to `count` pages matching criteria

    Example:
        >>> pages = sample_pages(site, count=10, exclude_generated=True)
        >>> for page in pages:
        ...     validate_seo(page)

    """
    if require_output:
        return list(
            iter_pages_with_output(site, limit=count, exclude_generated=exclude_generated)
        )

    result = []
    for page in site.pages:
        if exclude_generated and page.metadata.get("_generated"):
            continue
        result.append(page)
        if len(result) >= count:
            break
    return result


__all__ = [
    "get_health_config",
    "get_section_pages",
    "iter_pages_with_output",
    "read_output_content",
    "relative_path",
    "sample_pages",
]
