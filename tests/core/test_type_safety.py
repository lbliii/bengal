"""
Type safety tests for core package.

These tests verify type contracts and API consistency that static analysis
might miss at runtime. They complement ty checks with runtime verification.

Motivation:
- Mixin self-reference bugs (e.g., list.index(self) failing)
- Logger API misuse (positional vs keyword args)
- Diagnostics API evolution
- PIL enum vs int mismatches
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _pillow_available() -> bool:
    """Check if Pillow is installed."""
    try:
        from PIL import Image

        return True
    except ImportError:
        return False


class TestLoggerAPIConsistency:
    """Verify logger calls use correct API signature."""

    def test_no_message_keyword_in_logger_calls(self) -> None:
        """
        Logger methods take message as first positional arg.

        Passing message= as kwarg causes "gets multiple values" error.
        This test scans source files for this anti-pattern.
        """
        core_dir = Path(__file__).parent.parent.parent / "bengal" / "core"
        violations: list[str] = []

        for py_file in core_dir.rglob("*.py"):
            content = py_file.read_text()

            # Quick check before expensive parsing
            if "logger." not in content:
                continue

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for logger.warning/error/info/debug calls
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("warning", "error", "info", "debug", "critical")
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "logger"
                    ):
                        # Check for message= keyword
                        for kw in node.keywords:
                            if kw.arg == "message":
                                violations.append(
                                    f"{py_file.relative_to(core_dir.parent.parent)}:{node.lineno} - "
                                    f"logger.{node.func.attr}() uses message= keyword"
                                )

        assert not violations, (
            "Found logger calls using message= keyword (should be positional):\n"
            + "\n".join(violations)
        )


class TestDiagnosticsAPIConsistency:
    """Verify diagnostics API is used correctly."""

    def test_diagnostics_sink_not_called_directly_with_multiple_args(self) -> None:
        """
        DiagnosticsSink.emit() takes a single DiagnosticEvent.

        The convenience emit() function should be used instead.
        This catches misuse like: sink.emit(self, "error", "code", **kwargs)
        """
        core_dir = Path(__file__).parent.parent.parent / "bengal" / "core"
        violations: list[str] = []

        for py_file in core_dir.rglob("*.py"):
            content = py_file.read_text()

            if "_diagnostics.emit(" not in content and "diagnostics.emit(" not in content:
                continue

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for *.diagnostics.emit() or *._diagnostics.emit() calls
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "emit"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr in ("diagnostics", "_diagnostics")
                    ):
                        # If it has more than 1 positional arg, it's wrong
                        if len(node.args) > 1:
                            violations.append(
                                f"{py_file.relative_to(core_dir.parent.parent)}:{node.lineno} - "
                                f"Direct .emit() call with multiple args (use emit_diagnostic helper)"
                            )

        assert not violations, "Found diagnostics.emit() calls with multiple args:\n" + "\n".join(
            violations
        )


class TestMixinComposition:
    """Verify mixins compose correctly in combined classes."""

    def test_section_mixin_attributes_accessible(self) -> None:
        """Section class has all expected attributes from mixins."""
        from bengal.core.section import Section

        # These should be accessible (defined across multiple mixins)
        expected_attrs = [
            "sorted_pages",
            "sorted_subsections",
            "regular_pages_recursive",
            "hierarchy",
            "content_pages",
            "href",
            "_path",
        ]

        for attr in expected_attrs:
            assert hasattr(Section, attr), f"Section missing expected attribute: {attr}"

    def test_page_mixin_attributes_accessible(self) -> None:
        """Page class has all expected attributes from mixins."""
        from bengal.core.page import Page

        expected_attrs = [
            "content",
            "html",
            "plain_text",
            "next",
            "prev",
            "next_in_section",
            "prev_in_section",
            "word_count",
            "reading_time",
            "meta_description",
        ]

        for attr in expected_attrs:
            assert hasattr(Page, attr), f"Page missing expected attribute: {attr}"

    def test_section_can_be_used_in_list_operations(self) -> None:
        """Section instances work with list.index() and similar operations."""
        from pathlib import Path as PathLib

        from bengal.core.section import Section

        # Create minimal sections for testing
        s1 = Section(
            name="test1",
            path=PathLib("/fake/test1"),
            parent=None,
            pages=[],
            subsections=[],
            metadata={},
            index_page=None,
        )
        s2 = Section(
            name="test2",
            path=PathLib("/fake/test2"),
            parent=None,
            pages=[],
            subsections=[],
            metadata={},
            index_page=None,
        )

        sections = [s1, s2]

        # These operations should work without type errors at runtime
        assert sections.index(s1) == 0
        assert sections.index(s2) == 1
        assert s1 in sections
        assert s2 in sections


class TestPILIntegration:
    """Verify PIL integration uses correct types."""

    @pytest.mark.skipif(not _pillow_available(), reason="Pillow not installed")
    def test_resampling_enum_used(self) -> None:
        """Image processing uses Resampling enum, not raw integers."""
        import inspect

        from bengal.core.resources.processor import ImageProcessor

        # Get source of relevant methods
        methods_to_check = ["_fill", "_fit", "_resize", "_smart_crop"]

        for method_name in methods_to_check:
            method = getattr(ImageProcessor, method_name)
            source = inspect.getsource(method)

            # Should use Resampling.LANCZOS, not raw integer 3
            assert "Resampling.LANCZOS" in source or "PILImage.Resampling.LANCZOS" in source, (
                f"ImageProcessor.{method_name} should use Resampling.LANCZOS enum"
            )

            # Should NOT have bare ", 3)" which was the old pattern
            # (Excluding comments)
            lines = [l for l in source.split("\n") if not l.strip().startswith("#")]
            non_comment_source = "\n".join(lines)
            assert ", 3)" not in non_comment_source, (
                f"ImageProcessor.{method_name} uses integer 3 instead of Resampling enum"
            )


class TestASTTypeConsistency:
    """Verify AST types are consistent across modules."""

    def test_ast_cache_annotation_exists(self) -> None:
        """
        _ast_cache type annotation should exist on Page and mixin.

        Note: We can't fully resolve forward references at runtime (ASTNode),
        so we just verify the annotation exists via __annotations__.
        """
        from bengal.core.page import Page
        from bengal.core.page.content import PageContentMixin

        # Both should have _ast_cache in their annotations
        assert "_ast_cache" in Page.__annotations__, "Page missing _ast_cache annotation"
        assert "_ast_cache" in PageContentMixin.__annotations__, (
            "PageContentMixin missing _ast_cache annotation"
        )

        # Both annotations should be Any (Patitas Document — external dependency)
        page_annotation = str(Page.__annotations__["_ast_cache"])
        mixin_annotation = str(PageContentMixin.__annotations__["_ast_cache"])

        # Accept Any, ASTNode, or dict (backward compat)
        for label, annotation in [("Page", page_annotation), ("Mixin", mixin_annotation)]:
            assert any(
                token in annotation.lower()
                for token in ("any", "astnode", "dict")
            ), f"{label}._ast_cache annotation unexpected: {annotation}"
