"""
Tests for bengal graph commands.

Covers:
- graph orphans
- graph bridges
- graph pagerank
- graph communities
- graph suggest
- graph report
- graph analyze
With mock Site or minimal site fixture.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from bengal.cli.commands.graph import graph_cli


def _create_minimal_site(tmp_path: Path) -> None:
    """Create minimal site for graph commands."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")
    (content_dir / "about.md").write_text("---\ntitle: About\n---\n# About")

    config_file = tmp_path / "bengal.toml"
    config_file.write_text(
        """
[site]
title = "Test Site"

[build]
output_dir = "public"
"""
    )


class TestGraphOrphans:
    """Test graph orphans command."""

    def test_orphans_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph orphans runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["orphans", str(tmp_path)])

        assert result.exit_code == 0

    def test_orphans_with_format_paths(self, tmp_path: Path) -> None:
        """Graph orphans --format paths outputs paths."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            graph_cli,
            ["orphans", "--format", "paths", str(tmp_path)],
        )

        assert result.exit_code == 0


class TestGraphAnalyze:
    """Test graph analyze command."""

    def test_analyze_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph analyze runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["analyze", str(tmp_path)])

        assert result.exit_code == 0
        assert "pages" in result.output.lower() or "Analyzing" in result.output


class TestGraphReport:
    """Test graph report command."""

    def test_report_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph report runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["report", str(tmp_path)])

        assert result.exit_code == 0


class TestGraphPagerank:
    """Test graph pagerank command."""

    def test_pagerank_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph pagerank runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["pagerank", str(tmp_path)])

        assert result.exit_code == 0


class TestGraphCommunities:
    """Test graph communities command."""

    def test_communities_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph communities runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["communities", str(tmp_path)])

        assert result.exit_code == 0


class TestGraphBridges:
    """Test graph bridges command."""

    def test_bridges_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph bridges runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["bridges", str(tmp_path)])

        assert result.exit_code == 0


class TestGraphSuggest:
    """Test graph suggest command."""

    def test_suggest_with_minimal_site(self, tmp_path: Path) -> None:
        """Graph suggest runs with minimal site."""
        _create_minimal_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(graph_cli, ["suggest", str(tmp_path)])

        assert result.exit_code == 0
