"""Assets CLI for Bengal."""

import time
from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
def assets() -> None:
    """Manage and build assets."""
    pass


@assets.command()
@click.option("--watch", is_flag=True, help="Watch assets and rebuild on changes")
@click.argument("source", type=click.Path(exists=True), default=".")
def build(watch: bool, source: str) -> None:
    """Build assets using the configured pipeline (if enabled)."""
    root = Path(source).resolve()
    site = Site.from_config(root)

    def run_once() -> None:
        try:
            from bengal.assets.pipeline import from_site as pipeline_from_site

            pipeline = pipeline_from_site(site)
            outputs = pipeline.build()
            click.echo(click.style(f"✓ Assets built ({len(outputs)} outputs)", fg="green"))
        except Exception as e:
            click.echo(click.style(f"✗ Asset pipeline failed: {e}", fg="red"))

    if not watch:
        run_once()
        return

    click.echo(click.style("Watching assets... Press Ctrl+C to stop.", fg="cyan"))
    try:
        last_run = 0.0
        while True:
            # naive: re-run every 2s; a proper watcher can be added later
            now = time.time()
            if now - last_run >= 2.0:
                run_once()
                last_run = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("Stopped asset watcher.", fg="yellow"))
