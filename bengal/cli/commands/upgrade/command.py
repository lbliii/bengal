"""
bengal upgrade command implementation.

Provides an interactive upgrade experience that:
- Checks PyPI for the latest version
- Detects how Bengal was installed
- Shows a clear upgrade summary
- Executes the appropriate upgrade command

Usage:
    bengal upgrade           # Interactive upgrade
    bengal upgrade -y        # Skip confirmation
    bengal upgrade --dry-run # Show command without running
    bengal upgrade --force   # Force upgrade even if on latest

Related:
- bengal/cli/commands/upgrade/check.py: Version checking
- bengal/cli/commands/upgrade/installers.py: Installer detection
"""

from __future__ import annotations

import subprocess

import click
import questionary

from bengal import __version__
from bengal.cli.base import BengalCommand
from bengal.cli.commands.upgrade.check import fetch_latest_version
from bengal.cli.commands.upgrade.installers import detect_installer
from bengal.output import CLIOutput


@click.command(cls=BengalCommand, name="upgrade")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without executing",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force upgrade even if already on latest version",
)
def upgrade(dry_run: bool, yes: bool, force: bool) -> None:
    """
    Upgrade Bengal to the latest version.

    Automatically detects how Bengal was installed (uv, pip, pipx, conda)
    and runs the appropriate upgrade command.

    Examples:
        bengal upgrade           # Interactive upgrade
        bengal upgrade -y        # Skip confirmation
        bengal upgrade --dry-run # Show command without running
        bengal upgrade --force   # Force upgrade even if on latest

    """
    cli = CLIOutput()

    # Check for latest version
    cli.info("Checking for updates...")
    latest = fetch_latest_version()

    if not latest:
        cli.error("Failed to check PyPI for latest version")
        cli.tip("Check your internet connection or try again later")
        raise SystemExit(1)

    # Detect installer
    installer = detect_installer()

    # Display upgrade info
    is_outdated = latest != __version__

    # Calculate padding for box alignment
    current_line = f"Current version: {__version__}"
    latest_line = f"Latest version:  {latest}"
    detected_line = f"Detected: {installer.name}"
    command_line = f"Command:  {installer.display_command}"

    # Find max content width
    max_width = max(len(current_line), len(latest_line), len(detected_line), len(command_line))
    box_width = max_width + 4  # Add padding

    click.echo()
    click.secho("╭─ Bengal Upgrade " + "─" * (box_width - 16) + "╮", fg="cyan")
    click.secho(f"│ {current_line:<{box_width - 2}} │", fg="cyan")
    click.secho(f"│ {latest_line:<{box_width - 2}} │", fg="cyan")
    click.secho(f"│ {'':<{box_width - 2}} │", fg="cyan")
    click.secho(f"│ {detected_line:<{box_width - 2}} │", fg="cyan")
    click.secho(f"│ {command_line:<{box_width - 2}} │", fg="cyan")
    click.secho("╰" + "─" * box_width + "╯", fg="cyan")
    click.echo()

    if not is_outdated and not force:
        cli.success(f"Already on latest version (v{__version__})")
        return

    if dry_run:
        cli.info(f"Would run: {installer.display_command}")
        cli.info(f"Current: {__version__} → Latest: {latest}")
        return

    # Confirm with user
    if not yes:
        confirm = questionary.confirm("Proceed with upgrade?", default=True).ask()
        if not confirm:
            cli.info("Upgrade cancelled")
            return

    # Execute upgrade
    cli.info("Upgrading bengal...")

    try:
        result = subprocess.run(
            installer.command,
            check=True,
            capture_output=True,
            text=True,
        )
        cli.success(f"Successfully upgraded to v{latest}")
        click.echo()
        click.secho(
            f"Release notes: https://github.com/lbliii/bengal/releases/tag/v{latest}",
            dim=True,
        )
    except subprocess.CalledProcessError as e:
        cli.error("Upgrade failed")
        if e.stderr:
            click.echo(e.stderr, err=True)
        cli.tip(f"Try running manually: {installer.display_command}")
        raise SystemExit(1)


def show_upgrade_notification() -> None:
    """
    Show upgrade notification if available (non-blocking).

    Called after CLI commands complete to display a non-intrusive banner
    when a newer version is available. Designed to never fail or slow
    down the CLI.
    """
    try:
        from bengal.cli.commands.upgrade.check import check_for_upgrade

        info = check_for_upgrade()
        if info and info.is_outdated:
            # Calculate padding for box alignment
            version_text = f"Bengal v{info.latest} is available (you have v{info.current})"
            run_text = "Run: bengal upgrade"
            max_width = max(len(version_text), len(run_text)) + 2
            box_width = max_width + 2

            click.echo()
            click.secho(
                "╭─ Upgrade Available " + "─" * (box_width - 19) + "╮",
                fg="yellow",
                err=True,
            )
            click.secho(
                f"│ {version_text:<{box_width - 2}} │",
                fg="yellow",
                err=True,
            )
            click.secho(
                f"│ {run_text:<{box_width - 2}} │",
                fg="yellow",
                err=True,
            )
            click.secho("╰" + "─" * box_width + "╯", fg="yellow", err=True)
    except Exception:
        pass  # Never fail CLI due to upgrade check
