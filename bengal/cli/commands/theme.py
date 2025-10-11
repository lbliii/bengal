"""Theme-related CLI commands (swizzle)."""

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.swizzle import SwizzleManager


@click.group()
def theme() -> None:
    """Theme utilities (swizzle)."""
    pass


@theme.command()
@click.argument('template_path')
@click.argument('source', type=click.Path(exists=True), default='.')
def swizzle(template_path: str, source: str) -> None:
    """Copy a theme template/partial to project templates/ and track provenance."""
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    dest = mgr.swizzle(template_path)
    click.echo(click.style(f"✓ Swizzled to {dest}", fg='green'))


@theme.command('swizzle-list')
@click.argument('source', type=click.Path(exists=True), default='.')
def swizzle_list(source: str) -> None:
    """List swizzled templates."""
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    records = mgr.list()
    if not records:
        click.echo("No swizzled templates.")
        return
    for r in records:
        click.echo(f"- {r.target} (from {r.theme})")


@theme.command('swizzle-update')
@click.argument('source', type=click.Path(exists=True), default='.')
def swizzle_update(source: str) -> None:
    """Update swizzled templates if unchanged locally."""
    site = Site.from_config(Path(source).resolve())
    mgr = SwizzleManager(site)
    summary = mgr.update()
    click.echo(click.style(
        f"Updated: {summary['updated']}, Skipped (changed): {summary['skipped_changed']}, Missing upstream: {summary['missing_upstream']}",
        fg='cyan'))


