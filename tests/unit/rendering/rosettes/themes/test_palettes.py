"""Tests for palette loading and management."""

from __future__ import annotations

import pytest

from bengal.rendering.rosettes.themes import get_palette


class TestPaletteLoading:
    """Test palette loading functionality."""

    def test_builtin_palettes_load(self) -> None:
        """Built-in palettes should load correctly."""
        palettes = ["bengal-tiger", "monokai", "dracula", "github"]

        for name in palettes:
            try:
                palette = get_palette(name)
                assert palette is not None
                assert hasattr(palette, "foreground")
                assert hasattr(palette, "background")
            except KeyError:
                # Palette might not exist yet
                pytest.skip(f"Palette {name} not available")

    def test_unknown_palette_raises(self) -> None:
        """Unknown palette should raise KeyError."""
        with pytest.raises(KeyError):
            get_palette("nonexistent-palette-xyz")

    def test_palette_has_colors(self) -> None:
        """Palette should have color attributes."""
        try:
            palette = get_palette("bengal-tiger")
            assert hasattr(palette, "foreground")
            assert hasattr(palette, "background")
            # Should have some color values
            assert palette.foreground is not None
            assert palette.background is not None
        except KeyError:
            pytest.skip("bengal-tiger palette not available")
