"""Shared fixtures for Patitas tests."""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse, parse_to_ast, render_ast
from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.parser import Parser
from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer
from bengal.rendering.parsers.patitas.wrapper import PatitasParser


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
    """HTML renderer with highlighting enabled."""
    return HtmlRenderer(highlight=True)


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
    """Parse markdown and return HTML."""
    return parse


@pytest.fixture
def parse_ast():
    """Parse markdown and return AST."""
    return parse_to_ast


@pytest.fixture
def render_nodes():
    """Render AST nodes to HTML."""
    return render_ast
