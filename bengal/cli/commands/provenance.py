"""
Provenance CLI commands for debugging and analysis.

Usage:
    bengal provenance lineage content/about.md
    bengal provenance affected templates/base.html
    bengal provenance stats
    bengal provenance build --limit 100
"""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)


@click.group(name="provenance")
def provenance_cli() -> None:
    """Provenance-based incremental build analysis (experimental).

    Tools for debugging and analyzing the provenance-based incremental
    build system. Shows what inputs affect each page and enables
    fine-grained cache analysis.
    """


@provenance_cli.command(cls=BengalCommand)
@command_metadata(
    category="experimental",
    description="Show what inputs produced a page (provenance lineage)",
    examples=[
        "bengal provenance lineage content/about.md",
        "bengal provenance lineage content/docs/getting-started.md",
    ],
)
@click.argument("page_path")
@click.option("--source", type=click.Path(exists=True), default=".")
@handle_cli_errors()
def lineage(page_path: str, source: str) -> None:
    """Show what inputs produced a page.

    Displays the complete provenance chain: content, templates,
    data files, config, and any other inputs that affected the
    page's output.
    """
    cli = get_cli_output()
    site = load_site_from_cli(source)

    from bengal.build.contracts.keys import content_key
    from bengal.build.provenance import ProvenanceCache as ProvenanceStore

    cache_dir = site.root_path / ".bengal" / "provenance"
    store = ProvenanceStore(cache_dir)

    # Normalize path to canonical CacheKey (relative to site root)
    normalized_path = content_key(Path(page_path), site.root_path)
    record = store.get(normalized_path)

    if record is None:
        cli.error(f"No provenance found for {page_path}")
        cli.info(f"  (Normalized key: {normalized_path})")
        cli.info("Run 'bengal provenance build' first to capture provenance.")
        raise click.Abort()

    cli.info(f"Provenance for {page_path}")
    cli.blank()

    cli.info(f"Combined hash: {record.provenance.combined_hash}")
    cli.info(f"Output hash: {record.output_hash}")
    cli.info(f"Created: {record.created_at}")
    cli.blank()

    cli.info(f"Inputs ({record.provenance.input_count}):")

    # Group by type
    from bengal.build.provenance.types import InputRecord

    by_type: dict[str, list[InputRecord]] = {}
    for inp in record.provenance.inputs:
        if inp.input_type not in by_type:
            by_type[inp.input_type] = []
        by_type[inp.input_type].append(inp)

    for input_type in sorted(by_type.keys()):
        inputs = by_type[input_type]
        cli.info(f"\n  [{input_type}] ({len(inputs)})")
        for inp in sorted(inputs, key=lambda x: x.path):
            cli.info(f"    {inp.path} = {inp.hash}")


@provenance_cli.command(cls=BengalCommand)
@command_metadata(
    category="experimental",
    description="Show what pages depend on a file (subvenance query)",
    examples=[
        "bengal provenance affected templates/base.html",
        "bengal provenance affected data/team.yaml",
        "bengal provenance affected --by-hash 0c01589269330704",
    ],
)
@click.argument("file_path", required=False)
@click.option("--by-hash", help="Query by content hash directly")
@click.option("--by-path", help="Search subvenance index for path substring")
@click.option("--source", type=click.Path(exists=True), default=".")
@handle_cli_errors()
def affected(file_path: str | None, by_hash: str | None, by_path: str | None, source: str) -> None:
    """Show what pages depend on a file.

    This is the SUBVENANCE query - the inverse of lineage.
    Shows which pages would need rebuilding if the specified
    file changed.

    Can query by file path, content hash, or path pattern.
    """
    import json

    cli = get_cli_output()
    site = load_site_from_cli(source)

    from bengal.build.provenance import ProvenanceCache as ProvenanceStore
    from bengal.build.provenance.types import ContentHash, hash_file

    cache_dir = site.root_path / ".bengal" / "provenance"
    store = ProvenanceStore(cache_dir)

    # Query by hash directly
    if by_hash:
        affected_pages = store.get_affected_by(ContentHash(by_hash))
        cli.info(f"Pages affected by hash {by_hash}")
        cli.blank()

        if not affected_pages:
            cli.warning("No pages found with this hash.")
        else:
            cli.success(f"Affected pages ({len(affected_pages)}):")
            for page in sorted(affected_pages):
                cli.info(f"  {page}")
        return

    # Query by path pattern (search stored inputs)
    if by_path:
        # Search through all records for inputs matching the path pattern
        matching_pages: set[str] = set()
        subvenance_path = cache_dir / "subvenance.json"

        if not subvenance_path.exists():
            cli.warning("No subvenance index found. Run 'bengal provenance build' first.")
            return

        # Load records and search inputs
        for record_file in (cache_dir / "records").glob("*.json"):
            try:
                data = json.loads(record_file.read_text())
                for inp in data.get("inputs", []):
                    if by_path.lower() in inp.get("path", "").lower():
                        matching_pages.add(data["page_path"])
            except (json.JSONDecodeError, KeyError):
                continue

        cli.info(f"Pages with inputs matching '{by_path}'")
        cli.blank()

        if not matching_pages:
            cli.warning("No pages found with inputs matching this path.")
        else:
            cli.success(f"Affected pages ({len(matching_pages)}):")
            for page in sorted(matching_pages):
                cli.info(f"  {page}")
        return

    # Query by file path
    if not file_path:
        cli.error("Provide a file path, --by-hash, or --by-path")
        raise click.Abort()

    full_path = site.root_path / file_path
    if not full_path.exists():
        cli.error(f"File not found: {file_path}")
        raise click.Abort()

    current_hash = hash_file(full_path)

    # Query subvenance
    affected_pages = store.get_affected_by(current_hash)

    cli.info(f"Pages affected by {file_path}")
    cli.info(f"Current hash: {current_hash}")
    cli.blank()

    if not affected_pages:
        cli.warning("No pages found that depend on this file.")
        cli.info("This could mean:")
        cli.info("  - No provenance has been captured yet (run 'bengal provenance build')")
        cli.info("  - The file was recently changed (hash doesn't match stored provenance)")
        cli.info("  - No pages actually use this file")
        cli.blank()
        cli.info("Try: bengal provenance affected --by-path <partial_path>")
    else:
        cli.success(f"Affected pages ({len(affected_pages)}):")
        for page in sorted(affected_pages):
            cli.info(f"  {page}")


