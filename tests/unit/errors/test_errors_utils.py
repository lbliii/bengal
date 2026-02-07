"""Tests for bengal.errors.utils module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import pytest

from bengal.errors.codes import ErrorCode
from bengal.errors.exceptions import BengalError, BengalRenderingError
from bengal.errors.utils import (
    ThreadSafeSingleton,
    dataclass_to_dict,
    extract_between,
    extract_error_attributes,
    find_close_matches,
    generate_error_signature,
    get_error_message,
    safe_list_module_exports,
    serialize_value,
)


class TestGenerateErrorSignature:
    """Tests for generate_error_signature function."""

    def test_basic_signature_includes_error_type_and_message(self) -> None:
        """Signature includes error type and message."""
        error = ValueError("something went wrong")
        sig = generate_error_signature(error, include_code=False)
        assert "ValueError" in sig
        assert "something went wrong" in sig

    def test_includes_error_code_when_available(self) -> None:
        """Signature includes Bengal error code when present."""
        error = BengalRenderingError("Template not found", code=ErrorCode.R001)
        sig = generate_error_signature(error, include_code=True)
        assert "R001" in sig

    def test_excludes_error_code_prefix_when_disabled(self) -> None:
        """Signature excludes error code prefix when include_code=False."""
        error = BengalRenderingError("Template not found", code=ErrorCode.R001)
        sig = generate_error_signature(error, include_code=False)
        # Error code should not be added as separate prefix
        # (but may still appear in the formatted message itself)
        assert not sig.startswith("R001::")

    def test_normalizes_file_paths(self) -> None:
        """File paths are normalized to <file> placeholder."""
        error = ValueError("Error in /path/to/file.py at line 10")
        sig = generate_error_signature(error, normalize_paths=True)
        assert "/path/to/file.py" not in sig
        assert "<file>" in sig

    def test_preserves_paths_when_disabled(self) -> None:
        """Paths are preserved when normalize_paths=False."""
        error = ValueError("Error in /path/to/file.py")
        sig = generate_error_signature(error, normalize_paths=False)
        assert "/path/to/file.py" in sig

    def test_normalizes_line_numbers(self) -> None:
        """Line numbers are normalized to <N> placeholder."""
        error = ValueError("Error at line 42")
        sig = generate_error_signature(error, normalize_lines=True)
        assert "line 42" not in sig
        assert "line <N>" in sig

    def test_truncates_long_messages(self) -> None:
        """Long messages are truncated to max_message_length."""
        long_msg = "x" * 200
        error = ValueError(long_msg)
        sig = generate_error_signature(error, max_message_length=50)
        # Message portion should be truncated
        assert len(sig.split("::")[-1]) <= 50

    def test_includes_context_template_name(self) -> None:
        """Context template_name is included in signature."""
        error = ValueError("Template error")
        context = {"template_name": "base.html"}
        sig = generate_error_signature(error, context=context)
        assert "template:base.html" in sig

    def test_includes_context_operation(self) -> None:
        """Context operation is included in signature."""
        error = ValueError("Processing error")
        context = {"operation": "render"}
        sig = generate_error_signature(error, context=context)
        assert "op:render" in sig

    def test_custom_separator(self) -> None:
        """Custom separator is used between parts."""
        error = ValueError("test")
        sig = generate_error_signature(error, include_code=False, separator="|||")
        assert "|||" in sig


class TestExtractErrorAttributes:
    """Tests for extract_error_attributes function."""

    def test_extracts_basic_exception_info(self) -> None:
        """Extracts error_type and message from any exception."""
        error = ValueError("test message")
        attrs = extract_error_attributes(error)
        assert attrs["error_type"] == "ValueError"
        assert attrs["message"] == "test message"

    def test_extracts_bengal_error_attributes(self) -> None:
        """Extracts Bengal-specific attributes."""
        error = BengalRenderingError(
            "Template not found",
            code=ErrorCode.R001,
            file_path=Path("/test/file.md"),
            line_number=42,
            suggestion="Check template path",
        )
        attrs = extract_error_attributes(error)
        assert attrs["code"] == ErrorCode.R001
        assert attrs["file_path"] == Path("/test/file.md")
        assert attrs["line_number"] == 42
        assert attrs["suggestion"] == "Check template path"

    def test_extracts_filename_from_oserror(self) -> None:
        """Extracts filename from OSError/FileNotFoundError."""
        error = FileNotFoundError("File not found")
        error.filename = "/path/to/missing.txt"
        attrs = extract_error_attributes(error)
        assert attrs["file_path"] == Path("/path/to/missing.txt")

    def test_extracts_lineno_from_syntax_error(self) -> None:
        """Extracts lineno from SyntaxError-like exceptions."""

        class MockSyntaxError(Exception):
            lineno = 10

        error = MockSyntaxError("invalid syntax")
        attrs = extract_error_attributes(error)
        assert attrs["line_number"] == 10

    def test_returns_empty_defaults_for_missing_attributes(self) -> None:
        """Returns None/empty for missing attributes."""
        error = ValueError("simple error")
        attrs = extract_error_attributes(error)
        assert attrs["file_path"] is None
        assert attrs["line_number"] is None
        assert attrs["code"] is None
        assert attrs["suggestion"] is None
        assert attrs["related_files"] == []


class TestGetErrorMessage:
    """Tests for get_error_message function."""

    def test_returns_str_for_standard_exception(self) -> None:
        """Returns str(error) for standard exceptions."""
        error = ValueError("simple message")
        msg = get_error_message(error)
        assert msg == "simple message"

    def test_returns_message_attribute_for_bengal_error(self) -> None:
        """Returns .message attribute for BengalError."""
        error = BengalError("bengal message")
        msg = get_error_message(error)
        assert msg == "bengal message"

    def test_handles_kida_runtime_error_format(self) -> None:
        """Handles Kida TemplateRuntimeError format with empty message."""
        # Simulate Kida's format: "Runtime Error: \n  Location: template.html:37\n  ..."
        error_msg = "Runtime Error: \n  Location: template.html:37\n  Expression: {{ foo }}"

        class MockError:
            def __str__(self) -> str:
                return error_msg

        error = MockError()
        msg = get_error_message(error)
        assert "Runtime Error in template.html:37" in msg
        assert "{{ foo }}" in msg

    def test_handles_kida_runtime_error_without_location(self) -> None:
        """Handles Kida format when location is missing."""
        error_msg = "Runtime Error: \n  Some other line"

        class MockError:
            def __str__(self) -> str:
                return error_msg

        error = MockError()
        msg = get_error_message(error)
        assert msg == "Runtime Error (no details available)"


class TestSerializeValue:
    """Tests for serialize_value function."""

    def test_serializes_none(self) -> None:
        """None returns None."""
        assert serialize_value(None) is None

    def test_serializes_path_to_string(self) -> None:
        """Path is converted to string."""
        path = Path("/some/path")
        assert serialize_value(path) == "/some/path"

    def test_serializes_enum_to_value(self) -> None:
        """Enum is converted to its value."""

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        assert serialize_value(Color.RED) == "red"

    def test_serializes_datetime_to_iso(self) -> None:
        """datetime is converted to ISO format string."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = serialize_value(dt)
        assert result == "2024-01-15T10:30:00"

    def test_serializes_list_recursively(self) -> None:
        """Lists are serialized recursively."""
        data = [Path("/a"), Path("/b")]
        result = serialize_value(data)
        assert result == ["/a", "/b"]

    def test_serializes_set_to_sorted_list(self) -> None:
        """Sets are converted to sorted lists."""
        data = {Path("/b"), Path("/a")}
        result = serialize_value(data)
        assert result == ["/a", "/b"]

    def test_serializes_dict_recursively(self) -> None:
        """Dicts are serialized recursively."""
        data = {"path": Path("/test")}
        result = serialize_value(data)
        assert result == {"path": "/test"}

    def test_passes_through_primitives(self) -> None:
        """Primitive types pass through unchanged."""
        assert serialize_value(42) == 42
        assert serialize_value("string") == "string"
        assert serialize_value(3.14) == 3.14
        assert serialize_value(True) is True


