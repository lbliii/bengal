"""Thread-local parser and renderer instance pools.

Provides pooling for Parser and HtmlRenderer instances to avoid
allocation overhead. Thread-safe via thread-local storage.

Pool Size:
    Default: 8 per thread (covers typical parallel template includes)
    Override: Set BENGAL_PARSER_POOL_SIZE or BENGAL_RENDERER_POOL_SIZE
    environment variables to tune.

Memory Overhead:
    ~1KB per Parser, ~0.5KB per Renderer = ~12KB per thread with default pool size.

Thread Safety:
    Uses threading.local() for per-thread pool isolation.
    No locks needed - each thread has its own pool.

RFC: rfc-contextvar-downstream-patterns.md

"""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from threading import local
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from patitas.parser import Parser

    from bengal.directives.cache import DirectiveCache
    from bengal.parsing.backends.patitas.protocols import LexerDelegate
    from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer


__all__ = [
    "ParserPool",
    "RendererPool",
]


# Pool size rationale:
# - 8 covers typical concurrent renders per thread (parallel template includes)
# - Memory overhead: ~1KB per Parser, ~0.5KB per Renderer = ~12KB per thread
# - Configurable via environment for tuning
_DEFAULT_POOL_SIZE = 8


class ParserPool:
    """Thread-local parser instance pool.

    Reuses Parser instances to avoid allocation overhead.
    Thread-safe via thread-local storage.

    Pool Size:
        Default: 8 per thread (covers typical parallel template includes)
        Override: Set BENGAL_PARSER_POOL_SIZE environment variable

    Memory: ~1KB per pooled Parser instance

    Usage:
        with ParserPool.acquire(content) as parser:
            ast = parser.parse()

    Thread Safety:
        Each thread has its own pool. No locks needed.
    """

    _local = local()
    _max_pool_size: int = int(os.environ.get("BENGAL_PARSER_POOL_SIZE", _DEFAULT_POOL_SIZE))

    @classmethod
    def _get_pool(cls) -> deque[Parser]:
        """Get or create thread-local pool."""
        if not hasattr(cls._local, "pool"):
            cls._local.pool: deque[Parser] = deque(maxlen=cls._max_pool_size)
        return cls._local.pool

    @classmethod
    @contextmanager
    def acquire(cls, source: str, source_file: str | None = None) -> Iterator[Parser]:
        """Acquire a parser from pool or create new one.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages

        Yields:
            Parser instance ready for parsing

        Usage:
            with ParserPool.acquire(content) as parser:
                ast = parser.parse()

        Performance:
            Pooling reduces allocation overhead by ~78% for high-volume parsing.
            On a 1,000-page site, this saves ~2,000 Parser allocations.

        Requires:
            patitas>=0.1.1 (provides Parser._reinit() method)
        """
        from patitas.parser import Parser

        pool = cls._get_pool()

        if pool:
            # Reuse existing parser from pool
            parser = pool.pop()
            parser._reinit(source, source_file)
        else:
            # Create new parser if pool is empty
            parser = Parser(source, source_file)

        try:
            yield parser
        finally:
            # Return to pool if not full
            if len(pool) < cls._max_pool_size:
                pool.append(parser)

    @classmethod
    def clear(cls) -> None:
        """Clear the pool for current thread.

        Useful for testing or memory cleanup.
        """
        if hasattr(cls._local, "pool"):
            cls._local.pool.clear()

    @classmethod
    def size(cls) -> int:
        """Get current pool size for this thread."""
        if hasattr(cls._local, "pool"):
            return len(cls._local.pool)
        return 0


class RendererPool:
    """Thread-local renderer instance pool.

    Reuses HtmlRenderer instances to avoid allocation overhead.
    Thread-safe via thread-local storage.

    Pool Size:
        Default: 8 per thread
        Override: Set BENGAL_RENDERER_POOL_SIZE environment variable

    Memory: ~0.5KB per pooled Renderer instance

    Usage:
        with RendererPool.acquire(source) as renderer:
            html = renderer.render(ast)

    Thread Safety:
        Each thread has its own pool. No locks needed.
    """

    _local = local()
    _max_pool_size: int = int(os.environ.get("BENGAL_RENDERER_POOL_SIZE", _DEFAULT_POOL_SIZE))

    @classmethod
    def _get_pool(cls) -> deque[HtmlRenderer]:
        """Get or create thread-local pool."""
        if not hasattr(cls._local, "pool"):
            cls._local.pool: deque[HtmlRenderer] = deque(maxlen=cls._max_pool_size)
        return cls._local.pool

    @classmethod
    @contextmanager
    def acquire(
        cls,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
    ) -> Iterator[HtmlRenderer]:
        """Acquire a renderer from pool or create new one.

        Args:
            source: Original source buffer for zero-copy extraction
            delegate: Optional sub-lexer delegate for ZCLH handoff
            directive_cache: Optional cache for rendered directive output
            page_context: Optional page context for directives

        Yields:
            HtmlRenderer instance ready for rendering

        Usage:
            with RendererPool.acquire(source) as renderer:
                html = renderer.render(ast)
        """
        from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

        pool = cls._get_pool()

        if pool:
            renderer = pool.pop()
            renderer._reset(
                source,
                delegate=delegate,
                directive_cache=directive_cache,
                page_context=page_context,
            )
        else:
            renderer = HtmlRenderer(
                source,
                delegate=delegate,
                directive_cache=directive_cache,
                page_context=page_context,
            )

        try:
            yield renderer
        finally:
            # Return to pool if not full
            if len(pool) < cls._max_pool_size:
                pool.append(renderer)

    @classmethod
    def clear(cls) -> None:
        """Clear the pool for current thread.

        Useful for testing or memory cleanup.
        """
        if hasattr(cls._local, "pool"):
            cls._local.pool.clear()

    @classmethod
    def size(cls) -> int:
        """Get current pool size for this thread."""
        if hasattr(cls._local, "pool"):
            return len(cls._local.pool)
        return 0
