"""CLI serve command contract tests.

Ensures default port behavior and URL output formatting are stable.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from bengal.cli import main as cli_main


class DummySite:
    """Minimal stand-in for Site to avoid starting the real server."""

    def __init__(self, root_path: Path, config: dict[str, Any] | None = None) -> None:
        self.root_path = root_path
        self.config = config or {}

    @classmethod
    def from_config(cls, root_path: Path, _config_path: Path | None = None) -> DummySite:
        return cls(root_path, config={})

    # Do not block; just print the URL like BuildHandler would after rebuild
    def serve(self, host: str, port: int, watch: bool, auto_port: bool, open_browser: bool) -> None:
        print(f"\n  \x1b[36m➜\x1b[0m  Local: \x1b[1mhttp://{host}:{port}/\x1b[0m\n")


@pytest.mark.usefixtures()
def test_serve_uses_default_port_and_prints_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default port should be 5173 and URL printed should match."""
    # Patch Site to DummySite
    import bengal.core.site as site_module

    monkeypatch.setattr(site_module, "Site", DummySite, raising=True)

    runner = CliRunner()

    # Capture stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = runner.invoke(cli_main, ["serve", str(tmp_path)])

    assert result.exit_code == 0
    out = buf.getvalue()
    assert "http://localhost:5173/" in out


def test_serve_respects_custom_port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom port via --port should be respected."""
    import bengal.core.site as site_module

    monkeypatch.setattr(site_module, "Site", DummySite, raising=True)

    runner = CliRunner()
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = runner.invoke(cli_main, ["serve", "--port", "8080", str(tmp_path)])

    assert result.exit_code == 0
    out = buf.getvalue()
    assert "http://localhost:8080/" in out
