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
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information and progress')
@click.option('--strict', is_flag=True, help='Fail on template errors (recommended for CI/CD)')
@click.option('--debug', is_flag=True, help='Show debug output and full tracebacks')
@click.option('--validate', is_flag=True, help='Validate templates before building (catch errors early)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output - only show errors and summary')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, verbose: bool, strict: bool, debug: bool, validate: bool, config: str, quiet: bool, source: str) -> None:
    """
    🔨 Build the static site.
    
    Generates HTML files from your content, applies templates,
    processes assets, and outputs a production-ready site.
    """
    # Validate conflicting flags
    if quiet and verbose:
        raise click.UsageError("--quiet and --verbose cannot be used together")
    
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
        
        stats = site.build(parallel=parallel, incremental=incremental, verbose=verbose)
        
        # Display template errors first (if any)
        if stats.template_errors:
            from bengal.utils.build_stats import display_template_errors
            display_template_errors(stats)
        
        # Display build stats (unless quiet mode)
        if not quiet:
            display_build_stats(stats, show_art=True, output_dir=str(site.output_dir))
        else:
            click.echo(click.style("✅ Build complete!", fg='green', bold=True))
            click.echo(click.style(f"   ↪ {site.output_dir}", fg='cyan'))
        
    except Exception as e:
        show_error(f"Build failed: {e}", show_art=True)
        if debug:
            raise
        raise click.Abort()


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
        (site_path / 'bengal.toml').write_text(config_content)
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
        (site_path / 'content' / 'index.md').write_text(index_content)
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
        page_path.write_text(page_content)
        
        click.echo(click.style(f"\n✨ Created new page: ", fg='cyan') + 
                  click.style(str(page_path), fg='green', bold=True))
        click.echo()
        
    except Exception as e:
        show_error(f"Failed to create page: {e}", show_art=False)
        raise click.Abort()


if __name__ == '__main__':
    main()

