"""
Shared utilities for output format generation.

Provides common functions used across all output format generators
including text processing, URL handling, path resolution, content
normalization, and parallel I/O operations. These utilities ensure
consistent behavior across JSON, TXT, index, and LLM text generators.

Functions:
Text Processing:
    - strip_html: Remove HTML tags and normalize whitespace
    - generate_excerpt: Create truncated preview text

URL Handling:
    - get_page_relative_url: Get URL without baseurl (for objectID)
    - get_page_public_url: Get full URL with baseurl
    - get_page_url: Alias for get_page_public_url
    - normalize_url: Normalize URL for consistent comparison

Path Resolution:
    - get_page_json_path: Get output path for page's JSON file
    - get_page_txt_path: Get output path for page's TXT file
    - get_i18n_output_path: Get output path with i18n prefix handling

I/O Operations:
    - parallel_write_files: Write files in parallel with ThreadPoolExecutor
    - write_if_content_changed: Hash-based change detection for writes

Implementation Notes:
Text utilities delegate to bengal.utils.text for DRY compliance.
URL utilities work with Page._path (internal path) and Page.href
(public URL) to avoid baseurl duplication issues.

Example:
    >>> from bengal.postprocess.output_formats.utils import (
    ...     generate_excerpt,
    ...     get_page_json_path,
    ...     get_page_url,
    ...     get_i18n_output_path,
    ...     parallel_write_files,
    ... )
    >>>
    >>> excerpt = generate_excerpt(page.plain_text, length=200)
    >>> json_path = get_page_json_path(page)
    >>> url = get_page_url(page, site)
    >>> index_path = get_i18n_output_path(site, "index.json")

Related:
- bengal.utils.text: Canonical text processing utilities
- bengal.postprocess.output_formats: Output format generators

"""

from __future__ import annotations

import concurrent.futures
import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_normalization import normalize_url as _normalize_url_base
from bengal.utils.primitives.text import normalize_whitespace
from bengal.utils.primitives.text import strip_html as _strip_html_base

logger = get_logger(__name__)

T = TypeVar("T")

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike


def strip_html(text: str) -> str:
    """
    Remove HTML tags from text and normalize whitespace.

    Delegates to bengal.utils.text.strip_html with additional whitespace
    normalization specific to output format generation.

    Args:
        text: HTML text

    Returns:
        Plain text with HTML tags, entities, and excess whitespace removed

    """
    if not text:
        return ""

    # Use canonical implementation for tag stripping and entity decoding
    text = _strip_html_base(text, decode_entities=True)

    # Normalize whitespace (specific to output formats - collapse to single space)
    return normalize_whitespace(text, collapse=True)


def generate_excerpt(text: str, length: int = 200) -> str:
    """
    Generate excerpt from text using character-based truncation.

    Note: This uses character-based truncation for backward compatibility
    with output format generation. For word-based truncation, use
    bengal.utils.text.generate_excerpt directly.

    Args:
        text: Source text (may contain HTML)
        length: Maximum character length

    Returns:
        Excerpt string, truncated at word boundary with ellipsis

    """
    if not text:
        return ""

    # Strip HTML first
    text = strip_html(text)

    if len(text) <= length:
        return text

    # Find last space before limit (preserve word boundary)
    excerpt = text[:length].rsplit(" ", 1)[0]
    return excerpt + "..."


def get_page_relative_url(page: PageLike, site: SiteLike) -> str:
    """
    Get clean relative URL for page (without baseurl).

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Relative URL string (without baseurl)

    """
    # Use _path (internal path without baseurl)
    return page._path


def get_page_public_url(page: PageLike, site: SiteLike) -> str:
    """
    Get the page's public URL including baseurl.

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl

    """
    # page.href already includes baseurl
    return page.href


def get_page_url(page: PageLike, site: SiteLike) -> str:
    """
    Get the public URL for a page.

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl

    """
    # page.href already includes baseurl
    return page.href


