"""Shared fixtures for Patitas tests."""

from __future__ import annotations

import pytest

from bengal.parsing.backends.patitas import (
    RenderConfig,
    create_markdown,
    parse,
    parse_to_ast,
    render_ast,
    set_render_config,
)
from patitas.lexer import Lexer
from patitas.parser import Parser
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer
from bengal.parsing.backends.patitas.wrapper import PatitasParser


# Default plugins for tests (matches PatitasParser.DEFAULT_PLUGINS)
DEFAULT_TEST_PLUGINS = ["table", "strikethrough", "task_lists", "math", "footnotes"]


@pytest.fixture
def lexer_factory():
    """Factory for creating lexers."""

    def create(source: str, source_file: str | None = None):
        return Lexer(source, source_file)

    return create


@pytest.fixture
def parser_factory():
    """Factory for creating parsers."""

    def create(source: str, source_file: str | None = None):
        return Parser(source, source_file)

    return create


@pytest.fixture
def renderer():
    """HTML renderer instance."""
    return HtmlRenderer()


@pytest.fixture
def renderer_highlight():
    """HTML renderer with highlighting enabled via ContextVar config."""
    # Set highlight config - stays active for test duration
    set_render_config(RenderConfig(highlight=True))
    return HtmlRenderer()


@pytest.fixture
def patitas_parser():
    """PatitasParser wrapper instance."""
    return PatitasParser()


@pytest.fixture
def patitas_parser_no_highlight():
    """PatitasParser without syntax highlighting."""
    return PatitasParser(enable_highlighting=False)


# =============================================================================
# Helper functions available as fixtures
# =============================================================================


@pytest.fixture
def tokenize():
    """Tokenize source and return list of tokens."""

    def _tokenize(source: str):
        lexer = Lexer(source)
        return list(lexer.tokenize())

    return _tokenize


@pytest.fixture
def parse_md():
    """Parse markdown and return HTML with default plugins enabled.
    
    Uses create_markdown() to enable table, strikethrough, task_lists,
    math, and footnotes plugins (matches PatitasParser defaults).
    """
    md = create_markdown(plugins=DEFAULT_TEST_PLUGINS)
    return md


@pytest.fixture
def parse_ast():
    """Parse markdown and return AST with default plugins enabled."""
    def _parse_ast(source: str):
        return parse_to_ast(source, plugins=DEFAULT_TEST_PLUGINS)
    return _parse_ast


@pytest.fixture
def render_nodes():
    """Render AST nodes to HTML."""
    return render_ast
