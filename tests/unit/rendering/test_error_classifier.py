"""
Unit tests for ``bengal.rendering.errors.classifier`` (Sprint A1.1).

Covers the canonical ``ErrorClassifier.classify`` mapping per
``plan/rfc-template-error-codes.md`` Part 3 (one test per ErrorCode in
the classification table) plus parametrized message-based tests for the
TypeError sub-categories (R015/R016/R017).
"""

from __future__ import annotations

import pytest
from kida.environment.exceptions import (
    TemplateRuntimeError,
    TemplateSyntaxError,
    UndefinedError,
)

from bengal.errors.codes import ErrorCode
from bengal.rendering.errors.classifier import (
    ErrorClassifier,
    build_inclusion_chain,
    classify_legacy,
    find_first_code_line,
)


@pytest.fixture
def classifier() -> ErrorClassifier:
    return ErrorClassifier()


class TestClassifyByExceptionType:
    """One test per ErrorCode reachable via exception-type dispatch."""

    def test_syntax_error_maps_to_r002(self, classifier: ErrorClassifier) -> None:
        exc = TemplateSyntaxError("unexpected '%}'", lineno=1)
        assert classifier.classify(exc) == ErrorCode.R002

    def test_undefined_error_maps_to_r003(self, classifier: ErrorClassifier) -> None:
        exc = UndefinedError("'page' is undefined")
        assert classifier.classify(exc) == ErrorCode.R003

    def test_runtime_error_maps_to_r014(self, classifier: ErrorClassifier) -> None:
        exc = TemplateRuntimeError("loop divided by zero")
        assert classifier.classify(exc) == ErrorCode.R014

    def test_unknown_exception_falls_back_to_r010(self, classifier: ErrorClassifier) -> None:
        exc = RuntimeError("something unspecified")
        assert classifier.classify(exc) == ErrorCode.R010


class TestClassifyByMessage:
    """Message-based dispatch within a TypeError or generic exception."""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("'NoneType' object is not callable", ErrorCode.R015),
            ("nonetype object is not callable", ErrorCode.R015),
        ],
    )
    def test_callable_error_maps_to_r015(
        self, classifier: ErrorClassifier, message: str, expected: ErrorCode
    ) -> None:
        assert classifier.classify(TypeError(message)) == expected

    @pytest.mark.parametrize(
        "message",
        [
            "'<' not supported between instances of 'int' and 'str'",
            "'>' not supported between instances of 'NoneType' and 'int'",
        ],
    )
    def test_type_comparison_maps_to_r017(self, classifier: ErrorClassifier, message: str) -> None:
        assert classifier.classify(TypeError(message)) == ErrorCode.R017

    @pytest.mark.parametrize(
        "message",
        [
            "argument of type 'NoneType' is not iterable",
            "'NoneType' object is not iterable",
            "'NoneType' object is not subscriptable",
            "'NoneType' has no attribute 'title'",
        ],
    )
    def test_none_access_maps_to_r016(self, classifier: ErrorClassifier, message: str) -> None:
        assert classifier.classify(TypeError(message)) == ErrorCode.R016

    @pytest.mark.parametrize(
        "message",
        [
            "no filter named 'format_dat'",
            "filter 'fmt' not found",
            "unknown filter 'truncatewords'",
        ],
    )
    def test_filter_error_maps_to_r004_via_message(
        self, classifier: ErrorClassifier, message: str
    ) -> None:
        # Plain Exception so we exercise the message-based filter heuristic.
        assert classifier.classify(Exception(message)) == ErrorCode.R004

    def test_unknown_filter_phrase_maps_to_r004(self, classifier: ErrorClassifier) -> None:
        assert classifier.classify(Exception("unknown filter")) == ErrorCode.R004


class TestBranchOrderPriority:
    """TypeError sub-categories must beat the generic-exception fallbacks."""

    def test_typeerror_callable_beats_runtime_check(self, classifier: ErrorClassifier) -> None:
        # TypeError is not a TemplateRuntimeError, but if branch order
        # ever broke we'd fall through to R010 — verify R015 still wins.
        exc = TypeError("'NoneType' object is not callable")
        assert classifier.classify(exc) == ErrorCode.R015


class TestLegacyShim:
    """``classify_legacy`` returns the pre-A1.1 string constants."""

    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (TemplateSyntaxError("oops", lineno=1), "syntax"),
            (UndefinedError("nope"), "undefined"),
            (TemplateRuntimeError("boom"), "runtime"),
            (TypeError("'NoneType' object is not callable"), "callable"),
            (TypeError("'NoneType' object is not iterable"), "none_access"),
            (
                TypeError("'<' not supported between instances of 'int' and 'str'"),
                "type_comparison",
            ),
            (Exception("no filter named 'x'"), "filter"),
            (RuntimeError("???"), "other"),
        ],
    )
    def test_classify_legacy_round_trip(self, exc: BaseException, expected: str) -> None:
        assert classify_legacy(exc) == expected


class TestBuildInclusionChain:
    """Inclusion-chain extraction from ``__traceback__``."""

    def test_no_template_frames_returns_none(self) -> None:
        try:
            raise RuntimeError("not a template error")
        except RuntimeError as exc:
            result = build_inclusion_chain(exc)
        assert result is None

    def test_template_frames_produce_chain(self) -> None:
        # Synthesize a frame whose code object reports a templates/ path by
        # compiling source against that filename, then executing it.
        src = compile(
            "raise RuntimeError('boom')",
            "/tmp/site/templates/page.html",
            "exec",
        )
        try:
            exec(src, {})  # noqa: S102
        except RuntimeError as exc:
            chain = build_inclusion_chain(exc)
        assert chain is not None
        entries = list(chain.entries)
        assert ("page.html", 1) in entries


class TestFindFirstCodeLine:
    """Heuristic that locates a likely failure line for TypeError."""

    def test_returns_one_for_empty_input(self) -> None:
        assert find_first_code_line([], TypeError("x")) == 1

    def test_skips_jinja_comment_blocks(self) -> None:
        lines = [
            "{# header comment #}",
            "{# multi",
            "    line comment #}",
            "{{ page.title }}",
        ]
        # No callable patterns, so we get the first non-comment line: 4.
        assert find_first_code_line(lines, RuntimeError("x")) == 4

    def test_skips_multiline_comment_interior(self) -> None:
        # Three-line comment so the middle line takes the in_comment branch.
        lines = [
            "{# start",
            "  middle comment line",
            "  end of comment #}",
            "{{ page.title }}",
        ]
        assert find_first_code_line(lines, RuntimeError("x")) == 4

    def test_typeerror_prefers_callable_line(self) -> None:
        lines = [
            "{# leading comment #}",
            "{{ static_var }}",
            "{{ render_page(page) }}",
        ]
        assert find_first_code_line(lines, TypeError("x")) == 3

    def test_non_typeerror_returns_first_code_line(self) -> None:
        lines = [
            "",
            "{# comment #}",
            "{{ static_var }}",
            "{{ another_call() }}",
        ]
        # Not a TypeError — return the first code line, not the call site.
        assert find_first_code_line(lines, RuntimeError("x")) == 3
