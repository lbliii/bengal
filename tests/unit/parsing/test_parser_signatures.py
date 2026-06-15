"""Tests pinning the parser ``parse_with_toc`` contract to a 4-tuple.

The ``BaseMarkdownParser.parse_with_toc`` contract returns
``(html, toc, excerpt, meta_description)``. Both concrete parsers must honor
that 4-tuple shape so callers can unpack four values uniformly (#443).
"""

from __future__ import annotations

import inspect

from bengal.parsing.backends.patitas.wrapper import PatitasParser
from bengal.parsing.base import BaseMarkdownParser
from bengal.parsing.python_markdown import PythonMarkdownParser


def test_base_parse_with_toc_declares_four_tuple() -> None:
    """The abstract contract advertises a 4-tuple of strings."""
    annotation = inspect.signature(BaseMarkdownParser.parse_with_toc).return_annotation
    assert annotation == "tuple[str, str, str, str]"


def test_patitas_parse_with_toc_returns_four_tuple_of_str() -> None:
    """PatitasParser returns (html, toc, excerpt, meta_description)."""
    parser = PatitasParser()
    result = parser.parse_with_toc("# Heading\n\nBody paragraph.", {})

    html, toc, excerpt, meta = result
    assert len(result) == 4
    assert all(isinstance(part, str) for part in (html, toc, excerpt, meta))


def test_python_markdown_parse_with_toc_returns_four_tuple_of_str() -> None:
    """PythonMarkdownParser returns a 4-tuple with empty excerpt/meta."""
    parser = PythonMarkdownParser()
    result = parser.parse_with_toc("# Heading\n\nBody paragraph.", {})

    html, toc, excerpt, meta = result
    assert len(result) == 4
    assert all(isinstance(part, str) for part in (html, toc, excerpt, meta))
    # python-markdown does not extract excerpt/meta in this path.
    assert excerpt == ""
    assert meta == ""
