"""
Tests for PythonExtractor exclude pattern semantics.

These tests protect against regressions where exclude patterns are treated as
substring matches (which can cause broad patterns like "*/.*" to skip everything).
"""

from __future__ import annotations

from pathlib import Path

from bengal.autodoc.extractors.python import PythonExtractor


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
