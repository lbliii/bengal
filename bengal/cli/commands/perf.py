"""Performance metrics and analysis commands."""

import click


@click.command()
@click.option("--last", "-n", default=10, help="Show last N builds (default: 10)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "summary"]),
    default="table",
    help="Output format",
)
@click.option("--compare", "-c", is_flag=True, help="Compare last two builds")
def perf(last, format, compare):
    """Show performance metrics and trends.

    Displays build performance metrics collected from previous builds.
    Metrics are automatically saved to .bengal-metrics/ directory.

    Examples:
      bengal perf              # Show last 10 builds as table
      bengal perf -n 20        # Show last 20 builds
      bengal perf -f summary   # Show summary of latest build
      bengal perf -f json      # Output as JSON
      bengal perf --compare    # Compare last two builds
    """
    from bengal.utils.performance_report import PerformanceReport

    report = PerformanceReport()

    if compare:
        report.compare()
    else:
        report.show(last=last, format=format)
