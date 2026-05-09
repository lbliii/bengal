"""Tests for the plugin introspection CLI command handlers."""

from __future__ import annotations

import pytest

from bengal.cli.milo_commands import plugin as plugin_command
from bengal.plugins.inspection import PluginInspection


class FakeCLI:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.renders: list[tuple[str, dict]] = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def render_write(self, template: str, **context: object) -> None:
        self.renders.append((template, context))

    def error(self, message: str) -> None:
        self.infos.append(message)

    def tip(self, message: str) -> None:
        self.infos.append(message)


def test_plugin_list_reports_no_plugins(monkeypatch) -> None:
    cli = FakeCLI()
    monkeypatch.setattr(plugin_command, "_load_reports", list)
    monkeypatch.setattr("bengal.output.get_cli_output", lambda: cli)

    result = plugin_command.plugin_list()

    assert result == {"plugins": [], "count": 0}
    assert cli.infos == []
    assert cli.renders == [
        (
            "command_empty.kida",
            {
                "title": "Bengal Plugins",
                "message": "No Bengal plugins discovered.",
                "steps": [
                    "Install a package that exposes the bengal.plugins entry point.",
                    "Run `bengal plugin validate` after installing or editing a plugin.",
                ],
            },
        )
    ]


def test_plugin_validate_fails_on_pending_capability(monkeypatch) -> None:
    cli = FakeCLI()
    report = PluginInspection(
        entry_point="content-source",
        value="example:ContentSourcePlugin",
        plugin_name="content-source-plugin",
        version="1.0.0",
        status="partial",
        capabilities={"content_sources": 1},
    )
    monkeypatch.setattr(plugin_command, "_load_reports", lambda: [report])
    monkeypatch.setattr("bengal.output.get_cli_output", lambda: cli)

    with pytest.raises(SystemExit):
        plugin_command.plugin_validate()

    assert cli.renders
    _template, context = cli.renders[0]
    assert context["summary"]["warnings"] == 1
    assert "content_sources registered" in context["issues"][0]["message"]
