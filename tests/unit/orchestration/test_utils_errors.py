"""
Tests for orchestration/utils/errors.py.

Tests is_shutdown_error, handle_orchestration_error, and create_error_context_for_item.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.orchestration.utils.errors import (
    create_error_context_for_item,
    is_shutdown_error,
)


class TestIsShutdownError:
    """Test is_shutdown_error detection."""

    def test_detects_shutdown_error(self) -> None:
        """Interpreter shutdown errors should be detected."""
        e = RuntimeError("can't schedule during interpreter shutdown")
        assert is_shutdown_error(e) is True

    def test_detects_shutdown_variant(self) -> None:
        """Variant shutdown error messages should be detected."""
        e = Exception("interpreter shutdown in progress")
        assert is_shutdown_error(e) is True

    def test_normal_error_not_detected(self) -> None:
        """Normal errors should not be flagged as shutdown."""
        e = ValueError("some validation error")
        assert is_shutdown_error(e) is False

    def test_empty_error_not_detected(self) -> None:
        """Empty error messages should not be flagged as shutdown."""
        e = Exception("")
        assert is_shutdown_error(e) is False

    def test_none_like_error(self) -> None:
        """Error with None-like string should not crash."""
        e = Exception(None)
        assert is_shutdown_error(e) is False


class TestCreateErrorContextForItem:
    """Test create_error_context_for_item utility."""

    def test_basic_context(self) -> None:
        """Basic context creation with item and operation."""
        item = MagicMock()
        item.__str__ = lambda s: "test_item"

        context = create_error_context_for_item(item, "processing")

        assert context["operation"] == "processing"
        assert context["item"] == "test_item"

    def test_extracts_source_path(self) -> None:
        """Extracts source_path from item if available."""
        item = MagicMock()
        item.source_path = Path("/content/test.md")
        item.__str__ = lambda s: "test_item"

        context = create_error_context_for_item(item, "rendering")

        assert context["file_path"] == "/content/test.md"
        assert context["file_name"] == "test.md"

    def test_extracts_path_attribute(self) -> None:
        """Falls back to path attribute if source_path not available."""
        item = MagicMock(spec=["path", "__str__"])
        item.path = Path("/assets/style.css")
        item.__str__ = lambda s: "asset_item"

        context = create_error_context_for_item(item, "copying")

        assert context["file_path"] == "/assets/style.css"
        assert context["file_name"] == "style.css"

    def test_includes_suggestion(self) -> None:
        """Includes suggestion if provided."""
        item = MagicMock()
        item.__str__ = lambda s: "test"

        context = create_error_context_for_item(
            item, "parsing", suggestion="Check YAML syntax"
        )

        assert context["suggestion"] == "Check YAML syntax"

    def test_no_path_attributes(self) -> None:
        """Handles items without path attributes."""
        item = MagicMock(spec=["__str__"])
        item.__str__ = lambda s: "plain_item"

        context = create_error_context_for_item(item, "processing")

        assert "file_path" not in context
        assert context["item"] == "plain_item"
