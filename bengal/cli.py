"""
Command-line interface for Bengal SSG.
"""

from pathlib import Path
from datetime import datetime
import click

from bengal import __version__
from bengal.core.site import Site
from bengal.utils.build_stats import (
    display_build_stats,
    show_building_indicator,
    show_error,
    show_clean_success,
)
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers, print_all_summaries
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.generator import DocumentationGenerator
from bengal.autodoc.config import load_autodoc_config


class BengalGroup(click.Group):
    """Custom Click group with typo detection and suggestions."""
    
    def resolve_command(self, ctx, args):
        """Resolve command with fuzzy matching for typos."""
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            # Check if it's an unknown command error
            if "No such command" in str(e) and args:
                unknown_cmd = args[0]
                suggestions = self._get_similar_commands(unknown_cmd)
                
                if suggestions:
                    # Format error message with suggestions
                    msg = f"Unknown command '{unknown_cmd}'.\n\n"
                    msg += "Did you mean one of these?\n"
                    for i, suggestion in enumerate(suggestions, 1):
                        msg += f"  • {click.style(suggestion, fg='cyan', bold=True)}\n"
                    msg += f"\nRun '{click.style('bengal --help', fg='yellow')}' to see all commands."
                    raise click.exceptions.UsageError(msg)
            
            # Re-raise original error if no suggestions
            raise
    
    def _get_similar_commands(self, unknown_cmd: str, max_suggestions: int = 3):
        """Find similar command names using simple string similarity."""
        from difflib import get_close_matches
        
        available_commands = list(self.commands.keys())
        
        # Use difflib for fuzzy matching
        matches = get_close_matches(
            unknown_cmd,
            available_commands,
            n=max_suggestions,
            cutoff=0.6  # 60% similarity threshold
        )
        
        return matches


@click.group(cls=BengalGroup)
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main() -> None:
    """
    🐯 Bengal SSG - A high-performance static site generator.
    
    Fast & fierce static site generation with personality!
    """
    # Install rich traceback handler for beautiful error messages (unless in CI)
    import os
    if not os.getenv('CI'):
        try:
            from rich.traceback import install
            from bengal.utils.rich_console import get_console
            install(
                console=get_console(),
                show_locals=True,
                suppress=[click],  # Don't show click internals
                max_frames=20,
                width=None,  # Auto-detect terminal width
            )
        except ImportError:
            # Rich not available, skip
            pass


def _should_regenerate_autodoc(autodoc_flag: bool, config_path: Path, root_path: Path, quiet: bool) -> bool:
    """
    Determine if autodoc should be regenerated based on:
    1. CLI flag (highest priority)
    2. Config setting
    3. Timestamp checking (if neither flag nor config explicitly disable)
    """
    # CLI flag takes precedence
    if autodoc_flag is not None:
        return autodoc_flag
    
    # Check config
    from bengal.autodoc.config import load_autodoc_config
    config = load_autodoc_config(config_path)
    build_config = config.get('build', {})
    
    # Check if auto_regenerate_autodoc is explicitly set in config
    auto_regen = build_config.get('auto_regenerate_autodoc', False)
    
    if not auto_regen:
        return False
    
    # If enabled in config, check timestamps to see if regeneration is needed
    needs_regen = _check_autodoc_needs_regeneration(config, root_path, quiet)
    return needs_regen


def _check_autodoc_needs_regeneration(autodoc_config: dict, root_path: Path, quiet: bool) -> bool:
    """
    Check if source files are newer than generated docs.
    Returns True if regeneration is needed.
    """
    import os
    from pathlib import Path
    
    python_config = autodoc_config.get('python', {})
    cli_config = autodoc_config.get('cli', {})
    
    needs_regen = False
    
    # Check Python docs
    if python_config.get('enabled', True):
        source_dirs = python_config.get('source_dirs', ['.'])
        output_dir = root_path / python_config.get('output_dir', 'content/api')
        
        if output_dir.exists():
            # Get newest source file
            newest_source = 0
            for source_dir in source_dirs:
                source_path = root_path / source_dir
                if source_path.exists():
                    for py_file in source_path.rglob('*.py'):
                        if '__pycache__' not in str(py_file):
                            mtime = os.path.getmtime(py_file)
                            newest_source = max(newest_source, mtime)
            
            # Get oldest generated file
            oldest_output = float('inf')
            for md_file in output_dir.rglob('*.md'):
                mtime = os.path.getmtime(md_file)
                oldest_output = min(oldest_output, mtime)
            
            if newest_source > oldest_output:
                if not quiet:
                    click.echo(click.style("📝 Python source files changed, regenerating API docs...", fg='yellow'))
                needs_regen = True
        else:
            # Output doesn't exist, need to generate
            if not quiet:
                click.echo(click.style("📝 API docs not found, generating...", fg='yellow'))
            needs_regen = True
    
    # Check CLI docs
    if cli_config.get('enabled', False) and cli_config.get('app_module'):
        output_dir = root_path / cli_config.get('output_dir', 'content/cli')
        
        if not output_dir.exists() or not list(output_dir.rglob('*.md')):
            if not quiet:
                click.echo(click.style("📝 CLI docs not found, generating...", fg='yellow'))
            needs_regen = True
    
    return needs_regen


