"""Autodoc CLI extraction tests for the real Bengal Milo app (issue #621)."""

from __future__ import annotations

from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.cli import cli
from tests._testing.cli_help_snapshot import registered_command_inventory


def test_bengal_cli_extractor_matches_registered_inventory() -> None:
    """Autodoc CLI extraction must cover every advertised leaf command."""
    elements = CLIExtractor(framework="milo").extract(cli)
    extracted = sorted(
        element.qualified_name.removeprefix("bengal.")
        for element in elements
        if element.element_type == "command"
    )
    registered = registered_command_inventory()
    assert extracted == registered, (
        "Autodoc CLI extraction drifted from Milo registry.\n"
        f"  autodoc-only: {sorted(set(extracted) - set(registered))}\n"
        f"  registry-only: {sorted(set(registered) - set(extracted))}"
    )


def test_bengal_cli_extractor_includes_option_metadata() -> None:
    """Leaf commands should expose Milo JSON Schema options for autodoc pages."""
    elements = CLIExtractor(framework="milo").extract(cli)
    build = next(element for element in elements if element.qualified_name == "bengal.build")
    option_names = {child.name for child in build.children if child.element_type == "option"}
    assert "strict" in option_names
    assert "incremental" in option_names
