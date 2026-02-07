"""Tests for ContextVar Downstream Patterns.

Tests the three patterns from RFC: rfc-contextvar-downstream-patterns.md
1. Parser/Renderer Pooling
2. Metadata Accumulator
3. Request-Scoped Context

"""

from __future__ import annotations

import pytest
from patitas.parser import Parser

from bengal.parsing.backends.patitas import (
    ParserPool,
    RendererPool,
    RenderMetadata,
    RequestContext,
    RequestContextError,
    get_metadata,
    get_request_context,
    metadata_context,
    parse_to_ast,
    render_ast,
    request_context,
    try_get_request_context,
)
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

# =============================================================================
# Pattern 1: Parser/Renderer Pooling Tests
# =============================================================================


class TestParserPool:
    """Test ParserPool thread-local instance pooling."""

    def test_acquire_creates_parser(self):
        """Pool creates new parser when empty."""
        ParserPool.clear()
        with ParserPool.acquire("# Hello") as parser:
            assert isinstance(parser, Parser)
            ast = parser.parse()
            assert len(ast) == 1

    def test_acquire_reuses_parser(self):
        """Pool reuses parser instances via _reinit().

        Parser pooling is enabled with patitas>=0.1.1 which provides
        the Parser._reinit() method for instance reuse.

        See: RFC rfc-patitas-external-migration.md
        """
        ParserPool.clear()

        # First acquire - creates new parser
        with ParserPool.acquire("# Hello") as parser1:
            id1 = id(parser1)
            _ = parser1.parse()

        # Second acquire - should reuse the parser from pool
        with ParserPool.acquire("## World") as parser2:
            id2 = id(parser2)
            ast = parser2.parse()

        # Same instance - pooling reuses via _reinit()
        assert id1 == id2
        assert len(ast) == 1

    def test_pool_respects_max_size(self):
        """Pool doesn't grow beyond max size."""
        ParserPool.clear()

        # Acquire multiple parsers
        parsers = []
        for i in range(10):
            with ParserPool.acquire(f"# Test {i}") as p:
                parsers.append(id(p))
                p.parse()

        # Pool should not exceed max size
        assert ParserPool.size() <= ParserPool._max_pool_size

    def test_reinit_resets_state(self):
        """Parser._reinit() properly resets all parse state."""
        ParserPool.clear()

        # Parse document with link refs
        source1 = "[link][ref]\n\n[ref]: https://example.com"
        with ParserPool.acquire(source1) as parser1:
            ast1 = parser1.parse()
            assert len(parser1._link_refs) == 1

        # Reuse parser - link refs should be cleared
        source2 = "# Simple heading"
        with ParserPool.acquire(source2) as parser2:
            ast2 = parser2.parse()
            # Link refs should be reset
            assert len(parser2._link_refs) == 0

    def test_clear_empties_pool(self):
        """clear() removes all pooled instances."""
        with ParserPool.acquire("# Test") as _:
            pass

        assert ParserPool.size() >= 0
        ParserPool.clear()
        assert ParserPool.size() == 0


class TestRendererPool:
    """Test RendererPool thread-local instance pooling."""

    def test_acquire_creates_renderer(self):
        """Pool creates new renderer when empty."""
        RendererPool.clear()

        source = "# Hello"
        ast = parse_to_ast(source)

        with RendererPool.acquire(source) as renderer:
            assert isinstance(renderer, HtmlRenderer)
            html = renderer.render(ast)
            assert "<h1" in html

    def test_acquire_reuses_renderer(self):
        """Pool reuses returned renderer instances."""
        RendererPool.clear()

        source1 = "# Hello"
        ast1 = parse_to_ast(source1)

        # First acquire
        with RendererPool.acquire(source1) as renderer1:
            id1 = id(renderer1)
            renderer1.render(ast1)

        source2 = "## World"
        ast2 = parse_to_ast(source2)

        # Second acquire - should reuse
        with RendererPool.acquire(source2) as renderer2:
            id2 = id(renderer2)
            renderer2.render(ast2)

        assert id1 == id2

    def test_reset_clears_headings(self):
        """Renderer._reset() clears heading state."""
        RendererPool.clear()

        source1 = "# Heading 1\n## Heading 2"
        ast1 = parse_to_ast(source1)

        with RendererPool.acquire(source1) as renderer1:
            renderer1.render(ast1)
            headings1 = renderer1.get_headings()
            assert len(headings1) == 2

        source2 = "# Single Heading"
        ast2 = parse_to_ast(source2)

        with RendererPool.acquire(source2) as renderer2:
            renderer2.render(ast2)
            headings2 = renderer2.get_headings()
            # Should have fresh heading state
            assert len(headings2) == 1

    def test_clear_empties_pool(self):
        """clear() removes all pooled instances."""
        source = "# Test"
        with RendererPool.acquire(source) as _:
            pass

        RendererPool.clear()
        assert RendererPool.size() == 0


# =============================================================================
# Pattern 2: Metadata Accumulator Tests
# =============================================================================


