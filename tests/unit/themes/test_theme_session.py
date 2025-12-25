"""Tests for theme error session tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.errors import BengalConfigError
from bengal.errors.session import get_session, reset_session
from bengal.themes.config import AppearanceConfig, ThemeConfig


@pytest.fixture(autouse=True)
def fresh_session():
    """Reset session before each test."""
    reset_session()
    yield
    reset_session()


def test_yaml_error_tracked_in_session(tmp_path: Path) -> None:
    """Verify YAML parse errors are recorded in error session."""
    theme_dir = tmp_path / "theme"
    theme_dir.mkdir()
    (theme_dir / "theme.yaml").write_text("invalid: [")

    with pytest.raises(BengalConfigError):
        ThemeConfig.load(theme_dir)

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C001" in str(summary.get("errors_by_code", {}))


def test_missing_file_tracked_in_session(tmp_path: Path) -> None:
    """Verify missing theme.yaml errors are recorded in error session."""
    with pytest.raises(BengalConfigError):
        ThemeConfig.load(tmp_path / "nonexistent")

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C005" in str(summary.get("errors_by_code", {}))


def test_invalid_mode_tracked_in_session() -> None:
    """Verify invalid mode errors are recorded in error session."""
    with pytest.raises(BengalConfigError):
        AppearanceConfig(default_mode="invalid")

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 1
    assert "C003" in str(summary.get("errors_by_code", {}))


def test_multiple_errors_tracked_separately(tmp_path: Path) -> None:
    """Verify multiple errors are tracked separately in session."""
    # First error: missing file
    with pytest.raises(BengalConfigError):
        ThemeConfig.load(tmp_path / "nonexistent1")

    # Second error: also missing file
    with pytest.raises(BengalConfigError):
        ThemeConfig.load(tmp_path / "nonexistent2")

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 2


def test_valid_config_does_not_track_error(tmp_path: Path) -> None:
    """Verify valid config does not add errors to session."""
    theme_dir = tmp_path / "theme"
    theme_dir.mkdir()
    (theme_dir / "theme.yaml").write_text(
        """
name: test-theme
version: 1.0.0
appearance:
  default_mode: system
"""
    )

    ThemeConfig.load(theme_dir)

    session = get_session()
    summary = session.get_summary()

    assert summary["total_errors"] == 0
