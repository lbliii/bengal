"""Comprehensive unit tests for Python function signature building and extraction."""

from __future__ import annotations

import ast

import pytest

from bengal.autodoc.extractors.python.signature import build_signature, extract_arguments


def _get_func_node(code: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Helper to parse code and return the first function node."""
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError(f"No function definition found in code: {code}")


@pytest.mark.unit
class TestPythonSignaturesComprehensive:
    """
    Tests for build_signature and extract_arguments covering all Python argument types.
    """

    @pytest.mark.parametrize(
        "code,expected_sig",
        [
            # Basic
            ("def f(a, b): pass", "def f(a, b)"),
            ("def f(a: int, b: str = 'hi') -> bool: pass", "def f(a: int, b: str = 'hi') -> bool"),
            # Positional-only
            ("def f(a, b, /): pass", "def f(a, b, /)"),
            ("def f(a, b=1, /): pass", "def f(a, b = 1, /)"),
            ("def f(a, b=1, /, c=2): pass", "def f(a, b = 1, /, c = 2)"),
            # Keyword-only
            ("def f(*, a, b=1): pass", "def f(*, a, b = 1)"),
            ("def f(a, *args, b, c=2): pass", "def f(a, *args, b, c = 2)"),
            # Varargs and Kwargs
            ("def f(*args, **kwargs): pass", "def f(*args, **kwargs)"),
            ("def f(a, *args: int, **kwargs: str): pass", "def f(a, *args: int, **kwargs: str)"),
            # Kitchen Sink (The ultimate test)
            (
                "async def complex_func(a, b=1, /, c=2, *args, d, e=3, **kwargs) -> list[str]: pass",
                "async def complex_func(a, b = 1, /, c = 2, *args, d, e = 3, **kwargs) -> list[str]",
            ),
            # Bare * with kwonly
            ("def f(a, /, *, b): pass", "def f(a, /, *, b)"),
        ],
    )
    def test_build_signature_permutations(self, code: str, expected_sig: str):
        """Test build_signature with various argument permutations."""
        node = _get_func_node(code)
        assert build_signature(node) == expected_sig

    def test_extract_arguments_details(self):
        """Test detailed argument extraction including kinds and defaults."""
        code = "def f(pos_only, /, reg, *vargs, kw_only=True, **kwargs): pass"
        node = _get_func_node(code)
        args = extract_arguments(node)

        # 1. pos_only
        assert args[0] == {
            "name": "pos_only",
            "type": None,
            "default": None,
            "kind": "positional_only",
        }

        # 2. reg
        assert args[1] == {
            "name": "reg",
            "type": None,
            "default": None,
            "kind": "positional_or_keyword",
        }

        # 3. *vargs
        assert args[2] == {
            "name": "*vargs",
            "type": None,
            "default": None,
            "kind": "var_positional",
        }

        # 4. kw_only
        assert args[3] == {
            "name": "kw_only",
            "type": None,
            "default": "True",
            "kind": "keyword_only",
        }

        # 5. **kwargs
        assert args[4] == {
            "name": "**kwargs",
            "type": None,
            "default": None,
            "kind": "var_keyword",
        }

    def test_async_generator_signature(self):
        """Test signature building for async generators."""
        code = "async def gen(n: int): yield n"
        node = _get_func_node(code)
        assert build_signature(node) == "async def gen(n: int)"

    def test_complex_annotations(self):
        """Test that complex type annotations are correctly unparsed."""
        code = "def f(a: dict[str, list[int | None]]): pass"
        node = _get_func_node(code)
        sig = build_signature(node)
        assert "dict[str, list[int | None]]" in sig
