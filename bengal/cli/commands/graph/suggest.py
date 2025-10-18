"""Smart link suggestion command for improving internal linking."""

import json
from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.core.site import Site
from bengal.utils.cli_output import CLIOutput
from bengal.utils.logger import LogLevel, close_all_loggers, configure_logging


@click.command(cls=BengalCommand)
@click.option(
    "--top-n", "-n", default=50, type=int, help="Number of suggestions to show (default: 50)"
)
@click.option(
    "--min-score", "-s", default=0.3, type=float, help="Minimum score threshold (default: 0.3)"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def suggest(top_n: int, min_score: float, format: str, config: str, source: str) -> None:
    """
    💡 Generate smart link suggestions to improve internal linking.

    Analyzes your content to recommend links based on:
    - Topic similarity (shared tags/categories)
    - Page importance (PageRank scores)
    - Navigation value (bridge pages)
    - Link gaps (underlinked content)

    Use link suggestions to:
    - Improve internal linking structure
    - Boost SEO through better connectivity
    - Increase content discoverability
    - Fill navigation gaps

    Examples:
        # Show top 50 link suggestions
        bengal suggest

        # Show only high-confidence suggestions
        bengal suggest --min-score 0.5

        # Export as JSON
        bengal suggest --format json > suggestions.json

        # Generate markdown checklist
        bengal suggest --format markdown > TODO.md
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    cli = CLIOutput()

    try:
        configure_logging(level=LogLevel.WARNING)

        source_path = Path(source).resolve()

        if config:
            config_path = Path(config).resolve()
            site = Site.from_config(source_path, config_file=config_path)
        else:
            site = Site.from_config(source_path)

        cli.info("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator

        content_orch = ContentOrchestrator(site)
        content_orch.discover()

        cli.header(f"Building knowledge graph from {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()

        cli.info("💡 Generating link suggestions...")
        results = graph_obj.suggest_links(min_score=min_score)

        top_suggestions = results.get_top_suggestions(top_n)

        if format == "json":
            data = {
                "total_suggestions": results.total_suggestions,
                "pages_analyzed": results.pages_analyzed,
                "min_score": min_score,
                "suggestions": [
                    {
                        "source": {"title": s.source.title, "path": str(s.source.source_path)},
                        "target": {"title": s.target.title, "path": str(s.target.source_path)},
                        "score": s.score,
                        "reasons": s.reasons,
                    }
                    for s in top_suggestions
                ],
            }
            cli.info(json.dumps(data, indent=2))

        elif format == "markdown":
            cli.info("# Link Suggestions\n")
            cli.info(
                f"Generated {results.total_suggestions} suggestions from {results.pages_analyzed} pages\n"
            )
            cli.info(f"## Top {len(top_suggestions)} Suggestions\n")

            for i, suggestion in enumerate(top_suggestions, 1):
                cli.info(f"### {i}. {suggestion.source.title} → {suggestion.target.title}")
                cli.info(f"**Score:** {suggestion.score:.3f}\n")
                cli.info("**Reasons:**")
                for reason in suggestion.reasons:
                    cli.info(f"- {reason}")
                cli.info(
                    f"\n**Action:** Add link from `{suggestion.source.source_path}` to `{suggestion.target.source_path}`\n"
                )
                cli.info("---\n")

        else:  # table format
            cli.blank()
            cli.info("=" * 120)
            cli.header(f"💡 Top {len(top_suggestions)} Link Suggestions")
            cli.info("=" * 120)
            cli.info(
                f"Generated {results.total_suggestions} suggestions from {results.pages_analyzed} pages (min score: {min_score})"
            )
            cli.info("=" * 120)
            cli.info(f"{'#':<4} {'From':<35} {'To':<35} {'Score':<8} {'Reasons':<35}")
            cli.info("-" * 120)

            for i, suggestion in enumerate(top_suggestions, 1):
                source_title = suggestion.source.title
                if len(source_title) > 33:
                    source_title = source_title[:30] + "..."

                target_title = suggestion.target.title
                if len(target_title) > 33:
                    target_title = target_title[:30] + "..."

                reasons_str = "; ".join(suggestion.reasons[:2])
                if len(reasons_str) > 33:
                    reasons_str = reasons_str[:30] + "..."

                cli.info(
                    f"{i:<4} {source_title:<35} {target_title:<35} {suggestion.score:.4f}  {reasons_str:<35}"
                )

            cli.info("=" * 120)
            cli.blank()
            cli.info("💡 Tip: Use --format markdown to generate implementation checklist")
            cli.info("       Use --format json to export for programmatic processing")
            cli.info("       Use --min-score to filter low-confidence suggestions")
            cli.blank()

        if format != "json":
            cli.blank()
            cli.info("=" * 60)
            cli.header("📊 Summary")
            cli.info("=" * 60)
            cli.info(f"• Total suggestions:          {results.total_suggestions}")
            cli.info(f"• Above threshold ({min_score}):      {len(top_suggestions)}")
            cli.info(f"• Pages analyzed:             {results.pages_analyzed}")
            cli.info(
                f"• Avg suggestions per page:   {results.total_suggestions / results.pages_analyzed:.1f}"
            )
            cli.blank()

    except Exception as e:
        cli.error(f"❌ Error: {e}")
        raise click.Abort() from e
    finally:
        close_all_loggers()
