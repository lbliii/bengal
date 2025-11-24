"""Helper for loading Site instances from CLI arguments."""

from __future__ import annotations

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.cli_output import CLIOutput


def load_site_from_cli(
    source: str = ".",
    config: str | None = None,
    environment: str | None = None,
    profile: str | None = None,
    cli: CLIOutput | None = None,
) -> Site:
    """
    Load a Site instance from CLI arguments with consistent error handling.

    Args:
        source: Source directory path (default: current directory)
        config: Optional config file path
        environment: Optional environment name (local, preview, production)
        profile: Optional profile name (writer, theme-dev, dev)
        cli: Optional CLIOutput instance (creates new if not provided)

    Returns:
        Site instance

    Raises:
        click.Abort: If site loading fails

    Example:
        @click.command()
        def my_command(source: str, config: str | None):
            site = load_site_from_cli(source, config)
            # ... use site ...
    """
    if cli is None:
        cli = CLIOutput()

    root_path = Path(source).resolve()

    if not root_path.exists():
        cli.error(f"Source directory does not exist: {root_path}")
        raise click.Abort()

    config_path = Path(config).resolve() if config else None

    if config_path and not config_path.exists():
        cli.error(f"Config file does not exist: {config_path}")
        raise click.Abort()

    try:
        site = Site.from_config(root_path, config_path, environment=environment, profile=profile)
        return site
    except Exception as e:
        cli.error(f"Failed to load site from {root_path}: {e}")
        raise click.Abort() from e
