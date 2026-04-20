"""
Unit tests for ``bengal.errors.overlay.renderer`` (Sprint A3.1).

Pins the contract for the HTML overlay renderer that displays
:class:`TemplateRenderError` to a developer hitting the failed page in
their browser. The renderer must be:

- **Pure**: no I/O beyond the bundled template; no mutation of the error.
- **Self-contained**: the returned string is a complete ``<!doctype html>``
  document with inline styles. No external CSS/JS dependencies.
- **Safe**: every user-controlled string (template names, source code,
  error messages) is HTML-escaped before substitution. The ``reload_script``
  parameter is the only verbatim-injected hook.
- **Surface-complete**: every section the terminal renderer surfaces
  (code window, alternatives, inclusion chain, search paths, docs URL,
  collapsible stack) appears in the overlay when the underlying data is
  present, and is omitted when absent.
"""

from __future__ import annotations

from pathlib import Path

from bengal.errors import ErrorCode
from bengal.errors.overlay import render_error_page
from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError


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
    template_path: Path | None = None,
    suggestion: str | None = "Use format_date filter (formats a datetime).",
    alternatives: list[str] | None = None,
    inclusion_chain: list[tuple[str, int]] | None = None,
    page_source: Path | None = None,
    search_paths: list[Path] | None = None,
) -> TemplateRenderError:
    if surrounding_lines is None:
        surrounding_lines = [
            (20, "<article>"),
            (21, "  <header>"),
            (22, '    <time datetime="{{ page.date }}">'),
            (23, "      {{ page.date | format_datte }}"),
            (24, "    </time>"),
            (25, "  </header>"),
            (26, "</article>"),
        ]
    if alternatives is None:
        alternatives = ["format_date", "dateformat"]
    if template_path is None:
        template_path = Path("/repo/templates/post.html")

    chain = None
    if inclusion_chain:
        from bengal.rendering.errors.context import InclusionChain

        chain = InclusionChain(list(inclusion_chain))

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


class TestStructure:
    def test_returns_complete_html_document(self) -> None:
        out = render_error_page(_make_error())
        assert out.startswith("<!doctype html>")
        assert out.rstrip().endswith("</html>")
        assert '<meta charset="utf-8">' in out

    def test_page_title_is_escaped(self) -> None:
        out = render_error_page(_make_error(), page_title='X<script>"&y')
        assert "<title>X&lt;script&gt;&quot;&amp;y</title>" in out

    def test_default_page_title(self) -> None:
        out = render_error_page(_make_error())
        assert "<title>Build Error — Bengal</title>" in out


class TestHeader:
    def test_renders_code_badge_for_each_error_code(self) -> None:
        for code, label in [
            (ErrorCode.R002, "Template Syntax Error"),
            (ErrorCode.R003, "Undefined Variable"),
            (ErrorCode.R004, "Unknown Filter"),
            (ErrorCode.R015, "None Is Not Callable"),
        ]:
            error_type_for_label = {
                "Template Syntax Error": "syntax",
                "Undefined Variable": "undefined",
                "Unknown Filter": "filter",
                "None Is Not Callable": "callable",
            }[label]
            out = render_error_page(_make_error(error_type=error_type_for_label, code=code))
            assert f">{code.name}<" in out
            assert f">{label}<" in out

    def test_falls_back_to_error_label_when_code_missing(self) -> None:
        out = render_error_page(_make_error(code=None))
        assert ">ERROR<" in out

    def test_unknown_error_type_uses_generic_label(self) -> None:
        out = render_error_page(_make_error(error_type="totally-novel"))
        assert ">Template Error<" in out


class TestFileLocation:
    def test_renders_template_path_with_line_and_column(self) -> None:
        out = render_error_page(_make_error())
        assert "/repo/templates/post.html:23:14" in out

    def test_falls_back_to_template_name_when_path_missing(self) -> None:
        out = render_error_page(_make_error(template_path=None))
        assert "templates/post.html:23" in out

    def test_omits_column_when_none(self) -> None:
        out = render_error_page(_make_error(column=None))
        assert "/repo/templates/post.html:23<" in out
        assert ":23:" not in out


class TestCodeFrame:
    def test_renders_each_surrounding_line_with_line_number(self) -> None:
        out = render_error_page(_make_error())
        for line_num in (20, 21, 22, 23, 24, 25, 26):
            assert f">{line_num:>4}<" in out

    def test_marks_error_line_with_is_error_class(self) -> None:
        out = render_error_page(_make_error())
        assert 'class="line is-error"' in out
        # Exactly one error line.
        assert out.count('class="line is-error"') == 1

    def test_caret_line_present_under_error_line(self) -> None:
        out = render_error_page(_make_error())
        assert '<span class="caret">' in out
        # Caret count derives from stripped source_line length, capped at 40.
        # source_line = "      {{ page.date | format_datte }}" → strip → 30 chars.
        assert "^" * 30 in out

    def test_caret_omitted_when_no_source_line(self) -> None:
        err = _make_error(source_line="")
        out = render_error_page(err)
        assert '<span class="caret">' not in out

    def test_omits_frame_section_when_no_surrounding_lines(self) -> None:
        out = render_error_page(_make_error(surrounding_lines=[]))
        assert "<header>Code</header>" not in out

    def test_html_escapes_source_lines(self) -> None:
        err = _make_error(
            surrounding_lines=[
                (1, "<script>alert(1)</script>"),
                (2, "{{ page.title | safe }}"),
            ],
            line_number=2,
            source_line="{{ page.title | safe }}",
        )
        out = render_error_page(err)
        assert "<script>alert(1)</script>" not in out
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


