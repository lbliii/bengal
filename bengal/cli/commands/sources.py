"""
CLI commands for managing content sources.

Commands:
    bengal sources list     - List configured content sources
    bengal sources fetch    - Fetch/refresh content from sources
    bengal sources status   - Show cache status
    bengal sources clear    - Clear cached content
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bengal.cli.base import pass_site_context
from bengal.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.group("sources")
def sources_group() -> None:
    """
    Manage content sources (Content Layer).

    Content sources can be local directories or remote sources like
    GitHub repositories, Notion databases, or REST APIs.

    Use 'bengal sources list' to see configured sources.
    """
    pass


@sources_group.command("list")
@click.pass_context
def list_sources(ctx: click.Context) -> None:
    """List all configured content sources."""
    from bengal.collections.loader import load_collections

    # Try to load collections
    site_root = ctx.obj.get("site_root", Path.cwd()) if ctx.obj else Path.cwd()
    collections = load_collections(site_root)

    if not collections:
        console.print("[yellow]No collections configured.[/yellow]")
        console.print("\nTo configure collections, create a collections.py file:")
        console.print("""
[dim]# collections.py
from bengal.collections import define_collection
from dataclasses import dataclass

@dataclass
class Doc:
    title: str

collections = {
    "docs": define_collection(schema=Doc, directory="content/docs"),
}[/dim]
""")
        return

    # Build table
    table = Table(title="Content Sources")
    table.add_column("Collection", style="cyan")
    table.add_column("Source Type", style="green")
    table.add_column("Location", style="dim")
    table.add_column("Schema", style="magenta")

    for name, config in collections.items():
        source_type = config.source_type
        if config.loader:
            location = config.loader.name
        elif config.directory:
            location = str(config.directory)
        else:
            location = "N/A"

        schema_name = config.schema.__name__

        table.add_row(name, source_type, location, schema_name)

    console.print(table)

    # Show install hints for remote sources
    remote_sources = [
        (name, config)
        for name, config in collections.items()
        if config.is_remote
    ]

    if remote_sources:
        console.print("\n[dim]Remote sources require extras:[/dim]")
        console.print("[dim]  pip install bengal[github]   # GitHub loader[/dim]")
        console.print("[dim]  pip install bengal[notion]   # Notion loader[/dim]")


@sources_group.command("status")
@click.pass_context
def cache_status(ctx: click.Context) -> None:
    """Show cache status for content sources."""
    from datetime import timedelta

    from bengal.collections.loader import load_collections
    from bengal.content_layer.manager import ContentLayerManager

    site_root = ctx.obj.get("site_root", Path.cwd()) if ctx.obj else Path.cwd()
    collections = load_collections(site_root)

    if not collections:
        console.print("[yellow]No collections configured.[/yellow]")
        return

    # Check for remote sources
    remote_collections = {
        name: config for name, config in collections.items() if config.is_remote
    }

    if not remote_collections:
        console.print("[dim]No remote content sources configured.[/dim]")
        console.print("Local sources don't use caching.")
        return

    # Initialize manager and check cache status
    cache_dir = site_root / ".bengal" / "content_cache"
    manager = ContentLayerManager(cache_dir=cache_dir)

    # Register sources
    for name, config in remote_collections.items():
        if config.loader:
            manager.register_custom_source(name, config.loader)

    # Get cache status
    status = manager.get_cache_status()

    # Build table
    table = Table(title="Content Cache Status")
    table.add_column("Source", style="cyan")
    table.add_column("Cached", style="green")
    table.add_column("Entries", justify="right")
    table.add_column("Age", style="dim")
    table.add_column("Status")

    for name, info in status.items():
        if info.get("cached"):
            cached = "✅ Yes"
            entries = str(info.get("entry_count", 0))
            age_seconds = info.get("age_seconds", 0)
            if age_seconds < 60:
                age = f"{int(age_seconds)}s"
            elif age_seconds < 3600:
                age = f"{int(age_seconds / 60)}m"
            else:
                age = f"{int(age_seconds / 3600)}h"

            if info.get("expired"):
                status_text = "[yellow]Expired[/yellow]"
            else:
                status_text = "[green]Valid[/green]"
        else:
            cached = "❌ No"
            entries = "-"
            age = "-"
            status_text = "[dim]Not cached[/dim]"

        table.add_row(name, cached, entries, age, status_text)

    console.print(table)
    console.print(f"\n[dim]Cache directory: {cache_dir}[/dim]")


@sources_group.command("fetch")
@click.option("--source", "-s", help="Specific source to fetch (default: all)")
@click.option("--force", "-f", is_flag=True, help="Force refresh (ignore cache)")
@click.pass_context
def fetch_sources(ctx: click.Context, source: str | None, force: bool) -> None:
    """Fetch content from remote sources."""
    from bengal.collections.loader import load_collections
    from bengal.content_layer.manager import ContentLayerManager

    site_root = ctx.obj.get("site_root", Path.cwd()) if ctx.obj else Path.cwd()
    collections = load_collections(site_root)

    if not collections:
        console.print("[yellow]No collections configured.[/yellow]")
        return

    # Filter to remote sources
    remote_collections = {
        name: config
        for name, config in collections.items()
        if config.is_remote and (source is None or name == source)
    }

    if not remote_collections:
        if source:
            console.print(f"[yellow]Source '{source}' not found or is not remote.[/yellow]")
        else:
            console.print("[dim]No remote content sources configured.[/dim]")
        return

    # Initialize manager
    cache_dir = site_root / ".bengal" / "content_cache"
    manager = ContentLayerManager(cache_dir=cache_dir)

    # Register sources
    for name, config in remote_collections.items():
        if config.loader:
            manager.register_custom_source(name, config.loader)

    # Fetch content
    console.print(f"[bold]Fetching from {len(remote_collections)} source(s)...[/bold]\n")

    try:
        entries = manager.fetch_all_sync(use_cache=not force)

        # Group by source
        by_source: dict[str, int] = {}
        for entry in entries:
            by_source[entry.source_name] = by_source.get(entry.source_name, 0) + 1

        # Report results
        console.print("[green]✅ Fetch complete![/green]\n")

        table = Table()
        table.add_column("Source", style="cyan")
        table.add_column("Entries", justify="right", style="green")

        for name, count in by_source.items():
            table.add_row(name, str(count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Fetch failed: {e}[/red]")
        raise click.Abort()


@sources_group.command("clear")
@click.option("--source", "-s", help="Specific source to clear (default: all)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def clear_cache(ctx: click.Context, source: str | None, yes: bool) -> None:
    """Clear cached content from remote sources."""
    from bengal.content_layer.manager import ContentLayerManager

    site_root = ctx.obj.get("site_root", Path.cwd()) if ctx.obj else Path.cwd()
    cache_dir = site_root / ".bengal" / "content_cache"

    if not cache_dir.exists():
        console.print("[dim]No cache to clear.[/dim]")
        return

    # Confirm
    if not yes:
        target = f"source '{source}'" if source else "all sources"
        if not click.confirm(f"Clear cache for {target}?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    # Clear cache
    manager = ContentLayerManager(cache_dir=cache_dir)
    deleted = manager.clear_cache(source)

    if deleted > 0:
        console.print(f"[green]✅ Cleared {deleted} cache file(s).[/green]")
    else:
        console.print("[dim]No cache files to clear.[/dim]")


# Register command group
def register_commands(cli: click.Group) -> None:
    """Register source commands with CLI."""
    cli.add_command(sources_group)

