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

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from bengal.parsing.backends.patitas.utils.pool import ThreadLocalPool

if TYPE_CHECKING:
    from patitas.parser import Parser

    from bengal.cache.directive_cache import DirectiveCache
    from bengal.parsing.backends.patitas.protocols import LexerDelegate
    from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer


__all__ = [
    "ParserPool",
    "RendererPool",
]


class ParserPool(ThreadLocalPool["Parser"]):
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

    _env_var_name = "BENGAL_PARSER_POOL_SIZE"

    @classmethod
    def _create(cls, source: str, source_file: str | None = None) -> Parser:
        """Create a new Parser instance."""
        from patitas.parser import Parser

        return Parser(source, source_file)

    @classmethod
    def _reinit(cls, instance: Parser, source: str, source_file: str | None = None) -> None:
        """Reinitialize an existing Parser for reuse."""
        instance._reinit(source, source_file)

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
        pool = cls._get_pool()

        if pool:
            parser = pool.pop()
            cls._reinit(parser, source, source_file)
        else:
            parser = cls._create(source, source_file)

        try:
            yield parser
        finally:
            if len(pool) < cls._max_pool_size:
                pool.append(parser)


class RendererPool(ThreadLocalPool["HtmlRenderer"]):
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

    _env_var_name = "BENGAL_RENDERER_POOL_SIZE"

    @classmethod
    def _create(
        cls,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
    ) -> HtmlRenderer:
        """Create a new HtmlRenderer instance."""
        from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

        return HtmlRenderer(
            source,
            delegate=delegate,
            directive_cache=directive_cache,
            page_context=page_context,
        )

    @classmethod
    def _reinit(
        cls,
        instance: HtmlRenderer,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        directive_cache: DirectiveCache | None = None,
        page_context: Any | None = None,
    ) -> None:
        """Reinitialize an existing HtmlRenderer for reuse."""
        instance._reset(
            source,
            delegate=delegate,
            directive_cache=directive_cache,
            page_context=page_context,
        )

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
        pool = cls._get_pool()

        if pool:
            renderer = pool.pop()
            cls._reinit(
                renderer,
                source,
                delegate=delegate,
                directive_cache=directive_cache,
                page_context=page_context,
            )
        else:
            renderer = cls._create(
                source,
                delegate=delegate,
                directive_cache=directive_cache,
                page_context=page_context,
            )

        try:
            yield renderer
        finally:
            if len(pool) < cls._max_pool_size:
                pool.append(renderer)
