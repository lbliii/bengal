"""
Command-line interface for Bengal SSG.
"""

from pathlib import Path
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
@click.option('--parallel/--no-parallel', default=True, help='Use parallel processing')
@click.option('--incremental', is_flag=True, help='Perform incremental build')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information')
@click.option('--strict', is_flag=True, help='Fail on template errors (recommended for CI)')
@click.option('--debug', is_flag=True, help='Show debug output and full tracebacks')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output (no stats table)')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, verbose: bool, strict: bool, debug: bool, config: str, quiet: bool, source: str) -> None:
    """
    🔨 Build the static site.
    """
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
        
        stats = site.build(parallel=parallel, incremental=incremental, verbose=verbose)
        
        # Display build stats (unless quiet mode)
        if not quiet:
            display_build_stats(stats, show_art=True)
        else:
            click.echo(click.style("✅ Build complete!", fg='green', bold=True))
        
    except Exception as e:
        show_error(f"Build failed: {e}", show_art=True)
        if debug:
            raise
        raise click.Abort()


@main.command()
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8000, type=int, help='Server port')
@click.option('--no-watch', is_flag=True, help='Disable file watching')
@click.option('--no-auto-port', is_flag=True, help='Disable automatic port selection (fail if port is in use)')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.argument('source', type=click.Path(exists=True), default='.')
def serve(host: str, port: int, no_watch: bool, no_auto_port: bool, config: str, source: str) -> None:
    """
    🚀 Start development server with hot reload.
    
    By default, if the specified port is already in use, the server will
    automatically find and use the next available port. Use --no-auto-port
    to disable this behavior and fail instead.
    """
    try:
        show_welcome()
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site
        site = Site.from_config(root_path, config_path)
        
        # Enable strict mode in development (fail fast on errors)
        site.config["strict_mode"] = True
        
        # Start server
        site.serve(host=host, port=port, watch=not no_watch, auto_port=not no_auto_port)
        
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")
    except Exception as e:
        show_error(f"Server failed: {e}", show_art=True)
        raise click.Abort()


@main.command()
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.argument('source', type=click.Path(exists=True), default='.')
def clean(config: str, source: str) -> None:
    """
    🧹 Clean the output directory.
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site and clean
        site = Site.from_config(root_path, config_path)
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
        
        # Create page content
        page_content = f"""---
title: {name.replace('-', ' ').title()}
date: {Path(__file__).stat().st_mtime}
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

