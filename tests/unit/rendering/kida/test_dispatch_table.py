"""Tests for the block keyword dispatch table in Kida parser.

Verifies that the dispatch table refactoring (RFC: rfc-code-smell-remediation.md §1.1)
maintains correct behavior for all block keywords.
"""

import pytest

from bengal.rendering.kida import Environment
from bengal.rendering.kida.parser.statements import (
    _BLOCK_PARSERS,
    _CONTINUATION_KEYWORDS,
    _END_KEYWORDS,
    _VALID_KEYWORDS,
)


class TestDispatchTableStructure:
    """Verify dispatch table structure and completeness."""

    def test_block_parsers_maps_to_method_names(self):
        """All dispatch table values should be method name strings."""
        for keyword, method_name in _BLOCK_PARSERS.items():
            assert isinstance(keyword, str), f"Key {keyword} should be a string"
            assert isinstance(method_name, str), f"Value for {keyword} should be a string"
            assert method_name.startswith("_parse_"), (
                f"Method {method_name} should start with _parse_"
            )

    def test_continuation_keywords_are_frozenset(self):
        """Continuation keywords should be a frozenset for O(1) lookup."""
        assert isinstance(_CONTINUATION_KEYWORDS, frozenset)
        assert "elif" in _CONTINUATION_KEYWORDS
        assert "else" in _CONTINUATION_KEYWORDS
        assert "empty" in _CONTINUATION_KEYWORDS
        assert "case" in _CONTINUATION_KEYWORDS

    def test_end_keywords_are_frozenset(self):
        """End keywords should be a frozenset for O(1) lookup."""
        assert isinstance(_END_KEYWORDS, frozenset)
        assert "end" in _END_KEYWORDS
        assert "endif" in _END_KEYWORDS
        assert "endfor" in _END_KEYWORDS
        assert "endblock" in _END_KEYWORDS

    def test_valid_keywords_matches_block_parsers(self):
        """_VALID_KEYWORDS should match _BLOCK_PARSERS keys."""
        assert frozenset(_BLOCK_PARSERS.keys()) == _VALID_KEYWORDS

    def test_no_overlap_between_keyword_sets(self):
        """Block, continuation, and end keywords should not overlap."""
        block_keys = set(_BLOCK_PARSERS.keys())
        continuation = set(_CONTINUATION_KEYWORDS)
        end = set(_END_KEYWORDS)

        assert block_keys.isdisjoint(continuation), "Block and continuation overlap"
        assert block_keys.isdisjoint(end), "Block and end overlap"
        assert continuation.isdisjoint(end), "Continuation and end overlap"


class TestDispatchTableKeywords:
    """Test that all expected keywords are present in the dispatch table."""

    @pytest.mark.parametrize(
        "keyword",
        [
            # Control flow
            "if",
            "unless",
            "for",
            "while",
            "break",
            "continue",
            # Variables
            "set",
            "let",
            "export",
            # Template structure
            "block",
            "extends",
            "include",
            "import",
            "macro",
            "from",
            # Scope and execution
            "with",
            "do",
            "raw",
            "def",
            "call",
            "capture",
            "cache",
            "filter",
            # Advanced features
            "slot",
            "match",
            "spaceless",
            "embed",
        ],
    )
    def test_keyword_in_dispatch_table(self, keyword):
        """Verify keyword exists in dispatch table."""
        assert keyword in _BLOCK_PARSERS, f"Keyword '{keyword}' missing from dispatch table"


class TestDispatchTableBehavior:
    """Test that dispatch table produces correct parsing behavior."""

    @pytest.fixture
    def env(self):
        """Create a Kida environment for testing."""
        return Environment()

    def test_if_keyword_dispatches_correctly(self, env):
        """{% if %} should work via dispatch table."""
        tmpl = env.from_string("{% if true %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_for_keyword_dispatches_correctly(self, env):
        """{% for %} should work via dispatch table."""
        tmpl = env.from_string("{% for i in [1,2,3] %}{{ i }}{% endfor %}")
        assert tmpl.render() == "123"

    def test_set_keyword_dispatches_correctly(self, env):
        """{% set %} should work via dispatch table."""
        tmpl = env.from_string("{% set x = 42 %}{{ x }}")
        assert tmpl.render() == "42"

    def test_with_keyword_dispatches_correctly(self, env):
        """{% with %} should work via dispatch table."""
        tmpl = env.from_string("{% with x = 5 %}{{ x }}{% endwith %}")
        assert tmpl.render() == "5"

    def test_raw_keyword_dispatches_correctly(self, env):
        """{% raw %} should work via dispatch table."""
        tmpl = env.from_string("{% raw %}{{ not rendered }}{% endraw %}")
        assert tmpl.render() == "{{ not rendered }}"

    def test_macro_keyword_dispatches_correctly(self, env):
        """{% macro %} should work via dispatch table."""
        tmpl = env.from_string(
            "{% macro hello(name) %}Hello {{ name }}{% endmacro %}{{ hello('World') }}"
        )
        assert tmpl.render() == "Hello World"

    def test_block_keyword_dispatches_correctly(self, env):
        """{% block %} should work via dispatch table."""
        tmpl = env.from_string("{% block content %}default{% endblock %}")
        assert tmpl.render() == "default"

    def test_unknown_keyword_raises_error(self, env):
        """Unknown keywords should raise appropriate error."""
        with pytest.raises(Exception) as exc_info:
            env.from_string("{% unknown_keyword %}")
        assert "unknown" in str(exc_info.value).lower()


class TestEndKeywordHandling:
    """Test that end keywords are handled correctly."""

    @pytest.fixture
    def env(self):
        """Create a Kida environment for testing."""
        return Environment()

    def test_unified_end_tag(self, env):
        """{% end %} should close any open block."""
        tmpl = env.from_string("{% if true %}yes{% end %}")
        assert tmpl.render() == "yes"

    def test_specific_end_tag(self, env):
        """Specific end tags should close matching blocks."""
        tmpl = env.from_string("{% if true %}yes{% endif %}")
        assert tmpl.render() == "yes"

    def test_mismatched_end_tag_raises(self, env):
        """Mismatched end tags should raise error."""
        with pytest.raises(Exception) as exc_info:
            env.from_string("{% if true %}yes{% endfor %}")
        # Parser may report as "unclosed" (missing proper close) or "mismatch"
        msg = str(exc_info.value).lower()
        assert "unclosed" in msg or "mismatch" in msg or "expected" in msg


class TestContinuationKeywordHandling:
    """Test that continuation keywords outside blocks raise errors."""

    @pytest.fixture
    def env(self):
        """Create a Kida environment for testing."""
        return Environment()

    def test_else_outside_if_raises(self, env):
        """{% else %} outside if block should raise error."""
        with pytest.raises(Exception) as exc_info:
            env.from_string("{% else %}")
        assert (
            "unexpected" in str(exc_info.value).lower()
            or "not inside" in str(exc_info.value).lower()
        )

    def test_elif_outside_if_raises(self, env):
        """{% elif %} outside if block should raise error."""
        with pytest.raises(Exception) as exc_info:
            env.from_string("{% elif true %}")
        assert (
            "unexpected" in str(exc_info.value).lower()
            or "not inside" in str(exc_info.value).lower()
        )