class TestSuggestionAndAlternatives:
    def test_renders_hint_section_when_suggestion_present(self) -> None:
        out = render_error_page(_make_error())
        assert "<header>Hint</header>" in out
        assert "Use format_date filter" in out

    def test_omits_hint_section_when_no_suggestion(self) -> None:
        out = render_error_page(_make_error(suggestion=None))
        assert "<header>Hint</header>" not in out

    def test_promotes_top_alternative_in_headline(self) -> None:
        out = render_error_page(_make_error())
        assert "<header>Did you mean?</header>" in out
        assert 'Did you mean <code class="alt-top-name">format_date</code>?' in out

    def test_renders_remaining_alternatives_as_secondary_list(self) -> None:
        out = render_error_page(_make_error(alternatives=["format_date", "dateformat", "fmt_date"]))
        assert "Other close matches" in out
        assert "<li>dateformat</li>" in out
        assert "<li>fmt_date</li>" in out
        # Top match is not duplicated in the secondary list.
        assert "<li>format_date</li>" not in out

    def test_omits_secondary_list_when_only_one_alternative(self) -> None:
        out = render_error_page(_make_error(alternatives=["format_date"]))
        assert 'Did you mean <code class="alt-top-name">format_date</code>?' in out
        assert "Other close matches" not in out

    def test_omits_alternatives_section_when_empty(self) -> None:
        out = render_error_page(_make_error(alternatives=[]))
        assert "<header>Did you mean?</header>" not in out

    def test_html_escapes_suggestion_and_alternatives(self) -> None:
        err = _make_error(
            suggestion="<b>bold</b>",
            alternatives=["<top>", "<script>", "safe_name"],
        )
        out = render_error_page(err)
        assert "<b>bold</b>" not in out
        assert "&lt;b&gt;bold&lt;/b&gt;" in out
        # Top match is escaped inside the headline.
        assert 'Did you mean <code class="alt-top-name">&lt;top&gt;</code>?' in out
        # Remaining matches escaped inside the secondary list.
        assert "<li><script></li>" not in out
        assert "<li>&lt;script&gt;</li>" in out


class TestInclusionChain:
    def test_renders_chain_when_present(self) -> None:
        out = render_error_page(
            _make_error(
                inclusion_chain=[("_base.html", 12), ("post.html", 23)],
            )
        )
        assert "<header>Template Chain</header>" in out
        assert "<strong>_base.html</strong>:12" in out
        assert "<strong>post.html</strong>:23" in out

    def test_omits_chain_when_absent(self) -> None:
        out = render_error_page(_make_error(inclusion_chain=None))
        assert "<header>Template Chain</header>" not in out


class TestPageSourceAndSearchPaths:
    def test_renders_page_source_when_present(self) -> None:
        out = render_error_page(_make_error(page_source=Path("content/posts/hello.md")))
        assert "<header>Used by Page</header>" in out
        assert "content/posts/hello.md" in out

    def test_omits_page_source_when_absent(self) -> None:
        out = render_error_page(_make_error(page_source=None))
        assert "<header>Used by Page</header>" not in out

    def test_renders_search_paths_with_found_marker(self) -> None:
        out = render_error_page(
            _make_error(
                template_path=Path("/repo/templates/post.html"),
                search_paths=[
                    Path("/repo/templates"),
                    Path("/repo/themes/default/templates"),
                ],
            )
        )
        assert "<header>Template Search Paths</header>" in out
        assert "1. /repo/templates" in out
        assert "found here" in out
        assert "2. /repo/themes/default/templates" in out


class TestDocsLink:
    def test_renders_docs_url_when_code_present(self) -> None:
        out = render_error_page(_make_error(code=ErrorCode.R004))
        assert "<header>Documentation</header>" in out
        assert 'href="https://lbliii.github.io/bengal' in out

    def test_omits_docs_when_code_missing(self) -> None:
        out = render_error_page(_make_error(code=None))
        assert "<header>Documentation</header>" not in out


class TestStackSection:
    def test_omits_stack_by_default(self) -> None:
        out = render_error_page(_make_error())
        assert "<header>Stack Trace</header>" not in out

    def test_renders_stack_when_show_traceback_true(self) -> None:
        try:
            raise ValueError("inner cause")
        except ValueError as exc:
            err = _make_error()
            err._show_traceback = True
            err._original_exception = exc
            out = render_error_page(err)

        assert "<header>Stack Trace</header>" in out
        assert "ValueError" in out
        assert "inner cause" in out

    def test_omits_stack_when_no_original_exception(self) -> None:
        err = _make_error()
        err._show_traceback = True
        # No _original_exception set.
        out = render_error_page(err)
        assert "<header>Stack Trace</header>" not in out


class TestReloadScript:
    def test_injects_reload_script_verbatim(self) -> None:
        marker = '<script>console.log("test-marker")</script>'
        out = render_error_page(_make_error(), reload_script=marker)
        assert marker in out

    def test_no_script_by_default(self) -> None:
        out = render_error_page(_make_error())
        assert "<script>" not in out


class TestErrorMessage:
    def test_html_escapes_error_message(self) -> None:
        out = render_error_page(_make_error(message='<img src=x onerror="x">'))
        assert '<img src=x onerror="x">' not in out
        assert "&lt;img" in out
