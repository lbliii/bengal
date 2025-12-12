"""Performance metrics and analysis commands."""

from __future__ import annotations

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import command_metadata, handle_cli_errors


@click.command(cls=BengalCommand)
@command_metadata(
    category="performance",
    description="Show performance metrics and trends",
    examples=[
        "bengal perf",
        "bengal perf --last 20",
        "bengal perf --compare",
    ],
    requires_site=False,
    tags=["performance", "metrics", "analysis"],
)
@handle_cli_errors(show_art=False)
@click.option("--last", "-n", default=10, help="Show last N builds (default: 10)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "summary"]),
    default="table",
    help="Output format",
)
@click.option("--compare", "-c", is_flag=True, help="Compare last two builds")
def perf(last: int, format: str, compare: bool) -> None:
    """Show performance metrics and trends.

    Displays build performance metrics collected from previous builds.
    Metrics are automatically saved to .bengal/metrics/ directory.

    Examples:
      bengal perf              # Show last 10 builds as table
      bengal perf -n 20        # Show last 20 builds
      bengal perf -f summary   # Show summary of latest build
      bengal perf -f json      # Output as JSON
      bengal perf --compare    # Compare last two builds
    """
    from pathlib import Path

    from bengal.cache.paths import BengalPaths
    from bengal.utils.performance_report import PerformanceReport

    paths = BengalPaths(Path.cwd())
    report = PerformanceReport(metrics_dir=paths.metrics_dir)

    if compare:
        report.compare()
    else:
        report.show(last=last, format=format)
