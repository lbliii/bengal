"""Tests for the Milo clean command output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class _FakePaths:
    state_dir: Path


@dataclass
class _FakeConfigService:
    paths: _FakePaths


class _FakeSite:
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config_service = _FakeConfigService(_FakePaths(root_path / ".bengal"))
        self.cleaned = False

    def clean(self) -> None:
        self.cleaned = True
        self.output_dir.mkdir(exist_ok=True)


def test_clean_cache_output_uses_bengal_template(monkeypatch, tmp_path, capsys):
    """Clean preflight/result output should be branded, concise, and relative."""
    import bengal.cli.utils as cli_utils
    from bengal.cli.milo_commands.clean import clean

    cli_utils.reset_cli_output()
    site = _FakeSite(tmp_path)
    site.config_service.paths.state_dir.mkdir()

    monkeypatch.setattr(cli_utils, "load_site_from_cli", lambda **_kwargs: site)

    result = clean(source=".", force=True, cache=True)
    output = capsys.readouterr().out

    assert result["status"] == "ok"
    assert site.cleaned is True
    assert output.startswith("ᓚᘏᗢ Clean output and cache")
    assert "Output    public/" in output
    assert "Cache     .bengal/" in output
    assert "Complete rebuild required next time." in output
    assert "✓ Clean complete" in output
    assert "Next build will be cold." in output
