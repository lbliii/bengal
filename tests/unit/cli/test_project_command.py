"""
Tests for bengal project commands.

Covers:
- project info display
- project validate (config and structure)
- project profile list and set
- Path resolution
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from bengal.cli.commands.project import project_cli


def _create_test_site(tmp_path: Path) -> None:
    """Create minimal valid site structure."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "base.html").write_text("<html><body>{{ content }}</body></html>")

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    config_file = tmp_path / "bengal.toml"
    config_file.write_text(
        """
[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
"""
    )


class TestProjectInfo:
    """Test project info command."""

    def test_info_displays_site_config(self, tmp_path: Path, monkeypatch) -> None:
        """Project info shows site title, baseurl, theme."""
        _create_test_site(tmp_path)
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["info"])

        assert result.exit_code == 0
        assert "Test Site" in result.output
        assert "Site Configuration" in result.output or "Title" in result.output

    def test_info_fails_without_config(self, tmp_path: Path, monkeypatch) -> None:
        """Project info fails when bengal.toml missing."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["info"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestProjectValidate:
    """Test project validate command."""

    def test_validate_passes_with_valid_site(self, tmp_path: Path, monkeypatch) -> None:
        """Project validate passes with valid structure."""
        _create_test_site(tmp_path)
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["validate"])

        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "✓" in result.output

    def test_validate_fails_without_config(self, tmp_path: Path, monkeypatch) -> None:
        """Project validate fails when bengal.toml missing."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["validate"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestProjectProfile:
    """Test project profile command."""

    def test_profile_list_shows_available(self, tmp_path: Path, monkeypatch) -> None:
        """Project profile without arg lists available profiles."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["profile"])

        assert result.exit_code == 0
        assert "dev" in result.output or "writer" in result.output

    def test_profile_set_saves_profile(self, tmp_path: Path, monkeypatch) -> None:
        """Project profile dev sets profile."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["profile", "dev"])

        assert result.exit_code == 0
        assert (tmp_path / ".bengal-profile").exists()
        assert (tmp_path / ".bengal-profile").read_text().strip() == "dev"

    def test_profile_invalid_fails(self, tmp_path: Path, monkeypatch) -> None:
        """Project profile with invalid name fails."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(project_cli, ["profile", "invalid-profile-name"])

        assert result.exit_code != 0
        assert "Unknown" in result.output or "invalid" in result.output.lower()
