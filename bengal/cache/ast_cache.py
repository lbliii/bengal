"""
AST disk cache for Patitas Document ASTs.

Enables incremental ``bengal build`` by persisting parsed ASTs to the build
cache. On subsequent builds, unchanged files load their AST from cache
and skip parsing entirely.

Usage in the parsing phase:
    # Before parsing: try loading from cache
    loaded = load_ast_from_cache(build_cache, page, site_root)
    if loaded:
        page._ast_cache = loaded
        # Still need html_content from snapshot cache, but AST is ready

    # After parsing: save to cache
    save_ast_to_cache(build_cache, page, site_root)

Thread Safety:
    Each function operates on a build cache instance and page objects that
    should not be shared across threads without synchronization.

"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page

logger = get_logger(__name__)


def _page_cache_key(page: Page, site_root: Path) -> str:
    """Compute the cache key for a page's AST."""
    try:
        return str(page.source_path.relative_to(site_root))
    except ValueError:
        return str(page.source_path)


def _content_hash(content: str) -> str:
    """Compute a short content hash for cache validity."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def save_ast_to_cache(
    build_cache: BuildCache,
    page: Page,
    site_root: Path,
) -> bool:
    """Save a page's Patitas Document AST to the build cache.

    Serializes the AST to JSON and stores it alongside the content hash
    for cache validity checking on subsequent builds.

    Args:
        build_cache: The build cache instance
        page: Page with a populated _ast_cache
        site_root: Site root path for relative key computation

    Returns:
        True if saved successfully, False otherwise
    """
    ast = getattr(page, "_ast_cache", None)
    if ast is None:
        return False

    try:
        from patitas.serialization import to_json

        key = _page_cache_key(page, site_root)
        content = getattr(page, "_raw_content", "") or ""
        c_hash = _content_hash(content)
        ast_json = to_json(ast)

        build_cache.ast_cache[key] = {
            "content_hash": c_hash,
            "ast_json": ast_json,
        }
        return True
    except Exception:
        return False


def load_ast_from_cache(
    build_cache: BuildCache,
    page: Page,
    site_root: Path,
) -> Any | None:
    """Load a page's Patitas Document AST from the build cache.

    Checks the content hash to ensure the cached AST matches the current
    page content. If the hash matches, deserializes and returns the AST.

    Args:
        build_cache: The build cache instance
        page: Page to load AST for
        site_root: Site root path for relative key computation

    Returns:
        Patitas Document AST if cache hit, None otherwise
    """
    try:
        from patitas.serialization import from_json
    except ImportError:
        return None

    key = _page_cache_key(page, site_root)
    cached = build_cache.ast_cache.get(key)
    if cached is None:
        return None

    # Verify content hash matches
    content = getattr(page, "_raw_content", "") or ""
    c_hash = _content_hash(content)
    if cached.get("content_hash") != c_hash:
        return None

    # Deserialize the AST
    try:
        ast_json = cached.get("ast_json", "")
        if not ast_json:
            return None
        return from_json(ast_json)
    except Exception:
        return None


def load_asts_for_pages(
    build_cache: BuildCache,
    pages: list[Page],
    site_root: Path,
) -> int:
    """Batch-load cached ASTs for multiple pages.

    Sets page._ast_cache for each page that has a valid cache entry.
    Returns the number of pages that got ASTs from cache.

    Args:
        build_cache: The build cache instance
        pages: Pages to load ASTs for
        site_root: Site root path for relative key computation

    Returns:
        Number of pages that received cached ASTs
    """
    if not build_cache.ast_cache:
        return 0

    loaded = 0
    for page in pages:
        ast = load_ast_from_cache(build_cache, page, site_root)
        if ast is not None:
            page._ast_cache = ast
            loaded += 1

    if loaded > 0:
        logger.info(
            "ast_cache_loaded",
            loaded=loaded,
            total=len(pages),
            hit_rate=f"{loaded / len(pages) * 100:.1f}%",
        )

    return loaded


def save_asts_for_pages(
    build_cache: BuildCache,
    pages: list[Page],
    site_root: Path,
) -> int:
    """Batch-save ASTs for multiple pages to the build cache.

    Args:
        build_cache: The build cache instance
        pages: Pages to save ASTs for
        site_root: Site root path for relative key computation

    Returns:
        Number of pages whose ASTs were saved
    """
    saved = 0
    for page in pages:
        if save_ast_to_cache(build_cache, page, site_root):
            saved += 1

    if saved > 0:
        logger.info(
            "ast_cache_saved",
            saved=saved,
            total=len(pages),
        )

    return saved
