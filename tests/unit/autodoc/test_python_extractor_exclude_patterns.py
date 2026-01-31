"""
Tests for PythonExtractor exclude pattern semantics.

These tests protect against regressions where exclude patterns are treated as
substring matches (which can cause broad patterns like "*/.*" to skip everything).
"""

from __future__ import annotations

from pathlib import Path

from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.extractors.python.skip_logic import should_skip_shadowed_module


def test_exclude_pattern_hidden_glob_does_not_skip_normal_files(tmp_path: Path) -> None:
    """
    Pattern "*/.*" should match hidden files/dirs, not all paths.

    """
    extractor = PythonExtractor(exclude_patterns=["*/.*"], config={"exclude": ["*/.*"]})

    normal = tmp_path / "pkg" / "core" / "site.py"
    normal.parent.mkdir(parents=True)
    normal.write_text("'''module doc'''")

    assert extractor._should_skip(normal) is False


def test_exclude_pattern_hidden_glob_skips_hidden_files(tmp_path: Path) -> None:
    extractor = PythonExtractor(exclude_patterns=["*/.*"], config={"exclude": ["*/.*"]})

    hidden = tmp_path / "pkg" / ".hidden" / "x.py"
    hidden.parent.mkdir(parents=True)
    hidden.write_text("'''module doc'''")

    assert extractor._should_skip(hidden) is True


def test_exclude_pattern_filename_glob_skips_test_files(tmp_path: Path) -> None:
    extractor = PythonExtractor(exclude_patterns=["*_test.py"], config={"exclude": ["*_test.py"]})

    test_file = tmp_path / "pkg" / "core" / "site_test.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("'''module doc'''")

    assert extractor._should_skip(test_file) is True


def test_exclude_pattern_venv_glob_skips_venv_files(tmp_path: Path) -> None:
    extractor = PythonExtractor(exclude_patterns=["*/.venv/*"], config={"exclude": ["*/.venv/*"]})

    venv_file = tmp_path / "pkg" / ".venv" / "lib" / "x.py"
    venv_file.parent.mkdir(parents=True)
    venv_file.write_text("'''module doc'''")

    assert extractor._should_skip(venv_file) is True


# ============================================================================
# Shadowed module tests (module file + package directory with same name)
# ============================================================================


def test_shadowed_module_skipped_when_package_exists(tmp_path: Path) -> None:
    """
    Module files should be skipped when a package directory with same name exists.

    Example: template_functions.py should be skipped when template_functions/ exists
    with an __init__.py. This prevents URL collisions in autodoc output.

    """
    # Create both: foo.py (module) and foo/ (package)
    module_file = tmp_path / "foo.py"
    module_file.write_text("'''module doc'''")

    package_dir = tmp_path / "foo"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("'''package doc'''")

    # The module file should be skipped
    assert should_skip_shadowed_module(module_file) is True


def test_shadowed_module_not_skipped_when_no_package(tmp_path: Path) -> None:
    """Module files should NOT be skipped when no shadowing package exists."""
    module_file = tmp_path / "bar.py"
    module_file.write_text("'''module doc'''")

    # No bar/ directory exists
    assert should_skip_shadowed_module(module_file) is False


def test_shadowed_module_not_skipped_for_init_files(tmp_path: Path) -> None:
    """__init__.py files should never be skipped as shadowed."""
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    init_file = package_dir / "__init__.py"
    init_file.write_text("'''package doc'''")

    assert should_skip_shadowed_module(init_file) is False


def test_shadowed_module_not_skipped_when_dir_has_no_init(tmp_path: Path) -> None:
    """
    Module files should NOT be skipped if the directory has no __init__.py.

    A directory without __init__.py is not a package, so no collision occurs.

    """
    module_file = tmp_path / "baz.py"
    module_file.write_text("'''module doc'''")

    # Create directory without __init__.py (not a package)
    dir_without_init = tmp_path / "baz"
    dir_without_init.mkdir()

    assert should_skip_shadowed_module(module_file) is False


def test_extractor_skips_shadowed_modules_during_extraction(tmp_path: Path) -> None:
    """
    Integration test: PythonExtractor should skip shadowed modules.

    When both template_functions.py and template_functions/__init__.py exist,
    only the package should be extracted.

    """
    # Create package structure
    pkg = tmp_path / "mypackage"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('"""Root package."""')

    # Create shadowed module + package
    (pkg / "utils.py").write_text('"""This module is shadowed."""')

    utils_pkg = pkg / "utils"
    utils_pkg.mkdir()
    (utils_pkg / "__init__.py").write_text('"""Utils package."""')
    (utils_pkg / "helpers.py").write_text('"""Helpers module."""')

    # Extract
    extractor = PythonExtractor(exclude_patterns=[])
    elements = extractor.extract(pkg)

    # Find all qualified names
    qualified_names = [e.qualified_name for e in elements]

    # Should have: mypackage, mypackage.utils (package), mypackage.utils.helpers
    # Should NOT have: mypackage.utils from utils.py (shadowed)

    # The package utils should exist
    assert any("utils" in qn for qn in qualified_names)

    # There should be only ONE element with "utils" as the final component
    utils_elements = [e for e in elements if e.qualified_name.endswith("utils")]
    assert len(utils_elements) == 1

    # And it should be from __init__.py (a package), not utils.py
    assert utils_elements[0].source_file.name == "__init__.py"
