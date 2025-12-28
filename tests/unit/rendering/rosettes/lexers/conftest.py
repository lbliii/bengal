"""Shared fixtures for lexer tests."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes import get_lexer

# High-priority languages from RFC
HIGH_PRIORITY_LANGUAGES = [
    "kida",
    "python",
    "javascript",
    "typescript",
    "rust",
    "go",
    "yaml",
    "json",
    "bash",
    "html",
    "css",
    "sql",
    "markdown",
    "java",
    "c",
    "cpp",
    "jinja",
]


@pytest.fixture
def lexer(request):
    """Parametrized fixture to get any lexer by name."""
    language = request.param
    return get_lexer(language)
