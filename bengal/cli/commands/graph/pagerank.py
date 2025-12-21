"""PageRank analysis command for identifying important pages."""

from __future__ import annotations

import json

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
    description="Analyze page importance using PageRank algorithm",
    examples=[
        "bengal graph pagerank",
        "bengal graph pagerank --top-n 50",
        "bengal graph pagerank --format json",
    ],
    requires_site=True,
    tags=["analysis", "graph", "ranking"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--top-n", "-n", default=20, type=int, help="Number of top pages to show (default: 20)"
)
@click.option(
    "--damping", "-d", default=0.85, type=float, help="PageRank damping factor (default: 0.85)"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv", "summary"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def pagerank(top_n: int, damping: float, format: str, config: str, source: str) -> None:
    """
    🏆 Analyze page importance using PageRank algorithm.

    Computes PageRank scores for all pages based on their link structure.
    Pages that are linked to by many important pages receive high scores.

    Use PageRank to:
    - Identify your most important content
    - Prioritize content updates
    - Guide navigation and sitemap design
    - Find underlinked valuable content

    Examples:
        # Show top 20 most important pages
        bengal pagerank

        # Show top 50 pages
        bengal pagerank --top-n 50

        # Export scores as JSON
        bengal pagerank --format json > pagerank.json
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    cli = get_cli_output()
    configure_logging(level=LogLevel.WARNING)

    # Validate damping factor
    if not 0 < damping < 1:
        cli.error(f"Damping factor must be between 0 and 1, got {damping}")
        raise click.Abort()

    # Load site using helper
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    # Discover content and compute PageRank with status indicator
    if cli.use_rich:
        with cli.console.status("[info]Discovering site content...", spinner="dots") as status:
            from bengal.orchestration.content import ContentOrchestrator

            content_orch = ContentOrchestrator(site)
            content_orch.discover()

            status.update(f"[info]Building knowledge graph from {len(site.pages)} pages...")
            graph_obj = KnowledgeGraph(site)
            graph_obj.build()

            status.update(f"[info]Computing PageRank (damping={damping})...")
            results = graph_obj.compute_pagerank(damping=damping)
    else:
        cli.info("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator

        content_orch = ContentOrchestrator(site)
        content_orch.discover()

        cli.info(f"📊 Building knowledge graph from {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()

        cli.info(f"🏆 Computing PageRank (damping={damping})...")
        results = graph_obj.compute_pagerank(damping=damping)

    # Get top pages
    top_pages = results.get_top_pages(top_n)

    # Output based on format
    if format == "csv":
        # Export as CSV
        import csv
        import sys

        writer = csv.writer(sys.stdout)
        writer.writerow(
            ["Rank", "Title", "URL", "PageRank Score", "Incoming Links", "Outgoing Links"]
        )

        for i, (page, score) in enumerate(top_pages, 1):
            incoming = graph_obj.incoming_refs.get(page, 0)
            outgoing = len(graph_obj.outgoing_refs.get(page, set()))
            url = getattr(page, "url_path", str(page.source_path))
            writer.writerow([i, page.title, url, f"{score:.8f}", incoming, outgoing])

    elif format == "json":
        # Export as JSON
        data = {
            "total_pages": len(results.scores),
            "iterations": results.iterations,
            "converged": results.converged,
            "damping_factor": results.damping_factor,
            "top_pages": [
                {
                    "rank": i + 1,
                    "title": page.title,
                    "url": getattr(page, "href", str(page.source_path)),
                    "score": score,
                    "incoming_refs": graph_obj.incoming_refs.get(page, 0),
                    "outgoing_refs": len(graph_obj.outgoing_refs.get(page, set())),
                }
                for i, (page, score) in enumerate(top_pages)
            ],
        }
        cli.info(json.dumps(data, indent=2))

    elif format == "summary":
        # Show summary stats
        cli.blank()
        cli.info("=" * 60)
        cli.header("📈 PageRank Summary")
        cli.info("=" * 60)
        cli.info(f"Total pages analyzed:    {len(results.scores)}")
        cli.info(f"Iterations to converge:  {results.iterations}")
        cli.info(f"Converged:               {'✅ Yes' if results.converged else '⚠️  No'}")
        cli.info(f"Damping factor:          {results.damping_factor}")
        cli.blank()
        cli.info(f"Top {min(top_n, len(top_pages))} pages by importance:")
        cli.info("-" * 60)

        for i, (page, score) in enumerate(top_pages, 1):
            incoming = graph_obj.incoming_refs.get(page, 0)
            outgoing = len(graph_obj.outgoing_refs.get(page, set()))
            cli.info(f"{i:3d}. {page.title:<40} Score: {score:.6f}")
            cli.info(f"     {incoming} incoming, {outgoing} outgoing links")

    else:  # table format
        cli.blank()
        cli.info("=" * 100)
        cli.header(f"🏆 Top {min(top_n, len(top_pages))} Pages by PageRank")
        cli.info("=" * 100)
        cli.info(
            f"Analyzed {len(results.scores)} pages • Converged in {results.iterations} iterations • Damping: {damping}"
        )
        cli.info("=" * 100)
        cli.info(f"{'Rank':<6} {'Title':<45} {'Score':<12} {'In':<5} {'Out':<5}")
        cli.info("-" * 100)

        for i, (page, score) in enumerate(top_pages, 1):
            incoming = graph_obj.incoming_refs.get(page, 0)
            outgoing = len(graph_obj.outgoing_refs.get(page, set()))

            # Truncate title if too long
            title = page.title
            if len(title) > 43:
                title = title[:40] + "..."

            cli.info(f"{i:<6} {title:<45} {score:.8f}  {incoming:<5} {outgoing:<5}")

        cli.info("=" * 100)
        cli.blank()
        cli.tip("Use --format json to export scores for further analysis")
        cli.tip("Use --top-n to show more/fewer pages")
        cli.blank()

    # Show insights
    if format != "json" and results.converged:
        cli.subheader("Insights", icon="📊")

        # Calculate some basic stats
        scores_list = sorted(results.scores.values(), reverse=True)
        top_10_pct = results.get_pages_above_percentile(90)
        avg_score = sum(scores_list) / len(scores_list) if scores_list else 0
        max_score = max(scores_list) if scores_list else 0

        cli.info(f"• Average PageRank score:     {avg_score:.6f}")
        cli.info(f"• Maximum PageRank score:     {max_score:.6f}")
        cli.info(
            f"• Top 10% threshold:          {len(top_10_pct)} pages (score ≥ {scores_list[int(len(scores_list) * 0.1)]:.6f})"
        )
        cli.info(
            f"• Score concentration:        {'High' if max_score > avg_score * 10 else 'Moderate' if max_score > avg_score * 5 else 'Low'}"
        )
        cli.blank()

    close_all_loggers()


# Compatibility export expected by tests
pagerank_command = pagerank
