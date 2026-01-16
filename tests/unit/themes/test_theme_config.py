"""Tests for ThemeConfig error handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.errors import BengalConfigError, ErrorCode
from bengal.themes.config import AppearanceConfig, ThemeConfig


class TestThemeConfigErrors:
    """Tests for ThemeConfig error codes."""

    def test_missing_theme_yaml_has_error_code(self, tmp_path: Path) -> None:
        """Verify ThemeConfig.load raises BengalConfigError with C005."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(BengalConfigError) as exc_info:
            ThemeConfig.load(nonexistent)

        assert exc_info.value.code == ErrorCode.C005
        assert exc_info.value.file_path is not None
        assert (
            "theme.yaml" in str(exc_info.value).lower()
            or "not found" in str(exc_info.value).lower()
        )

    def test_invalid_yaml_has_error_code(self, tmp_path: Path) -> None:
        """Verify ThemeConfig.load raises BengalConfigError with C001 for invalid YAML."""
        theme_dir = tmp_path / "theme"
        theme_dir.mkdir()
        (theme_dir / "theme.yaml").write_text("invalid: yaml: [")

        with pytest.raises(BengalConfigError) as exc_info:
            ThemeConfig.load(theme_dir)

        assert exc_info.value.code == ErrorCode.C001
        assert exc_info.value.file_path is not None

    def test_invalid_mode_has_error_code(self) -> None:
        """Verify AppearanceConfig raises BengalConfigError with C003."""
        with pytest.raises(BengalConfigError) as exc_info:
            AppearanceConfig(default_mode="invalid")

        assert exc_info.value.code == ErrorCode.C003
        assert "default_mode" in str(exc_info.value)

    def test_valid_config_loads_successfully(self, tmp_path: Path) -> None:
        """Verify valid theme.yaml loads without error."""
        theme_dir = tmp_path / "theme"
        theme_dir.mkdir()
        (theme_dir / "theme.yaml").write_text(
            """
name: test-theme
version: 1.0.0
appearance:
  default_mode: dark
"""
        )

        config = ThemeConfig.load(theme_dir)

        assert config.name == "test-theme"
        assert config.appearance.default_mode == "dark"

    def test_missing_theme_yaml_has_suggestion(self, tmp_path: Path) -> None:
        """Verify missing theme.yaml error has actionable suggestion."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(BengalConfigError) as exc_info:
            ThemeConfig.load(nonexistent)

        assert exc_info.value.suggestion is not None
        assert "theme.yaml" in exc_info.value.suggestion.lower()

    def test_valid_appearance_modes(self) -> None:
        """Verify all valid appearance modes are accepted."""
        for mode in ("light", "dark", "system"):
            config = AppearanceConfig(default_mode=mode)
            assert config.default_mode == mode

    def test_invalid_palette_has_error_code(self) -> None:
        """Verify AppearanceConfig raises BengalConfigError with C003 for invalid palette."""
        with pytest.raises(BengalConfigError) as exc_info:
            AppearanceConfig(default_palette="nonexistent-palette")

        assert exc_info.value.code == ErrorCode.C003
        assert "default_palette" in str(exc_info.value)

    def test_valid_palettes_accepted(self) -> None:
        """Verify all valid palette names are accepted."""
        valid_palettes = [
            "",  # Empty string = no override
            "default",
            "blue-bengal",
            "brown-bengal",
            "charcoal-bengal",
            "silver-bengal",
            "snow-lynx",
        ]
        for palette in valid_palettes:
            config = AppearanceConfig(default_palette=palette)
            assert config.default_palette == palette

    def test_invalid_palette_suggestion_lists_valid_options(self) -> None:
        """Verify invalid palette error includes valid options in suggestion."""
        with pytest.raises(BengalConfigError) as exc_info:
            AppearanceConfig(default_palette="invalid-palette")

        assert exc_info.value.suggestion is not None
        # Should mention at least one valid palette
        assert "blue-bengal" in exc_info.value.suggestion or "snow-lynx" in exc_info.value.suggestion