def get_page_json_path(page: PageLike) -> Path | None:
    """
    Get the output path for a page's JSON file.

    Args:
        page: Page to get JSON path for

    Returns:
        Path for the JSON file, or None if output_path not available

    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None

    # Handle invalid output paths (e.g., Path('.'))
    if str(output_path) in (".", "..") or output_path.name == "":
        return None

    # If output is index.html, put index.json next to it
    if output_path.name == "index.html":
        return output_path.parent / "index.json"

    # If output is page.html, put page.json next to it
    return output_path.with_suffix(".json")


def get_page_txt_path(page: PageLike) -> Path | None:
    """
    Get the output path for a page's TXT file.

    Args:
        page: Page to get TXT path for

    Returns:
        Path for the TXT file, or None if output_path not available

    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None

    # Handle invalid output paths (e.g., Path('.'))
    if str(output_path) in (".", "..") or output_path.name == "":
        return None

    # If output is index.html, put index.txt next to it
    if output_path.name == "index.html":
        return output_path.parent / "index.txt"

    # If output is page.html, put page.txt next to it
    return output_path.with_suffix(".txt")


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent comparison (strips trailing slashes).

    Uses the canonical normalize_url with ensure_trailing_slash=False
    for URL matching/comparison purposes.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL without trailing slash (except for root "/")

    """
    if not url:
        return ""
    url = url.strip()
    # Use canonical implementation without trailing slash for comparison
    normalized = _normalize_url_base(url, ensure_trailing_slash=False)
    # For consistency with original behavior, return empty for empty input
    # (canonical returns "/" for empty, but this is filtered in usage anyway)
    return normalized


def get_i18n_output_path(site: SiteLike, filename: str) -> Path:
    """
    Get output path with i18n prefix handling.

    When i18n strategy is "prefix" and the current language requires a
    subdirectory, returns path under the language prefix. Otherwise
    returns path directly under output_dir.

    Args:
        site: Site instance with config and output_dir
        filename: Output filename (e.g., "index.json", "search-index.json")

    Returns:
        Path to the output file, with i18n prefix if applicable

    Example:
        >>> # Non-i18n or default language without subdir
        >>> get_i18n_output_path(site, "index.json")
        Path("/output/index.json")
        >>>
        >>> # i18n prefix strategy with non-default language
        >>> get_i18n_output_path(site, "index.json")
        Path("/output/es/index.json")

    """
    i18n = site.config.get("i18n", {}) or {}

    if i18n.get("strategy") == "prefix":
        default_lang = i18n.get("default_language", "en")
        current_lang = getattr(site, "current_language", None) or default_lang
        default_in_subdir = bool(i18n.get("default_in_subdir", False))

        # Put in language subdir if: non-default language OR default_in_subdir is True
        if default_in_subdir or current_lang != default_lang:
            return site.output_dir / current_lang / filename

    return site.output_dir / filename


def parallel_write_files[T](
    items: list[tuple[Path, T]],
    write_fn: Callable[[Path, T], None],
    max_workers: int = 8,
    operation_name: str = "file_write",
) -> int:
    """
    Write files in parallel using ThreadPoolExecutor.

    Handles graceful shutdown during interpreter exit and provides
    consistent error handling across all generators.

    Args:
        items: List of (path, content) tuples to write
        write_fn: Function that takes (path, content) and writes the file
        max_workers: Maximum parallel workers (default: 8)
        operation_name: Name for logging purposes

    Returns:
        Number of files successfully written

    Example:
        >>> def write_json(path: Path, data: dict) -> None:
        ...     path.parent.mkdir(parents=True, exist_ok=True)
        ...     with AtomicFile(path, "w") as f:
        ...         json.dump(data, f)
        >>>
        >>> items = [(Path("a.json"), {"a": 1}), (Path("b.json"), {"b": 2})]
        >>> count = parallel_write_files(items, write_json)

    Note:
        The write_fn should handle directory creation and use atomic writes.
        Exceptions in write_fn are caught and logged, not propagated.

    """
    if not items:
        return 0

    def safe_write(item: tuple[Path, T]) -> bool:
        path, content = item
        try:
            write_fn(path, content)
            return True
        except Exception as e:
            logger.warning(
                f"{operation_name}_failed",
                path=str(path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    count = 0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Consume iterator fully before exiting context manager
            # This ensures all tasks complete and exceptions are raised properly
            results = list(executor.map(safe_write, items))
            count = sum(1 for r in results if r)
    except RuntimeError as e:
        # Handle graceful shutdown - "cannot schedule new futures after interpreter shutdown"
        if "interpreter shutdown" in str(e):
            logger.debug(f"{operation_name}_shutdown", reason="interpreter_shutting_down")
            return count
        raise

    return count


def write_if_content_changed(
    path: Path,
    content: str,
    hash_suffix: str = ".hash",
) -> bool:
    """
    Write file only if content hash has changed.

    Uses SHA-256 hash comparison to avoid unnecessary writes:
    - O(1) hash comparison vs O(n) string comparison
    - Avoids reading entire existing file into memory
    - Hash stored in sidecar file (e.g., file.json.hash)

    Args:
        path: Output file path
        content: Content to write
        hash_suffix: Suffix for hash sidecar file (default: ".hash")

    Returns:
        True if file was written (content changed), False if skipped

    Example:
        >>> changed = write_if_content_changed(
        ...     Path("index.json"),
        ...     json.dumps(data),
        ... )
        >>> if changed:
        ...     logger.info("Index updated")

    Note:
        Both content file and hash file are written atomically to
        prevent inconsistent state on crash.

    """
    # Compute hash of new content
    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Determine hash file path
    hash_path = path.parent / f"{path.name}{hash_suffix}"

    # Check if content unchanged via hash comparison
    try:
        if hash_path.exists():
            existing_hash = hash_path.read_text(encoding="utf-8").strip()
            if existing_hash == new_hash:
                logger.debug(
                    "write_skipped_unchanged",
                    path=str(path),
                    reason="content_hash_unchanged",
                )
                return False
    except Exception as e:
        # Hash check failed, proceed to write
        logger.debug(
            "hash_check_failed",
            path=str(hash_path),
            error=str(e),
            error_type=type(e).__name__,
            action="proceeding_to_write",
        )

    # Write content and hash atomically
    path.parent.mkdir(parents=True, exist_ok=True)
    with AtomicFile(path, "w", encoding="utf-8") as f:
        f.write(content)
    with AtomicFile(hash_path, "w", encoding="utf-8") as f:
        f.write(new_hash)

    return True
