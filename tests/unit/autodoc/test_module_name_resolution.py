"""
Unit tests for module name resolution in PythonExtractor.

This module tests the _infer_module_name() method, which was the source
of a critical bug where module names were computed by searching for the
deepest __init__.py file instead of using the source root.

Regression test for: Module names should be computed relative to source root.
"""

from __future__ import annotations

import contextlib

from bengal.autodoc.extractors.python import PythonExtractor


class TestModuleNameResolution:
    """Test module name inference from file paths."""

    def test_infer_module_name_with_source_root(self, tmp_path):
        """Test module name computed relative to source root."""
        # Create test structure
        source_root = tmp_path / "bengal"
        source_root.mkdir()
        (source_root / "cli").mkdir()
        (source_root / "cli" / "commands").mkdir()

        # Create __init__.py files
        (source_root / "__init__.py").touch()
        (source_root / "cli" / "__init__.py").touch()
        (source_root / "cli" / "commands" / "__init__.py").touch()
        (source_root / "cli" / "commands" / "build.py").touch()

        # Create extractor and set source root
        extractor = PythonExtractor()
        extractor._source_root = source_root

        # Test regular module
        result = extractor._infer_module_name(source_root / "cli" / "commands" / "build.py")
        assert result == "cli.commands.build"

        # Test package (__init__.py)
        result = extractor._infer_module_name(source_root / "cli" / "__init__.py")
        assert result == "cli"

        # Test nested package
        result = extractor._infer_module_name(source_root / "cli" / "commands" / "__init__.py")
        assert result == "cli.commands"

    def test_infer_module_name_without_source_root_falls_back(self, tmp_path):
        """Test fallback to old behavior when source root not set."""
        # Create nested structure
        root = tmp_path / "project"
        root.mkdir()
        (root / "mypackage").mkdir()
        (root / "mypackage" / "cli").mkdir()
        (root / "mypackage" / "cli" / "commands").mkdir()

        # Create __init__.py files
        (root / "mypackage" / "__init__.py").touch()
        (root / "mypackage" / "cli" / "__init__.py").touch()
        (root / "mypackage" / "cli" / "commands" / "__init__.py").touch()
        (root / "mypackage" / "cli" / "commands" / "build.py").touch()

        # Create extractor WITHOUT setting source root
        extractor = PythonExtractor()
        # _source_root is None (not set)

        # Should fall back to searching for __init__.py
        # The old buggy behavior searches backwards and finds the DEEPEST __init__.py
        result = extractor._infer_module_name(root / "mypackage" / "cli" / "commands" / "build.py")

        # OLD BUGGY BEHAVIOR: Finds commands/__init__.py (deepest) and builds from there
        # This is what caused the bug - it gives 'commands.build' instead of the full path
        assert result == "commands.build", (
            "Fallback behavior should use old (buggy) algorithm that searches for deepest __init__.py"
        )

    def test_regression_bug_module_names_relative_to_source_not_init_files(self, tmp_path):
        """
        Regression test: Module names must be computed from source root,
        not by searching for __init__.py files.

        This tests the fix for the bug where:
        - Source root: bengal/
        - File: bengal/cli/commands/build.py
        - Bug: Searched for deepest __init__.py (commands/), got 'commands.build'
        - Fix: Use source root, get 'cli.commands.build'
        """
        # Create Bengal-like structure
        bengal_root = tmp_path / "bengal"
        bengal_root.mkdir()
        (bengal_root / "cli").mkdir()
        (bengal_root / "cli" / "commands").mkdir()
        (bengal_root / "cli" / "templates").mkdir()

        # Create __init__.py files at multiple levels
        (bengal_root / "__init__.py").touch()
        (bengal_root / "cli" / "__init__.py").touch()
        (bengal_root / "cli" / "commands" / "__init__.py").touch()
        (bengal_root / "cli" / "templates" / "__init__.py").touch()

        # Create module files
        (bengal_root / "cli" / "commands" / "build.py").touch()
        (bengal_root / "cli" / "templates" / "blog.py").touch()

        # Create extractor with source root set
        extractor = PythonExtractor()
        extractor._source_root = bengal_root

        # Test: Should use source root, not search for __init__.py
        result1 = extractor._infer_module_name(bengal_root / "cli" / "commands" / "build.py")
        assert result1 == "cli.commands.build", (
            "Bug present: Module name should be 'cli.commands.build' "
            "computed from source root, not 'commands.build' from deepest __init__.py"
        )

        result2 = extractor._infer_module_name(bengal_root / "cli" / "templates" / "blog.py")
        assert result2 == "cli.templates.blog", (
            "Bug present: Module name should be 'cli.templates.blog' "
            "computed from source root, not 'templates.blog' from deepest __init__.py"
        )

    def test_module_name_for_nested_packages(self, tmp_path):
        """Test module name resolution for deeply nested packages."""
        # Create deep nesting
        source_root = tmp_path / "src"
        source_root.mkdir()
        deep_path = source_root / "a" / "b" / "c" / "d"
        deep_path.mkdir(parents=True)

        # Create __init__.py at each level
        for part in [
            source_root / "a",
            source_root / "a" / "b",
            source_root / "a" / "b" / "c",
            deep_path,
        ]:
            (part / "__init__.py").touch()

        (deep_path / "module.py").touch()

        extractor = PythonExtractor()
        extractor._source_root = source_root

        result = extractor._infer_module_name(deep_path / "module.py")
        assert result == "a.b.c.d.module"

    def test_module_name_at_root_level(self, tmp_path):
        """Test module name for files directly in source root."""
        source_root = tmp_path / "src"
        source_root.mkdir()
        (source_root / "__init__.py").touch()
        (source_root / "main.py").touch()

        extractor = PythonExtractor()
        extractor._source_root = source_root

        # Module at root should just be the filename
        result = extractor._infer_module_name(source_root / "main.py")
        assert result == "main"

        # Package at root should use source root directory name
        result_pkg = extractor._infer_module_name(source_root / "__init__.py")
        assert result_pkg == "src"  # Source root name

    def test_extract_sets_source_root_for_directory(self, tmp_path):
        """Test that extract() sets _source_root when called with a directory."""
        source_dir = tmp_path / "myproject"
        source_dir.mkdir()
        (source_dir / "__init__.py").write_text("# Empty")

        extractor = PythonExtractor()
        assert extractor._source_root is None

        # Extract from directory
        extractor.extract(source_dir)

        # Should have set source root
        assert extractor._source_root == source_dir

    def test_extract_sets_source_root_for_file(self, tmp_path):
        """Test that extract() sets _source_root when called with a file."""
        source_dir = tmp_path / "myproject"
        source_dir.mkdir()
        module_file = source_dir / "module.py"
        module_file.write_text("# Empty")

        extractor = PythonExtractor()
        assert extractor._source_root is None

        # Extract from file (may fail due to empty file, but source_root should be set)
        with contextlib.suppress(Exception):
            extractor.extract(module_file)

        # Should have set source root to parent directory
        assert extractor._source_root == source_dir
