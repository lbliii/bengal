"""Orphan page listing command with connectivity level filtering."""

from __future__ import annotations

import json

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    handle_cli_errors,
)
from bengal.utils.observability.logger import close_all_loggers

from .common import load_graph


@click.command("orphans", cls=BengalCommand)
@command_metadata(
    category="analysis",
    description="List pages by connectivity level (isolated, lightly linked, etc.)",
    examples=[
        "bengal graph orphans",
        "bengal graph orphans --level isolated",
        "bengal graph orphans --level lightly",
        "bengal graph orphans --format paths",
        "bengal graph orphans --format json > orphans.json",
    ],
    requires_site=True,
    tags=["analysis", "graph", "seo"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--level",
    "-l",
    type=click.Choice(["isolated", "lightly", "adequately", "all"]),
    default="isolated",
    help="Connectivity level to show (default: isolated)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "paths"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=None,
    help="Limit number of results (default: all)",
)
@click.option(
    "--sort",
    type=click.Choice(["path", "title", "score"]),
    default="score",
    help="Sort order (default: score)",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to config file (default: bengal.toml)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def orphans(
    level: str,
    format: str,
    limit: int | None,
    sort: str,
    config: str,
    source: str,
) -> None:
    """
    List pages by connectivity level.

    Shows pages grouped by how well they're connected:
    - 🔴 isolated: No meaningful connections (score < 0.25)
    - 🟠 lightly: Only structural links (score 0.25-1.0)
    - 🟡 adequately: Some connections (score 1.0-2.0)
    - 🟢 well: Well connected (score >= 2.0)

    Use this command to:
    - Find truly isolated pages that need attention
    - Identify pages relying only on structural links
    - Prioritize internal linking improvements

    Examples:
        # List isolated pages (truly orphaned)
        bengal graph orphans

        # List lightly linked pages
        bengal graph orphans --level lightly

        # Show all levels for full picture
        bengal graph orphans --level all

        # Export as JSON
        bengal graph orphans --format json > orphans.json

    """
    cli, _site, graph_obj = load_graph(source, config, quiet=(format == "paths"))

    try:
        # Get connectivity report
        report = graph_obj.get_connectivity_report()

        # Select pages based on level
        if level == "isolated":
            pages_to_show = report.isolated
            level_label = "🔴 Isolated"
        elif level == "lightly":
            pages_to_show = report.lightly_linked
            level_label = "🟠 Lightly Linked"
        elif level == "adequately":
            pages_to_show = report.adequately_linked
            level_label = "🟡 Adequately Linked"
        else:  # all
            pages_to_show = report.isolated + report.lightly_linked
            level_label = "🔴 Isolated + 🟠 Lightly Linked"

        # Calculate scores for sorting
        page_scores = []
        for page in pages_to_show:
            metrics = graph_obj.get_page_link_metrics(page)
            score = metrics.connectivity_score()
            page_scores.append((page, score, metrics))

        # Sort
        if sort == "title":
            page_scores.sort(key=lambda x: getattr(x[0], "title", str(x[0].source_path)))
        elif sort == "path":
            page_scores.sort(key=lambda x: str(x[0].source_path))
        else:  # score
            page_scores.sort(key=lambda x: x[1])

        # Apply limit
        if limit:
            page_scores = page_scores[:limit]

        # Output based on format
        if format == "json":
            dist = report.get_distribution()
            data = {
                "level_filter": level,
                "distribution": dist,
                "total_pages": report.total_pages,
                "avg_score": round(report.avg_score, 2),
                "showing": len(page_scores),
                "pages": [
                    {
                        "path": str(p.source_path),
                        "title": getattr(p, "title", "Untitled"),
                        "score": round(score, 2),
                        "metrics": metrics.to_dict(),
                    }
                    for p, score, metrics in page_scores
                ],
            }
            click.echo(json.dumps(data, indent=2))

        elif format == "paths":
            # Just output paths, one per line (for scripting)
            for p, _score, _metrics in page_scores:
                click.echo(str(p.source_path))

        else:  # table format
            cli.blank()

            # Show distribution first
            dist = report.get_distribution()
            pct = report.get_percentages()
            cli.info("=" * 90)
            cli.header("📊 Connectivity Distribution")
            cli.info("=" * 90)
            cli.info(
                f"  🟢 Well-Connected (≥2.0):    {dist['well_connected']:>4} pages ({pct['well_connected']:.1f}%)"
            )
            cli.info(
                f"  🟡 Adequately Linked (1-2):  {dist['adequately_linked']:>4} pages ({pct['adequately_linked']:.1f}%)"
            )
            cli.info(
                f"  🟠 Lightly Linked (0.25-1):  {dist['lightly_linked']:>4} pages ({pct['lightly_linked']:.1f}%)"
            )
            cli.info(
                f"  🔴 Isolated (<0.25):         {dist['isolated']:>4} pages ({pct['isolated']:.1f}%)"
            )
            cli.info("=" * 90)
            cli.blank()

            if not page_scores:
                cli.success(f"✅ No {level} pages found!")
                cli.blank()
                return

            cli.info("=" * 90)
            cli.header(f"{level_label} Pages ({len(page_scores)} total)")
            cli.info("=" * 90)
            cli.info(f"{'#':<4} {'Score':<8} {'Path':<45} {'Title':<30}")
            cli.info("-" * 90)

            for i, (page, score, _metrics) in enumerate(page_scores, 1):
                path = str(page.source_path)
                if len(path) > 43:
                    path = "..." + path[-40:]

                title = getattr(page, "title", "Untitled")
                if len(title) > 28:
                    title = title[:25] + "..."

                cli.info(f"{i:<4} {score:<8.2f} {path:<45} {title:<30}")

            cli.info("=" * 90)

            if limit and len(pages_to_show) > limit:
                cli.info(f"Showing {limit} of {len(pages_to_show)} pages")

            cli.blank()
            cli.tip("Use --level lightly to see pages with only structural links")
            cli.tip("Use --level all to see both isolated and lightly linked pages")
            cli.tip("Use --format json for detailed metrics breakdown")
            cli.blank()

    finally:
        close_all_loggers()


# Compatibility export
orphans_command = orphans