@provenance_cli.command(cls=BengalCommand)
@command_metadata(
    category="experimental",
    description="Show provenance store statistics",
    examples=["bengal provenance stats"],
)
@click.option("--source", type=click.Path(exists=True), default=".")
@handle_cli_errors()
def stats(source: str) -> None:
    """Show provenance store statistics.

    Displays information about the provenance cache including
    number of pages tracked, total inputs, and storage size.
    """
    cli = get_cli_output()
    site = load_site_from_cli(source)

    from bengal.build.provenance import ProvenanceCache as ProvenanceStore

    cache_dir = site.root_path / ".bengal" / "provenance"

    if not cache_dir.exists():
        cli.warning("No provenance cache found.")
        cli.info("Run 'bengal provenance build' to capture provenance.")
        return

    store = ProvenanceStore(cache_dir)
    store_stats = store.stats()

    cli.info("Provenance Store Statistics")
    cli.blank()

    cli.info(f"Pages tracked:        {store_stats['pages_tracked']}")
    cli.info(f"Records cached:       {store_stats['records_cached']}")
    cli.info(f"Subvenance entries:   {store_stats['subvenance_entries']}")
    cli.info(f"Total input refs:     {store_stats['total_input_references']}")

    # Calculate storage size
    total_size = 0
    for f in cache_dir.rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size

    cli.blank()
    cli.info(f"Storage size:         {total_size / 1024:.1f} KB")
    cli.info(f"Cache directory:      {cache_dir}")


@provenance_cli.command(cls=BengalCommand, name="build")
@command_metadata(
    category="experimental",
    description="Run an incremental build (provenance filtering)",
    examples=[
        "bengal provenance build",
        "bengal provenance build --limit 100",
    ],
)
@click.option("--limit", type=int, help="Limit number of pages to process")
@click.option("--source", type=click.Path(exists=True), default=".")
@handle_cli_errors()
def build(limit: int | None, source: str) -> None:
    """Run an incremental build with provenance filtering.

    This is equivalent to `bengal build --incremental` but shows
    detailed provenance statistics. Use --limit to process only
    a subset of pages for testing.
    """
    cli = get_cli_output()
    site = load_site_from_cli(source)

    # Discover content
    from bengal.orchestration.content import ContentOrchestrator

    content = ContentOrchestrator(site)
    content.discover()

    pages = list(site.pages)
    if limit:
        pages = pages[:limit]

    cli.info(f"Processing {len(pages)} pages with provenance filtering...")
    cli.blank()

    # Use the provenance filter to check cache status
    from bengal.build.provenance import ProvenanceCache, ProvenanceFilter

    cache = ProvenanceCache(site.root_path / ".bengal" / "provenance")
    filter = ProvenanceFilter(site, cache)

    import time

    start = time.time()
    result = filter.filter(pages, list(site.assets), incremental=True)
    elapsed_ms = (time.time() - start) * 1000

    cli.info("Provenance Filter Results")
    cli.blank()
    cli.info(f"Pages analyzed:       {result.total_pages}")
    cli.info(f"Cache hits:           {result.cache_hits} ({result.hit_rate:.1f}%)")
    cli.info(f"Cache misses:         {result.cache_misses}")
    cli.info(f"Pages to build:       {len(result.pages_to_build)}")
    cli.info(f"Assets to process:    {len(result.assets_to_process)}")
    cli.blank()
    cli.info(f"Filter time:          {elapsed_ms:.1f}ms")

    if result.pages_to_build:
        cli.blank()
        cli.info("Pages requiring rebuild:")
        for page in result.pages_to_build[:10]:
            cli.info(f"  - {page.source_path}")
        if len(result.pages_to_build) > 10:
            cli.info(f"  ... and {len(result.pages_to_build) - 10} more")


@provenance_cli.command(cls=BengalCommand)
@command_metadata(
    category="experimental",
    description="Clear provenance cache",
    examples=["bengal provenance clear"],
)
@click.option("--source", type=click.Path(exists=True), default=".")
@click.option("--force", is_flag=True, help="Skip confirmation")
@handle_cli_errors()
def clear(source: str, force: bool) -> None:
    """Clear the provenance cache.

    Removes all stored provenance data. Use this when you want
    to start fresh or if the cache becomes corrupted.
    """
    import shutil

    cli = get_cli_output()
    site = load_site_from_cli(source)

    cache_dir = site.root_path / ".bengal" / "provenance"

    if not cache_dir.exists():
        cli.info("No provenance cache to clear.")
        return

    if not force and not click.confirm(f"Delete {cache_dir}?"):
        cli.info("Cancelled.")
        return

    shutil.rmtree(cache_dir)
    cli.success("Provenance cache cleared.")
