"""Tests for theme CSS generation error handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.errors import BengalAssetError, ErrorCode
from bengal.themes.generate import generate_web_css, write_generated_css


class TestWriteGeneratedCSS:
    """Tests for write_generated_css error handling."""

    def test_successful_write(self, tmp_path: Path) -> None:
        """Verify successful CSS generation."""
        output_path = write_generated_css(tmp_path)

        assert output_path.exists()
        assert output_path.name == "generated.css"
        assert "--bengal-primary:" in output_path.read_text()

    @pytest.mark.skipif(
        hasattr(__import__("os"), "getuid") and __import__("os").getuid() == 0,
        reason="Cannot test permission error as root",
    )
    def test_permission_error_on_mkdir_raises_asset_error(self, tmp_path: Path) -> None:
        """Verify permission error on mkdir raises BengalAssetError with X004."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o444)

        try:
            with pytest.raises(BengalAssetError) as exc_info:
                write_generated_css(readonly_dir / "subdir")

            assert exc_info.value.code == ErrorCode.X004
            assert exc_info.value.suggestion is not None
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_permission_error_on_write_raises_asset_error(self, tmp_path: Path) -> None:
        """Verify permission error on write raises BengalAssetError with X004."""
        with patch.object(Path, "write_text") as mock_write:
            mock_write.side_effect = OSError("Permission denied")

            with pytest.raises(BengalAssetError) as exc_info:
                write_generated_css(tmp_path)

            assert exc_info.value.code == ErrorCode.X004
            assert "permission" in exc_info.value.suggestion.lower()

    def test_generate_web_css_contains_tokens(self) -> None:
        """Verify generated CSS contains expected tokens."""
        css = generate_web_css()

        assert ":root {" in css
        assert "--bengal-primary:" in css
        assert "--bengal-success:" in css
        assert "--bengal-error:" in css

    def test_generate_web_css_contains_palette_variants(self) -> None:
        """Verify generated CSS contains palette variant classes."""
        css = generate_web_css()

        # Should contain palette classes (not "default" which is skipped)
        assert ".palette-" in css

    def test_asset_error_has_file_path(self, tmp_path: Path) -> None:
        """Verify BengalAssetError includes file path context."""
        with patch.object(Path, "write_text") as mock_write:
            mock_write.side_effect = OSError("Disk full")

            with pytest.raises(BengalAssetError) as exc_info:
                write_generated_css(tmp_path)

            assert exc_info.value.file_path is not None