def _run_autodoc_before_build(config_path: Path, root_path: Path, quiet: bool) -> None:
    """Run autodoc generation before build."""
    from bengal.autodoc.config import load_autodoc_config
    
    if not quiet:
        click.echo()
        click.echo(click.style("📚 Regenerating documentation...", fg='cyan', bold=True))
        click.echo()
    
    autodoc_config = load_autodoc_config(config_path)
    python_config = autodoc_config.get('python', {})
    cli_config = autodoc_config.get('cli', {})
    
    # Determine what to generate
    generate_python = python_config.get('enabled', True)
    generate_cli = cli_config.get('enabled', False) and cli_config.get('app_module')
    
    # Generate Python docs
    if generate_python:
        try:
            _generate_python_docs(
                source=tuple(python_config.get('source_dirs', ['.'])),
                output=python_config.get('output_dir', 'content/api'),
                clean=False,
                parallel=True,
                verbose=False,
                stats=False,
                python_config=python_config
            )
        except Exception as e:
            if not quiet:
                click.echo(click.style(f"⚠️  Python autodoc failed: {e}", fg='yellow'))
                click.echo(click.style("Continuing with build...", fg='yellow'))
    
    # Generate CLI docs
    if generate_cli:
        try:
            _generate_cli_docs(
                app=cli_config.get('app_module'),
                framework=cli_config.get('framework', 'click'),
                output=cli_config.get('output_dir', 'content/cli'),
                include_hidden=cli_config.get('include_hidden', False),
                clean=False,
                verbose=False,
                cli_config=cli_config
            )
        except Exception as e:
            if not quiet:
                click.echo(click.style(f"⚠️  CLI autodoc failed: {e}", fg='yellow'))
                click.echo(click.style("Continuing with build...", fg='yellow'))
    
    if not quiet:
        click.echo()


@main.command()
@click.option('--parallel/--no-parallel', default=True, help='Enable parallel processing for faster builds (default: enabled)')
@click.option('--incremental', is_flag=True, help='Perform incremental build (only rebuild changed files)')
@click.option('--memory-optimized', is_flag=True, help='Use streaming build for memory efficiency (best for 5K+ pages)')
@click.option('--profile', type=click.Choice(['writer', 'theme-dev', 'dev']), 
              help='Build profile: writer (fast/clean), theme-dev (templates), dev (full debug)')
