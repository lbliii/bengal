"""Test that excerpt extraction failures are logged, not silently swallowed (Bug 3)."""

from __future__ import annotations

from unittest.mock import patch

from bengal.parsing.backends.patitas.wrapper import PatitasParser


def test_excerpt_extraction_failure_logs_warning() -> None:
    """When extract_excerpt raises, logger.warning is called with exc_info."""
    parser = PatitasParser()
    metadata = {"_source_path": "content/posts/test.md", "_excerpt_length": 160}

    with (
        patch("bengal.parsing.backends.patitas.wrapper.logger") as mock_logger,
        patch("patitas.extract_excerpt", side_effect=ValueError("extract failed")),
    ):
        result = parser.parse_with_toc("# Hi\n\nBody text.", metadata)

    # Should still return valid HTML (graceful degradation)
    assert result[0]  # html
    assert result[1]  # toc
    assert result[2] == ""  # excerpt empty on failure
    assert result[3] == ""  # meta_desc empty on failure

    # Logger should have been called with excerpt_extraction_failed
    mock_logger.warning.assert_called()
    calls = [
        c
        for c in mock_logger.warning.call_args_list
        if c[0] and c[0][0] == "excerpt_extraction_failed"
    ]
    assert len(calls) >= 1, "Expected excerpt_extraction_failed warning"
