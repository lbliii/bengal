"""
Skeleton Command.

CLI command to apply site skeletons.
"""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand, BengalGroup
from bengal.cli.helpers import command_metadata, handle_cli_errors
from bengal.cli.skeleton.hydrator import Hydrator
from bengal.cli.skeleton.schema import Skeleton
from bengal.output import CLIOutput


@click.group(cls=BengalGroup, name="skeleton")
def skeleton_cli() -> None:
    """
    Skeleton manifest commands.

    Apply declarative site structures from YAML manifests.
    """
    pass


@skeleton_cli.command(cls=BengalCommand)
@command_metadata(
    category="project",
    description="Apply a skeleton manifest to create site structure",
    examples=[
        "bengal project skeleton apply my-site.yaml",
        "bengal project skeleton apply my-site.yaml --dry-run",
    ],
    requires_site=True,
)
@click.argument("manifest")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without creating files",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
@handle_cli_errors(show_art=False)
def apply(manifest: str, dry_run: bool, force: bool) -> None:
    """
    Apply a skeleton manifest to hydrate site structure.

    The manifest is a YAML file defining the component structure (Identity/Mode/Data).
    """
    cli = CLIOutput()

    # 1. Load Manifest (Local file for now, URL support later)
    manifest_path = Path(manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest}")

    content = manifest_path.read_text()
    skeleton = Skeleton.from_yaml(content)

    cli.header(f"Applying skeleton: {skeleton.name or manifest}")
    if skeleton.description:
        cli.info(skeleton.description)
    cli.blank()

    # 2. Hydrate
    # Target 'content' directory by default
    target_dir = Path("content")
    hydrator = Hydrator(target_dir, dry_run=dry_run, force=force)

    try:
        hydrator.apply(skeleton)
    except Exception as e:
        cli.error(f"Failed to apply skeleton: {e}")
        raise click.Abort() from e

    # 3. Report
    cli.blank()
    if dry_run:
        cli.warning("📋 Dry Run - No files created")
    else:
        cli.success("✨ Skeleton applied successfully")

    cli.info(f"Created: {len(hydrator.created_files)} files")
    if hydrator.skipped_files:
        cli.warning(
            f"Skipped: {len(hydrator.skipped_files)} existing files (use --force to overwrite)"
        )
