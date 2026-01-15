"""
Rendering test configuration and fixtures.

This module provides scoped fixtures for rendering tests to reduce
expensive parser instantiation. The MistuneParser is instantiated once
per module and reused across tests, with state reset between tests
to prevent pollution.

Fixtures:
    parser: Module-scoped MistuneParser for rendering tests
    parser_with_site: Parser pre-configured with xref_index from test-directives root
    reset_parser_state: Autouse fixture that resets parser state between tests

Usage:
def test_simple_parsing(parser):
    result = parser.parse("# Hello", {})
    assert "<h1>" in result

def test_with_xref(parser_with_site):
    result = parser_with_site.parse("See [[cards]]", {})
    # Links resolved from test-directives xref_index

Safety:
The reset_parser_state fixture ensures test isolation even when sharing
a module-scoped parser. Tests that modify _xref_index get a fresh state
on each run.

"""

from __future__ import annotations

import pytest

from bengal.parsing import MistuneParser


@pytest.fixture(scope="module")
def parser() -> MistuneParser:
    """
    Module-scoped parser for rendering tests.
    
    Reused across all tests in a module to avoid repeated instantiation.
    Parser state is reset between tests by the reset_parser_state autouse fixture.
    
    Returns:
        MistuneParser instance
    
    Example:
        def test_markdown_parsing(parser):
            result = parser.parse("# Hello World", {})
            assert "<h1>Hello World</h1>" in result
        
    """
    return MistuneParser()


@pytest.fixture(autouse=True, scope="function")
def reset_parser_state(request: pytest.FixtureRequest) -> None:
    """
    Reset parser state between tests to prevent pollution.
    
    Some tests modify parser.md.renderer._xref_index. This fixture ensures
    each test starts with a clean parser state, even when using a
    module-scoped parser fixture.
    
    Only runs when parser fixture is used (checks if parser is in request.fixturenames).
        
    """
    # Only reset if parser fixture is used in this test
    if "parser" not in request.fixturenames and "parser_with_site" not in request.fixturenames:
        yield
        return

    # Determine which parser fixture to use
    parser_name = "parser" if "parser" in request.fixturenames else "parser_with_site"

    try:
        parser = request.getfixturevalue(parser_name)
    except pytest.FixtureLookupError:
        yield
        return

    # Save original state (if any)
    original_xref_index = getattr(parser.md.renderer, "_xref_index", None)

    yield

    # Reset after test completes
    parser.md.renderer._xref_index = original_xref_index


@pytest.fixture(scope="module")
def parser_with_site(request: pytest.FixtureRequest, site_factory):
    """
    Parser with xref_index from test-directives root.
    
    Provides a parser pre-configured with cross-reference index built from
    the test-directives test root. Useful for testing link resolution.
    
    Note: Tests using this fixture should NOT modify _xref_index directly.
    Use the base parser fixture if you need to modify xref_index per test.
    
    Returns:
        MistuneParser with populated xref_index
    
    Example:
        def test_xref_resolution(parser_with_site):
            result = parser_with_site.parse("See [[cards]] for examples", {})
            assert "/cards/" in result
        
    """
    site = site_factory("test-directives")
    site.discover_content()

    parser = MistuneParser()
    parser.md.renderer._xref_index = site.build_xref_index()
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
            parser.md.renderer._xref_index = mock_xref_index
            result = parser.parse("See [[custom]]", {})
        
    """
    return {
        "by_id": {},
        "by_path": {},
        "by_slug": {},
        "by_heading": {},
    }
