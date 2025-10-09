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
    show_welcome,
    show_clean_success,
)
from bengal.utils.logger import configure_logging, LogLevel, close_all_loggers, print_all_summaries
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.extractors.cli import CLIExtractor
from bengal.autodoc.generator import DocumentationGenerator
from bengal.autodoc.config import load_autodoc_config


@click.group()
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main() -> None:
    """
    🐯 Bengal SSG - A high-performance static site generator.
    
    Fast & fierce static site generation with personality!
    """
    pass


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
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output - only show errors and summary')
@click.option('--log-file', type=click.Path(), help='Write detailed logs to file (default: .bengal-build.log)')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, memory_optimized: bool, profile: str, perf_profile: str, use_theme_dev: bool, use_dev: bool, verbose: bool, strict: bool, debug: bool, validate: bool, config: str, quiet: bool, log_file: str, source: str) -> None:
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
        show_building_indicator("Building site")
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create and build site
        site = Site.from_config(root_path, config_path)
        
        # Override config with CLI flags
        if strict:
            site.config["strict_mode"] = True
        if debug:
            site.config["debug"] = True
        
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
                profile=build_profile,
                memory_optimized=memory_optimized
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
                profile=build_profile,
                memory_optimized=memory_optimized
            )
        
        # Display template errors first if we're in theme-dev or dev mode
        if stats.template_errors and build_profile != BuildProfile.WRITER:
            from bengal.utils.build_stats import display_template_errors
            display_template_errors(stats)
        
        # Display build stats based on profile (unless quiet mode)
        if not quiet:
            if build_profile == BuildProfile.WRITER:
                # Simple, clean output for writers
                from bengal.utils.build_stats import display_simple_build_stats
                display_simple_build_stats(stats, output_dir=str(site.output_dir))
            else:
                # Detailed output for theme-dev and dev profiles
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
@click.option('--output', type=click.Path(), help='Generate interactive visualization to file (e.g., public/graph.html)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def graph(show_stats: bool, output: str, config: str, source: str) -> None:
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
        click.echo("🔍 Discovering site content...")
        from bengal.orchestration.content import ContentOrchestrator
        content_orch = ContentOrchestrator(site)
        content_orch.discover()
        
        # Build knowledge graph
        click.echo(f"📊 Analyzing {len(site.pages)} pages...")
        graph = KnowledgeGraph(site)
        graph.build()
        
        # Show statistics
        if show_stats:
            stats = graph.format_stats()
            click.echo(stats)
        
        # Generate visualization if requested
        if output:
            output_path = Path(output).resolve()
            click.echo(f"\n🎨 Generating interactive visualization...")
            click.echo(f"   ↪ {output_path}")
            
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
        show_welcome()
        
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
        
        # Confirm before cleaning unless --force
        if not force:
            if not click.confirm(f"Delete all files in {site.output_dir}?"):
                click.echo("Cancelled")
                return
        
        # Clean
        site.clean()
        
        show_clean_success(str(site.output_dir))
        
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
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str) -> None:
    """
    📚 Generate API documentation from Python source code.
    
    Extracts documentation via AST parsing (no imports needed!).
    Fast, reliable, and works even with complex dependencies.
    
    Example:
        bengal autodoc --source src/mylib --output content/api
    """
    import time
    
    try:
        click.echo()
        click.echo(click.style("📚 Bengal Autodoc", fg='cyan', bold=True))
        click.echo()
        
        # Load configuration
        config_path = Path(config) if config else None
        autodoc_config = load_autodoc_config(config_path)
        python_config = autodoc_config.get('python', {})
        
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
        click.echo(click.style("\n🔨 Generating documentation...", fg='blue'))
        gen_start = time.time()
        
        generator = DocumentationGenerator(extractor, autodoc_config)
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
        
    except Exception as e:
        click.echo()
        click.echo(click.style(f"❌ Error: {e}", fg='red', bold=True))
        if verbose:
            import traceback
            click.echo()
            click.echo(traceback.format_exc())
        raise click.Abort()


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
        click.echo(click.style("📄 Generating documentation...", fg='blue'))
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

