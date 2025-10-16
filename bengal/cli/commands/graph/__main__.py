"""Graph analysis and knowledge graph commands."""

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.logger import LogLevel, close_all_loggers, configure_logging

from .bridges import bridges
from .communities import communities
from .pagerank import pagerank
from .suggest import suggest


@click.group("graph")
def graph_cli():
    """Commands for analyzing the site's knowledge graph."""
    pass


@click.command("analyze")
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
    📊 Analyze site structure and connectivity.
    """
    from bengal.analysis.knowledge_graph import KnowledgeGraph

    try:
        # Configure minimal logging
        configure_logging(level=LogLevel.WARNING)

        # Load site
        source_path = Path(source).resolve()

        if config:
            config_path = Path(config).resolve()
            site = Site.from_config(source_path, config_file=config_path)
        else:
            site = Site.from_config(source_path)

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
                click.echo("🔍 Discovering site content...")
                from bengal.orchestration.content import ContentOrchestrator

                content_orch = ContentOrchestrator(site)
                content_orch.discover()

                click.echo(f"📊 Analyzing {len(site.pages)} pages...")
                graph_obj = KnowledgeGraph(site)
                graph_obj.build()
        except ImportError:
            # Rich not available, use simple messages
            click.echo("🔍 Discovering site content...")
            from bengal.orchestration.content import ContentOrchestrator

            content_orch = ContentOrchestrator(site)
            content_orch.discover()

            click.echo(f"📊 Analyzing {len(site.pages)} pages...")
            graph_obj = KnowledgeGraph(site)
            graph_obj.build()

        # Show tree visualization if requested
        if tree:
            try:
                from rich.tree import Tree

                from bengal.utils.rich_console import get_console, should_use_rich

                if should_use_rich():
                    console = get_console()
                    console.print()

                    # Create tree visualization
                    tree_root = Tree("📁 [bold cyan]Site Structure[/bold cyan]")

                    # Group pages by section
                    sections_dict = {}
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
                        section_label = f"📁 [cyan]{section_name}[/cyan] [dim]({len(pages_in_section)} pages)[/dim]"
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

                    console.print(tree_root)
                    console.print()
                else:
                    click.echo(
                        click.style("Tree visualization requires a TTY terminal", fg="yellow")
                    )
            except ImportError:
                click.echo(
                    click.style("⚠️  Tree visualization requires 'rich' library", fg="yellow")
                )

        # Show statistics
        if show_stats:
            stats = graph_obj.format_stats()
            click.echo(stats)

        # Generate visualization if requested
        if output:
            from bengal.utils.cli_output import CLIOutput

            cli = CLIOutput()

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

                click.echo(click.style("✅ Visualization generated!", fg="green", bold=True))
                click.echo(f"   Open {output_path} in your browser to explore.")
            except ImportError:
                click.echo(click.style("⚠️  Graph visualization not yet implemented.", fg="yellow"))
                click.echo("   This feature is coming in Phase 2!")

    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg="red", bold=True))
        raise click.Abort() from e
    finally:
        close_all_loggers()

graph_cli.add_command(analyze)
graph_cli.add_command(pagerank)
graph_cli.add_command(communities)
graph_cli.add_command(bridges)
graph_cli.add_command(suggest)
