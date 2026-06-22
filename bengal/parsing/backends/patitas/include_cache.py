"""Thread-safe HTML and AST cache for static markdown include snippets."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from patitas.nodes import Block

__all__ = [
    "IncludeCacheKey",
    "clear_include_cache",
    "get_cached_include_ast",
    "get_cached_include_html",
    "store_cached_include_ast",
    "store_cached_include_html",
]

_MAX_ENTRIES = 512


@dataclass(frozen=True, slots=True)
class IncludeCacheKey:
    """Cache key for rendered include output."""

    path: str
    mtime_ns: int
    start_line: int | None
    end_line: int | None


_html_cache: dict[IncludeCacheKey, str] = {}
_ast_cache: dict[IncludeCacheKey, tuple[str, tuple[Any, ...]]] = {}
_lock = threading.Lock()


def _evict_if_needed(cache: dict[Any, Any]) -> None:
    if len(cache) <= _MAX_ENTRIES:
        return
    for key in list(cache.keys())[: len(cache) // 2]:
        cache.pop(key, None)


def _is_key_stale(key: IncludeCacheKey) -> bool:
    try:
        return Path(key.path).stat().st_mtime_ns != key.mtime_ns
    except OSError:
        return True


def cache_key_for(
    resolved_path: Path,
    *,
    start_line: int | None,
    end_line: int | None,
) -> IncludeCacheKey:
    """Build a cache key from a resolved include path and optional line bounds."""
    stat = resolved_path.stat()
    return IncludeCacheKey(
        path=str(resolved_path.resolve()),
        mtime_ns=stat.st_mtime_ns,
        start_line=start_line,
        end_line=end_line,
    )


def get_cached_include_html(key: IncludeCacheKey) -> str | None:
    """Return cached HTML when *key* matches a live file mtime."""
    with _lock:
        cached = _html_cache.get(key)
    if cached is None:
        return None
    if _is_key_stale(key):
        with _lock:
            _html_cache.pop(key, None)
            _ast_cache.pop(key, None)
        return None
    return cached


def store_cached_include_html(key: IncludeCacheKey, html: str) -> None:
    """Store rendered include HTML under *key*."""
    with _lock:
        _html_cache[key] = html
        _evict_if_needed(_html_cache)


def get_cached_include_ast(key: IncludeCacheKey) -> tuple[str, Sequence[Block]] | None:
    """Return cached source and AST blocks when *key* is still valid."""
    with _lock:
        cached = _ast_cache.get(key)
    if cached is None:
        return None
    if _is_key_stale(key):
        with _lock:
            _html_cache.pop(key, None)
            _ast_cache.pop(key, None)
        return None
    source, blocks = cached
    return source, blocks


def store_cached_include_ast(
    key: IncludeCacheKey,
    source: str,
    blocks: Sequence[Block],
) -> None:
    """Store parsed include AST blocks under *key*."""
    with _lock:
        _ast_cache[key] = (source, tuple(blocks))
        _evict_if_needed(_ast_cache)


def clear_include_cache() -> None:
    """Clear all cached include HTML and AST entries (for tests)."""
    with _lock:
        _html_cache.clear()
        _ast_cache.clear()
