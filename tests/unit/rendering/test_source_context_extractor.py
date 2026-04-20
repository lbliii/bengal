"""
Unit tests for ``bengal.rendering.errors.context_extractor`` (Sprint A1.2).

Covers the extraction path that the legacy
``TemplateRenderError._extract_context`` method used to handle: file
I/O, surrounding-line slicing, TypeError traceback walking, and
template scanning for callable suspects.

Existing fixtures in ``tests/unit/rendering/test_template_errors.py``
exercise the full extraction path through ``TemplateRenderError``;
these tests pin the decoupled component so future refactors don't have
to keep the wider class around.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.rendering.errors.context_extractor import (
    SourceContextExtractor,
    scan_template_for_callables,
)

if TYPE_CHECKING:
    from pathlib import Path


class _StubEngine:
    """Mimics ``TemplateEngine._find_template_path``."""

    def __init__(self, path: Path | None) -> None:
        self._path = path

    def _find_template_path(self, _name: str) -> Path | None:
        return self._path


def _write_template(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def extractor() -> SourceContextExtractor:
    return SourceContextExtractor()


class TestExtract:
    def test_returns_lineno_and_filename_from_exception(
        self, extractor: SourceContextExtractor, tmp_path: Path
    ) -> None:
        path = _write_template(tmp_path, "page.html", "{{ page.title }}\n")
        engine = _StubEngine(path)

        err = SyntaxError("bad")
        err.lineno = 1
        err.filename = "page.html"

        ctx = extractor.extract(err, "fallback.html", engine)

        assert ctx.template_name == "page.html"
        assert ctx.line_number == 1
        assert ctx.template_path == path
        assert ctx.source_line == "{{ page.title }}"

    def test_uses_fallback_filename_when_exception_has_none(
        self, extractor: SourceContextExtractor, tmp_path: Path
    ) -> None:
        path = _write_template(tmp_path, "page.html", "x\n")
        engine = _StubEngine(path)

        ctx = extractor.extract(RuntimeError("oops"), "page.html", engine)

        assert ctx.template_name == "page.html"
        # No lineno → no source slicing.
        assert ctx.source_line is None
        assert ctx.surrounding_lines == []

    def test_surrounding_lines_window_clipped_to_file_bounds(
        self, extractor: SourceContextExtractor, tmp_path: Path
    ) -> None:
        body = "\n".join(f"line {i}" for i in range(1, 11)) + "\n"
        path = _write_template(tmp_path, "page.html", body)
        engine = _StubEngine(path)

        err = SyntaxError("bad")
        err.lineno = 5
        err.filename = "page.html"

        ctx = extractor.extract(err, "page.html", engine)

        # ±3 lines around line 5 = lines 2..8 inclusive.
        line_numbers = [n for n, _ in ctx.surrounding_lines]
        assert line_numbers == [2, 3, 4, 5, 6, 7, 8]
        assert ctx.source_line == "line 5"

    def test_first_line_comment_promotes_to_first_code_line(
        self, extractor: SourceContextExtractor, tmp_path: Path
    ) -> None:
        # Reported lineno=1 but line 1 is a comment — extractor should
        # forward to the first real code line via find_first_code_line.
        body = "{# header #}\n\n{{ page.title }}\n"
        path = _write_template(tmp_path, "page.html", body)
        engine = _StubEngine(path)

        err = SyntaxError("bad")
        err.lineno = 1
        err.filename = "page.html"

        ctx = extractor.extract(err, "page.html", engine)

        assert ctx.line_number == 3
        assert ctx.source_line == "{{ page.title }}"

    def test_missing_template_path_returns_context_without_source(
        self, extractor: SourceContextExtractor
    ) -> None:
        engine = _StubEngine(None)
        err = SyntaxError("bad")
        err.lineno = 5
        err.filename = "page.html"

        ctx = extractor.extract(err, "page.html", engine)

        assert ctx.template_name == "page.html"
        assert ctx.template_path is None
        assert ctx.source_line is None
        assert ctx.surrounding_lines == []

    def test_typeerror_walks_traceback_for_template_frame(
        self, extractor: SourceContextExtractor, tmp_path: Path
    ) -> None:
        # Compile against a fake templates/ filename so the traceback
        # frame carries the expected marker.
        src = compile(
            "raise TypeError(\"'NoneType' object is not callable\")",
            "/tmp/site/templates/macros/widgets.html",
            "exec",
        )
        path = _write_template(tmp_path, "widgets.html", "{{ render_widget() }}\n")
        engine = _StubEngine(path)

        try:
            exec(src, {})  # noqa: S102
        except TypeError as exc:
            ctx = extractor.extract(exc, "fallback.html", engine)

        # Filename should be promoted from the templates/ frame.
        assert ctx.template_name == "macros/widgets.html"
        assert ctx.line_number == 1


class TestScanTemplateForCallables:
    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        assert scan_template_for_callables(tmp_path / "nope.html") == []

    def test_skips_known_safe_callables(self, tmp_path: Path) -> None:
        path = _write_template(
            tmp_path,
            "page.html",
            "{{ len(items) }}\n{{ range(10) }}\n",
        )
        assert scan_template_for_callables(path) == []

    def test_finds_unknown_function_and_filter(self, tmp_path: Path) -> None:
        path = _write_template(
            tmp_path,
            "page.html",
            "{{ render_card(page) }}\n{{ title | format_title }}\n",
        )

        suspects = scan_template_for_callables(path)

        assert "function 'render_card'" in suspects
        assert "filter 'format_title'" in suspects
