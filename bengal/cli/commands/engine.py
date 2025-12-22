"""Template engine CLI commands."""

from __future__ import annotations

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@click.group(cls=BengalGroup)
def engine() -> None:
    """Template engine utilities (list, info)."""
    pass


@engine.command("list")
@command_metadata(
    category="engines",
    description="List available template engines",
    examples=[
        "bengal engine list",
        "bengal engine list --verbose",
    ],
    requires_site=False,
    tags=["engines", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list_engines(verbose: bool) -> None:
    """
    📋 List available template engines.

    Shows all built-in engines and any registered third-party engines.

    Examples:
        bengal engine list
        bengal engine list --verbose
    """
    cli = get_cli_output()
    from bengal.rendering.engines import _ENGINES

    # Built-in engines with their status
    builtin_engines = [
        {
            "name": "jinja2",
            "description": "Jinja2 templates (default)",
            "status": "✅ Available",
            "install": "Built-in",
        },
        {
            "name": "mako",
            "description": "Mako templates - HTML + real Python",
            "status": _check_engine_available("mako"),
            "install": "pip install bengal[mako]",
        },
        {
            "name": "patitas",
            "description": "Patitas templates - pure Python",
            "status": _check_engine_available("patitas"),
            "install": "pip install bengal[patitas]",
        },
    ]

    cli.info("[bold]Template Engines[/bold]")
    cli.info("")

    cli.info("[bold]Built-in Engines[/bold]")
    cli.info("")

    for eng in builtin_engines:
        status_icon = "🟢" if "Available" in eng["status"] else "⚪"
        cli.info(f"  {status_icon} [cyan]{eng['name']}[/cyan] - {eng['description']}")
        if verbose:
            cli.info(f"      Status: {eng['status']}")
            cli.info(f"      Install: {eng['install']}")
            cli.info("")

    # Third-party registered engines
    if _ENGINES:
        cli.info("")
        cli.info("[bold]Third-Party Engines[/bold]")
        cli.info("")
        for name, engine_class in _ENGINES.items():
            cli.info(f"  🔌 [cyan]{name}[/cyan] - {engine_class.__doc__ or 'Custom engine'}")
            if verbose:
                cli.info(f"      Class: {engine_class.__module__}.{engine_class.__name__}")
                cli.info("")

    cli.info("")
    cli.info("[dim]Configure in bengal.yaml:[/dim]")
    cli.info("[dim]  site:[/dim]")
    cli.info("[dim]    template_engine: jinja2[/dim]")

    if verbose:
        cli.info("")
        cli.info("[dim]To register a custom engine:[/dim]")
        cli.info("[dim]  from bengal.rendering.engines import register_engine[/dim]")
        cli.info("[dim]  register_engine('myengine', MyEngineClass)[/dim]")


@engine.command("info")
@command_metadata(
    category="engines",
    description="Show current template engine configuration",
    examples=[
        "bengal engine info",
        "bengal engine info --source /path/to/site",
    ],
    requires_site=True,
    tags=["engines", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
@click.option("--config", "-c", type=click.Path(), help="Path to config file")
def info(source: str, config: str | None) -> None:
    """
    Show current template engine configuration.

    Displays the active template engine and its configuration for a site.

    Examples:
        bengal engine info
        bengal engine info --source /path/to/site
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    engine_name = site.config.get("template_engine", "jinja2")

    cli.info("[bold]Template Engine Info[/bold]")
    cli.info("")

    cli.info(f"[bold]Active Engine:[/bold] [cyan]{engine_name}[/cyan]")
    cli.info(f"[bold]Site:[/bold] {site.root_path}")
    cli.info("")

    # Get engine instance for details
    from bengal.rendering.engines import create_engine

    try:
        engine = create_engine(site)
        cli.info("[bold]Template Directories:[/bold]")
        for i, template_dir in enumerate(engine.template_dirs, 1):
            exists = "✅" if template_dir.exists() else "❌"
            cli.info(f"  {i}. {exists} {template_dir}")

        cli.info("")
        templates = engine.list_templates()
        cli.info(f"[bold]Templates Available:[/bold] {len(templates)}")

        # Show first few templates as sample
        if templates:
            cli.info("")
            cli.info("[bold]Sample Templates:[/bold]")
            for template in templates[:5]:
                cli.info(f"  • {template}")
            if len(templates) > 5:
                cli.info(f"  [dim]... and {len(templates) - 5} more[/dim]")

    except ValueError as e:
        cli.error(f"Engine error: {e}")
        return

    cli.info("")
    cli.info("[dim]To change engine, update bengal.yaml:[/dim]")
    cli.info("[dim]  site:[/dim]")
    cli.info(f"[dim]    template_engine: {engine_name}[/dim]")


def _check_engine_available(engine_name: str) -> str:
    """Check if an optional engine is available."""
    if engine_name == "mako":
        try:
            import mako  # noqa: F401

            return "✅ Available"
        except ImportError:
            return "⚪ Not installed"
    elif engine_name == "patitas":
        try:
            import patitas  # noqa: F401

            return "✅ Available"
        except ImportError:
            return "⚪ Not installed"
    return "⚪ Unknown"