@click.option('--perf-profile', type=click.Path(), help='Enable performance profiling and save to file (e.g., profile.stats)')
@click.option('--theme-dev', 'use_theme_dev', is_flag=True, help='Use theme developer profile (shorthand for --profile theme-dev)')
@click.option('--dev', 'use_dev', is_flag=True, help='Use developer profile with full observability (shorthand for --profile dev)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information (maps to theme-dev profile)')
@click.option('--strict', is_flag=True, help='Fail on template errors (recommended for CI/CD)')
@click.option('--debug', is_flag=True, help='Show debug output and full tracebacks (maps to dev profile)')
@click.option('--validate', is_flag=True, help='Validate templates before building (catch errors early)')
@click.option('--autodoc/--no-autodoc', default=None, help='Force regenerate autodoc before building (overrides config)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output - only show errors and summary')
@click.option('--full-output', is_flag=True, help='Show full traditional output instead of live progress (useful for debugging)')
@click.option('--log-file', type=click.Path(), help='Write detailed logs to file (default: .bengal-build.log)')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, memory_optimized: bool, profile: str, perf_profile: str, use_theme_dev: bool, use_dev: bool, verbose: bool, strict: bool, debug: bool, validate: bool, autodoc: bool, config: str, quiet: bool, full_output: bool, log_file: str, source: str) -> None:
    """
    🔨 Build the static site.
    
    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.
    """
    # Import profile system
    from bengal.utils.profile import BuildProfile, set_current_profile
    
    # Validate conflicting flags
    if quiet and verbose:
        raise click.UsageError("--quiet and --verbose cannot be used together")
    if quiet and (use_dev or use_theme_dev):
        raise click.UsageError("--quiet cannot be used with --dev or --theme-dev")
    
    # New validations for build flag combinations
    if memory_optimized and perf_profile:
        raise click.UsageError("--memory-optimized and --perf-profile cannot be used together (profiler doesn't work with streaming)")
    
    if memory_optimized and incremental:
        click.echo(click.style("⚠️  Warning: --memory-optimized with --incremental may not fully utilize cache", fg='yellow'))
        click.echo(click.style("   Streaming build processes pages in batches, limiting incremental benefits.\n", fg='yellow'))
    
    # Determine build profile with proper precedence
    build_profile = BuildProfile.from_cli_args(
        profile=profile,
        dev=use_dev,
        theme_dev=use_theme_dev,
        verbose=verbose,
        debug=debug
    )
    
    # Set global profile for helper functions
    set_current_profile(build_profile)
    
    # Get profile configuration
    profile_config = build_profile.get_config()
    
    # Configure logging based on profile
    if build_profile == BuildProfile.DEVELOPER:
        log_level = LogLevel.DEBUG
    elif build_profile == BuildProfile.THEME_DEV:
        log_level = LogLevel.INFO
    else:  # WRITER
        log_level = LogLevel.WARNING
    
    # Determine log file path
    if log_file:
        log_path = Path(log_file)
    else:
        log_path = Path(source) / '.bengal-build.log'
    
    configure_logging(
        level=log_level,
        log_file=log_path,
        verbose=profile_config['verbose_build_stats'],
        track_memory=profile_config['track_memory']
    )
    
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create and build site
        site = Site.from_config(root_path, config_path)
        
        # Override config with CLI flags
        if strict:
            site.config["strict_mode"] = True
        if debug:
            site.config["debug"] = True
        
        # Handle autodoc regeneration
        should_regenerate_autodoc = _should_regenerate_autodoc(
            autodoc_flag=autodoc,
            config_path=config_path,
            root_path=root_path,
            quiet=quiet
        )
        
        if should_regenerate_autodoc:
            _run_autodoc_before_build(config_path=config_path, root_path=root_path, quiet=quiet)
        
        # Validate templates if requested
        if validate:
            from bengal.rendering.validator import validate_templates
            from bengal.rendering.template_engine import TemplateEngine
            
            template_engine = TemplateEngine(site)
            error_count = validate_templates(template_engine)
            
            if error_count > 0:
                click.echo(click.style(f"\n❌ Validation failed with {error_count} error(s).", 
                                      fg='red', bold=True))
                click.echo(click.style("Fix errors above, then run 'bengal build'", fg='yellow'))
                raise click.Abort()
            
            click.echo()  # Blank line before build
        
        # Determine if we should use rich status spinner
        try:
            from bengal.utils.rich_console import get_console, should_use_rich
            use_rich_spinner = should_use_rich() and not quiet
        except ImportError:
            use_rich_spinner = False
        
        if use_rich_spinner:
            # Show rich animated indicator
            console = get_console()
            console.print()
            console.print("    [bengal]ᓚᘏᗢ[/bengal]  [bold]Building your site...[/bold]")
            console.print()
        else:
            # Traditional static indicator
            show_building_indicator("Building site")
        
        # Validate templates if requested
        if validate:
            click.echo(click.style("\n🔍 Validating templates...", fg='cyan'))
            from bengal.rendering.validator import TemplateValidator
            validator = TemplateValidator(site)
            errors = validator.validate_all()
            
            if errors:
                click.echo(click.style(f"\n❌ Found {len(errors)} template error(s):", fg='red', bold=True))
                for error in errors[:5]:  # Show first 5
                    click.echo(f"  • {error}")
                if len(errors) > 5:
                    click.echo(f"  ... and {len(errors) - 5} more")
                raise click.Abort()
            else:
                click.echo(click.style("✓ All templates valid\n", fg='green'))
        
        # Enable performance profiling if requested
        if perf_profile:
            import cProfile
            import pstats
            from io import StringIO
            
            profiler = cProfile.Profile()
            profiler.enable()
            
            # Pass profile to build
            stats = site.build(
                parallel=parallel, 
                incremental=incremental, 
                verbose=profile_config['verbose_build_stats'],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output
            )
            
            profiler.disable()
            
            # Save profiling data
            perf_profile_path = Path(perf_profile)
            profiler.dump_stats(str(perf_profile_path))
            
            # Display summary
            if not quiet:
                s = StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
                ps.print_stats(20)  # Top 20 functions
                
                click.echo()
                click.echo(click.style("📊 Performance Profile (Top 20 by cumulative time):", 
                                      fg='cyan', bold=True))
                click.echo(s.getvalue())
                click.echo(click.style(f"Full profile saved to: {perf_profile_path}", 
                                      fg='green'))
                click.echo(click.style("Analyze with: python -m pstats " + str(perf_profile_path), 
                                      fg='yellow'))
        else:
            # Pass profile to build
            stats = site.build(
                parallel=parallel, 
                incremental=incremental, 
                verbose=profile_config['verbose_build_stats'],
                quiet=quiet,
                profile=build_profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output
            )
        
        # Display template errors first if we're in theme-dev or dev mode
        if stats.template_errors and build_profile != BuildProfile.WRITER:
            from bengal.utils.build_stats import display_template_errors
            display_template_errors(stats)
        
        # Store output directory in stats for display
        stats.output_dir = str(site.output_dir)
        
        # Display build stats based on profile (unless quiet mode)
        if not quiet:
            if build_profile == BuildProfile.WRITER:
                # Simple, clean output for writers
                from bengal.utils.build_stats import display_simple_build_stats
                display_simple_build_stats(stats, output_dir=str(site.output_dir))
            elif build_profile == BuildProfile.DEVELOPER:
                # Rich intelligent summary with performance insights (Phase 2)
                from bengal.utils.build_summary import display_build_summary
                from bengal.utils.rich_console import detect_environment
                environment = detect_environment()
                display_build_summary(stats, environment=environment)
            else:
                # Theme-dev: Use existing detailed display
                display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
        else:
            click.echo(click.style("✅ Build complete!", fg='green', bold=True))
            click.echo(click.style(f"   ↪ {site.output_dir}", fg='cyan'))
        
        # Print phase timing summary in dev mode only
        if build_profile == BuildProfile.DEVELOPER and not quiet:
            print_all_summaries()
        
    except Exception as e:
        show_error(f"Build failed: {e}", show_art=True)
        if debug:
            raise
        raise click.Abort()
    finally:
        # Always close log file handles
        close_all_loggers()


@main.command()
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
    from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers
    
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
                    graph = KnowledgeGraph(site)
                    graph.build()
            else:
                # Fallback to simple messages
                click.echo("🔍 Discovering site content...")
                from bengal.orchestration.content import ContentOrchestrator
                content_orch = ContentOrchestrator(site)
                content_orch.discover()
                
                click.echo(f"📊 Analyzing {len(site.pages)} pages...")
                graph = KnowledgeGraph(site)
                graph.build()
        except ImportError:
            # Rich not available, use simple messages
            click.echo("🔍 Discovering site content...")
            from bengal.orchestration.content import ContentOrchestrator
            content_orch = ContentOrchestrator(site)
            content_orch.discover()
            
            click.echo(f"📊 Analyzing {len(site.pages)} pages...")
            graph = KnowledgeGraph(site)
            graph.build()
        
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
                            incoming = len(graph.incoming_refs.get(page, []))
                            outgoing = len(graph.outgoing_refs.get(page, []))
                            
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
            stats = graph.format_stats()
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
                visualizer = GraphVisualizer(site, graph)
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


