"""
Command-line interface for Bengal SSG.
"""

from pathlib import Path
import click

from bengal import __version__
from bengal.core.site import Site


@click.group()
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main() -> None:
    """
    Bengal SSG - A high-performance static site generator.
    """
    pass


@main.command()
@click.option('--parallel/--no-parallel', default=True, help='Use parallel processing')
@click.option('--incremental', is_flag=True, help='Perform incremental build')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed build information')
@click.option('--strict', is_flag=True, help='Fail on template errors (recommended for CI)')
@click.option('--debug', is_flag=True, help='Show debug output and full tracebacks')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.argument('source', type=click.Path(exists=True), default='.')
def build(parallel: bool, incremental: bool, verbose: bool, strict: bool, debug: bool, config: str, source: str) -> None:
    """
    Build the static site.
    """
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
        
        site.build(parallel=parallel, incremental=incremental, verbose=verbose)
        
        click.echo(click.style("✅ Build complete!", fg='green', bold=True))
        
    except Exception as e:
        click.echo(click.style(f"❌ Build failed: {e}", fg='red'), err=True)
        raise click.Abort()


@main.command()
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8000, type=int, help='Server port')
@click.option('--no-watch', is_flag=True, help='Disable file watching')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.argument('source', type=click.Path(exists=True), default='.')
def serve(host: str, port: int, no_watch: bool, config: str, source: str) -> None:
    """
    Start development server with hot reload.
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site
        site = Site.from_config(root_path, config_path)
        
        # Enable strict mode in development (fail fast on errors)
        site.config["strict_mode"] = True
        
        # Start server
        site.serve(host=host, port=port, watch=not no_watch)
        
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")
    except Exception as e:
        click.echo(click.style(f"❌ Server failed: {e}", fg='red'), err=True)
        raise click.Abort()


@main.command()
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.argument('source', type=click.Path(exists=True), default='.')
def clean(config: str, source: str) -> None:
    """
    Clean the output directory.
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site and clean
        site = Site.from_config(root_path, config_path)
        site.clean()
        
        click.echo(click.style("✅ Clean complete!", fg='green', bold=True))
        
    except Exception as e:
        click.echo(click.style(f"❌ Clean failed: {e}", fg='red'), err=True)
        raise click.Abort()


@main.group()
def new() -> None:
    """
    Create new site, page, or section.
    """
    pass


@new.command()
@click.argument('name')
@click.option('--theme', default='default', help='Theme to use')
def site(name: str, theme: str) -> None:
    """
    Create a new Bengal site.
    """
    try:
        site_path = Path(name)
        
        if site_path.exists():
            click.echo(click.style(f"❌ Directory {name} already exists!", fg='red'), err=True)
            raise click.Abort()
        
        # Create directory structure
        site_path.mkdir(parents=True)
        (site_path / 'content').mkdir()
        (site_path / 'assets' / 'css').mkdir(parents=True)
        (site_path / 'assets' / 'js').mkdir()
        (site_path / 'assets' / 'images').mkdir()
        (site_path / 'templates').mkdir()
        
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
        
        click.echo(click.style(f"✅ Created new site: {name}", fg='green', bold=True))
        click.echo(f"\nNext steps:")
        click.echo(f"  cd {name}")
        click.echo(f"  bengal serve")
        
    except Exception as e:
        click.echo(click.style(f"❌ Failed to create site: {e}", fg='red'), err=True)
        raise click.Abort()


@new.command()
@click.argument('name')
@click.option('--section', default='', help='Section to create page in')
def page(name: str, section: str) -> None:
    """
    Create a new page.
    """
    try:
        # Ensure we're in a Bengal site
        content_dir = Path('content')
        if not content_dir.exists():
            click.echo(click.style("❌ Not in a Bengal site directory!", fg='red'), err=True)
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
            click.echo(click.style(f"❌ Page {page_path} already exists!", fg='red'), err=True)
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
        
        click.echo(click.style(f"✅ Created new page: {page_path}", fg='green', bold=True))
        
    except Exception as e:
        click.echo(click.style(f"❌ Failed to create page: {e}", fg='red'), err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()

