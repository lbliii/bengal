"""
Unit tests for ``bengal.errors.overlay.transport`` (Sprint A3.2).

Pins the wire schema for ``build_error`` and ``build_ok`` envelopes that
the dev server pushes over SSE to the browser-side overlay client. The
payloads are JSON-serializable dicts; the SSE notifier is the only call
site that ``json.dumps`` them.

The contract these tests pin (sourced from ``rfc-template-error-codes.md``
A0.2 schema):

- Top-level envelope shape: ``type``, ``schema_version``, ``timestamp``,
  plus ``errors`` (build_error) or optional ``build_ms`` (build_ok).
- Per-error projection: code metadata, error_type, title, message,
  optional hint, ranked suggestions, source frame with per-line
  ``is_error`` markers, inclusion chain, and ``page_source``.
- Pure: no I/O, no mutation of the error.
- JSON-serializable: every leaf is a primitive (str/int/None/bool/list/dict).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from bengal.errors import ErrorCode
from bengal.errors.overlay import (
    build_error_payload,
    build_ok_payload,
    error_to_dict,
)
from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError
from bengal.rendering.errors.context import InclusionChain

_MISSING = object()


def _make_error(
    *,
    error_type: str = "filter",
    code: ErrorCode | None = ErrorCode.R004,
    message: str = "No filter named 'format_datte'",
    source_line: str = "      {{ page.date | format_datte }}",
    surrounding_lines: list[tuple[int, str]] | None = None,
    line_number: int = 23,
    column: int | None = 14,
    template_name: str = "templates/post.html",
    template_path: Path | None = _MISSING,  # type: ignore[assignment]
    suggestion: str | None = "Use format_date filter (formats a datetime).",
    alternatives: list[str] | None = None,
    inclusion_chain: list[tuple[str, int]] | None = None,
    page_source: Path | None = None,
    search_paths: list[Path] | None = None,
) -> TemplateRenderError:
    if surrounding_lines is None:
        surrounding_lines = [
            (22, '    <time datetime="{{ page.date }}">'),
            (23, "      {{ page.date | format_datte }}"),
            (24, "    </time>"),
        ]
    if alternatives is None:
        alternatives = ["format_date", "dateformat"]
    if template_path is _MISSING:
        template_path = Path("/repo/templates/post.html")

    chain = InclusionChain(list(inclusion_chain)) if inclusion_chain else None

    return TemplateRenderError(
        error_type=error_type,
        message=message,
        template_context=TemplateErrorContext(
            template_name=template_name,
            line_number=line_number,
            column=column,
            source_line=source_line,
            surrounding_lines=surrounding_lines,
            template_path=template_path,
        ),
        inclusion_chain=chain,
        page_source=page_source,
        suggestion=suggestion,
        available_alternatives=alternatives,
        search_paths=search_paths,
        code=code,
    )


class TestBuildErrorEnvelope:
    def test_top_level_shape(self) -> None:
        payload = build_error_payload([_make_error()])
        assert payload["type"] == "build_error"
        assert payload["schema_version"] == 1
        assert isinstance(payload["timestamp"], str)
        assert payload["timestamp"].endswith("Z")
        assert isinstance(payload["errors"], list)
        assert len(payload["errors"]) == 1

    def test_preserves_error_order(self) -> None:
        e1 = _make_error(message="first")
        e2 = _make_error(message="second")
        e3 = _make_error(message="third")
        payload = build_error_payload([e1, e2, e3])
        assert [e["message"] for e in payload["errors"]] == [
            "first",
            "second",
            "third",
        ]

    def test_timestamp_override_is_used_verbatim(self) -> None:
        ts = datetime(2026, 4, 17, 15, 34, 12, tzinfo=UTC)
        payload = build_error_payload([_make_error()], timestamp=ts)
        assert payload["timestamp"] == "2026-04-17T15:34:12Z"

    def test_naive_timestamp_treated_as_utc(self) -> None:
        ts = datetime(2026, 4, 17, 15, 34, 12)
        payload = build_error_payload([_make_error()], timestamp=ts)
        assert payload["timestamp"] == "2026-04-17T15:34:12Z"

    def test_empty_error_list_still_valid(self) -> None:
        payload = build_error_payload([])
        assert payload["errors"] == []
        assert payload["type"] == "build_error"

    def test_payload_is_json_serializable(self) -> None:
        # If anything leaks an object the SSE notifier can't json.dumps it.
        payload = build_error_payload(
            [
                _make_error(
                    inclusion_chain=[("_base.html", 12), ("post.html", 23)],
                    page_source=Path("content/posts/hello.md"),
                    search_paths=[Path("/repo/templates")],
                )
            ]
        )
        json.dumps(payload)  # raises TypeError on failure


class TestBuildOkEnvelope:
    def test_top_level_shape(self) -> None:
        payload = build_ok_payload()
        assert payload["type"] == "build_ok"
        assert payload["schema_version"] == 1
        assert payload["timestamp"].endswith("Z")
        assert "build_ms" not in payload

    def test_includes_build_ms_when_provided(self) -> None:
        payload = build_ok_payload(build_ms=142)
        assert payload["build_ms"] == 142

    def test_build_ms_coerced_to_int(self) -> None:
        payload = build_ok_payload(build_ms=142.7)
        assert payload["build_ms"] == 142

    def test_payload_is_json_serializable(self) -> None:
        json.dumps(build_ok_payload(build_ms=42))


class TestErrorToDictCodeMetadata:
    def test_includes_code_name_value_and_docs_url(self) -> None:
        err = _make_error(code=ErrorCode.R004)
        d = error_to_dict(err)
        assert d["code"] == "R004"
        assert d["code_name"] == "template_filter_error"
        assert d["docs_url"] == "/docs/reference/errors/#r004"

    def test_code_fields_are_none_when_no_code(self) -> None:
        d = error_to_dict(_make_error(code=None))
        assert d["code"] is None
        assert d["code_name"] is None
        assert d["docs_url"] is None

    def test_includes_error_type(self) -> None:
        d = error_to_dict(_make_error(error_type="filter"))
        assert d["error_type"] == "filter"

    def test_title_derived_from_error_type(self) -> None:
        for et, expected_title in [
            ("syntax", "Template Syntax Error"),
            ("filter", "Unknown Filter"),
            ("undefined", "Undefined Variable"),
            ("callable", "None Is Not Callable"),
            ("totally-unknown", "Template Error"),
        ]:
            d = error_to_dict(_make_error(error_type=et))
            assert d["title"] == expected_title


class TestErrorToDictMessageAndHint:
    def test_includes_message(self) -> None:
        d = error_to_dict(_make_error(message="boom"))
        assert d["message"] == "boom"

    def test_message_does_not_contain_html_escape(self) -> None:
        # Wire format is structured data; escaping is the renderer's job.
        d = error_to_dict(_make_error(message="<script>alert(1)</script>"))
        assert d["message"] == "<script>alert(1)</script>"

    def test_hint_present_when_suggestion_set(self) -> None:
        d = error_to_dict(_make_error(suggestion="Use foo instead."))
        assert d["hint"] == "Use foo instead."

    def test_hint_none_when_no_suggestion(self) -> None:
        d = error_to_dict(_make_error(suggestion=None))
        assert d["hint"] is None


class TestErrorToDictSuggestions:
    def test_alternatives_emitted_as_did_you_mean_items(self) -> None:
        d = error_to_dict(_make_error(alternatives=["format_date", "dateformat"]))
        assert d["suggestions"] == [
            {"label": "Did you mean?", "value": "format_date"},
            {"label": "Did you mean?", "value": "dateformat"},
        ]

    def test_no_suggestions_when_alternatives_empty(self) -> None:
        d = error_to_dict(_make_error(alternatives=[]))
        assert d["suggestions"] == []


class TestErrorToDictFrame:
    def test_frame_includes_file_line_and_column(self) -> None:
        d = error_to_dict(_make_error())
        frame = d["frame"]
        assert frame["file"] == "templates/post.html"
        assert frame["file_abs"] == "/repo/templates/post.html"
        assert frame["line"] == 23
        assert frame["column"] == 14

    def test_lines_marked_with_is_error_on_match(self) -> None:
        d = error_to_dict(_make_error())
        lines = d["frame"]["lines"]
        # Only line 23 should be marked.
        for line in lines:
            if line["n"] == 23:
                assert line.get("is_error") is True
            else:
                assert "is_error" not in line

    def test_file_abs_none_when_no_template_path(self) -> None:
        d = error_to_dict(_make_error(template_path=None))
        assert d["frame"]["file_abs"] is None
        assert d["frame"]["file"] == "templates/post.html"


class TestErrorToDictInclusionChain:
    def test_chain_emitted_as_template_line_dicts(self) -> None:
        d = error_to_dict(_make_error(inclusion_chain=[("_base.html", 12), ("post.html", 23)]))
        assert d["inclusion_chain"] == [
            {"template": "_base.html", "line": 12},
            {"template": "post.html", "line": 23},
        ]

    def test_chain_empty_when_absent(self) -> None:
        d = error_to_dict(_make_error(inclusion_chain=None))
        assert d["inclusion_chain"] == []


class TestErrorToDictPageSourceAndSearchPaths:
    def test_page_source_stringified(self) -> None:
        d = error_to_dict(_make_error(page_source=Path("content/posts/hi.md")))
        assert d["page_source"] == "content/posts/hi.md"

    def test_page_source_none_when_absent(self) -> None:
        d = error_to_dict(_make_error(page_source=None))
        assert d["page_source"] is None

    def test_search_paths_stringified(self) -> None:
        d = error_to_dict(
            _make_error(
                search_paths=[Path("/a"), Path("/b")],
            )
        )
        assert d["search_paths"] == ["/a", "/b"]

    def test_search_paths_empty_when_absent(self) -> None:
        d = error_to_dict(_make_error(search_paths=None))
        assert d["search_paths"] == []


class TestPurity:
    def test_does_not_mutate_error(self) -> None:
        err = _make_error()
        before = (
            err.error_type,
            err.message,
            err.suggestion,
            tuple(err.available_alternatives),
            err.code,
        )
        error_to_dict(err)
        build_error_payload([err])
        after = (
            err.error_type,
            err.message,
            err.suggestion,
            tuple(err.available_alternatives),
            err.code,
        )
        assert before == after
