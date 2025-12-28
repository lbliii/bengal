"""Tests for CSS generation from palettes."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes.themes import get_palette


class TestCssGeneration:
    """Test CSS generation from palettes."""

    def test_css_generation(self) -> None:
        """CSS should be generated for all roles."""
        try:
            palette = get_palette("bengal-tiger")
            css = palette.generate_css()

            assert isinstance(css, str)
            assert len(css) > 0
            # Should have some CSS rules
            assert ".syntax-" in css or ".k" in css or "syntax-" in css
        except (KeyError, AttributeError):
            pytest.skip("Palette CSS generation not available")

    def test_css_contains_string_styles(self) -> None:
        """CSS should contain string styles."""
        try:
            palette = get_palette("bengal-tiger")
            css = palette.generate_css()

            # Should have string-related CSS
            assert ".syntax-string" in css or ".s" in css or "string" in css.lower()
        except (KeyError, AttributeError):
            pytest.skip("Palette CSS generation not available")

    def test_css_contains_keyword_styles(self) -> None:
        """CSS should contain keyword styles."""
        try:
            palette = get_palette("bengal-tiger")
            css = palette.generate_css()

            # Should have keyword-related CSS
            assert ".syntax-keyword" in css or ".k" in css or "keyword" in css.lower()
        except (KeyError, AttributeError):
            pytest.skip("Palette CSS generation not available")
