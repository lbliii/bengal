"""Bridge pages and navigation bottleneck analysis command."""

from __future__ import annotations

import json
from typing import Any

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import (
    command_metadata,
    handle_cli_errors,
)
from bengal.utils.observability.logger import close_all_loggers

from .common import load_graph, page_incoming, page_outgoing


@click.command(cls=BengalCommand)
@command_metadata(
    category="analysis",
    description="Identify bridge pages and navigation bottlenecks",
    examples=[
        "bengal graph bridges",
        "bengal graph bridges --metric closeness",
        "bengal graph bridges --format json",
    ],
    requires_site=True,
    tags=["analysis", "graph", "navigation"],
)
@handle_cli_errors(show_art=False)
@click.option("--top-n", "-n", default=20, type=int, help="Number of pages to show (default: 20)")
@click.option(
    "--metric",
    "-m",
    type=click.Choice(["betweenness", "closeness", "both"]),
    default="both",
    help="Centrality metric to display (default: both)",
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
def bridges(top_n: int, metric: str, format: str, config: str, source: str) -> None:
    """
    🌉 Identify bridge pages and navigation bottlenecks.

    Analyzes navigation paths to find:
    - Bridge pages (high betweenness): Pages that connect different parts of the site
    - Accessible pages (high closeness): Pages easy to reach from anywhere
    - Navigation bottlenecks: Critical pages for site navigation

    Use path analysis to:
    - Optimize navigation structure
    - Identify critical pages
    - Improve content discoverability
    - Find navigation gaps

    Examples:
        # Show top 20 bridge pages
        bengal bridges

        # Show most accessible pages
        bengal bridges --metric closeness

        # Show only betweenness centrality
        bengal bridges --metric betweenness

        # Export as JSON
        bengal bridges --format json > bridges.json

    """
    cli, _site, graph_obj = load_graph(source, config)

    # Analyze paths
    cli.info("🌉 Analyzing navigation paths...")
    results = graph_obj.analyze_paths()

    # Output based on format
    if format == "csv":
        # Export as CSV
        import csv
        import sys

        writer = csv.writer(sys.stdout)
        if metric in ["betweenness", "both"]:
            writer.writerow(["Rank", "Title", "URL", "Betweenness", "Incoming", "Outgoing"])
            bridges_list = results.get_top_bridges(top_n)
            for i, (page, score) in enumerate(bridges_list, 1):
                incoming = page_incoming(graph_obj, page)
                outgoing = page_outgoing(graph_obj, page)
                url = getattr(page, "url_path", str(page.source_path))
                writer.writerow([i, page.title, url, f"{score:.10f}", incoming, outgoing])

        if metric in ["closeness", "both"]:
            if metric == "both":
                writer.writerow([])  # Empty row separator
            writer.writerow(["Rank", "Title", "URL", "Closeness", "Outgoing"])
            accessible = results.get_most_accessible(top_n)
            for i, (page, score) in enumerate(accessible, 1):
                outgoing = page_outgoing(graph_obj, page)
                url = getattr(page, "url_path", str(page.source_path))
                writer.writerow([i, page.title, url, f"{score:.10f}", outgoing])

    elif format == "json":
        # Export as JSON
        data: dict[str, Any] = {
            "avg_path_length": results.avg_path_length,
            "diameter": results.diameter,
            "total_pages": len(results.betweenness_centrality),
        }

        if metric in ["betweenness", "both"]:
            bridges_list = results.get_top_bridges(top_n)
            data["top_bridges"] = [
                {
                    "title": page.title,
                    "url": getattr(page, "href", str(page.source_path)),
                    "betweenness": score,
                    "incoming_refs": page_incoming(graph_obj, page),
                }
                for page, score in bridges_list
            ]

        if metric in ["closeness", "both"]:
            accessible = results.get_most_accessible(top_n)
            data["most_accessible"] = [
                {
                    "title": page.title,
                    "url": getattr(page, "href", str(page.source_path)),
                    "closeness": score,
                    "outgoing_refs": page_outgoing(graph_obj, page),
                }
                for page, score in accessible
            ]

        cli.info(json.dumps(data, indent=2))

    elif format == "summary":
        # Show summary stats
        cli.info("\n" + "=" * 60)
        cli.info("🌉 Path Analysis Summary")
        cli.info("=" * 60)
        cli.info(f"Total pages analyzed:     {len(results.betweenness_centrality)}")
        cli.info(f"Average path length:      {results.avg_path_length:.2f}")
        cli.info(f"Network diameter:         {results.diameter}")
        cli.info("")

        if metric in ["betweenness", "both"]:
            cli.info("\n🔗 Top Bridge Pages (Betweenness Centrality)")
            cli.info("-" * 60)
            bridges_list = results.get_top_bridges(top_n)
            for i, (page, score) in enumerate(bridges_list, 1):
                incoming = page_incoming(graph_obj, page)
                outgoing = page_outgoing(graph_obj, page)
                cli.info(f"{i:3d}. {page.title}")
                cli.info(f"     Betweenness: {score:.6f} | {incoming} in, {outgoing} out")

        if metric in ["closeness", "both"]:
            cli.info("\n🎯 Most Accessible Pages (Closeness Centrality)")
            cli.info("-" * 60)
            accessible = results.get_most_accessible(top_n)
            for i, (page, score) in enumerate(accessible, 1):
                outgoing = page_outgoing(graph_obj, page)
                cli.info(f"{i:3d}. {page.title}")
                cli.info(f"     Closeness: {score:.6f} | Can reach {outgoing} pages")

    else:  # table format
        cli.info("\n" + "=" * 100)
        cli.info("🌉 Navigation Path Analysis")
        cli.info("=" * 100)
        cli.info(
            f"Analyzed {len(results.betweenness_centrality)} pages • Avg path: {results.avg_path_length:.2f} • Diameter: {results.diameter}"
        )
        cli.info("=" * 100)

        if metric in ["betweenness", "both"]:
            cli.info(f"\n🔗 Top {top_n} Bridge Pages (Betweenness Centrality)")
            cli.info("-" * 100)
            cli.info(f"{'Rank':<6} {'Title':<50} {'Betweenness':<14} {'In':<5} {'Out':<5}")
            cli.info("-" * 100)

            bridges_list = results.get_top_bridges(top_n)
            for i, (page, score) in enumerate(bridges_list, 1):
                title = page.title
                if len(title) > 48:
                    title = title[:45] + "..."

                incoming = page_incoming(graph_obj, page)
                outgoing = page_outgoing(graph_obj, page)

                cli.info(f"{i:<6} {title:<50} {score:.10f}  {incoming:<5} {outgoing:<5}")

        if metric in ["closeness", "both"]:
            cli.info(f"\n🎯 Top {top_n} Most Accessible Pages (Closeness Centrality)")
            cli.info("-" * 100)
            cli.info(f"{'Rank':<6} {'Title':<50} {'Closeness':<14} {'Out':<5}")
            cli.info("-" * 100)

            accessible = results.get_most_accessible(top_n)
            for i, (page, score) in enumerate(accessible, 1):
                title = page.title
                if len(title) > 48:
                    title = title[:45] + "..."

                outgoing = page_outgoing(graph_obj, page)

                cli.info(f"{i:<6} {title:<50} {score:.10f}  {outgoing:<5}")

        cli.info("=" * 100)
        cli.tip("Use --metric to focus on betweenness or closeness")
        cli.tip("Use --format json to export for analysis")
        cli.blank()

    # Show insights
    if format != "json":
        cli.info("\n" + "=" * 60)
        cli.info("📊 Insights")
        cli.info("=" * 60)

        avg_betweenness = (
            sum(results.betweenness_centrality.values()) / len(results.betweenness_centrality)
            if results.betweenness_centrality
            else 0
        )
        max_betweenness = (
            max(results.betweenness_centrality.values()) if results.betweenness_centrality else 0
        )

        cli.info(f"• Average path length:        {results.avg_path_length:.2f} hops")
        cli.info(f"• Network diameter:           {results.diameter} hops")
        cli.info(f"• Average betweenness:        {avg_betweenness:.6f}")
        cli.info(f"• Max betweenness:            {max_betweenness:.6f}")

        if results.diameter > 5:
            cli.info("• Structure:                  Deep (consider shortening paths)")
        elif results.diameter > 3:
            cli.info("• Structure:                  Medium depth")
        else:
            cli.info("• Structure:                  Shallow (well connected)")

        cli.info("\n")

    close_all_loggers()
