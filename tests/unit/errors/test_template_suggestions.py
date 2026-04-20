"""
Unit tests for the template-error suggestion engine in
``bengal.errors.suggestions`` (Sprint A1.3).

Pins the contract for the four functions absorbed from
``bengal/rendering/errors/exceptions.py`` plus the display-time
``enhance_template_suggestions`` helper that replaced the legacy
``_generate_enhanced_suggestions``.
"""

from __future__ import annotations

import pytest

from bengal.errors.suggestions import (
    enhance_template_suggestions,
    find_filter_alternatives,
    find_variable_alternatives,
    generate_template_suggestion,
    identify_none_callable,
    suggest_type_comparison,
)


class _UndefinedLike:
    """Stand-in for kida.UndefinedError in unit tests.

    Real Kida exceptions carry both ``name`` (the unresolved identifier)
    and ``_available_names`` (the in-scope candidate set the resolver
    saw). The function under test reads both attributes via ``getattr``,
    so any object exposing them works.
    """

    def __init__(
        self,
        name: str | None,
        *,
        available_names: frozenset[str] | list[str] | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        self._available_names = available_names


class TestSuggestTypeComparison:
    def test_extracts_type_names_from_message(self) -> None:
        err = TypeError("'<' not supported between instances of 'int' and 'str'")
        msg = suggest_type_comparison(err)

        assert "int" in msg
        assert "str" in msg
        assert "weight" in msg

    def test_falls_back_when_message_unparseable(self) -> None:
        err = TypeError("something unrelated")
        msg = suggest_type_comparison(err)

        assert "mixed types" in msg


class TestIdentifyNoneCallable:
    def test_returns_none_without_traceback(self) -> None:
        assert identify_none_callable(TypeError("oops")) is None

    def test_finds_filter_in_traceback(self, tmp_path) -> None:
        path = tmp_path / "page.html"
        path.write_text("{{ data | format_widget }}\n", encoding="utf-8")

        try:
            raise TypeError("'NoneType' object is not callable")
        except TypeError as exc:
            result = identify_none_callable(exc, path)

        # Without a real Jinja-rendered traceback the only cue is the
        # template scan, but it must produce *something* useful.
        assert result is not None
        assert "format_widget" in result


class TestFindFilterAlternatives:
    def test_returns_empty_when_no_filter_phrase(self) -> None:
        assert find_filter_alternatives(Exception("nope"), ["safe", "len"]) == []

    def test_returns_close_matches(self) -> None:
        err = Exception("No filter named 'fomratdate'")
        matches = find_filter_alternatives(err, ["formatdate", "format_date", "safe"])
        assert "formatdate" in matches

    def test_respects_max_results(self) -> None:
        err = Exception("No filter named 'render'")
        matches = find_filter_alternatives(
            err, ["render_html", "render_text", "render_md", "render_xml"], max_results=2
        )
        assert len(matches) <= 2


class TestFindVariableAlternatives:
    def test_returns_empty_when_error_has_no_name(self) -> None:
        err = _UndefinedLike(None, available_names=frozenset({"page", "site"}))
        assert find_variable_alternatives(err) == []

    def test_prefers_exception_available_names_over_kwarg(self) -> None:
        # When _available_names is present it is the truth — `available_names`
        # kwarg is only a fallback for exceptions that didn't carry one.
        err = _UndefinedLike("titel", available_names=frozenset({"title", "subtitle"}))
        result = find_variable_alternatives(err, available_names=["totally_unrelated"])
        assert "title" in result
        assert "totally_unrelated" not in result

    def test_falls_back_to_available_names_kwarg(self) -> None:
        err = _UndefinedLike("titel", available_names=None)
        result = find_variable_alternatives(err, available_names=["title", "subtitle"])
        assert "title" in result

    def test_returns_empty_when_no_candidate_set(self) -> None:
        err = _UndefinedLike("titel", available_names=None)
        assert find_variable_alternatives(err) == []

    def test_returns_empty_when_no_match_clears_cutoff(self) -> None:
        err = _UndefinedLike("xyz", available_names=frozenset({"alpha", "beta"}))
        assert find_variable_alternatives(err) == []

    def test_respects_max_results(self) -> None:
        err = _UndefinedLike(
            "render",
            available_names=frozenset({"render_html", "render_text", "render_md", "render_xml"}),
        )
        matches = find_variable_alternatives(err, max_results=2)
        assert len(matches) <= 2

    def test_accepts_non_undefined_exceptions_with_name(self) -> None:
        # `getattr(error, "name", None)` means any exception type with a
        # `.name` attribute and `_available_names` works — this lets the
        # helper handle any future Kida exception subclass without churn.
        class _Other(Exception):
            name = "format_datte"
            _available_names = frozenset({"format_date"})

        assert "format_date" in find_variable_alternatives(_Other("ignored"))


class TestGenerateTemplateSuggestion:
    @pytest.mark.parametrize(
        ("error_type", "needle"),
        [
            ("none_access", "None when it should be"),
            ("callable", "function or filter"),
            ("type_comparison", "mixed types"),
        ],
    )
    def test_returns_canned_advice_per_error_type(self, error_type: str, needle: str) -> None:
        err = TypeError("anything")
        result = generate_template_suggestion(err, error_type)
        assert result is not None
        assert needle in result

    def test_filter_in_section_special_case(self) -> None:
        err = Exception("no filter named 'in_section'")
        result = generate_template_suggestion(err, "filter")
        assert result is not None
        assert "in_section" in result

    def test_undefined_metadata_weight_special_case(self) -> None:
        err = Exception("page.metadata.weight is undefined")
        result = generate_template_suggestion(err, "undefined")
        assert result is not None
        assert "page.metadata.get('weight'" in result

    def test_syntax_with_special_case(self) -> None:
        err = Exception("with not supported here")
        result = generate_template_suggestion(err, "syntax")
        assert result is not None
        assert "{% set %}" in result

    def test_unmapped_error_type_returns_none(self) -> None:
        assert generate_template_suggestion(Exception("x"), "totally-novel") is None


class TestEnhanceTemplateSuggestions:
    def test_includes_primary_suggestion_first(self) -> None:
        result = enhance_template_suggestions(
            "syntax", "missing endif", primary_suggestion="primary advice"
        )
        assert result[0] == "primary advice"

    def test_callable_branch_includes_filter_hints_from_source(self) -> None:
        result = enhance_template_suggestions(
            "callable",
            "'NoneType' object is not callable",
            source_line="{{ widget | format_card }}",
        )
        joined = "\n".join(result)
        assert "format_card" in joined

    def test_none_access_branch_includes_for_loop_guard(self) -> None:
        result = enhance_template_suggestions(
            "none_access",
            "'NoneType' object is not iterable",
            source_line="{% for item in section.children %}",
        )
        joined = "\n".join(result)
        assert "section.children" in joined
        assert "{% if section.children %}" in joined

    def test_undefined_dict_attribute_branch(self) -> None:
        result = enhance_template_suggestions(
            "undefined", "'dict object' has no attribute 'author'"
        )
        joined = "\n".join(result)
        assert "Unsafe dict access detected" in joined
        assert "dict.get('author'" in joined

    def test_undefined_typo_branch(self) -> None:
        result = enhance_template_suggestions("undefined", "'titel' is undefined")
        joined = "\n".join(result)
        assert "Common typo" in joined
        assert "title" in joined

    def test_syntax_branch_endif_hint(self) -> None:
        result = enhance_template_suggestions("syntax", "missing endif")
        joined = "\n".join(result)
        assert "endif" in joined