@main.command()
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
    from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers
    import json
    
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
                    graph = KnowledgeGraph(site)
                    graph.build()
                    
                    status.update(f"[bold green]Computing PageRank (damping={damping})...")
                    results = graph.compute_pagerank(damping=damping)
            else:
                # Fallback to simple messages
                click.echo("🔍 Discovering site content...")
                from bengal.orchestration.content import ContentOrchestrator
                content_orch = ContentOrchestrator(site)
                content_orch.discover()
                
                click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
                graph = KnowledgeGraph(site)
                graph.build()
                
                click.echo(f"🏆 Computing PageRank (damping={damping})...")
                results = graph.compute_pagerank(damping=damping)
        except ImportError:
            # Rich not available, use simple messages
            click.echo("🔍 Discovering site content...")
            from bengal.orchestration.content import ContentOrchestrator
            content_orch = ContentOrchestrator(site)
            content_orch.discover()
            
            click.echo(f"📊 Building knowledge graph from {len(site.pages)} pages...")
            graph = KnowledgeGraph(site)
            graph.build()
            
            click.echo(f"🏆 Computing PageRank (damping={damping})...")
            results = graph.compute_pagerank(damping=damping)
        
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
                        'incoming_refs': graph.incoming_refs.get(page, 0),
                        'outgoing_refs': len(graph.outgoing_refs.get(page, set()))
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
                incoming = graph.incoming_refs.get(page, 0)
                outgoing = len(graph.outgoing_refs.get(page, set()))
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
                incoming = graph.incoming_refs.get(page, 0)
                outgoing = len(graph.outgoing_refs.get(page, set()))
                
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


@main.command()
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
    from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers
    import json
    
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
        graph = KnowledgeGraph(site)
        graph.build()
        
        # Detect communities
        click.echo(f"🔍 Detecting communities (resolution={resolution})...")
        results = graph.detect_communities(resolution=resolution, random_seed=seed)
        
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
                    (page, graph.incoming_refs.get(page, 0))
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
                    (page, graph.incoming_refs.get(page, 0))
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
                    (page, graph.incoming_refs.get(page, 0))
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


