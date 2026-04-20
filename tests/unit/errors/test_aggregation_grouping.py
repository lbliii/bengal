"""
Unit tests for ErrorCode-aware aggregation helpers (Sprint A4.3).

Covers `group_errors_by_code` and `format_error_code_summary` which power
the build-end summary line.
"""

from __future__ import annotations

import pytest

from bengal.errors import BengalRenderingError, ErrorCode
from bengal.errors.aggregation import (
    format_error_code_summary,
    group_errors_by_code,
)


class TestGroupErrorsByCode:
    def test_empty_returns_empty_dict(self) -> None:
        assert group_errors_by_code([]) == {}

    def test_single_error(self) -> None:
        err = BengalRenderingError("boom", code=ErrorCode.R002)
        assert group_errors_by_code([err]) == {"R002": 1}

    def test_groups_same_code(self) -> None:
        errs = [
            BengalRenderingError("a", code=ErrorCode.R002),
            BengalRenderingError("b", code=ErrorCode.R002),
            BengalRenderingError("c", code=ErrorCode.R004),
        ]
        result = group_errors_by_code(errs)
        assert result == {"R002": 2, "R004": 1}

    def test_sorts_most_frequent_first(self) -> None:
        errs = [
            BengalRenderingError("only", code=ErrorCode.R007),
            BengalRenderingError("a", code=ErrorCode.R002),
            BengalRenderingError("b", code=ErrorCode.R002),
            BengalRenderingError("c", code=ErrorCode.R002),
        ]
        keys = list(group_errors_by_code(errs).keys())
        assert keys[0] == "R002"

    def test_errors_without_code_bucketed_under_none(self) -> None:
        errs = [BengalRenderingError("uncoded")]
        result = group_errors_by_code(errs)
        assert result == {"none": 1}

    def test_mixed_coded_and_uncoded(self) -> None:
        errs = [
            BengalRenderingError("a", code=ErrorCode.R002),
            BengalRenderingError("uncoded"),
        ]
        result = group_errors_by_code(errs)
        assert result["R002"] == 1
        assert result["none"] == 1


class TestFormatErrorCodeSummary:
    def test_empty_returns_empty_string(self) -> None:
        assert format_error_code_summary([]) == ""

    def test_single_error(self) -> None:
        err = BengalRenderingError("boom", code=ErrorCode.R002)
        assert format_error_code_summary([err]) == "1 error (1 [R002])"

    def test_multiple_errors_pluralized(self) -> None:
        errs = [
            BengalRenderingError("a", code=ErrorCode.R002),
            BengalRenderingError("b", code=ErrorCode.R002),
            BengalRenderingError("c", code=ErrorCode.R004),
        ]
        out = format_error_code_summary(errs)
        assert out == "3 errors (2 [R002], 1 [R004])"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
