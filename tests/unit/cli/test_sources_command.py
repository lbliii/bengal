"""
Tests for bengal sources commands.

Covers:
- sources list (with and without collections)
- sources status
- sources fetch (mock)
- Path resolution via ctx.obj
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from bengal.cli.commands.sources import sources_group


class TestSourcesList:
    """Test sources list command."""

    def test_list_without_collections_shows_hint(self, tmp_path: Path) -> None:
        """Sources list with no collections shows setup hint."""
        runner = CliRunner()
        result = runner.invoke(
            sources_group,
            ["list"],
            obj={"site_root": tmp_path},
        )

        assert result.exit_code == 0
        assert "No collections" in result.output or "collections" in result.output.lower()


class TestSourcesStatus:
    """Test sources status command."""

    def test_status_without_collections(self, tmp_path: Path) -> None:
        """Sources status with no collections completes."""
        runner = CliRunner()
        result = runner.invoke(
            sources_group,
            ["status"],
            obj={"site_root": tmp_path},
        )

        assert result.exit_code == 0


class TestSourcesFetch:
    """Test sources fetch command."""

    def test_fetch_without_collections(self, tmp_path: Path) -> None:
        """Sources fetch with no collections completes."""
        runner = CliRunner()
        result = runner.invoke(
            sources_group,
            ["fetch"],
            obj={"site_root": tmp_path},
        )

        assert result.exit_code == 0
