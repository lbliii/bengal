"""
Tests for bengal.fonts.utils module.

Tests the extracted utility functions for filename handling and other
common font operations.
"""

import pytest

from bengal.fonts.utils import (
    make_font_filename,
    make_safe_name,
    make_style_suffix,
)


class TestMakeSafeName:
    """Tests for make_safe_name function."""

    def test_simple_name(self) -> None:
        """Single word names are lowercased."""
        assert make_safe_name("Inter") == "inter"

    def test_multi_word_name(self) -> None:
        """Multi-word names become kebab-case."""
        assert make_safe_name("Playfair Display") == "playfair-display"

    def test_already_lowercase(self) -> None:
        """Already lowercase names pass through."""
        assert make_safe_name("roboto") == "roboto"

    def test_multiple_spaces(self) -> None:
        """Multiple spaces become multiple hyphens."""
        assert make_safe_name("Source Sans Pro") == "source-sans-pro"


class TestMakeStyleSuffix:
    """Tests for make_style_suffix function."""

    def test_normal_style(self) -> None:
        """Normal style returns empty string."""
        assert make_style_suffix("normal") == ""

    def test_italic_style(self) -> None:
        """Italic style returns -italic suffix."""
        assert make_style_suffix("italic") == "-italic"

    def test_other_style(self) -> None:
        """Other styles return empty string (same as normal)."""
        assert make_style_suffix("oblique") == ""


class TestMakeFontFilename:
    """Tests for make_font_filename function."""

    def test_normal_woff2(self) -> None:
        """Normal weight with woff2 extension."""
        assert make_font_filename("Inter", 400, "normal") == "inter-400.woff2"

    def test_bold_woff2(self) -> None:
        """Bold weight with woff2 extension."""
        assert make_font_filename("Inter", 700, "normal") == "inter-700.woff2"

    def test_italic_woff2(self) -> None:
        """Italic style adds suffix."""
        assert make_font_filename("Inter", 400, "italic") == "inter-400-italic.woff2"

    def test_ttf_extension(self) -> None:
        """Custom extension is used."""
        assert make_font_filename("Outfit", 600, "normal", ".ttf") == "outfit-600.ttf"

    def test_multi_word_family(self) -> None:
        """Multi-word family names become kebab-case."""
        result = make_font_filename("Playfair Display", 700, "normal")
        assert result == "playfair-display-700.woff2"

    def test_italic_ttf(self) -> None:
        """Italic TTF combines suffix and extension."""
        result = make_font_filename("Outfit", 400, "italic", ".ttf")
        assert result == "outfit-400-italic.ttf"