class TestRenderMetadata:
    """Test RenderMetadata dataclass functionality."""

    def test_default_values(self):
        """Metadata has sensible defaults."""
        meta = RenderMetadata()
        assert meta.has_math is False
        assert meta.has_code_blocks is False
        assert meta.has_mermaid is False
        assert meta.has_tables is False
        assert meta.word_count == 0
        assert meta.code_languages == set()
        assert meta.internal_links == []
        assert meta.external_links == []
        assert meta.image_refs == []

    def test_add_words(self):
        """add_words() accumulates word count."""
        meta = RenderMetadata()
        meta.add_words("Hello world")
        assert meta.word_count == 2
        meta.add_words("More words here")
        assert meta.word_count == 5

    def test_add_code_block(self):
        """add_code_block() tracks languages."""
        meta = RenderMetadata()
        meta.add_code_block("python")
        assert meta.has_code_blocks is True
        assert "python" in meta.code_languages

        meta.add_code_block("javascript")
        assert "javascript" in meta.code_languages

    def test_add_code_block_mermaid(self):
        """Mermaid language sets has_mermaid flag."""
        meta = RenderMetadata()
        meta.add_code_block("mermaid")
        assert meta.has_mermaid is True

    def test_add_internal_link(self):
        """add_internal_link() tracks internal links."""
        meta = RenderMetadata()
        meta.add_internal_link("docs/getting-started.md")
        assert "docs/getting-started.md" in meta.internal_links

    def test_add_external_link(self):
        """add_external_link() tracks external links."""
        meta = RenderMetadata()
        meta.add_external_link("https://example.com")
        assert "https://example.com" in meta.external_links

    def test_add_image(self):
        """add_image() tracks image refs."""
        meta = RenderMetadata()
        meta.add_image("images/photo.png")
        assert "images/photo.png" in meta.image_refs

    def test_to_dict(self):
        """to_dict() returns dictionary representation."""
        meta = RenderMetadata()
        meta.has_math = True
        meta.word_count = 100
        meta.code_languages.add("python")

        d = meta.to_dict()
        assert d["has_math"] is True
        assert d["word_count"] == 100
        assert "python" in d["code_languages"]


class TestMetadataContext:
    """Test metadata_context() context manager."""

    def test_metadata_context_provides_accumulator(self):
        """Context manager yields RenderMetadata."""
        with metadata_context() as meta:
            assert isinstance(meta, RenderMetadata)

    def test_get_metadata_returns_current(self):
        """get_metadata() returns current context."""
        assert get_metadata() is None  # Outside context

        with metadata_context() as meta:
            assert get_metadata() is meta

    def test_metadata_context_nesting(self):
        """Nested contexts work correctly."""
        with metadata_context() as outer:
            outer.word_count = 10

            with metadata_context() as inner:
                assert get_metadata() is inner
                assert inner.word_count == 0  # Fresh

            assert get_metadata() is outer
            assert outer.word_count == 10

    def test_metadata_accumulation_during_render(self):
        """Metadata is accumulated during rendering."""
        source = """# Hello World

This is a paragraph with some text.

```python
print("Hello")
```

[Link](https://example.com)

![Image](photo.png)
"""
        ast = parse_to_ast(source)

        with metadata_context() as meta:
            html = render_ast(ast, source)

            # Verify accumulation
            assert meta.has_code_blocks is True
            assert "python" in meta.code_languages
            assert meta.word_count > 0
            assert "https://example.com" in meta.external_links
            assert "photo.png" in meta.image_refs

    def test_metadata_math_detection(self):
        """Math content is detected."""
        source = "Inline math: $x = 1$ and block:\n\n$$\ny = 2\n$$"
        ast = parse_to_ast(source, plugins=["math"])

        with metadata_context() as meta:
            html = render_ast(ast, source)
            assert meta.has_math is True

    def test_metadata_table_detection(self):
        """Tables are detected."""
        source = """| A | B |
|---|---|
| 1 | 2 |"""
        ast = parse_to_ast(source, plugins=["table"])

        with metadata_context() as meta:
            html = render_ast(ast, source)
            assert meta.has_tables is True


# =============================================================================
# Pattern 3: Request-Scoped Context Tests
# =============================================================================


