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
    - get_page_relative_url: Get URL without baseurl (for objectID/search index)
    - get_page_url: Get full public URL with baseurl
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

import hashlib
import re
from typing import TYPE_CHECKING

from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_normalization import normalize_url as _normalize_url_base
from bengal.utils.primitives.text import normalize_whitespace
from bengal.utils.primitives.text import strip_html as _strip_html_base

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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


def get_page_url(page: PageLike, site: SiteLike) -> str:
    """
    Get the public URL for a page (includes baseurl).

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl

    """
    # page.href already includes baseurl
    return page.href


def get_page_output_path(page: PageLike, ext: str) -> Path | None:
    """
    Get the output path for a page's companion file with the given extension.

    For index.html pages, returns index.{ext} in the same directory.
    For other pages (page.html), returns page.{ext} with suffix swapped.

    Args:
        page: Page to get output path for
        ext: File extension without dot (e.g., "json", "txt", "md")

    Returns:
        Path for the companion file, or None if output_path not available

    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None

    # Handle invalid output paths (e.g., Path('.'))
    if str(output_path) in (".", "..") or output_path.name == "":
        return None

    if output_path.name == "index.html":
        return output_path.parent / f"index.{ext}"

    return output_path.with_suffix(f".{ext}")


def get_page_json_path(page: PageLike) -> Path | None:
    """Get the output path for a page's JSON file."""
    return get_page_output_path(page, "json")


def get_page_txt_path(page: PageLike) -> Path | None:
    """Get the output path for a page's TXT file."""
    return get_page_output_path(page, "txt")


def get_page_md_path(page: PageLike) -> Path | None:
    """Get the output path for a page's Markdown file."""
    return get_page_output_path(page, "md")


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
    write_fn: Callable[[Path, T], bool | None],
    max_workers: int = 8,
    operation_name: str = "file_write",
) -> int:
    """
    Write files in parallel using ThreadPoolExecutor.

    Handles graceful shutdown during interpreter exit and provides
    consistent error handling across all generators.

    Args:
        items: List of (path, content) tuples to write
        write_fn: Function that takes (path, content) and writes the file.
            Return False to mark an unchanged file as skipped; return None for
            backward-compatible "written successfully" behavior.
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
            written = write_fn(path, content)
            return True if written is None else written
        except Exception as e:
            logger.warning(
                f"{operation_name}_failed",
                path=str(path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    from bengal.utils.concurrency.work_scope import WorkScope

    with WorkScope("FileWrite", max_workers=max_workers) as scope:
        results = scope.map(safe_write, items)

    count = sum(1 for r in results if r.ok and r.value)
    return count


def write_text_if_changed(path: Path, content: str) -> bool:
    """
    Write text atomically only when the existing file differs.

    This avoids rewriting unchanged per-page output-format files during serve
    rebuilds without creating public sidecar hash files for every page.

    Args:
        path: Output file path.
        content: Text content to write.

    Returns:
        True if the file was written, False if the existing content matched.
    """
    try:
        if path.exists() and path.read_text(encoding="utf-8") == content:
            logger.debug(
                "write_skipped_unchanged",
                path=str(path),
                reason="content_unchanged",
            )
            return False
    except OSError as e:
        logger.debug(
            "existing_output_read_failed",
            path=str(path),
            error=str(e),
            error_type=type(e).__name__,
            action="proceeding_to_write",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with AtomicFile(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def extract_heading_chunks(
    html_content: str,
    toc_items: list[dict[str, str | int]],
    page_url: str,
) -> list[dict[str, str | int]]:
    """
    Split HTML content by heading boundaries into chunks with anchors.

    Uses toc_items (id, title, level) to split at <h[2-6] id="..."> boundaries,
    strips HTML per segment, and returns chunks with anchor URLs for citation.

    Args:
        html_content: Rendered HTML with heading tags
        toc_items: List of {id, title, level} from page.toc_items
        page_url: Base URL for anchor links (e.g. /docs/install/)

    Returns:
        List of chunks with anchor, title, level, content, content_hash

    Example:
        >>> chunks = extract_heading_chunks(html, toc_items, "/docs/install/")
        >>> chunks[0]["anchor"]
        'installation'
        >>> chunks[0]["content_hash"]
        'f3a1...'
    """
    if not html_content:
        return []

    base_url = page_url.rstrip("/") if page_url else ""
    chunks: list[dict[str, str | int]] = []
    # Build regex to split at h2-h6 with an id attribute in any position,
    # supporting both single- and double-quoted HTML attributes.
    heading_pattern = re.compile(
        r"""<h([2-6])\b[^>]*\bid\s*=\s*["']([^"']+)["'][^>]*>""",
        re.IGNORECASE,
    )

    # Find all heading positions (level, id, start_pos)
    matches = list(heading_pattern.finditer(html_content))
    if not matches:
        # No headings with ids - treat whole content as one chunk
        plain = strip_html(html_content)
        if plain.strip():
            content_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "anchor": "",
                    "anchor_url": base_url or "",
                    "title": "",
                    "level": 1,
                    "content": plain.strip(),
                    "content_hash": content_hash,
                }
            )
        return chunks

    # Map toc_items by id for title/level lookup
    toc_by_id: dict[str, dict[str, str | int]] = {
        str(item.get("id", "")): item for item in toc_items if item.get("id")
    }

    # Capture content before the first heading as an intro chunk
    first_match_start = matches[0].start()
    if first_match_start > 0:
        intro_segment = html_content[:first_match_start]
        intro_plain = strip_html(intro_segment).strip()
        if intro_plain:
            content_hash = hashlib.sha256(intro_plain.encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "anchor": "",
                    "anchor_url": base_url or "",
                    "title": "",
                    "level": 1,
                    "content": intro_plain,
                    "content_hash": content_hash,
                }
            )

    for i, match in enumerate(matches):
        level_num = int(match.group(1))
        anchor_id = match.group(2)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html_content)
        segment = html_content[start:end]
        plain = strip_html(segment).strip()

        toc_item = toc_by_id.get(anchor_id, {})
        title = str(toc_item.get("title", ""))
        level = int(toc_item.get("level", level_num))

        anchor_url = f"{base_url}#{anchor_id}" if base_url else f"#{anchor_id}"
        content_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
        chunks.append(
            {
                "anchor": anchor_id,
                "anchor_url": anchor_url,
                "title": title,
                "level": level,
                "content": plain,
                "content_hash": content_hash,
            }
        )

    return chunks


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
