"""
Tests for the bengal serve command.

Covers:
- Port selection and host binding validation
- --open flag handling
- Error on missing site directory
- Conflicting flag validation (--verbose and --debug)
- Mock server startup to avoid binding
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bengal.cli.commands.serve import serve


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


class TestServeCommand:
    """Test serve command behavior."""

    def test_serve_validates_verbose_debug_conflict(self) -> None:
        """Serve fails when --verbose and --debug used together."""
        runner = CliRunner()
        result = runner.invoke(
            serve,
            ["--verbose", "--debug", "/tmp"],
        )

        assert result.exit_code != 0
        assert "cannot be used together" in result.output

    def test_serve_validates_version_flags_conflict(self, tmp_path: Path) -> None:
        """Serve fails when --version and --all-versions used together."""
        _create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            serve,
            ["--version", "v2", "--all-versions", str(tmp_path)],
        )

        assert result.exit_code != 0
        assert "cannot be used together" in result.output

    def test_serve_fails_on_missing_source(self) -> None:
        """Serve fails when source directory does not exist."""
        runner = CliRunner()
        result = runner.invoke(serve, ["/nonexistent/path/12345"])

        assert result.exit_code != 0

    @patch("bengal.cli.commands.serve.load_site_from_cli")
    def test_serve_loads_site_and_calls_serve(self, mock_load: MagicMock, tmp_path: Path) -> None:
        """Serve loads site and calls site.serve() with correct args."""
        _create_test_site(tmp_path)
        mock_site = MagicMock()
        mock_load.return_value = mock_site

        runner = CliRunner()
        # Use --no-open to avoid browser, mock will prevent actual server start
        result = runner.invoke(
            serve,
            ["--port", "19999", "--no-open", str(tmp_path)],
        )

        assert result.exit_code == 0
        mock_load.assert_called_once()
        mock_site.serve.assert_called_once()
        call_kwargs = mock_site.serve.call_args[1]
        assert call_kwargs["port"] == 19999
        assert call_kwargs["open_browser"] is False
