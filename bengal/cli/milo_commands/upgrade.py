"""Upgrade command — check for and install Bengal updates."""

from __future__ import annotations

import subprocess
from typing import Annotated

from milo import Description


def upgrade(
    dry_run: Annotated[bool, Description("Show what would be done without executing")] = False,
    yes: Annotated[bool, Description("Skip confirmation prompt")] = False,
    force: Annotated[bool, Description("Force upgrade even if already on latest version")] = False,
) -> dict:
    """Check for and install Bengal updates."""
    from bengal import __version__
    from bengal.cli.helpers.upgrade_check import fetch_latest_version
    from bengal.cli.helpers.upgrade_installers import detect_installer
    from bengal.cli.utils import get_cli_output

    cli = get_cli_output()

    cli.info("Checking for updates...")
    latest = fetch_latest_version()

    if not latest:
        cli.error("Failed to check PyPI for latest version")
        cli.tip("Check your internet connection or try again later")
        raise SystemExit(1)

    installer = detect_installer()
    is_outdated = latest != __version__

    cli.render_write(
        "upgrade_status.kida",
        current=__version__,
        latest=latest,
        installer={"name": installer.name, "command": installer.display_command},
        up_to_date=not is_outdated and not force,
        dry_run=dry_run,
    )

    if not is_outdated and not force:
        return {"current": __version__, "latest": latest, "upgraded": False, "up_to_date": True}

    if dry_run:
        return {"current": __version__, "latest": latest, "upgraded": False, "dry_run": True}

    if not yes:
        try:
            answer = input("Proceed with upgrade? [Y/n] ").strip().lower()
            if answer and answer not in ("y", "yes"):
                cli.info("Upgrade cancelled")
                return {"status": "skipped", "message": "Upgrade cancelled", "upgraded": False}
        except EOFError, KeyboardInterrupt:
            cli.info("\nUpgrade cancelled")
            return {"status": "skipped", "message": "Upgrade cancelled", "upgraded": False}

    cli.info("Upgrading bengal...")

    try:
        subprocess.run(
            installer.command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        cli.success(f"Successfully upgraded to v{latest}")
        return {"current": __version__, "latest": latest, "upgraded": True}
    except subprocess.CalledProcessError as e:
        cli.error("Upgrade failed")
        if e.stderr:
            cli.info(e.stderr)
        cli.info(f"Try running manually: {installer.display_command}")
        raise SystemExit(1) from None
    except subprocess.TimeoutExpired:
        cli.error("Upgrade timed out after 120s")
        cli.info(f"Try running manually: {installer.display_command}")
        raise SystemExit(1) from None
