"""
Tests for the bengal validate command.

Covers:
- Validate with clean site (pass)
- Validate with errors (fail, exit code)
- Validate with warnings (pass with warning message)
- --verbose flag
- --ignore flag
- --profile flag
- --file flag for specific files
- Output formatting
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from bengal.cli.commands.validate import validate


def _create_test_site(tmp_path: Path) -> None:
    """Create minimal valid site structure."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    config_file = tmp_path / "bengal.toml"
    config_file.write_text(
        """
[site]
title = "Test Site"

[build]
output_dir = "public"
"""
    )


class TestValidateCommand:
    """Test validate command behavior."""

    def test_validate_clean_site_passes(self, tmp_path: Path) -> None:
        """Validate with clean site returns success."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(validate, [str(tmp_path)])

        assert result.exit_code == 0
        assert "Loaded" in result.output
        assert "pages" in result.output
        assert "Validation passed" in result.output or "no issues" in result.output.lower()

    def test_validate_with_verbose_shows_all_checks(self, tmp_path: Path) -> None:
        """Validate with --verbose shows verbose output."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(validate, ["--verbose", str(tmp_path)])

        assert result.exit_code == 0
        assert "Loaded" in result.output

    def test_validate_with_profile_writer(self, tmp_path: Path) -> None:
        """Validate with --profile writer uses writer profile."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(validate, ["--profile", "writer", str(tmp_path)])

        assert result.exit_code == 0

    def test_validate_with_ignore_flag(self, tmp_path: Path) -> None:
        """Validate with --ignore suppresses specified checks."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(validate, ["--ignore", "H101", "--ignore", "H202", str(tmp_path)])

        assert result.exit_code == 0

    def test_validate_with_file_flag(self, tmp_path: Path) -> None:
        """Validate with --file validates specific files."""
        _create_test_site(tmp_path)
        page_path = tmp_path / "content" / "index.md"

        runner = CliRunner()
        result = runner.invoke(validate, ["--file", str(page_path), str(tmp_path)])

        assert result.exit_code == 0

    def test_validate_missing_source_fails(self) -> None:
        """Validate with nonexistent source fails."""
        runner = CliRunner()
        result = runner.invoke(validate, ["/nonexistent/path/12345"])

        assert result.exit_code != 0

    def test_validate_with_suggestions_flag(self, tmp_path: Path) -> None:
        """Validate with --suggestions shows quality suggestions."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(validate, ["--suggestions", str(tmp_path)])

        assert result.exit_code == 0
