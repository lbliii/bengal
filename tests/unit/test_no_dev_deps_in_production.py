"""
Test that production code (bengal/*) doesn't import dev dependencies.

This prevents issues where users building sites need testing libraries installed.
Dev dependencies should ONLY be used in tests/ directory.
"""

import ast
from pathlib import Path

import pytest

# Dev dependencies that should NEVER be imported in production code
DEV_ONLY_IMPORTS = {
    "pytest",
    "hypothesis",
    "mypy",
    "ruff",
    "pytest_mock",
    "pytest_cov",
    "pytest_xdist",
    "pytest_timeout",
}

# Optional dependencies that CAN be imported but must be handled gracefully
OPTIONAL_IMPORTS = {
    "bs4",
    "beautifulsoup4",
    "lxml",
    "html5lib",
    "lightningcss",
}


def get_imports_from_file(file_path: Path) -> set[str]:
    """
    Extract all import names from a Python file.

    Returns top-level package names (e.g., 'hypothesis' from 'import hypothesis.strategies').
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError:
        # Skip files with syntax errors (might be templates, etc.)
        return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Get top-level package name
                top_level = alias.name.split(".")[0]
                imports.add(top_level)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # Get top-level package name
            top_level = node.module.split(".")[0]
            imports.add(top_level)

    return imports


def get_all_production_files() -> list[Path]:
    """Get all Python files in bengal/ (production code)."""
    bengal_dir = Path(__file__).parent.parent.parent / "bengal"
    python_files = []

    for file_path in bengal_dir.rglob("*.py"):
        # Skip __pycache__ and similar
        if "__pycache__" in str(file_path):
            continue
        python_files.append(file_path)

    return python_files


class TestNoDevDepsInProduction:
    """Test that production code doesn't import dev dependencies."""

    def test_no_hypothesis_in_production(self):
        """Test that hypothesis is not imported in production code."""
        production_files = get_all_production_files()
        files_with_hypothesis = []

        for file_path in production_files:
            imports = get_imports_from_file(file_path)
            if "hypothesis" in imports:
                files_with_hypothesis.append(file_path)

        assert not files_with_hypothesis, (
            f"Found hypothesis imports in production code: {files_with_hypothesis}\n"
            "hypothesis is a dev dependency and should only be used in tests/"
        )

    def test_no_pytest_in_production(self):
        """Test that pytest is not imported in production code."""
        production_files = get_all_production_files()
        files_with_pytest = []

        for file_path in production_files:
            imports = get_imports_from_file(file_path)
            pytest_imports = {
                "pytest",
                "pytest_mock",
                "pytest_cov",
                "pytest_xdist",
                "pytest_timeout",
            }
            if imports & pytest_imports:
                files_with_pytest.append(file_path)

        assert not files_with_pytest, (
            f"Found pytest imports in production code: {files_with_pytest}\n"
            "pytest is a dev dependency and should only be used in tests/"
        )

    def test_no_dev_tools_in_production(self):
        """Test that dev tools (mypy, ruff) are not imported in production code."""
        production_files = get_all_production_files()
        files_with_dev_tools = []

        for file_path in production_files:
            imports = get_imports_from_file(file_path)
            dev_tool_imports = {"mypy", "ruff"}
            if imports & dev_tool_imports:
                files_with_dev_tools.append(file_path)

        assert not files_with_dev_tools, (
            f"Found dev tool imports in production code: {files_with_dev_tools}\n"
            "mypy and ruff are dev dependencies and should only be used in development"
        )

    def test_all_dev_deps_not_in_production(self):
        """Comprehensive test: no dev dependencies in production code."""
        production_files = get_all_production_files()
        violations = {}

        for file_path in production_files:
            imports = get_imports_from_file(file_path)
            dev_imports_found = imports & DEV_ONLY_IMPORTS

            if dev_imports_found:
                violations[file_path] = dev_imports_found

        if violations:
            error_msg = "Found dev dependencies imported in production code:\n"
            for file_path, imports in violations.items():
                error_msg += f"  {file_path}: {imports}\n"
            error_msg += "\nDev dependencies should ONLY be used in tests/ directory."
            pytest.fail(error_msg)


class TestOptionalDepsHandled:
    """Test that optional dependencies are imported with try/except."""

    def test_optional_deps_have_fallbacks(self):
        """
        Test that optional dependencies are imported with try/except.

        This is a reminder check - if it fails, verify the file handles ImportError.
        """
        production_files = get_all_production_files()
        files_with_optional = {}

        for file_path in production_files:
            imports = get_imports_from_file(file_path)
            optional_found = imports & OPTIONAL_IMPORTS

            if optional_found:
                # Check if file has try/except for ImportError
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    has_import_error_handling = "ImportError" in content

                    if not has_import_error_handling:
                        files_with_optional[file_path] = optional_found

        if files_with_optional:
            error_msg = "Found optional dependencies without ImportError handling:\n"
            for file_path, imports in files_with_optional.items():
                error_msg += f"  {file_path}: {imports}\n"
            error_msg += (
                "\nOptional dependencies should be imported with try/except ImportError.\n"
                "See bengal/rendering/parsers/factory.py for an example."
            )
            pytest.fail(error_msg)


class TestProductionCodeStructure:
    """Test that production code structure is correct."""

    def test_bengal_package_exists(self):
        """Test that bengal package directory exists."""
        bengal_dir = Path(__file__).parent.parent.parent / "bengal"
        assert bengal_dir.exists(), "bengal/ directory not found"
        assert bengal_dir.is_dir(), "bengal/ is not a directory"

    def test_can_scan_production_files(self):
        """Test that we can find production Python files."""
        production_files = get_all_production_files()
        assert len(production_files) > 0, "No Python files found in bengal/"

        # Should have at least some key modules
        file_names = {f.name for f in production_files}
        assert "__init__.py" in file_names
        assert "site.py" in file_names or any("site" in name for name in file_names)
