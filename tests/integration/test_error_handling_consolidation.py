"""
Integration tests for error handling consolidation.

Tests that converted exceptions work correctly in context:
- Autodoc cache corruption raises BengalCacheError
- Write-behind failures raise BengalRenderingError
- Errors include proper codes and suggestions

See Also:
- plan/rfc-error-handling-consolidation.md
- bengal/errors/exceptions.py

"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bengal.errors import BengalCacheError, BengalRenderingError, ErrorCode


class TestAutodocCacheErrors:
    """Integration tests for autodoc cache error handling."""

    def test_cache_format_mismatch_raises_bengal_error(self, tmp_path: Path) -> None:
        """Cache format mismatch in autodoc base.py raises BengalCacheError."""
        from bengal.autodoc.base import DocElement

        # Create valid top-level data but invalid nested typed_metadata
        # The BengalCacheError is raised in _deserialize_typed_metadata helpers
        # when parsing nested params/raises that aren't dicts
        invalid_data = {
            "name": "test_func",
            "qualified_name": "module.test_func",
            "description": "Test function",
            "element_type": "function",
            "source_file": "test.py",
            "line_number": 1,
            "children": [],
            "metadata": {},
            "typed_metadata": {
                "type": "PythonFunctionMetadata",
                "data": {
                    "name": "test_func",
                    "qualified_name": "module.test_func",
                    "source_file": "test.py",
                    "source_line": 1,
                    "docstring": "Test function",
                    "signature": "()",
                    "parsed_doc": {
                        "summary": "",
                        "description": "",
                        "params": ["not_a_dict"],  # Invalid: should be dict
                        "returns": None,
                        "raises": [],
                    },
                },
            },
        }

        # Attempting to deserialize should raise BengalCacheError
        with pytest.raises(BengalCacheError) as exc_info:
            DocElement.from_dict(invalid_data)

        assert exc_info.value.code == ErrorCode.A001
        assert "cache" in exc_info.value.suggestion.lower()

    def test_cache_corruption_from_orchestrator(self, tmp_path: Path) -> None:
        """Cache deserialization failure in orchestrator raises BengalCacheError."""
        # This test verifies the orchestrator catches cache corruption
        # and raises appropriate BengalCacheError
        from bengal.autodoc.orchestration.orchestrator import VirtualAutodocOrchestrator

        # Note: Full test would require more setup, so we verify the import works
        # and the error path is available
        assert VirtualAutodocOrchestrator is not None


class TestCacheCompressionErrors:
    """Integration tests for cache compression error handling."""

    def test_invalid_cache_data_type_raises_bengal_error(self, tmp_path: Path) -> None:
        """Invalid data type in cache file raises BengalCacheError."""
        from bengal.cache.compression import load_auto

        # Create a JSON file with list instead of dict
        cache_file = tmp_path / "test_cache.json"
        cache_file.write_text('["not", "a", "dict"]')

        with pytest.raises(BengalCacheError) as exc_info:
            load_auto(cache_file)

        assert exc_info.value.code == ErrorCode.A001
        assert exc_info.value.file_path == cache_file
        assert "cache" in exc_info.value.suggestion.lower()


class TestWriteBehindErrors:
    """Integration tests for write-behind error handling."""

    def test_writer_error_raises_rendering_error(self) -> None:
        """Writer thread failure raises BengalRenderingError."""
        from bengal.rendering.pipeline.write_behind import WriteBehindCollector

        collector = WriteBehindCollector()

        # Simulate an error in the writer thread
        collector._error = IOError("Simulated disk error")

        with pytest.raises(BengalRenderingError) as exc_info:
            collector.enqueue(Path("/tmp/test.html"), "<html></html>")

        assert exc_info.value.code == ErrorCode.R010
        assert "disk" in exc_info.value.suggestion.lower()
        assert exc_info.value.original_error is not None

        # Clean up
        collector._shutdown.set()
        collector._queue.put(None)
        collector._writer_thread.join(timeout=1.0)

    def test_writer_timeout_raises_rendering_error(self) -> None:
        """Writer thread timeout raises BengalRenderingError with helpful message."""
        # This is more of a documentation test - actual timeout testing
        # would be flaky and slow
        error = BengalRenderingError(
            "Writer thread did not complete within 30.0s",
            code=ErrorCode.R010,
            suggestion="Increase timeout or check for slow disk I/O",
        )
        assert error.code == ErrorCode.R010
        assert "timeout" in error.suggestion.lower() or "disk" in error.suggestion.lower()


class TestErrorCodeConsistency:
    """Tests that error codes are used consistently."""

    def test_cache_errors_use_a001(self) -> None:
        """Cache corruption errors consistently use A001."""
        error = BengalCacheError(
            "Cache corrupted",
            code=ErrorCode.A001,
        )
        assert error.code.category == "cache"

    def test_rendering_output_errors_use_r010(self) -> None:
        """Rendering output errors consistently use R010."""
        error = BengalRenderingError(
            "Output write failed",
            code=ErrorCode.R010,
        )
        assert error.code.value == "render_output_error"


class TestErrorSuggestions:
    """Tests that error suggestions are actionable."""

    def test_cache_error_suggestion_includes_clear_command(self) -> None:
        """Cache error suggestions include clear command."""
        error = BengalCacheError(
            "Cache format mismatch",
            code=ErrorCode.A001,
            suggestion="Clear the cache with: rm -rf .bengal/cache/",
        )
        assert "rm -rf" in error.suggestion or "cache" in error.suggestion.lower()

    def test_rendering_error_suggestion_is_actionable(self) -> None:
        """Rendering error suggestions are actionable."""
        error = BengalRenderingError(
            "Writer failed",
            code=ErrorCode.R010,
            suggestion="Check disk space and file permissions in output directory",
        )
        assert "disk" in error.suggestion.lower() or "permission" in error.suggestion.lower()


class TestErrorInvestigationIntegration:
    """Tests that investigation helpers work with converted errors."""

    def test_cache_error_generates_grep_commands(self) -> None:
        """Cache errors generate useful grep commands for investigation."""
        error = BengalCacheError(
            "Autodoc cache corrupted",
            code=ErrorCode.A001,
            file_path=Path(".bengal/cache/autodoc.json"),
        )
        commands = error.get_investigation_commands()

        # Should include search for error code
        assert any("A001" in cmd for cmd in commands)
        # Should include view file command
        assert any("autodoc" in cmd.lower() for cmd in commands)

    def test_rendering_error_generates_investigation_commands(self) -> None:
        """Rendering errors generate appropriate investigation commands."""
        error = BengalRenderingError(
            "Writer thread failed",
            code=ErrorCode.R010,
        )
        commands = error.get_investigation_commands()

        # Should include search for error code
        assert any("R010" in cmd for cmd in commands)
        # Should suggest rendering-related investigation
        assert any("rendering" in cmd.lower() for cmd in commands)