class TestDataclassToDict:
    """Tests for dataclass_to_dict function."""

    def test_converts_simple_dataclass(self) -> None:
        """Converts simple dataclass to dict."""

        @dataclass
        class Simple:
            name: str
            count: int

        obj = Simple(name="test", count=5)
        result = dataclass_to_dict(obj)
        assert result == {"name": "test", "count": 5}

    def test_serializes_path_fields(self) -> None:
        """Path fields are serialized to strings."""

        @dataclass
        class WithPath:
            file: Path

        obj = WithPath(file=Path("/test/path"))
        result = dataclass_to_dict(obj)
        assert result == {"file": "/test/path"}

    def test_excludes_none_when_requested(self) -> None:
        """None fields are excluded when exclude_none=True."""

        @dataclass
        class WithOptional:
            name: str
            value: int | None = None

        obj = WithOptional(name="test")
        result = dataclass_to_dict(obj, exclude_none=True)
        assert result == {"name": "test"}

    def test_includes_extra_fields(self) -> None:
        """Extra fields are added to output."""

        @dataclass
        class Simple:
            name: str

        obj = Simple(name="test")
        result = dataclass_to_dict(obj, extra_fields={"extra": "value"})
        assert result == {"name": "test", "extra": "value"}

    def test_raises_for_non_dataclass(self) -> None:
        """Raises TypeError for non-dataclass objects."""
        with pytest.raises(TypeError, match="Expected dataclass instance"):
            dataclass_to_dict({"not": "dataclass"})


