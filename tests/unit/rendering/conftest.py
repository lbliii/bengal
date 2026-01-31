"""
Rendering test configuration and fixtures.

This module provides scoped fixtures for rendering tests to reduce
expensive parser instantiation. The PatitasParser is instantiated once
per module and reused across tests.

Fixtures:
    parser: Module-scoped PatitasParser for rendering tests
    parser_with_site: Parser pre-configured with xref_index from test-directives root
    reset_parser_state: Autouse fixture (no-op for PatitasParser, kept for compatibility)

Usage:
    def test_simple_parsing(parser):
        result = parser.parse("# Hello", {})
        assert "<h1>" in result

    def test_with_xref(parser_with_site):
        result = parser_with_site.parse("See [[cards]]", {})
        # Links resolved from test-directives xref_index

Note:
    PatitasParser is stateless by design - each parse() call creates
    independent parser/renderer instances. No state reset is needed.

"""

from __future__ import annotations

import pytest

from bengal.parsing import PatitasParser


@pytest.fixture(scope="module")
def parser() -> PatitasParser:
    """
    Module-scoped parser for rendering tests.

    Reused across all tests in a module to avoid repeated instantiation.

    Returns:
        PatitasParser instance

    Example:
        def test_markdown_parsing(parser):
            result = parser.parse("# Hello World", {})
            assert "<h1>Hello World</h1>" in result

    """
    return PatitasParser()


@pytest.fixture(autouse=True)
def reset_parser_state(request: pytest.FixtureRequest):
    """
    Reset parser state between tests to prevent pollution.

    PatitasParser is stateless by design - each parse() call creates
    independent parser/renderer instances. However, directive caching
    may cause cross-test pollution, so we clear the cache between tests.
    """
    # Clear directive cache to prevent cross-test pollution
    from bengal.directives.cache import clear_cache

    clear_cache()
    yield
    clear_cache()


@pytest.fixture(scope="module")
def parser_with_site(request: pytest.FixtureRequest, site_factory):
    """
    Parser with xref_index from test-directives root.

    Provides a parser pre-configured with cross-reference index built from
    the test-directives test root. Useful for testing link resolution.

    Returns:
        PatitasParser with populated xref_index

    Example:
        def test_xref_resolution(parser_with_site):
            result = parser_with_site.parse("See [[cards]] for examples", {})
            assert "/cards/" in result

    """
    site = site_factory("test-directives")
    site.discover_content()

    parser = PatitasParser()
    # PatitasParser uses enable_cross_references() method
    xref_index = site.build_xref_index()
    parser.enable_cross_references(xref_index)
    return parser


@pytest.fixture
def mock_xref_index():
    """
    Empty xref_index for tests that need manual control.

    Returns:
        Empty xref_index dict structure

    Example:
        def test_custom_xref(parser, mock_xref_index):
            from tests._testing.mocks import MockPage
            mock_xref_index["by_slug"]["custom"] = [MockPage(title="Custom", url="/custom/")]
            parser.enable_cross_references(mock_xref_index)
            result = parser.parse("See [[custom]]", {})

    """
    return {
        "by_id": {},
        "by_path": {},
        "by_slug": {},
        "by_heading": {},
    }
