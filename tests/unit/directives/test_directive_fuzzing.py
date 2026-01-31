"""
Property-based tests for directive parsing using Hypothesis.

These tests use fuzzing to discover edge cases that manual tests might miss.
They ensure directive parsing is robust against arbitrary and malformed input.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from bengal.directives.validator import DirectiveSyntaxValidator


class TestValidatorFuzzing:
    """Property-based tests for DirectiveSyntaxValidator robustness."""

    @given(st.text(max_size=5000))
    @settings(max_examples=200)
    def test_validate_nested_fences_never_crashes(self, content: str):
        """Validator should never crash on any input."""
        # Should not raise any exceptions
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)
        assert all(isinstance(e, str) for e in errors)

    @given(
        st.lists(
            st.sampled_from(["```", "~~~", ":::", "::::", ":::::", "`````"]),
            min_size=0,
            max_size=50,
        )
    )
    @settings(max_examples=100)
    def test_random_fence_sequences_never_crash(self, fences: list[str]):
        """Validator should handle any sequence of fence markers."""
        content = "\n".join(fences)
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    @given(
        st.lists(
            st.tuples(
                st.sampled_from(["```", "~~~"]),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_", max_size=20),
            ),
            min_size=0,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_code_fences_with_languages_never_crash(self, fence_specs: list[tuple[str, str]]):
        """Code fences with various language specifiers should not crash."""
        lines = []
        for fence, lang in fence_specs:
            lines.append(f"{fence}{lang}")
            lines.append("code content")
            lines.append(fence)
        content = "\n".join(lines)
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=3, max_value=10),  # colon count
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_", min_size=1, max_size=15),
            ),
            min_size=0,
            max_size=15,
        )
    )
    @settings(max_examples=100)
    def test_directive_fences_with_types_never_crash(self, directive_specs: list[tuple[int, str]]):
        """Directive fences with various types should not crash."""
        lines = []
        for colon_count, directive_type in directive_specs:
            fence = ":" * colon_count
            lines.append(f"{fence}{{{directive_type}}}")
            lines.append("directive content")
            lines.append(fence)
        content = "\n".join(lines)
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)

    @given(st.binary(max_size=1000))
    @settings(max_examples=50)
    def test_binary_content_handled_gracefully(self, data: bytes):
        """Binary/non-UTF8 content should be handled gracefully."""
        try:
            content = data.decode("utf-8", errors="replace")
            errors = DirectiveSyntaxValidator.validate_nested_fences(content)
            assert isinstance(errors, list)
        except Exception:
            # If we can't even decode, that's fine
            pass

    @given(
        st.integers(min_value=1, max_value=100),
        st.sampled_from(["note", "warning", "tip", "tab-set", "steps"]),
    )
    @settings(max_examples=50)
    def test_repeated_same_directive_never_crashes(self, count: int, dtype: str):
        """Many repeated directives should not crash."""
        block = f":::{{{dtype}}}\ncontent\n:::\n\n"
        content = block * count
        errors = DirectiveSyntaxValidator.validate_nested_fences(content)
        assert isinstance(errors, list)


class TestDirectiveSpecificValidatorFuzzing:
    """Fuzz tests for directive-specific validators."""

    @given(st.text(max_size=2000))
    @settings(max_examples=100)
    def test_tabs_directive_validation_never_crashes(self, content: str):
        """Tabs directive validation should never crash."""
        errors = DirectiveSyntaxValidator.validate_tabs_directive(content)
        assert isinstance(errors, list)

    @given(st.text(max_size=2000))
    @settings(max_examples=100)
    def test_code_tabs_directive_validation_never_crashes(self, content: str):
        """Code-tabs directive validation should never crash."""
        errors = DirectiveSyntaxValidator.validate_code_tabs_directive(content)
        assert isinstance(errors, list)

    @given(st.text(max_size=2000), st.text(max_size=100))
    @settings(max_examples=100)
    def test_dropdown_directive_validation_never_crashes(self, content: str, title: str):
        """Dropdown directive validation should never crash."""
        errors = DirectiveSyntaxValidator.validate_dropdown_directive(content, title)
        assert isinstance(errors, list)

    @given(
        st.sampled_from(["note", "tip", "warning", "danger", "error", "info", "example"]),
        st.text(max_size=2000),
    )
    @settings(max_examples=100)
    def test_admonition_directive_validation_never_crashes(self, admon_type: str, content: str):
        """Admonition directive validation should never crash."""
        errors = DirectiveSyntaxValidator.validate_admonition_directive(admon_type, content)
        assert isinstance(errors, list)

    @given(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz-_0123456789",
            min_size=1,
            max_size=30,
        ),
        st.text(max_size=1000),
    )
    @settings(max_examples=100)
    def test_directive_validation_never_crashes(self, directive_type: str, content: str):
        """General directive validation should never crash."""
        errors = DirectiveSyntaxValidator.validate_directive(
            directive_type=directive_type,
            content=content,
            title="Test Title",
        )
        assert isinstance(errors, list)


class TestOptionsParsingFuzzing:
    """Fuzz tests for directive options parsing."""

    @given(
        st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_", min_size=1, max_size=20),
            values=st.text(max_size=100),
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_options_from_raw_never_crashes(self, raw_options: dict[str, str]):
        """DirectiveOptions.from_raw should never crash."""
        from bengal.directives.options import DirectiveOptions

        # Should not raise any exceptions
        result = DirectiveOptions.from_raw(raw_options)
        assert result is not None

    @given(
        st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz-_", min_size=1, max_size=20),
            values=st.text(max_size=100),
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_styled_options_from_raw_never_crashes(self, raw_options: dict[str, str]):
        """StyledOptions.from_raw should never crash."""
        from bengal.directives.options import StyledOptions

        result = StyledOptions.from_raw(raw_options)
        assert result is not None

    @given(st.text(max_size=100))
    @settings(max_examples=100)
    def test_bool_coercion_edge_cases(self, value: str):
        """Boolean coercion should handle any string value."""
        from bengal.directives.options import DirectiveOptions

        result = DirectiveOptions._coerce_value(value, bool)
        assert isinstance(result, bool)

    @given(st.text(max_size=100))
    @settings(max_examples=100)
    def test_int_coercion_edge_cases(self, value: str):
        """Integer coercion should handle any string value."""
        from bengal.directives.options import DirectiveOptions

        result = DirectiveOptions._coerce_value(value, int)
        assert isinstance(result, int)

    @given(st.text(max_size=100))
    @settings(max_examples=100)
    def test_list_coercion_edge_cases(self, value: str):
        """List coercion should handle any string value."""
        from bengal.directives.options import DirectiveOptions

        result = DirectiveOptions._coerce_value(value, list)
        assert isinstance(result, list)
