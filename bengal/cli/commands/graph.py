"""Graph analysis and knowledge graph commands."""

from pathlib import Path
import click
import json

from bengal.core.site import Site
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers


@click.command()
@click.option('--stats', 'show_stats', is_flag=True, default=True, help='Show graph statistics (default: enabled)')
@click.option('--tree', is_flag=True, help='Show site structure as tree visualization')
@click.option('--output', type=click.Path(), help='Generate interactive visualization to file (e.g., public/graph.html)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def graph(show_stats: bool, tree: bool, output: str, config: str, source: str) -> None:
    """
    📊 Analyze site structure and connectivity.
    
    Builds a knowledge graph of your site to:
    - Find orphaned pages (no incoming links)
    - Identify hub pages (highly connected)
    - Understand content structure
    - Generate interactive visualizations
    
    Examples:
        # Show connectivity statistics
        bengal graph
        
        # Generate interactive visualization
        bengal graph --output public/graph.html
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
            from rich.status import Status
            
            if should_use_rich():
                console = get_console()
                
                with console.status("[bold green]Discovering site content...", spinner="dots") as status:
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
                        if hasattr(page, 'section') and page.section:
                            section_name = page.section
                        else:
                            # Try to extract from path
                            parts = Path(page.source_path).parts
                            if len(parts) > 1:
                                section_name = parts[0]
                            else:
                                section_name = "Root"
                        
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
                            if hasattr(page, 'is_index') and page.is_index:
                                icon = "🏠"
                            elif hasattr(page, 'source_path') and 'blog' in str(page.source_path):
                                icon = "📝"
                            
                            # Get incoming/outgoing links
                            incoming = len(graph_obj.incoming_refs.get(page, []))
                            outgoing = len(graph_obj.outgoing_refs.get(page, []))
                            
                            # Format page entry
                            title = getattr(page, 'title', str(page.source_path))
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
                    click.echo(click.style("Tree visualization requires a TTY terminal", fg='yellow'))
            except ImportError:
                click.echo(click.style("⚠️  Tree visualization requires 'rich' library", fg='yellow'))
        
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
                output_path.write_text(html, encoding='utf-8')
                
                click.echo(click.style("✅ Visualization generated!", fg='green', bold=True))
                click.echo(f"   Open {output_path} in your browser to explore.")
            except ImportError:
                click.echo(click.style("⚠️  Graph visualization not yet implemented.", fg='yellow'))
                click.echo("   This feature is coming in Phase 2!")
        
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        raise click.Abort()
    finally:
        close_all_loggers()


@click.command()
@click.option('--top-n', '-n', default=20, type=int, help='Number of top pages to show (default: 20)')
@click.option('--damping', '-d', default=0.85, type=float, help='PageRank damping factor (default: 0.85)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'summary']), 
              default='table', help='Output format (default: table)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
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
    
    try:
        # Configure minimal logging
        configure_logging(level=LogLevel.WARNING)
        
        # Validate damping factor
        if not 0 < damping < 1:
            click.echo(click.style(f"❌ Error: Damping factor must be between 0 and 1, got {damping}", fg='red', bold=True))
            raise click.Abort()
        
        # Load site
        source_path = Path(source).resolve()
        
        if config:
            config_path = Path(config).resolve()
            site = Site.from_config(source_path, config_file=config_path)
        else:
            site = Site.from_config(source_path)
        
        # Discover content and compute PageRank with status indicator
        try:
            from bengal.utils.rich_console import get_console, should_use_rich
            from rich.status import Status
            
            if should_use_rich():
                console = get_console()
                
                with console.status("[bold green]Discovering site content...", spinner="dots") as status:
                    from bengal.orchestration.content import ContentOrchestrator
                    content_orch = ContentOrchestrator(site)
                    content_orch.discover()
                    
                    status.update(f"[bold green]Building knowledge graph from {len(site.pages)} pages...")
                    graph_obj = KnowledgeGraph(site)
                    graph_obj.build()
                    
                    status.update(f"[bold green]Computing PageRank (damping={damping})...")
                    results = graph_obj.compute_pagerank(damping=damping)
            else:
                # Fallback to simple messages
                click.echo("🔍 Discovering site content...")
                from bengal.orchestration.content import ContentOrchestrator
                content_orch = ContentOrchestrator(site)
                content_orch.discover()
                
                click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
                graph_obj = KnowledgeGraph(site)
                graph_obj.build()
                
                click.echo(f"🏆 Computing PageRank (damping={damping})...")
                results = graph_obj.compute_pagerank(damping=damping)
        except ImportError:
            # Rich not available, use simple messages
            click.echo("🔍 Discovering site content...")
            from bengal.orchestration.content import ContentOrchestrator
            content_orch = ContentOrchestrator(site)
            content_orch.discover()
            
            click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
            graph_obj = KnowledgeGraph(site)
            graph_obj.build()
            
            click.echo(f"🏆 Computing PageRank (damping={damping})...")
            results = graph_obj.compute_pagerank(damping=damping)
        
        # Get top pages
        top_pages = results.get_top_pages(top_n)
        
        # Output based on format
        if format == 'json':
            # Export as JSON
            data = {
                'total_pages': len(results.scores),
                'iterations': results.iterations,
                'converged': results.converged,
                'damping_factor': results.damping_factor,
                'top_pages': [
                    {
                        'rank': i + 1,
                        'title': page.title,
                        'url': getattr(page, 'url_path', page.source_path),
                        'score': score,
                        'incoming_refs': graph_obj.incoming_refs.get(page, 0),
                        'outgoing_refs': len(graph_obj.outgoing_refs.get(page, set()))
                    }
                    for i, (page, score) in enumerate(top_pages)
                ]
            }
            click.echo(json.dumps(data, indent=2))
        
        elif format == 'summary':
            # Show summary stats
            click.echo("\n" + "=" * 60)
            click.echo(f"📈 PageRank Summary")
            click.echo("=" * 60)
            click.echo(f"Total pages analyzed:    {len(results.scores)}")
            click.echo(f"Iterations to converge:  {results.iterations}")
            click.echo(f"Converged:               {'✅ Yes' if results.converged else '⚠️  No'}")
            click.echo(f"Damping factor:          {results.damping_factor}")
            click.echo(f"\nTop {min(top_n, len(top_pages))} pages by importance:")
            click.echo("-" * 60)
            
            for i, (page, score) in enumerate(top_pages, 1):
                incoming = graph_obj.incoming_refs.get(page, 0)
                outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                click.echo(f"{i:3d}. {page.title:<40} Score: {score:.6f}")
                click.echo(f"     {incoming} incoming, {outgoing} outgoing links")
        
        else:  # table format
            click.echo("\n" + "=" * 100)
            click.echo(f"🏆 Top {min(top_n, len(top_pages))} Pages by PageRank")
            click.echo("=" * 100)
            click.echo(f"Analyzed {len(results.scores)} pages • Converged in {results.iterations} iterations • Damping: {damping}")
            click.echo("=" * 100)
            click.echo(f"{'Rank':<6} {'Title':<45} {'Score':<12} {'In':<5} {'Out':<5}")
            click.echo("-" * 100)
            
            for i, (page, score) in enumerate(top_pages, 1):
                incoming = graph_obj.incoming_refs.get(page, 0)
                outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                
                # Truncate title if too long
                title = page.title
                if len(title) > 43:
                    title = title[:40] + "..."
                
                click.echo(f"{i:<6} {title:<45} {score:.8f}  {incoming:<5} {outgoing:<5}")
            
            click.echo("=" * 100)
            click.echo("\n💡 Tip: Use --format json to export scores for further analysis")
            click.echo("       Use --top-n to show more/fewer pages\n")
        
        # Show insights
        if format != 'json' and results.converged:
            click.echo("\n" + "=" * 60)
            click.echo("📊 Insights")
            click.echo("=" * 60)
            
            # Calculate some basic stats
            scores_list = sorted(results.scores.values(), reverse=True)
            top_10_pct = results.get_pages_above_percentile(90)
            avg_score = sum(scores_list) / len(scores_list) if scores_list else 0
            max_score = max(scores_list) if scores_list else 0
            
            click.echo(f"• Average PageRank score:     {avg_score:.6f}")
            click.echo(f"• Maximum PageRank score:     {max_score:.6f}")
            click.echo(f"• Top 10% threshold:          {len(top_10_pct)} pages (score ≥ {scores_list[int(len(scores_list)*0.1)]:.6f})")
            click.echo(f"• Score concentration:        {'High' if max_score > avg_score * 10 else 'Moderate' if max_score > avg_score * 5 else 'Low'}")
            click.echo("\n")
        
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if '--debug' in click.get_current_context().args:
            raise
        raise click.Abort()
    finally:
        close_all_loggers()


@click.command()
@click.option('--min-size', '-m', default=2, type=int, help='Minimum community size to show (default: 2)')
@click.option('--resolution', '-r', default=1.0, type=float, help='Resolution parameter (higher = more communities, default: 1.0)')
@click.option('--top-n', '-n', default=10, type=int, help='Number of communities to show (default: 10)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'summary']), 
              default='table', help='Output format (default: table)')
@click.option('--seed', type=int, help='Random seed for reproducibility')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def communities(min_size: int, resolution: float, top_n: int, format: str, seed: int, config: str, source: str) -> None:
    """
    🔍 Discover topical communities in your content.
    
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
        
        # Discover content
        click.echo("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator
        content_orch = ContentOrchestrator(site)
        content_orch.discover()
        
        # Build knowledge graph
        click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()
        
        # Detect communities
        click.echo(f"🔍 Detecting communities (resolution={resolution})...")
        results = graph_obj.detect_communities(resolution=resolution, random_seed=seed)
        
        # Filter by minimum size
        communities_to_show = results.get_communities_above_size(min_size)
        
        # Sort by size
        communities_to_show.sort(key=lambda c: c.size, reverse=True)
        
        # Limit to top N
        communities_to_show = communities_to_show[:top_n]
        
        # Output based on format
        if format == 'json':
            # Export as JSON
            data = {
                'total_communities': len(results.communities),
                'modularity': results.modularity,
                'iterations': results.iterations,
                'resolution': resolution,
                'communities': []
            }
            
            for community in communities_to_show:
                # Get top pages by incoming links
                pages_with_refs = [
                    (page, graph_obj.incoming_refs.get(page, 0))
                    for page in community.pages
                ]
                pages_with_refs.sort(key=lambda x: x[1], reverse=True)
                
                data['communities'].append({
                    'id': community.id,
                    'size': community.size,
                    'pages': [
                        {
                            'title': page.title,
                            'url': getattr(page, 'url_path', str(page.source_path)),
                            'incoming_refs': refs
                        }
                        for page, refs in pages_with_refs[:5]  # Top 5 pages
                    ]
                })
            
            click.echo(json.dumps(data, indent=2))
        
        elif format == 'summary':
            # Show summary stats
            click.echo("\n" + "=" * 60)
            click.echo(f"🔍 Community Detection Summary")
            click.echo("=" * 60)
            click.echo(f"Total communities found:  {len(results.communities)}")
            click.echo(f"Showing communities:      {len(communities_to_show)}")
            click.echo(f"Modularity score:         {results.modularity:.4f}")
            click.echo(f"Iterations:               {results.iterations}")
            click.echo(f"Resolution:               {resolution}")
            click.echo("")
            
            for i, community in enumerate(communities_to_show, 1):
                click.echo(f"\nCommunity {i} (ID: {community.id})")
                click.echo(f"  Size: {community.size} pages")
                
                # Show top pages
                pages_with_refs = [
                    (page, graph_obj.incoming_refs.get(page, 0))
                    for page in community.pages
                ]
                pages_with_refs.sort(key=lambda x: x[1], reverse=True)
                
                click.echo(f"  Top pages:")
                for page, refs in pages_with_refs[:3]:
                    click.echo(f"    • {page.title} ({refs} refs)")
        
        else:  # table format
            click.echo("\n" + "=" * 100)
            click.echo(f"🔍 Top {len(communities_to_show)} Communities")
            click.echo("=" * 100)
            click.echo(f"Found {len(results.communities)} communities • Modularity: {results.modularity:.4f} • Resolution: {resolution}")
            click.echo("=" * 100)
            click.echo(f"{'ID':<5} {'Size':<6} {'Top Pages':<85}")
            click.echo("-" * 100)
            
            for community in communities_to_show:
                # Get top 3 pages by incoming links
                pages_with_refs = [
                    (page, graph_obj.incoming_refs.get(page, 0))
                    for page in community.pages
                ]
                pages_with_refs.sort(key=lambda x: x[1], reverse=True)
                
                top_page_titles = ", ".join([
                    page.title[:25] + "..." if len(page.title) > 25 else page.title
                    for page, _ in pages_with_refs[:3]
                ])
                
                if len(top_page_titles) > 83:
                    top_page_titles = top_page_titles[:80] + "..."
                
                click.echo(f"{community.id:<5} {community.size:<6} {top_page_titles:<85}")
            
            click.echo("=" * 100)
            click.echo("\n💡 Tip: Use --format json to export full data")
            click.echo("       Use --min-size to filter small communities")
            click.echo("       Use --resolution to control granularity\n")
        
        # Show insights
        if format != 'json':
            click.echo("\n" + "=" * 60)
            click.echo("📊 Insights")
            click.echo("=" * 60)
            
            total_pages = sum(c.size for c in results.communities)
            avg_size = total_pages / len(results.communities) if results.communities else 0
            largest = max((c.size for c in results.communities), default=0)
            
            click.echo(f"• Average community size:     {avg_size:.1f} pages")
            click.echo(f"• Largest community:          {largest} pages")
            click.echo(f"• Communities >= {min_size} pages:      {len(communities_to_show)}")
            
            if results.modularity > 0.3:
                click.echo(f"• Modularity:                 High (good clustering)")
            elif results.modularity > 0.1:
                click.echo(f"• Modularity:                 Moderate (some structure)")
            else:
                click.echo(f"• Modularity:                 Low (weak structure)")
            
            click.echo("\n")
        
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        raise click.Abort()
    finally:
        close_all_loggers()


@click.command()
@click.option('--top-n', '-n', default=20, type=int, help='Number of pages to show (default: 20)')
@click.option('--metric', '-m', type=click.Choice(['betweenness', 'closeness', 'both']), 
              default='both', help='Centrality metric to display (default: both)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'summary']), 
              default='table', help='Output format (default: table)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
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
        
        # Discover content
        click.echo("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator
        content_orch = ContentOrchestrator(site)
        content_orch.discover()
        
        # Build knowledge graph
        click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()
        
        # Analyze paths
        click.echo(f"🌉 Analyzing navigation paths...")
        results = graph_obj.analyze_paths()
        
        # Output based on format
        if format == 'json':
            # Export as JSON
            data = {
                'avg_path_length': results.avg_path_length,
                'diameter': results.diameter,
                'total_pages': len(results.betweenness_centrality)
            }
            
            if metric in ['betweenness', 'both']:
                bridges_list = results.get_top_bridges(top_n)
                data['top_bridges'] = [
                    {
                        'title': page.title,
                        'url': getattr(page, 'url_path', str(page.source_path)),
                        'betweenness': score,
                        'incoming_refs': graph_obj.incoming_refs.get(page, 0)
                    }
                    for page, score in bridges_list
                ]
            
            if metric in ['closeness', 'both']:
                accessible = results.get_most_accessible(top_n)
                data['most_accessible'] = [
                    {
                        'title': page.title,
                        'url': getattr(page, 'url_path', str(page.source_path)),
                        'closeness': score,
                        'outgoing_refs': len(graph_obj.outgoing_refs.get(page, set()))
                    }
                    for page, score in accessible
                ]
            
            click.echo(json.dumps(data, indent=2))
        
        elif format == 'summary':
            # Show summary stats
            click.echo("\n" + "=" * 60)
            click.echo(f"🌉 Path Analysis Summary")
            click.echo("=" * 60)
            click.echo(f"Total pages analyzed:     {len(results.betweenness_centrality)}")
            click.echo(f"Average path length:      {results.avg_path_length:.2f}")
            click.echo(f"Network diameter:         {results.diameter}")
            click.echo("")
            
            if metric in ['betweenness', 'both']:
                click.echo(f"\n🔗 Top Bridge Pages (Betweenness Centrality)")
                click.echo("-" * 60)
                bridges_list = results.get_top_bridges(top_n)
                for i, (page, score) in enumerate(bridges_list, 1):
                    incoming = graph_obj.incoming_refs.get(page, 0)
                    outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                    click.echo(f"{i:3d}. {page.title}")
                    click.echo(f"     Betweenness: {score:.6f} | {incoming} in, {outgoing} out")
            
            if metric in ['closeness', 'both']:
                click.echo(f"\n🎯 Most Accessible Pages (Closeness Centrality)")
                click.echo("-" * 60)
                accessible = results.get_most_accessible(top_n)
                for i, (page, score) in enumerate(accessible, 1):
                    outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                    click.echo(f"{i:3d}. {page.title}")
                    click.echo(f"     Closeness: {score:.6f} | Can reach {outgoing} pages")
        
        else:  # table format
            click.echo("\n" + "=" * 100)
            click.echo(f"🌉 Navigation Path Analysis")
            click.echo("=" * 100)
            click.echo(f"Analyzed {len(results.betweenness_centrality)} pages • Avg path: {results.avg_path_length:.2f} • Diameter: {results.diameter}")
            click.echo("=" * 100)
            
            if metric in ['betweenness', 'both']:
                click.echo(f"\n🔗 Top {top_n} Bridge Pages (Betweenness Centrality)")
                click.echo("-" * 100)
                click.echo(f"{'Rank':<6} {'Title':<50} {'Betweenness':<14} {'In':<5} {'Out':<5}")
                click.echo("-" * 100)
                
                bridges_list = results.get_top_bridges(top_n)
                for i, (page, score) in enumerate(bridges_list, 1):
                    title = page.title
                    if len(title) > 48:
                        title = title[:45] + "..."
                    
                    incoming = graph_obj.incoming_refs.get(page, 0)
                    outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                    
                    click.echo(f"{i:<6} {title:<50} {score:.10f}  {incoming:<5} {outgoing:<5}")
            
            if metric in ['closeness', 'both']:
                click.echo(f"\n🎯 Top {top_n} Most Accessible Pages (Closeness Centrality)")
                click.echo("-" * 100)
                click.echo(f"{'Rank':<6} {'Title':<50} {'Closeness':<14} {'Out':<5}")
                click.echo("-" * 100)
                
                accessible = results.get_most_accessible(top_n)
                for i, (page, score) in enumerate(accessible, 1):
                    title = page.title
                    if len(title) > 48:
                        title = title[:45] + "..."
                    
                    outgoing = len(graph_obj.outgoing_refs.get(page, set()))
                    
                    click.echo(f"{i:<6} {title:<50} {score:.10f}  {outgoing:<5}")
            
            click.echo("=" * 100)
            click.echo("\n💡 Tip: Use --metric to focus on betweenness or closeness")
            click.echo("       Use --format json to export for analysis\n")
        
        # Show insights
        if format != 'json':
            click.echo("\n" + "=" * 60)
            click.echo("📊 Insights")
            click.echo("=" * 60)
            
            avg_betweenness = sum(results.betweenness_centrality.values()) / len(results.betweenness_centrality) if results.betweenness_centrality else 0
            max_betweenness = max(results.betweenness_centrality.values()) if results.betweenness_centrality else 0
            
            click.echo(f"• Average path length:        {results.avg_path_length:.2f} hops")
            click.echo(f"• Network diameter:           {results.diameter} hops")
            click.echo(f"• Average betweenness:        {avg_betweenness:.6f}")
            click.echo(f"• Max betweenness:            {max_betweenness:.6f}")
            
            if results.diameter > 5:
                click.echo(f"• Structure:                  Deep (consider shortening paths)")
            elif results.diameter > 3:
                click.echo(f"• Structure:                  Medium depth")
            else:
                click.echo(f"• Structure:                  Shallow (well connected)")
            
            click.echo("\n")
        
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        raise click.Abort()
    finally:
        close_all_loggers()


@click.command()
@click.option('--top-n', '-n', default=50, type=int, help='Number of suggestions to show (default: 50)')
@click.option('--min-score', '-s', default=0.3, type=float, help='Minimum score threshold (default: 0.3)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'markdown']), 
              default='table', help='Output format (default: table)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
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
    
    try:
        configure_logging(level=LogLevel.WARNING)
        
        source_path = Path(source).resolve()
        
        if config:
            config_path = Path(config).resolve()
            site = Site.from_config(source_path, config_file=config_path)
        else:
            site = Site.from_config(source_path)
        
        click.echo("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator
        content_orch = ContentOrchestrator(site)
        content_orch.discover()
        
        from bengal.utils.cli_output import CLIOutput
        cli = CLIOutput()
        
        cli.header(f"Building knowledge graph from {len(site.pages)} pages...")
        graph_obj = KnowledgeGraph(site)
        graph_obj.build()
        
        click.echo(f"💡 Generating link suggestions...")
        results = graph_obj.suggest_links(min_score=min_score)
        
        top_suggestions = results.get_top_suggestions(top_n)
        
        if format == 'json':
            data = {
                'total_suggestions': results.total_suggestions,
                'pages_analyzed': results.pages_analyzed,
                'min_score': min_score,
                'suggestions': [
                    {
                        'source': {'title': s.source.title, 'path': str(s.source.source_path)},
                        'target': {'title': s.target.title, 'path': str(s.target.source_path)},
                        'score': s.score,
                        'reasons': s.reasons
                    }
                    for s in top_suggestions
                ]
            }
            click.echo(json.dumps(data, indent=2))
        
        elif format == 'markdown':
            click.echo(f"# Link Suggestions\n")
            click.echo(f"Generated {results.total_suggestions} suggestions from {results.pages_analyzed} pages\n")
            click.echo(f"## Top {len(top_suggestions)} Suggestions\n")
            
            for i, suggestion in enumerate(top_suggestions, 1):
                click.echo(f"### {i}. {suggestion.source.title} → {suggestion.target.title}")
                click.echo(f"**Score:** {suggestion.score:.3f}\n")
                click.echo(f"**Reasons:**")
                for reason in suggestion.reasons:
                    click.echo(f"- {reason}")
                click.echo(f"\n**Action:** Add link from `{suggestion.source.source_path}` to `{suggestion.target.source_path}`\n")
                click.echo("---\n")
        
        else:  # table format
            click.echo("\n" + "=" * 120)
            click.echo(f"💡 Top {len(top_suggestions)} Link Suggestions")
            click.echo("=" * 120)
            click.echo(f"Generated {results.total_suggestions} suggestions from {results.pages_analyzed} pages (min score: {min_score})")
            click.echo("=" * 120)
            click.echo(f"{'#':<4} {'From':<35} {'To':<35} {'Score':<8} {'Reasons':<35}")
            click.echo("-" * 120)
            
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
                
                click.echo(f"{i:<4} {source_title:<35} {target_title:<35} {suggestion.score:.4f}  {reasons_str:<35}")
            
            click.echo("=" * 120)
            click.echo("\n💡 Tip: Use --format markdown to generate implementation checklist")
            click.echo("       Use --format json to export for programmatic processing")
            click.echo("       Use --min-score to filter low-confidence suggestions\n")
        
        if format != 'json':
            click.echo("\n" + "=" * 60)
            click.echo("📊 Summary")
            click.echo("=" * 60)
            click.echo(f"• Total suggestions:          {results.total_suggestions}")
            click.echo(f"• Above threshold ({min_score}):      {len(top_suggestions)}")
            click.echo(f"• Pages analyzed:             {results.pages_analyzed}")
            click.echo(f"• Avg suggestions per page:   {results.total_suggestions / results.pages_analyzed:.1f}")
            click.echo("\n")
    
    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        raise click.Abort()
    finally:
        close_all_loggers()

