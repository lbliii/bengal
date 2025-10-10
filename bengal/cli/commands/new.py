"""Commands for creating new sites and pages."""

from pathlib import Path
from datetime import datetime
import click

from bengal.utils.build_stats import show_error


@click.group()
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

