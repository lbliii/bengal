"""Community detection command for discovering topical clusters."""

from __future__ import annotations

import json
from typing import Any

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.utils.logger import LogLevel, close_all_loggers, configure_logging


@click.command(cls=BengalCommand)
@command_metadata(
    category="analysis",
    description="Discover topical communities in your content",
    examples=[
        "bengal graph communities",
        "bengal graph communities --min-size 10",
        "bengal graph communities --format json",
    ],
    requires_site=True,
    tags=["analysis", "graph", "clustering"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--min-size", "-m", default=2, type=int, help="Minimum community size to show (default: 2)"
)
@click.option(
    "--resolution",
    "-r",
    default=1.0,
    type=float,
    help="Resolution parameter (higher = more communities, default: 1.0)",
)
@click.option(
    "--top-n", "-n", default=10, type=int, help="Number of communities to show (default: 10)"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "summary"]),
    default="table",
    help="Output format (default: table)",
)
@click.option("--seed", type=int, help="Random seed for reproducibility")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def communities(
    min_size: int, resolution: float, top_n: int, format: str, seed: int, config: str, source: str
) -> None:
    """
    Discover topical communities in your content.

    Uses the Louvain algorithm to find natural clusters of related pages.
    Communities represent topic areas or content groups based on link structure.

    Use community detection to:
    - Discover hidden content structure
    - Organize content into logical groups
    - Identify topic clusters
    - Guide taxonomy creation

    Examples:
        # Show top 10 communities
        bengal communities

        # Show only large communities (10+ pages)
        bengal communities --min-size 10

        # Find more granular communities
        bengal communities --resolution 2.0

        # Export as JSON
        bengal communities --format json > communities.json
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    cli = get_cli_output()
    configure_logging(level=LogLevel.WARNING)

    # Load site using helper
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    # Discover content
    cli.info("🔍 Discovering site content...")
    from bengal.orchestration.content import ContentOrchestrator

    content_orch = ContentOrchestrator(site)
    content_orch.discover()

    # Build knowledge graph
    cli.info(f"📊 Building knowledge graph from {len(site.pages)} pages...")
    graph_obj = KnowledgeGraph(site)
    graph_obj.build()

    # Detect communities
    cli.info(f"🔍 Detecting communities (resolution={resolution})...")
    results = graph_obj.detect_communities(resolution=resolution, random_seed=seed)

    # Filter by minimum size
    communities_to_show = results.get_communities_above_size(min_size)

    # Sort by size
    communities_to_show.sort(key=lambda c: c.size, reverse=True)

    # Limit to top N
    communities_to_show = communities_to_show[:top_n]

    # Output based on format
    if format == "csv":
        # Export as CSV
        import csv
        import sys

        writer = csv.writer(sys.stdout)
        writer.writerow(["Community ID", "Size", "Top Pages", "Incoming Refs"])

        for community in communities_to_show:
            pages_with_refs = [
                (page, graph_obj.incoming_refs.get(page, 0)) for page in community.pages
            ]
            pages_with_refs.sort(key=lambda x: x[1], reverse=True)
            top_pages = ", ".join(p.title for p, _ in pages_with_refs[:5])
            writer.writerow([community.id, community.size, top_pages, ""])

    elif format == "json":
        # Export as JSON
        data: dict[str, Any] = {
            "total_communities": len(results.communities),
            "modularity": results.modularity,
            "iterations": results.iterations,
            "resolution": resolution,
            "communities": [],
        }

        for community in communities_to_show:
            # Get top pages by incoming links
            pages_with_refs = [
                (page, graph_obj.incoming_refs.get(page, 0)) for page in community.pages
            ]
            pages_with_refs.sort(key=lambda x: x[1], reverse=True)

            data["communities"].append(
                {
                    "id": community.id,
                    "size": community.size,
                    "pages": [
                        {
                            "title": page.title,
                            "url": getattr(page, "href", str(page.source_path)),
                            "incoming_refs": refs,
                        }
                        for page, refs in pages_with_refs[:5]  # Top 5 pages
                    ],
                }
            )

        cli.info(json.dumps(data, indent=2))

    elif format == "summary":
        # Show summary stats
        cli.info("\n" + "=" * 60)
        cli.info("🔍 Community Detection Summary")
        cli.info("=" * 60)
        cli.info(f"Total communities found:  {len(results.communities)}")
        cli.info(f"Showing communities:      {len(communities_to_show)}")
        cli.info(f"Modularity score:         {results.modularity:.4f}")
        cli.info(f"Iterations:               {results.iterations}")
        cli.info(f"Resolution:               {resolution}")
        cli.info("")

        for i, community in enumerate(communities_to_show, 1):
            cli.info(f"\nCommunity {i} (ID: {community.id})")
            cli.info(f"  Size: {community.size} pages")

            # Show top pages
            pages_with_refs = [
                (page, graph_obj.incoming_refs.get(page, 0)) for page in community.pages
            ]
            pages_with_refs.sort(key=lambda x: x[1], reverse=True)

            cli.info("  Top pages:")
            for page, refs in pages_with_refs[:3]:
                cli.info(f"    • {page.title} ({refs} refs)")

    else:  # table format
        cli.info("\n" + "=" * 100)
        cli.info(f"🔍 Top {len(communities_to_show)} Communities")
        cli.info("=" * 100)
        cli.info(
            f"Found {len(results.communities)} communities • Modularity: {results.modularity:.4f} • Resolution: {resolution}"
        )
        cli.info("=" * 100)
        cli.info(f"{'ID':<5} {'Size':<6} {'Top Pages':<85}")
        cli.info("-" * 100)

        for community in communities_to_show:
            # Get top 3 pages by incoming links
            pages_with_refs = [
                (page, graph_obj.incoming_refs.get(page, 0)) for page in community.pages
            ]
            pages_with_refs.sort(key=lambda x: x[1], reverse=True)

            top_page_titles = ", ".join(
                [
                    page.title[:25] + "..." if len(page.title) > 25 else page.title
                    for page, _ in pages_with_refs[:3]
                ]
            )

            if len(top_page_titles) > 83:
                top_page_titles = top_page_titles[:80] + "..."

            cli.info(f"{community.id:<5} {community.size:<6} {top_page_titles:<85}")

        cli.info("=" * 100)
        cli.info("\n💡 Tip: Use --format json to export full data")
        cli.info("       Use --min-size to filter small communities")
        cli.info("       Use --resolution to control granularity\n")

    # Show insights
    if format != "json":
        cli.info("\n" + "=" * 60)
        cli.info("📊 Insights")
        cli.info("=" * 60)

        total_pages = sum(c.size for c in results.communities)
        avg_size = total_pages / len(results.communities) if results.communities else 0
        largest = max((c.size for c in results.communities), default=0)

        cli.info(f"• Average community size:     {avg_size:.1f} pages")
        cli.info(f"• Largest community:          {largest} pages")
        cli.info(f"• Communities >= {min_size} pages:      {len(communities_to_show)}")

        if results.modularity > 0.3:
            cli.info("• Modularity:                 High (good clustering)")
        elif results.modularity > 0.1:
            cli.info("• Modularity:                 Moderate (some structure)")
        else:
            cli.info("• Modularity:                 Low (weak structure)")

        cli.info("\n")

    close_all_loggers()


# Compatibility export expected by tests
communities_command = communities
