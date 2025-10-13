"""Basic build CLI flow contract test.

Verifies the command runs and prints a completion message in quiet mode.
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
    def __init__(self, root_path: Path, config: dict[str, Any] | None = None) -> None:
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.config = config or {}

    @classmethod
    def from_config(cls, root_path: Path, _config_path: Path | None = None) -> DummySite:
        return cls(root_path, config={})

    def build(self, **kwargs: Any):  # noqa: ANN401 - signature compatibility
        class Stats:
            template_errors: list[str] = []
            output_dir: str = str(self.output_dir)

        # Mimic output directory existence
        (self.output_dir).mkdir(parents=True, exist_ok=True)
        return Stats()


def test_build_quiet_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import bengal.core.site as site_module

    monkeypatch.setattr(site_module, "Site", DummySite, raising=True)

    runner = CliRunner()
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = runner.invoke(cli_main, ["build", "--quiet", str(tmp_path)])

    assert result.exit_code == 0
    out = buf.getvalue()
    assert "Build complete!" in out
