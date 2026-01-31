"""
Tests for GoogleFontsDownloader cache-checking functionality.

These tests cover the local cache detection methods which avoid network
requests when fonts are already downloaded. Network-dependent methods
remain untested by design (see TEST_COVERAGE.md).
"""

from pathlib import Path

import pytest

from bengal.fonts.downloader import FontVariant, GoogleFontsDownloader


class TestCheckCachedFonts:
    """Tests for _check_cached_fonts method."""

    @pytest.fixture
    def downloader(self) -> GoogleFontsDownloader:
        """Create a downloader instance."""
        return GoogleFontsDownloader()

    def test_returns_none_when_no_fonts_exist(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns None when no font files are cached."""
        result = downloader._check_cached_fonts("Inter", [400, 700], ["normal"], tmp_path)
        assert result is None

    def test_returns_none_when_partial_cache(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns None when only some fonts are cached (partial cache)."""
        # Create only one of two expected fonts
        (tmp_path / "inter-400.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts("Inter", [400, 700], ["normal"], tmp_path)
        assert result is None

    def test_returns_variants_when_all_woff2_cached(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns FontVariant list when all woff2 fonts are cached."""
        (tmp_path / "inter-400.woff2").write_bytes(b"fake font")
        (tmp_path / "inter-700.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts("Inter", [400, 700], ["normal"], tmp_path)

        assert result is not None
        assert len(result) == 2
        assert all(isinstance(v, FontVariant) for v in result)
        assert {v.weight for v in result} == {400, 700}

    def test_returns_variants_when_ttf_fallback_exists(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Falls back to TTF if woff2 not present (mixed format cache)."""
        (tmp_path / "inter-400.woff2").write_bytes(b"fake font")
        (tmp_path / "inter-700.ttf").write_bytes(b"fake font")  # TTF fallback

        result = downloader._check_cached_fonts("Inter", [400, 700], ["normal"], tmp_path)

        assert result is not None
        assert len(result) == 2

    def test_handles_italic_styles(self, downloader: GoogleFontsDownloader, tmp_path: Path) -> None:
        """Correctly checks for italic variants with -italic suffix."""
        (tmp_path / "inter-400.woff2").write_bytes(b"fake font")
        (tmp_path / "inter-400-italic.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts("Inter", [400], ["normal", "italic"], tmp_path)

        assert result is not None
        assert len(result) == 2
        styles = {v.style for v in result}
        assert styles == {"normal", "italic"}

    def test_handles_multi_word_font_names(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Correctly handles font names with spaces (e.g., 'Playfair Display')."""
        (tmp_path / "playfair-display-400.woff2").write_bytes(b"fake font")
        (tmp_path / "playfair-display-700.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts(
            "Playfair Display", [400, 700], ["normal"], tmp_path
        )

        assert result is not None
        assert len(result) == 2
        # Family name should be preserved in variants
        assert all(v.family == "Playfair Display" for v in result)

    def test_variant_has_cached_url(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Cached variants have placeholder URL (not network URL)."""
        (tmp_path / "outfit-400.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts("Outfit", [400], ["normal"], tmp_path)

        assert result is not None
        assert result[0].url.startswith("cached://")


class TestCheckCachedTTFFonts:
    """Tests for _check_cached_fonts method with font_format='ttf' (TTF-only cache check)."""

    @pytest.fixture
    def downloader(self) -> GoogleFontsDownloader:
        """Create a downloader instance."""
        return GoogleFontsDownloader()

    def test_returns_none_when_no_ttf_fonts_exist(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns None when no TTF font files are cached."""
        result = downloader._check_cached_fonts(
            "Outfit", [400, 700], ["normal"], tmp_path, font_format="ttf"
        )
        assert result is None

    def test_ignores_woff2_files(self, downloader: GoogleFontsDownloader, tmp_path: Path) -> None:
        """Only checks for TTF files, ignores woff2."""
        # Create woff2 files (should be ignored for TTF check)
        (tmp_path / "outfit-400.woff2").write_bytes(b"fake font")
        (tmp_path / "outfit-700.woff2").write_bytes(b"fake font")

        result = downloader._check_cached_fonts(
            "Outfit", [400, 700], ["normal"], tmp_path, font_format="ttf"
        )
        assert result is None  # No TTF files, should return None

    def test_returns_variants_when_all_ttf_cached(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns FontVariant list when all TTF fonts are cached."""
        (tmp_path / "outfit-400.ttf").write_bytes(b"fake font")
        (tmp_path / "outfit-700.ttf").write_bytes(b"fake font")

        result = downloader._check_cached_fonts(
            "Outfit", [400, 700], ["normal"], tmp_path, font_format="ttf"
        )

        assert result is not None
        assert len(result) == 2
        assert all(isinstance(v, FontVariant) for v in result)

    def test_returns_none_when_partial_ttf_cache(
        self, downloader: GoogleFontsDownloader, tmp_path: Path
    ) -> None:
        """Returns None when only some TTF fonts are cached."""
        (tmp_path / "outfit-400.ttf").write_bytes(b"fake font")
        # Missing outfit-700.ttf

        result = downloader._check_cached_fonts(
            "Outfit", [400, 700], ["normal"], tmp_path, font_format="ttf"
        )
        assert result is None


class TestFontVariant:
    """Tests for FontVariant dataclass."""

    def test_filename_normal_woff2(self) -> None:
        """Generates correct filename for normal weight woff2."""
        variant = FontVariant("Inter", 400, "normal", "https://fonts.gstatic.com/inter.woff2")
        assert variant.filename == "inter-400.woff2"

    def test_filename_italic_woff2(self) -> None:
        """Generates correct filename for italic weight woff2."""
        variant = FontVariant("Inter", 400, "italic", "https://fonts.gstatic.com/inter.woff2")
        assert variant.filename == "inter-400-italic.woff2"

    def test_filename_ttf(self) -> None:
        """Generates correct filename for TTF format."""
        variant = FontVariant("Outfit", 700, "normal", "https://fonts.gstatic.com/outfit.ttf")
        assert variant.filename == "outfit-700.ttf"

    def test_filename_multi_word_family(self) -> None:
        """Generates correct filename for multi-word family names."""
        variant = FontVariant(
            "Playfair Display", 700, "normal", "https://fonts.gstatic.com/playfair.woff2"
        )
        assert variant.filename == "playfair-display-700.woff2"
