"""Assets CLI for Bengal."""

from __future__ import annotations

import time

import click

from bengal.assets.manifest import AssetManifest
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
def assets() -> None:
    """Manage and build assets."""
    pass


@assets.command()
@command_metadata(
    category="assets",
    description="Build assets using the configured pipeline",
    examples=[
        "bengal assets build",
        "bengal assets build --watch",
    ],
    requires_site=True,
    tags=["assets", "build", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option("--watch", is_flag=True, help="Watch assets and rebuild on changes")
@click.argument("source", type=click.Path(exists=True), default=".")
def build(watch: bool, source: str) -> None:
    """
    Build assets using the configured pipeline.

    Processes CSS, JavaScript, and other assets according to your
    asset pipeline configuration. Use --watch to automatically rebuild
    on file changes.

    Examples:
        bengal assets build           # Build once
        bengal assets build --watch   # Watch and rebuild on changes

    See also:
        bengal assets status - View asset manifest
        bengal site build - Build site with assets
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)

    def run_once() -> None:
        try:
            import time

            from bengal.assets.pipeline import from_site as pipeline_from_site

            start_time = time.time()
            pipeline = pipeline_from_site(site)
            outputs = pipeline.build()
            elapsed_ms = (time.time() - start_time) * 1000

            # Show phase completion
            cli.phase("Assets", duration_ms=elapsed_ms, details=f"{len(outputs)} outputs")
        except Exception as e:
            cli.error(f"✗ Asset pipeline failed: {e}")

    if not watch:
        run_once()
        return

    cli.info("Watching assets... Press Ctrl+C to stop.")
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
        cli.blank()
        cli.warning("Stopped asset watcher.")


@assets.command()
@command_metadata(
    category="assets",
    description="Display the current asset manifest",
    examples=[
        "bengal assets status",
    ],
    requires_site=True,
    tags=["assets", "info", "quick"],
)
@handle_cli_errors(show_art=False)
@click.argument("source", type=click.Path(exists=True), default=".")
def status(source: str) -> None:
    """
    📋 Display the current asset manifest.

    Shows the mapping of logical asset paths to fingerprinted output files.
    Useful for debugging asset references and cache-busting.

    Examples:
        bengal assets status

    See also:
        bengal assets build - Build assets
        bengal site build - Build site with assets
    """
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    manifest_path = site.output_dir / "asset-manifest.json"
    manifest = AssetManifest.load(manifest_path)

    if manifest is None or not manifest.entries:
        cli.warning("No asset manifest found.")
        cli.info("Run 'bengal site build --clean-output' to regenerate all assets.")
        return

    cli.header("Asset Manifest")
    for logical_path in sorted(manifest.entries.keys()):
        entry = manifest.entries[logical_path]
        destination = f"/{entry.output_path}"
        if entry.fingerprint:
            cli.info(f"{logical_path} → {destination} (fingerprint: {entry.fingerprint})")
        else:
            cli.info(f"{logical_path} → {destination}")


# Compatibility export expected by tests
assets_command = assets