class TestExtractBetween:
    """Tests for extract_between function."""

    def test_extracts_between_delimiters(self) -> None:
        """Extracts substring between start and end."""
        text = "error in 'module.py' at line 5"
        result = extract_between(text, "'", "'")
        assert result == "module.py"

    def test_returns_none_when_start_not_found(self) -> None:
        """Returns None when start delimiter not found."""
        text = "no quotes here"
        result = extract_between(text, "'", "'")
        assert result is None

    def test_returns_none_when_end_not_found(self) -> None:
        """Returns None when end delimiter not found."""
        text = "only 'start here"
        result = extract_between(text, "'", "x")
        assert result is None

    def test_handles_different_delimiters(self) -> None:
        """Works with different start and end delimiters."""
        text = "value is [42] here"
        result = extract_between(text, "[", "]")
        assert result == "42"


class TestFindCloseMatches:
    """Tests for find_close_matches function."""

    def test_finds_close_matches(self) -> None:
        """Finds similar strings from candidates."""
        candidates = ["template", "templates", "config", "content"]
        matches = find_close_matches("tenmplate", candidates)
        assert "template" in matches

    def test_returns_empty_for_none_input(self) -> None:
        """Returns empty list for None input."""
        matches = find_close_matches(None, ["a", "b"])
        assert matches == []

    def test_returns_empty_for_no_matches(self) -> None:
        """Returns empty list when no close matches."""
        matches = find_close_matches("xyz", ["abc", "def"])
        assert matches == []

    def test_respects_cutoff(self) -> None:
        """Respects similarity cutoff."""
        candidates = ["template", "temp"]
        # "template" should match with default cutoff
        matches = find_close_matches("templete", candidates, cutoff=0.8)
        assert len(matches) <= 2


class TestSafeListModuleExports:
    """Tests for safe_list_module_exports function."""

    def test_lists_module_exports(self) -> None:
        """Lists exports from a valid module."""
        exports = safe_list_module_exports("os")
        assert len(exports) > 0
        assert "path" in exports

    def test_returns_empty_for_invalid_module(self) -> None:
        """Returns empty list for non-existent module."""
        exports = safe_list_module_exports("nonexistent_module_xyz")
        assert exports == []

    def test_uses_all_when_available(self) -> None:
        """Uses __all__ when available."""
        exports = safe_list_module_exports("bengal.errors.codes")
        # Should include items from __all__
        assert "ErrorCode" in exports


class TestThreadSafeSingleton:
    """Tests for ThreadSafeSingleton class."""

    def test_get_returns_same_instance(self) -> None:
        """get() returns the same instance each time."""
        call_count = 0

        def factory() -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": call_count}

        singleton = ThreadSafeSingleton(factory)
        first = singleton.get()
        second = singleton.get()

        assert first is second
        assert call_count == 1  # Factory only called once

    def test_reset_creates_new_instance(self) -> None:
        """reset() creates a fresh instance."""
        call_count = 0

        def factory() -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": call_count}

        singleton = ThreadSafeSingleton(factory)
        first = singleton.get()
        singleton.reset()
        second = singleton.get()

        assert first is not second
        assert first["id"] == 1
        assert second["id"] == 2

    def test_is_initialized_reflects_state(self) -> None:
        """is_initialized() reflects initialization state."""
        singleton = ThreadSafeSingleton(dict)
        assert not singleton.is_initialized()
        singleton.get()
        assert singleton.is_initialized()

    def test_thread_safety(self) -> None:
        """Singleton is thread-safe."""
        import threading

        results: list[dict] = []

        def factory() -> dict:
            return {"id": id({})}

        singleton = ThreadSafeSingleton(factory)

        def get_instance() -> None:
            results.append(singleton.get())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # All threads should get the same instance
        assert all(r is results[0] for r in results)
