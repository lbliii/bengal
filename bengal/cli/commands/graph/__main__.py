"""Graph analysis and knowledge graph commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from bengal.cli.base import BengalCommand, BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)
from bengal.utils.logger import LogLevel, close_all_loggers, configure_logging

from .bridges import bridges
from .communities import communities
from .orphans import orphans
from .pagerank import pagerank
from .report import report
from .suggest import suggest


@click.group("graph", cls=BengalGroup)
def graph_cli() -> None:
    """Commands for analyzing the site's knowledge graph."""
    pass


@click.command("analyze", cls=BengalCommand)
@command_metadata(
    category="analysis",
    description="Analyze site structure and connectivity",
    examples=[
        "bengal graph analyze",
        "bengal graph analyze --tree",
        "bengal graph analyze --output public/graph.html",
    ],
    requires_site=True,
    tags=["analysis", "graph", "visualization"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--stats",
    "show_stats",
    is_flag=True,
    default=True,
    help="Show graph statistics (default: enabled)",
)
@click.option("--tree", is_flag=True, help="Show site structure as tree visualization")
@click.option(
    "--output",
    type=click.Path(),
    help="Generate interactive visualization to file (e.g., public/graph.html)",
)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def analyze(show_stats: bool, tree: bool, output: str, config: str, source: str) -> None:
    """
    Analyze site structure and connectivity.
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    # Configure minimal logging
    configure_logging(level=LogLevel.WARNING)

    # Load site using helper
    cli = get_cli_output()
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    # We need to discover content to analyze it
    # This also builds the xref_index for link analysis
    try:
        from bengal.utils.rich_console import get_console, should_use_rich

        if should_use_rich():
            console = get_console()

            with console.status(
                "[bold green]Discovering site content...", spinner="dots"
            ) as status:
                from bengal.orchestration.content import ContentOrchestrator

                content_orch = ContentOrchestrator(site)
                content_orch.discover()

                # Build knowledge graph
                status.update(f"[bold green]Analyzing {len(site.pages)} pages...")
                graph_obj = KnowledgeGraph(site)
                graph_obj.build()
        else:
            # Fallback to simple messages
            cli.info("🔍 Discovering site content...")
            from bengal.orchestration.content import ContentOrchestrator

            content_orch = ContentOrchestrator(site)
            content_orch.discover()

            cli.info(f"📊 Analyzing {len(site.pages)} pages...")
            graph_obj = KnowledgeGraph(site)
            graph_obj.build()
    except ImportError:
        # Rich not available, use simple messages
        cli.info("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator

        content_orch = ContentOrchestrator(site)
        content_orch.discover()

        cli.info(f"📊 Analyzing {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()

    # Show tree visualization if requested
    if tree:
        try:
            from rich.tree import Tree

            from bengal.utils.rich_console import get_console, should_use_rich

            if should_use_rich():
                console = get_console()
                cli.blank()

                # Create tree visualization
                tree_root = Tree("📁 [header]Site Structure[/header]")

                # Group pages by section
                sections_dict: dict[str, list[Any]] = {}
                for page in site.pages:
                    # Get section from page path or use root
                    if hasattr(page, "section") and page.section:
                        section_name = page.section
                    else:
                        # Try to extract from path
                        parts = Path(page.source_path).parts
                        section_name = parts[0] if len(parts) > 1 else "Root"

                    if section_name not in sections_dict:
                        sections_dict[section_name] = []
                    sections_dict[section_name].append(page)

                # Build tree structure
                for section_name in sorted(sections_dict.keys()):
                    pages_in_section = sections_dict[section_name]

                    # Create section branch
                    section_label = (
                        f"📁 [info]{section_name}[/info] [dim]({len(pages_in_section)} pages)[/dim]"
                    )
                    section_branch = tree_root.add(section_label)

                    # Add pages (limit to first 15 per section)
                    for page in sorted(pages_in_section, key=lambda p: str(p.source_path))[:15]:
                        # Determine icon
                        icon = "📄"
                        if hasattr(page, "is_index") and page.is_index:
                            icon = "🏠"
                        elif hasattr(page, "source_path") and "blog" in str(page.source_path):
                            icon = "📝"

                        # Get incoming/outgoing links
                        incoming = len(graph_obj.incoming_refs.get(page, []))
                        outgoing = len(graph_obj.outgoing_refs.get(page, []))

                        # Format page entry
                        title = getattr(page, "title", str(page.source_path))
                        if len(title) > 50:
                            title = title[:47] + "..."

                        link_info = f"[dim]({incoming}↓ {outgoing}↑)[/dim]"
                        section_branch.add(f"{icon} {title} {link_info}")

                    # Show count if truncated
                    if len(pages_in_section) > 15:
                        remaining = len(pages_in_section) - 15
                        section_branch.add(f"[dim]... and {remaining} more pages[/dim]")

                # Print the Rich Tree component (complex visualization)
                cli.console.print(tree_root)
                cli.blank()
            else:
                cli.warning("Tree visualization requires a TTY terminal")
        except ImportError:
            cli.warning("⚠️  Tree visualization requires 'rich' library")

    # Show statistics
    if show_stats:
        stats = graph_obj.format_stats()
        cli.info(stats)

    # Generate visualization if requested
    if output:
        output_path = Path(output).resolve()
        cli.blank()
        cli.header("Generating interactive visualization...")
        cli.info(f"   ↪ {output_path}")

        # Check if visualization module exists
        try:
            from bengal.analysis.graph_visualizer import GraphVisualizer

            visualizer = GraphVisualizer(site, graph_obj)
            html = visualizer.generate_html()

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write HTML file
            output_path.write_text(html, encoding="utf-8")

            cli.success("✅ Visualization generated!")
            cli.info(f"   Open {output_path} in your browser to explore.")
        except ImportError:
            cli.warning("⚠️  Graph visualization not yet implemented.")
            cli.info("   This feature is coming in Phase 2!")

    close_all_loggers()


graph_cli.add_command(analyze)
graph_cli.add_command(report)
graph_cli.add_command(orphans)
graph_cli.add_command(pagerank)
graph_cli.add_command(communities)
graph_cli.add_command(bridges)
graph_cli.add_command(suggest)
