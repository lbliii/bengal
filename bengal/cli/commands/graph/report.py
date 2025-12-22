"""Unified site analysis report command."""

from __future__ import annotations

import json
import sys
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


@click.command("report", cls=BengalCommand)
@command_metadata(
    category="analysis",
    description="Generate comprehensive site analysis report",
    examples=[
        "bengal graph report",
        "bengal graph report --brief",
        "bengal graph report --ci --threshold-isolated 5",
        "bengal graph report --format json > report.json",
    ],
    requires_site=True,
    tags=["analysis", "graph", "seo", "ci"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--brief",
    is_flag=True,
    help="Compact output for CI pipelines and quick checks",
)
@click.option(
    "--ci",
    is_flag=True,
    help="CI mode: exit with code 1 if thresholds exceeded",
)
@click.option(
    "--threshold-isolated",
    type=int,
    default=5,
    help="Max isolated pages before CI failure (default: 5)",
)
@click.option(
    "--threshold-lightly",
    type=int,
    default=20,
    help="Max lightly-linked pages before CI warning (default: 20)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "json", "markdown"]),
    default="console",
    help="Output format (default: console)",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to config file (default: bengal.toml)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def report(
    brief: bool,
    ci: bool,
    threshold_isolated: int,
    threshold_lightly: int,
    format: str,
    config: str,
    source: str,
) -> None:
    """
    Generate comprehensive site analysis report.

    Combines multiple analyses into a single unified report:
    - Connectivity analysis (orphans, link density)
    - Link suggestions (top recommendations)
    - Bridge pages (navigation bottlenecks)
    - Communities (topic clusters)

    Use this command to get a complete picture of your site's structure
    and actionable recommendations for improvement.

    Examples:
        # Full analysis report
        bengal graph report

        # Quick summary for CI
        bengal graph report --brief

        # CI mode with thresholds
        bengal graph report --ci --threshold-isolated 5

        # Export as JSON
        bengal graph report --format json > report.json
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    cli = get_cli_output()
    configure_logging(level=LogLevel.WARNING)

    # Load site using helper
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    try:
        if not brief:
            cli.info("🔍 Discovering site content...")

        from bengal.orchestration.content import ContentOrchestrator

        content_orch = ContentOrchestrator(site)
        content_orch.discover()

        if not brief:
            cli.info(f"📊 Analyzing {len(site.pages)} pages...")

        graph_obj = KnowledgeGraph(site)
        graph_obj.build()

        # Gather analysis data
        metrics = graph_obj.get_metrics()
        connectivity_report = graph_obj.get_connectivity_report()

        # Get additional analysis data
        try:
            bridges = graph_obj.get_bridges()[:5]  # Top 5 bridges
        except Exception:
            bridges = []

        try:
            communities = graph_obj.get_communities()
            community_count = len(communities) if communities else 0
        except Exception:
            community_count = 0

        # Calculate connectivity stats
        total_pages = (
            getattr(metrics, "total_pages", 0)
            if hasattr(metrics, "total_pages")
            else metrics.get("nodes", len(site.pages))
        )
        total_links = (
            getattr(metrics, "total_links", 0)
            if hasattr(metrics, "total_links")
            else metrics.get("edges", 0)
        )
        avg_links = total_links / total_pages if total_pages > 0 else 0

        # Use connectivity report for nuanced analysis
        dist = connectivity_report.get_distribution()
        pct = connectivity_report.get_percentages()

        # Prepare report data
        report_data = {
            "total_pages": total_pages,
            "total_links": total_links,
            "avg_links_per_page": round(avg_links, 2),
            "avg_connectivity_score": round(connectivity_report.avg_score, 2),
            # Connectivity distribution
            "distribution": dist,
            "percentages": {k: round(v, 1) for k, v in pct.items()},
            # Orphan fields
            "orphan_count": dist["isolated"],
            "orphan_percentage": round(pct["isolated"], 1),
            "lightly_linked_count": dist["lightly_linked"],
            # Page lists
            "isolated_pages": [str(p.source_path) for p in connectivity_report.isolated[:20]],
            "lightly_linked_pages": [
                str(p.source_path) for p in connectivity_report.lightly_linked[:10]
            ],
            # Other analysis
            "bridge_count": len(bridges),
            "community_count": community_count,
            "bridges": [getattr(p, "title", str(p.source_path)) for p in bridges],
            "thresholds": {
                "isolated": threshold_isolated,
                "lightly_linked": threshold_lightly,
            },
        }

        # Output based on format
        if format == "json":
            click.echo(json.dumps(report_data, indent=2))

        elif format == "markdown":
            _output_markdown(cli, report_data, brief)

        else:  # console
            _output_console(cli, report_data, brief, ci, threshold_isolated, threshold_lightly)

        # CI exit code logic
        if ci:
            exit_code = 0
            isolated_count = dist["isolated"]
            if isolated_count > threshold_isolated:
                if format == "console":
                    cli.error(
                        f"❌ CI FAILED: {isolated_count} isolated pages exceeds threshold ({threshold_isolated})"
                    )
                exit_code = 1
            elif format == "console" and not brief:
                cli.success(
                    f"✅ CI PASSED: {isolated_count} isolated pages within threshold ({threshold_isolated})"
                )

            if exit_code != 0:
                sys.exit(exit_code)

    finally:
        close_all_loggers()


def _output_console(
    cli: Any,
    data: dict[str, Any],
    brief: bool,
    ci: bool,
    threshold_isolated: int,
    threshold_lightly: int,
) -> None:
    """Output report in console format."""
    dist = data.get("distribution", {})
    pct = data.get("percentages", {})

    if brief:
        # Compact output for CI
        score_quality = "good" if data.get("avg_connectivity_score", 0) >= 1.0 else "needs work"
        isolated_status = "⚠️" if dist.get("isolated", 0) > threshold_isolated else "✅"

        cli.info(f"📊 Site Analysis: {data['total_pages']} pages")
        cli.info(
            f"   Isolated: {dist.get('isolated', 0)} ({pct.get('isolated', 0):.1f}%) {isolated_status}"
        )
        cli.info(
            f"   Lightly linked: {dist.get('lightly_linked', 0)} ({pct.get('lightly_linked', 0):.1f}%)"
        )
        cli.info(f"   Avg score: {data.get('avg_connectivity_score', 0):.2f} ({score_quality})")
        if data.get("bridges"):
            cli.info(f"   Top bridges: {', '.join(data['bridges'][:3])}")

        if dist.get("isolated", 0) > threshold_isolated:
            cli.blank()
            cli.warning(
                f"⚠️ {dist['isolated']} isolated pages exceed threshold ({threshold_isolated})"
            )
    else:
        # Full report
        cli.blank()
        cli.info("=" * 80)
        cli.header("📊 Site Analysis Report")
        cli.info("=" * 80)
        cli.blank()

        # Overview section
        cli.header("📈 Overview")
        cli.info(f"   Total pages:        {data['total_pages']}")
        cli.info(f"   Total links:        {data['total_links']}")
        cli.info(f"   Avg links/page:     {data['avg_links_per_page']:.1f}")
        cli.info(f"   Avg conn. score:    {data.get('avg_connectivity_score', 0):.2f}")
        cli.info(f"   Communities:        {data['community_count']}")
        cli.blank()

        # Connectivity Distribution section
        cli.header("🔗 Connectivity Distribution")
        cli.info(
            f"   🟢 Well-Connected:    {dist.get('well_connected', 0):>4} pages ({pct.get('well_connected', 0):.1f}%)"
        )
        cli.info(
            f"   🟡 Adequately:        {dist.get('adequately_linked', 0):>4} pages ({pct.get('adequately_linked', 0):.1f}%)"
        )
        cli.info(
            f"   🟠 Lightly Linked:    {dist.get('lightly_linked', 0):>4} pages ({pct.get('lightly_linked', 0):.1f}%)"
        )
        isolated_status = "⚠️" if dist.get("isolated", 0) > threshold_isolated else "✅"
        cli.info(
            f"   🔴 Isolated:          {dist.get('isolated', 0):>4} pages ({pct.get('isolated', 0):.1f}%) {isolated_status}"
        )
        cli.blank()

        # Show isolated pages if any
        isolated_pages = data.get("isolated_pages", [])
        if isolated_pages:
            cli.header("🔴 Isolated Pages (need attention)")
            for page in isolated_pages[:5]:
                cli.info(f"      • {page}")
            if len(isolated_pages) > 5:
                cli.info(f"      ... and {len(isolated_pages) - 5} more")
            cli.blank()

        # Show lightly linked if many
        lightly_pages = data.get("lightly_linked_pages", [])
        if lightly_pages and dist.get("lightly_linked", 0) > threshold_lightly:
            cli.header("🟠 Lightly Linked (could improve)")
            for page in lightly_pages[:5]:
                cli.info(f"      • {page}")
            if len(lightly_pages) > 5:
                cli.info(f"      ... and {dist['lightly_linked'] - 5} more")
            cli.blank()

        # Bridges section
        if data.get("bridges"):
            cli.header("🌉 Bridge Pages (Navigation Bottlenecks)")
            for bridge in data["bridges"]:
                cli.info(f"   • {bridge}")
            cli.blank()

        # Recommendations
        cli.header("💡 Recommendations")
        if dist.get("isolated", 0) > 0:
            cli.info("   • Add explicit cross-references to isolated pages")
        if dist.get("lightly_linked", 0) > threshold_lightly:
            cli.info("   • Add internal links to lightly-linked pages")
        if data.get("avg_connectivity_score", 0) < 1.0:
            cli.info("   • Improve overall internal linking (aim for score ≥1.0)")
        if dist.get("isolated", 0) == 0 and data.get("avg_connectivity_score", 0) >= 1.0:
            cli.success("   ✅ Site structure looks good!")
        cli.blank()

        cli.info("=" * 80)
        cli.tip("Use --brief for CI-friendly output")
        cli.tip("Use --format json to export for processing")
        cli.tip("Use bengal graph orphans --level lightly for detailed list")
        cli.blank()


def _output_markdown(cli: Any, data: dict[str, Any], brief: bool) -> None:
    """Output report in markdown format."""
    dist = data.get("distribution", {})
    pct = data.get("percentages", {})

    cli.info("# Site Analysis Report\n")
    cli.info(
        f"**Pages:** {data['total_pages']} | **Links:** {data['total_links']} | **Avg Score:** {data.get('avg_connectivity_score', 0):.2f}\n"
    )

    cli.info("## Connectivity Distribution\n")
    cli.info("| Level | Count | Percentage |")
    cli.info("|-------|-------|------------|")
    cli.info(
        f"| 🟢 Well-Connected | {dist.get('well_connected', 0)} | {pct.get('well_connected', 0):.1f}% |"
    )
    cli.info(
        f"| 🟡 Adequately | {dist.get('adequately_linked', 0)} | {pct.get('adequately_linked', 0):.1f}% |"
    )
    cli.info(
        f"| 🟠 Lightly Linked | {dist.get('lightly_linked', 0)} | {pct.get('lightly_linked', 0):.1f}% |"
    )
    cli.info(f"| 🔴 Isolated | {dist.get('isolated', 0)} | {pct.get('isolated', 0):.1f}% |")
    cli.info("")

    isolated_pages = data.get("isolated_pages", [])
    if isolated_pages:
        cli.info("## 🔴 Isolated Pages\n")
        for page in isolated_pages[:10]:
            cli.info(f"- `{page}`")
        if len(isolated_pages) > 10:
            cli.info(f"- ... and {len(isolated_pages) - 10} more\n")

    if data.get("bridges"):
        cli.info("\n## Bridge Pages\n")
        for bridge in data["bridges"]:
            cli.info(f"- {bridge}")
        cli.info("")

    cli.info("## Recommendations\n")
    if dist.get("isolated", 0) > 0:
        cli.info("- [ ] Add explicit cross-references to isolated pages")
    if dist.get("lightly_linked", 0) > 10:
        cli.info("- [ ] Improve linking for lightly-linked pages")
    if data.get("avg_connectivity_score", 0) < 1.0:
        cli.info("- [ ] Increase overall internal linking (aim for score ≥1.0)")
    if dist.get("isolated", 0) == 0 and data.get("avg_connectivity_score", 0) >= 1.0:
        cli.info("- [x] Site structure looks good!")


# Compatibility export
report_command = report