class TestRequestContext:
    """Test RequestContext dataclass."""

    def test_default_values(self):
        """RequestContext has sensible defaults."""
        ctx = RequestContext()
        assert ctx.source_file is None
        assert ctx.source_content == ""
        assert ctx.page is None
        assert ctx.site is None
        assert ctx.error_handler is None
        assert ctx.strict_mode is False
        assert ctx.link_resolver is None
        assert ctx.trace_enabled is False

    def test_frozen_dataclass(self):
        """RequestContext is immutable."""
        ctx = RequestContext(source_content="test")
        with pytest.raises(AttributeError):
            ctx.source_content = "modified"

    def test_resolve_link_with_resolver(self):
        """resolve_link() uses provided resolver."""

        def resolver(target: str) -> str | None:
            return f"/resolved/{target}"

        ctx = RequestContext(link_resolver=resolver)
        assert ctx.resolve_link("docs/test.md") == "/resolved/docs/test.md"

    def test_resolve_link_without_resolver(self):
        """resolve_link() returns None without resolver."""
        ctx = RequestContext()
        assert ctx.resolve_link("docs/test.md") is None

    def test_report_error_with_handler(self):
        """report_error() calls handler if set."""
        errors = []

        def handler(err, context):
            errors.append((err, context))

        ctx = RequestContext(error_handler=handler)
        ctx.report_error(ValueError("test"), "test context")

        assert len(errors) == 1
        assert isinstance(errors[0][0], ValueError)
        assert errors[0][1] == "test context"

    def test_report_error_strict_mode(self):
        """report_error() raises in strict mode."""
        ctx = RequestContext(strict_mode=True)

        with pytest.raises(ValueError):
            ctx.report_error(ValueError("test"), "context")

    def test_report_error_silent(self):
        """report_error() is silent without handler/strict."""
        ctx = RequestContext()
        ctx.report_error(ValueError("test"), "context")  # Should not raise


class TestRequestContextManager:
    """Test request_context() context manager."""

    def test_context_manager_sets_context(self):
        """Context manager sets current context."""
        assert try_get_request_context() is None

        with request_context(source_content="test") as ctx:
            assert ctx.source_content == "test"
            assert get_request_context() is ctx

        assert try_get_request_context() is None

    def test_get_request_context_fails_outside(self):
        """get_request_context() raises without context."""
        with pytest.raises(RequestContextError):
            get_request_context()

    def test_try_get_returns_none_outside(self):
        """try_get_request_context() returns None outside context."""
        assert try_get_request_context() is None

    def test_context_nesting(self):
        """Nested contexts work correctly."""
        with request_context(source_content="outer") as outer:
            assert get_request_context().source_content == "outer"

            with request_context(source_content="inner") as inner:
                assert get_request_context().source_content == "inner"

            assert get_request_context().source_content == "outer"

    def test_context_with_all_parameters(self):
        """Context manager accepts all parameters."""
        from pathlib import Path

        def resolver(target):
            return f"/r/{target}"

        def handler(err, ctx):
            pass

        with request_context(
            source_file=Path("/test/file.md"),
            source_content="# Test",
            page=None,
            site=None,
            error_handler=handler,
            strict_mode=True,
            link_resolver=resolver,
            trace_enabled=True,
        ) as ctx:
            assert ctx.source_file == Path("/test/file.md")
            assert ctx.source_content == "# Test"
            assert ctx.strict_mode is True
            assert ctx.trace_enabled is True
            assert ctx.resolve_link("test") == "/r/test"


# =============================================================================
# Integration Tests
# =============================================================================


class TestContextVarComposition:
    """Test that all ContextVar patterns compose correctly."""

    def test_all_patterns_together(self):
        """All three patterns can be used together."""
        from pathlib import Path

        from bengal.parsing.backends.patitas import (
            ParseConfig,
            RenderConfig,
            parse_config_context,
            render_config_context,
        )

        source = """# Hello World

This is a test with [link](https://example.com).

```python
print("test")
```
"""

        # Layer 1: Configuration
        with parse_config_context(ParseConfig()):
            with render_config_context(RenderConfig()):
                # Layer 2: Request context
                with request_context(
                    source_file=Path("/test.md"),
                    source_content=source,
                ):
                    # Layer 3: Metadata accumulation
                    with metadata_context() as meta:
                        # Layer 4: Pooled instances
                        with ParserPool.acquire(source) as parser:
                            ast = parser.parse()

                        with RendererPool.acquire(source) as renderer:
                            html = renderer.render(ast)

                        # Verify all contexts worked
                        assert "<h1" in html
                        assert meta.has_code_blocks is True
                        assert "https://example.com" in meta.external_links


class TestPoolPerformance:
    """Performance-related tests for pooling."""

    def test_pool_reuses_instances(self):
        """Verify both ParserPool and RendererPool correctly reuse instances.

        Both pools are enabled with patitas>=0.1.1:
        - ParserPool uses Parser._reinit() for reuse
        - RendererPool uses HtmlRenderer._reset() for reuse
        """
        ParserPool.clear()
        RendererPool.clear()

        source = "# Test content"

        # Test parser pool
        with ParserPool.acquire(source) as parser:
            pid1 = id(parser)
            parser.parse()

        assert ParserPool.size() == 1

        with ParserPool.acquire(source) as parser:
            pid2 = id(parser)

        assert pid1 == pid2, "ParserPool should reuse instances"

        # Test renderer pool
        with RendererPool.acquire(source) as renderer:
            rid1 = id(renderer)

        assert RendererPool.size() == 1

        with RendererPool.acquire(source) as renderer:
            rid2 = id(renderer)

        assert rid1 == rid2, "RendererPool should reuse instances"
