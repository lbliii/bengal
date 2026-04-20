"""
Unit tests for the JSON error-format output (Sprint A4.2).

Verifies the schema produced by `_print_errors_json` so editor integrations
have a stable contract to depend on.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.cli.milo_commands.build import _print_errors_json
from bengal.errors import ErrorCode
from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError


def _make_template_error(
    code: ErrorCode = ErrorCode.R002,
    *,
    error_type: str = "syntax",
    template_name: str = "page.html",
    line: int = 3,
) -> TemplateRenderError:
    return TemplateRenderError(
        error_type=error_type,
        message="boom",
        template_context=TemplateErrorContext(
            template_name=template_name,
            line_number=line,
            column=None,
            source_line="{{ x }}",
            surrounding_lines=[(line - 1, "before"), (line, "{{ x }}"), (line + 1, "after")],
            template_path=Path(f"/tmp/{template_name}"),
        ),
        inclusion_chain=None,
        page_source=None,
        suggestion=None,
        available_alternatives=[],
        code=code,
    )


def _capture_json(mock_cli: MagicMock) -> dict:
    call = mock_cli.render_write.call_args
    template_name = call.args[0] if call.args else call.kwargs.get("template")
    assert template_name == "json_output.kida"
    payload = call.kwargs.get("data")
    assert isinstance(payload, str)
    return json.loads(payload)


class TestPrintErrorsJson:
    def test_no_errors_emits_empty_list(self) -> None:
        stats = MagicMock()
        stats.template_errors = []
        cli = MagicMock()

        _print_errors_json(stats, cli)

        data = _capture_json(cli)
        assert data["errors"] == []
        assert data["summary"] == {"total": 0, "by_code": {}}

    def test_single_error_serialized(self) -> None:
        err = _make_template_error()
        stats = MagicMock()
        stats.template_errors = [err]
        cli = MagicMock()

        _print_errors_json(stats, cli)

        data = _capture_json(cli)
        assert data["summary"] == {"total": 1, "by_code": {"R002": 1}}
        assert len(data["errors"]) == 1
        entry = data["errors"][0]
        assert entry["code"] == "R002"
        assert entry["error_type"] == "syntax"
        assert entry["frame"]["file"] == "page.html"
        assert entry["frame"]["line"] == 3

    def test_summary_groups_codes(self) -> None:
        errs = [
            _make_template_error(code=ErrorCode.R002),
            _make_template_error(code=ErrorCode.R002),
            _make_template_error(code=ErrorCode.R004, error_type="filter"),
        ]
        stats = MagicMock()
        stats.template_errors = errs
        cli = MagicMock()

        _print_errors_json(stats, cli)

        data = _capture_json(cli)
        assert data["summary"]["total"] == 3
        # group_errors_by_code sorts most-frequent first
        assert next(iter(data["summary"]["by_code"].items())) == ("R002", 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