@main.command()
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
    from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers
    import json
    
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
        graph = KnowledgeGraph(site)
        graph.build()
        
        # Analyze paths
        click.echo(f"🌉 Analyzing navigation paths...")
        results = graph.analyze_paths()
        
        # Output based on format
        if format == 'json':
            # Export as JSON
            data = {
                'avg_path_length': results.avg_path_length,
                'diameter': results.diameter,
                'total_pages': len(results.betweenness_centrality)
            }
            
            if metric in ['betweenness', 'both']:
                bridges = results.get_top_bridges(top_n)
                data['top_bridges'] = [
                    {
                        'title': page.title,
                        'url': getattr(page, 'url_path', str(page.source_path)),
                        'betweenness': score,
                        'incoming_refs': graph.incoming_refs.get(page, 0)
                    }
                    for page, score in bridges
                ]
            
            if metric in ['closeness', 'both']:
                accessible = results.get_most_accessible(top_n)
                data['most_accessible'] = [
                    {
                        'title': page.title,
                        'url': getattr(page, 'url_path', str(page.source_path)),
                        'closeness': score,
                        'outgoing_refs': len(graph.outgoing_refs.get(page, set()))
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
                bridges = results.get_top_bridges(top_n)
                for i, (page, score) in enumerate(bridges, 1):
                    incoming = graph.incoming_refs.get(page, 0)
                    outgoing = len(graph.outgoing_refs.get(page, set()))
                    click.echo(f"{i:3d}. {page.title}")
                    click.echo(f"     Betweenness: {score:.6f} | {incoming} in, {outgoing} out")
            
            if metric in ['closeness', 'both']:
                click.echo(f"\n🎯 Most Accessible Pages (Closeness Centrality)")
                click.echo("-" * 60)
                accessible = results.get_most_accessible(top_n)
                for i, (page, score) in enumerate(accessible, 1):
                    outgoing = len(graph.outgoing_refs.get(page, set()))
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
                
                bridges = results.get_top_bridges(top_n)
                for i, (page, score) in enumerate(bridges, 1):
                    title = page.title
                    if len(title) > 48:
                        title = title[:45] + "..."
                    
                    incoming = graph.incoming_refs.get(page, 0)
                    outgoing = len(graph.outgoing_refs.get(page, set()))
                    
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
                    
                    outgoing = len(graph.outgoing_refs.get(page, set()))
                    
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


@main.command()
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
    from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers
    import json
    
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
        graph = KnowledgeGraph(site)
        graph.build()
        
        click.echo(f"💡 Generating link suggestions...")
        results = graph.suggest_links(min_score=min_score)
        
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


@main.command()
@click.option('--host', default='localhost', help='Server host address')
@click.option('--port', '-p', default=5173, type=int, help='Server port number')
@click.option('--watch/--no-watch', default=True, help='Watch for file changes and rebuild (default: enabled)')
@click.option('--auto-port/--no-auto-port', default=True, help='Find available port if specified port is taken (default: enabled)')
@click.option('--open', '-o', 'open_browser', is_flag=True, help='Open browser automatically after server starts')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def serve(host: str, port: int, watch: bool, auto_port: bool, open_browser: bool, config: str, source: str) -> None:
    """
    🚀 Start development server with hot reload.
    
    Watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.
    """
    try:
        # Welcome banner removed for consistency with build command
        # The "Building your site..." header is sufficient
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site
        site = Site.from_config(root_path, config_path)
        
        # Enable strict mode in development (fail fast on errors)
        site.config["strict_mode"] = True
        
        # Start server (this blocks)
        site.serve(host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser)
        
    except Exception as e:
        show_error(f"Server failed: {e}", show_art=True)
        raise click.Abort()


@main.command()
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def clean(force: bool, config: str, source: str) -> None:
    """
    🧹 Clean the output directory.
    
    Removes all generated files from the output directory.
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site
        site = Site.from_config(root_path, config_path)
        
        # Show header (consistent with all other commands)
        from bengal.utils.cli_output import CLIOutput
        cli = CLIOutput()
        cli.blank()
        cli.header("Cleaning output directory...")
        cli.info(f"   ↪ {site.output_dir}")
        cli.blank()
        
        # Confirm before cleaning unless --force
        if not force:
            # Interactive mode: ask for confirmation (with warning icon for destructive operation)
            try:
                from bengal.utils.rich_console import get_console, should_use_rich
                from rich.prompt import Confirm
                
                if should_use_rich():
                    console = get_console()
                    console.print("[yellow bold]⚠️  Delete all files?[/yellow bold]")
                    if not Confirm.ask("Proceed", console=console, default=False):
                        console.print("[yellow]Cancelled[/yellow]")
                        return
                else:
                    # Fallback to click
                    prompt = click.style("⚠️  Delete all files?", fg='yellow', bold=True)
                    if not click.confirm(prompt, default=False):
                        click.echo(click.style("Cancelled", fg='yellow'))
                        return
            except ImportError:
                # Rich not available, use click
                prompt = click.style("⚠️  Delete all files?", fg='yellow', bold=True)
                if not click.confirm(prompt, default=False):
                    click.echo(click.style("Cancelled", fg='yellow'))
                    return
        
        # Clean
        site.clean()
        
        # Show success
        cli.blank()
        cli.success("Clean complete!", icon="✓")
        cli.blank()
        
    except Exception as e:
        show_error(f"Clean failed: {e}", show_art=False)
        raise click.Abort()


@main.command()
@click.option('--force', '-f', is_flag=True, help='Kill process without confirmation')
@click.option('--port', '-p', type=int, help='Also check if process is using this port')
@click.argument('source', type=click.Path(exists=True), default='.')
def cleanup(force: bool, port: int, source: str) -> None:
    """
    🔧 Clean up stale Bengal server processes.
    
    Finds and terminates any stale 'bengal serve' processes that may be
    holding ports or preventing new servers from starting.
    
    This is useful if a previous server didn't shut down cleanly.
    """
    try:
        from bengal.server.pid_manager import PIDManager
        
        root_path = Path(source).resolve()
        pid_file = PIDManager.get_pid_file(root_path)
        
        # Check for stale process
        stale_pid = PIDManager.check_stale_pid(pid_file)
        
        if not stale_pid:
            click.echo(click.style("✅ No stale processes found", fg='green'))
            
            # If port specified, check if something else is using it
            if port:
                port_pid = PIDManager.get_process_on_port(port)
                if port_pid:
                    click.echo(click.style(f"\n⚠️  However, port {port} is in use by PID {port_pid}", fg='yellow'))
                    if PIDManager.is_bengal_process(port_pid):
                        click.echo(f"   This appears to be a Bengal process not tracked by PID file")
                        if not force and not click.confirm(f"  Kill process {port_pid}?"):
                            click.echo("Cancelled")
                            return
                        if PIDManager.kill_stale_process(port_pid):
                            click.echo(click.style(f"✅ Process {port_pid} terminated", fg='green'))
                        else:
                            click.echo(click.style(f"❌ Failed to kill process {port_pid}", fg='red'))
                            raise click.Abort()
                    else:
                        click.echo(f"   This is not a Bengal process")
                        click.echo(f"   Try manually: kill {port_pid}")
            return
        
        # Found stale process
        click.echo(click.style(f"⚠️  Found stale Bengal server process", fg='yellow'))
        click.echo(f"   PID: {stale_pid}")
        
        # Check if it's holding a port
        if port:
            port_pid = PIDManager.get_process_on_port(port)
            if port_pid == stale_pid:
                click.echo(f"   Holding port: {port}")
        
        # Confirm unless --force
        if not force:
            try:
                from bengal.utils.rich_console import get_console, should_use_rich
                from rich.prompt import Confirm
                
                if should_use_rich():
                    console = get_console()
                    if not Confirm.ask("  Kill this process", console=console, default=False):
                        console.print("Cancelled")
                        return
                else:
                    if not click.confirm("  Kill this process?"):
                        click.echo("Cancelled")
                        return
            except ImportError:
                if not click.confirm("  Kill this process?"):
                    click.echo("Cancelled")
                    return
        
        # Kill the process
        if PIDManager.kill_stale_process(stale_pid):
            click.echo(click.style("✅ Stale process terminated successfully", fg='green'))
        else:
            click.echo(click.style(f"❌ Failed to terminate process", fg='red'))
            click.echo(f"   Try manually: kill {stale_pid}")
            raise click.Abort()
            
    except ImportError:
        show_error("Cleanup command requires server dependencies", show_art=False)
        raise click.Abort()
    except Exception as e:
        show_error(f"Cleanup failed: {e}", show_art=False)
        raise click.Abort()


@main.group()
def new() -> None:
    """
    ✨ Create new site, page, or section.
    """
    pass


@new.command()
@click.argument('name')
@click.option('--theme', default='default', help='Theme to use')
def site(name: str, theme: str) -> None:
    """
    🏗️  Create a new Bengal site.
    """
    try:
        site_path = Path(name)
        
        if site_path.exists():
            show_error(f"Directory {name} already exists!", show_art=False)
            raise click.Abort()
        
        click.echo(click.style(f"\n🏗️  Creating new Bengal site: {name}", fg='cyan', bold=True))
        
        # Create directory structure
        site_path.mkdir(parents=True)
        (site_path / 'content').mkdir()
        (site_path / 'assets' / 'css').mkdir(parents=True)
        (site_path / 'assets' / 'js').mkdir()
        (site_path / 'assets' / 'images').mkdir()
        (site_path / 'templates').mkdir()
        
        click.echo(click.style("   ├─ ", fg='cyan') + "Created directory structure")
        
        # Create config file
        config_content = f"""[site]
title = "{name}"
baseurl = ""
theme = "{theme}"

[build]
output_dir = "public"
parallel = true

[assets]
minify = true
fingerprint = true
"""
        # Write config atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text
        atomic_write_text(site_path / 'bengal.toml', config_content)
        click.echo(click.style("   ├─ ", fg='cyan') + "Created bengal.toml")
        
        # Create sample index page
        index_content = """---
title: Welcome to Bengal
---

# Welcome to Bengal SSG

This is your new Bengal static site. Start editing this file to begin!

## Features

- Fast builds with parallel processing
- Modular architecture
- Asset optimization
- SEO friendly

## Next Steps

1. Edit `content/index.md` (this file)
2. Create new pages with `bengal new page <name>`
3. Build your site with `bengal build`
4. Preview with `bengal serve`
"""
        # Write index page atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text
        atomic_write_text(site_path / 'content' / 'index.md', index_content)
        click.echo(click.style("   └─ ", fg='cyan') + "Created sample index page")
        
        click.echo(click.style(f"\n✅ Site created successfully!", fg='green', bold=True))
        click.echo(click.style("\n📚 Next steps:", fg='cyan', bold=True))
        click.echo(click.style("   ├─ ", fg='cyan') + f"cd {name}")
        click.echo(click.style("   └─ ", fg='cyan') + "bengal serve")
        click.echo()
        
    except Exception as e:
        show_error(f"Failed to create site: {e}", show_art=False)
        raise click.Abort()


@new.command()
@click.argument('name')
@click.option('--section', default='', help='Section to create page in')
def page(name: str, section: str) -> None:
    """
    📄 Create a new page.
    """
    try:
        # Ensure we're in a Bengal site
        content_dir = Path('content')
        if not content_dir.exists():
            show_error("Not in a Bengal site directory!", show_art=False)
            raise click.Abort()
        
        # Determine page path
        if section:
            page_dir = content_dir / section
            page_dir.mkdir(parents=True, exist_ok=True)
        else:
            page_dir = content_dir
        
        # Create page file
        page_path = page_dir / f"{name}.md"
        
        if page_path.exists():
            show_error(f"Page {page_path} already exists!", show_art=False)
            raise click.Abort()
        
        # Create page content with current timestamp
        page_content = f"""---
title: {name.replace('-', ' ').title()}
date: {datetime.now().isoformat()}
---

# {name.replace('-', ' ').title()}

Your content goes here.
"""
        # Write new page atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text
        atomic_write_text(page_path, page_content)
        
        click.echo(click.style(f"\n✨ Created new page: ", fg='cyan') + 
                  click.style(str(page_path), fg='green', bold=True))
        click.echo()
        
    except Exception as e:
        show_error(f"Failed to create page: {e}", show_art=False)
        raise click.Abort()


@main.command()
@click.option('--source', '-s', multiple=True, type=click.Path(exists=True), help='Source directory to document (can specify multiple)')
@click.option('--output', '-o', type=click.Path(), help='Output directory for generated docs (default: from config or content/api)')
@click.option('--clean', is_flag=True, help='Clean output directory before generating')
@click.option('--parallel/--no-parallel', default=True, help='Use parallel processing (default: enabled)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--stats', is_flag=True, help='Show performance statistics')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--python-only', is_flag=True, help='Only generate Python API docs (skip CLI docs)')
@click.option('--cli-only', is_flag=True, help='Only generate CLI docs (skip Python API docs)')
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str, python_only: bool, cli_only: bool) -> None:
    """
    📚 Generate comprehensive API documentation (Python + CLI).
    
    Automatically generates both Python API docs and CLI docs based on
    your bengal.toml configuration. Use --python-only or --cli-only to
    generate specific types.
    
    Examples:
        bengal autodoc                    # Generate all configured docs
        bengal autodoc --python-only      # Python API docs only
        bengal autodoc --cli-only         # CLI docs only
        bengal autodoc --source src       # Override Python source
    """
    import time
    
    try:
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        python_config = autodoc_config.get('python', {})
        cli_config = autodoc_config.get('cli', {})
        
        # Determine what to generate
        generate_python = not cli_only and (python_only or python_config.get('enabled', True))
        generate_cli = not python_only and (cli_only or (cli_config.get('enabled', False) and cli_config.get('app_module')))
        
        if not generate_python and not generate_cli:
            click.echo(click.style("⚠️  Nothing to generate", fg='yellow'))
            click.echo()
            click.echo("Either:")
            click.echo("  • Enable Python docs in bengal.toml: [autodoc.python] enabled = true")
            click.echo("  • Enable CLI docs in bengal.toml: [autodoc.cli] enabled = true, app_module = '...'")
            click.echo("  • Use --python-only or --cli-only flags")
            return
        
        click.echo()
        click.echo(click.style("📚 Bengal Autodoc", fg='cyan', bold=True))
        click.echo()
        
        total_start = time.time()
        
        # ========== PYTHON API DOCUMENTATION ==========
        if generate_python:
            _generate_python_docs(
                source=source,
                output=output,
                clean=clean,
                parallel=parallel,
                verbose=verbose,
                stats=stats,
                python_config=python_config
            )
        
        # ========== CLI DOCUMENTATION ==========
        if generate_cli:
            if generate_python:
                click.echo()
                click.echo(click.style("─" * 60, fg='blue'))
                click.echo()
            
            _generate_cli_docs(
                app=cli_config.get('app_module'),
                framework=cli_config.get('framework', 'click'),
                output=cli_config.get('output_dir', 'content/cli'),
                include_hidden=cli_config.get('include_hidden', False),
                clean=clean,
                verbose=verbose,
                cli_config=cli_config
            )
        
        # Summary
        if generate_python and generate_cli:
            total_time = time.time() - total_start
            click.echo()
            click.echo(click.style("─" * 60, fg='blue'))
            click.echo()
            click.echo(click.style(f"✅ All documentation generated in {total_time:.2f}s", fg='green', bold=True))
            click.echo()
        
    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("⚠️  Cancelled by user", fg='yellow'))
        raise click.Abort()
    except Exception as e:
        click.echo()
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


def _generate_python_docs(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, python_config: dict) -> None:
    """Generate Python API documentation."""
    import time
    
    click.echo(click.style("🐍 Python API Documentation", fg='cyan', bold=True))
    click.echo()
    
    # Use CLI args or fall back to config
    if source:
        sources = list(source)
    else:
        sources = python_config.get('source_dirs', ['.'])
    
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path(python_config.get('output_dir', 'content/api'))
    
    # Get exclusion patterns from config
    exclude_patterns = python_config.get('exclude', [])
    
    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract documentation
    click.echo(click.style("🔍 Extracting Python API documentation...", fg='blue'))
    start_time = time.time()
    
    extractor = PythonExtractor(exclude_patterns=exclude_patterns)
    all_elements = []
    
    for source_path in sources:
        source_path = Path(source_path)
        if verbose:
            click.echo(f"   📂 Scanning {source_path}")
        
        elements = extractor.extract(source_path)
        all_elements.extend(elements)
        
        if verbose:
            module_count = len(elements)
            class_count = sum(len([c for c in e.children if c.element_type == 'class']) for e in elements)
            func_count = sum(len([c for c in e.children if c.element_type == 'function']) for e in elements)
            click.echo(f"   ✓ Found {module_count} modules, {class_count} classes, {func_count} functions")
    
    extraction_time = time.time() - start_time
    
    if not all_elements:
        click.echo(click.style("⚠️  No Python modules found", fg='yellow'))
        return
    
    click.echo(click.style(f"   ✓ Extracted {len(all_elements)} modules in {extraction_time:.2f}s", fg='green'))
    
    # Generate documentation
    from bengal.utils.cli_output import CLIOutput
    cli = CLIOutput()
    cli.blank()
    cli.header("Generating documentation...")
    gen_start = time.time()
    
    generator = DocumentationGenerator(extractor, {'python': python_config})
    generated = generator.generate_all(all_elements, output_dir, parallel=parallel)
    
    generation_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    # Success message
    click.echo()
    click.echo(click.style(f"✅ Generated {len(generated)} documentation pages", fg='green', bold=True))
    click.echo(click.style(f"   📁 Output: {output_dir}", fg='cyan'))
    
    if stats:
        click.echo()
        click.echo(click.style("📊 Performance Statistics:", fg='blue'))
        click.echo(f"   Extraction time:  {extraction_time:.2f}s")
        click.echo(f"   Generation time:  {generation_time:.2f}s")
        click.echo(f"   Total time:       {total_time:.2f}s")
        click.echo(f"   Throughput:       {len(generated) / total_time:.1f} pages/sec")
    
    click.echo()
    click.echo(click.style("💡 Next steps:", fg='yellow'))
    click.echo(f"   • View docs: ls {output_dir}")
    click.echo(f"   • Build site: bengal build")
    click.echo()


def _generate_cli_docs(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, cli_config: dict) -> None:
    """Generate CLI documentation."""
    import time
    import importlib
    
    click.echo(click.style("⌨️  CLI Documentation", fg='cyan', bold=True))
    click.echo()
    
    output_dir = Path(output)
    
    # Clean output directory if requested
    if clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Import the CLI app
    click.echo(click.style(f"🔍 Loading CLI app from {app}...", fg='blue'))
    
    try:
        module_path, attr_name = app.split(':')
        module = importlib.import_module(module_path)
        cli_app = getattr(module, attr_name)
    except Exception as e:
        click.echo(click.style(f"❌ Failed to load app: {e}", fg='red', bold=True))
        click.echo()
        click.echo("Make sure the module path is correct:")
        click.echo(f"  • Module: {app.split(':')[0]}")
        click.echo(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
        click.echo()
        raise click.Abort()
    
    # Extract documentation
    click.echo(click.style(f"📝 Extracting CLI documentation...", fg='blue'))
    start_time = time.time()
    
    extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
    elements = extractor.extract(cli_app)
    
    extraction_time = time.time() - start_time
    
    # Count commands
    command_count = 0
    option_count = 0
    for element in elements:
        if element.element_type == 'command-group':
            command_count = len(element.children)
            for cmd in element.children:
                option_count += cmd.metadata.get('option_count', 0)
    
    click.echo(click.style(f"   ✓ Extracted {command_count} commands, {option_count} options", fg='green'))
    
    if verbose:
        click.echo()
        click.echo("Commands found:")
        for element in elements:
            if element.element_type == 'command-group':
                for cmd in element.children:
                    click.echo(f"  • {cmd.name}")
    
    # Generate documentation
    from bengal.utils.cli_output import CLIOutput
    cli = CLIOutput()
    cli.blank()
    cli.header("Generating documentation...")
    gen_start = time.time()
    
    generator = DocumentationGenerator(extractor, {'cli': cli_config})
    generated_files = generator.generate_all(elements, output_dir)
    
    gen_time = time.time() - gen_start
    total_time = time.time() - start_time
    
    # Display results
    click.echo()
    click.echo(click.style("✅ CLI Documentation Generated!", fg='green', bold=True))
    click.echo()
    click.echo(click.style("   📊 Statistics:", fg='blue'))
    click.echo(f"      • Commands: {command_count}")
    click.echo(f"      • Options:  {option_count}")
    click.echo(f"      • Pages:    {len(generated_files)}")
    click.echo()
    click.echo(click.style("   ⚡ Performance:", fg='blue'))
    click.echo(f"      • Extraction: {extraction_time:.3f}s")
    click.echo(f"      • Generation: {gen_time:.3f}s")
    click.echo(f"      • Total:      {total_time:.3f}s")
    click.echo()
    click.echo(click.style(f"   📂 Output: {output_dir}", fg='cyan'))
    click.echo()
    click.echo(click.style("💡 Next steps:", fg='yellow'))
    click.echo(f"   • View docs: ls {output_dir}")
    click.echo(f"   • Build site: bengal build")
    click.echo()


@main.command(name='autodoc-cli')
@click.option('--app', '-a', help='CLI app module (e.g., bengal.cli:main)')
@click.option('--framework', '-f', type=click.Choice(['click', 'argparse', 'typer']), default='click', help='CLI framework (default: click)')
@click.option('--output', '-o', type=click.Path(), help='Output directory for generated docs (default: content/cli)')
@click.option('--include-hidden', is_flag=True, help='Include hidden commands')
@click.option('--clean', is_flag=True, help='Clean output directory before generating')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
def autodoc_cli(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, config: str) -> None:
    """
    ⌨️  Generate CLI documentation from Click/argparse/typer apps.
    
    Extracts documentation from command-line interfaces to create
    comprehensive command reference documentation.
    
    Example:
        bengal autodoc-cli --app bengal.cli:main --output content/cli
    """
    import time
    import importlib
    
    try:
        click.echo()
        click.echo(click.style("⌨️  Bengal CLI Autodoc", fg='cyan', bold=True))
        click.echo()
        
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        cli_config = autodoc_config.get('cli', {})
        
        # Use CLI args or fall back to config
        if not app:
            app = cli_config.get('app_module')
        
        if not app:
            click.echo(click.style("❌ Error: No CLI app specified", fg='red', bold=True))
            click.echo()
            click.echo("Please specify the app module either:")
            click.echo("  • Via command line: --app bengal.cli:main")
            click.echo("  • Via config file: [autodoc.cli] app_module = 'bengal.cli:main'")
            click.echo()
            raise click.Abort()
        
        if not framework:
            framework = cli_config.get('framework', 'click')
        
        if output:
            output_dir = Path(output)
        else:
            output_dir = Path(cli_config.get('output_dir', 'content/cli'))
        
        if not include_hidden:
            include_hidden = cli_config.get('include_hidden', False)
        
        # Clean output directory if requested
        if clean and output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
            click.echo(click.style(f"🧹 Cleaned {output_dir}", fg='yellow'))
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Import the CLI app
        click.echo(click.style(f"🔍 Loading CLI app from {app}...", fg='blue'))
        
        try:
            module_path, attr_name = app.split(':')
            module = importlib.import_module(module_path)
            cli_app = getattr(module, attr_name)
        except Exception as e:
            click.echo(click.style(f"❌ Failed to load app: {e}", fg='red', bold=True))
            click.echo()
            click.echo("Make sure the module path is correct:")
            click.echo(f"  • Module: {app.split(':')[0]}")
            click.echo(f"  • Attribute: {app.split(':')[1] if ':' in app else '(missing)'}")
            click.echo()
            raise click.Abort()
        
        # Extract documentation
        click.echo(click.style(f"📝 Extracting CLI documentation...", fg='blue'))
        start_time = time.time()
        
        extractor = CLIExtractor(framework=framework, include_hidden=include_hidden)
        elements = extractor.extract(cli_app)
        
        extraction_time = time.time() - start_time
        
        # Count commands
        command_count = 0
        option_count = 0
        for element in elements:
            if element.element_type == 'command-group':
                command_count = len(element.children)
                for cmd in element.children:
                    option_count += cmd.metadata.get('option_count', 0)
        
        click.echo(click.style(f"   ✓ Extracted {command_count} commands, {option_count} options", fg='green'))
        
        if verbose:
            click.echo()
            click.echo("Commands found:")
            for element in elements:
                if element.element_type == 'command-group':
                    for cmd in element.children:
                        click.echo(f"  • {cmd.name}")
        
        # Generate documentation
        from bengal.utils.cli_output import CLIOutput
        cli = CLIOutput()
        cli.blank()
        cli.header("Generating documentation...")
        gen_start = time.time()
        
        generator = DocumentationGenerator(extractor, cli_config)
        generated_files = generator.generate_all(elements, output_dir)
        
        gen_time = time.time() - gen_start
        total_time = time.time() - start_time
        
        # Display results
        click.echo()
        click.echo(click.style("✅ CLI Documentation Generated!", fg='green', bold=True))
        click.echo()
        click.echo(f"   📊 Statistics:")
        click.echo(f"      • Commands: {command_count}")
        click.echo(f"      • Options:  {option_count}")
        click.echo(f"      • Pages:    {len(generated_files)}")
        click.echo()
        click.echo(f"   ⚡ Performance:")
        click.echo(f"      • Extraction: {extraction_time:.3f}s")
        click.echo(f"      • Generation: {gen_time:.3f}s")
        click.echo(f"      • Total:      {total_time:.3f}s")
        click.echo()
        click.echo(f"   📂 Output: {output_dir}")
        click.echo()
        
        if verbose:
            click.echo("Generated files:")
            for file in generated_files:
                click.echo(f"  • {file}")
            click.echo()
        
        click.echo(click.style("💡 Next steps:", fg='yellow'))
        click.echo(f"   • View docs: ls {output_dir}")
        click.echo(f"   • Build site: bengal build")
        click.echo()
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo()
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if verbose:
            import traceback
            click.echo()
            click.echo(traceback.format_exc())
        raise click.Abort()


@main.command()
@click.option('--last', '-n', default=10, help='Show last N builds (default: 10)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'summary']), 
              default='table', help='Output format')
@click.option('--compare', '-c', is_flag=True, help='Compare last two builds')
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


if __name__ == '__main__':
    main()

