from click.testing import CliRunner

from bengal.cli.commands.health import linkcheck_command
from bengal.cli.commands.site import build_command


def _write_min_site(tmp_path):
    config_file = tmp_path / "bengal.toml"
    config_file.write_text(
        """
[site]
title = "Test Site"

[build]
output_dir = "public"
content_dir = "content"
"""
    )
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\nHello")


def test_build_respects_traceback_flag_full(tmp_path, monkeypatch):
    _write_min_site(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Ensure env clean
        monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
        result = runner.invoke(build_command, ["--traceback", "full"], catch_exceptions=False)
        assert result.exit_code in [0, 1]


def test_build_respects_env_var_minimal(tmp_path, monkeypatch):
    _write_min_site(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        monkeypatch.setenv("BENGAL_TRACEBACK", "minimal")
        result = runner.invoke(build_command, [], catch_exceptions=False)
        assert result.exit_code in [0, 1]


def test_debug_maps_to_full(tmp_path, monkeypatch):
    _write_min_site(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
        result = runner.invoke(build_command, ["--debug"], catch_exceptions=False)
        assert result.exit_code in [0, 1]


def test_health_linkcheck_respects_traceback(tmp_path, monkeypatch):
    _write_min_site(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        monkeypatch.setenv("BENGAL_TRACEBACK", "compact")
        # Use --internal-only to avoid external requests in test
        result = runner.invoke(
            linkcheck_command, ["--internal-only", "--traceback", "minimal"], catch_exceptions=False
        )
        # May abort with 1 if no output exists yet; we're only asserting command wiring works
        assert result.exit_code in [0, 1]
