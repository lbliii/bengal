"""Commands for creating new sites and pages."""

from datetime import datetime
from pathlib import Path

import click

from bengal.cli.site_templates import get_template
from bengal.utils.build_stats import show_error


@click.group()
def new() -> None:
    """
    ✨ Create new site, page, or section.
    """
    pass


@new.command()
@click.argument("name")
@click.option("--theme", default="default", help="Theme to use")
@click.option(
    "--template",
    default="default",
    help="Site template (default, blog, docs, portfolio, resume, landing)",
)
def site(name: str, theme: str, template: str) -> None:
    """
    🏗️  Create a new Bengal site.
    """
    try:
        site_path = Path(name)

        if site_path.exists():
            show_error(f"Directory {name} already exists!", show_art=False)
            raise click.Abort()

        # Get the selected template
        site_template = get_template(template)

        click.echo(
            click.style(f"\n🏗️  Creating new Bengal site: {name}", fg="cyan", bold=True)
            + click.style(f" ({site_template.description})", fg="bright_black")
        )

        # Create directory structure
        site_path.mkdir(parents=True)
        (site_path / "content").mkdir()
        (site_path / "assets" / "css").mkdir(parents=True)
        (site_path / "assets" / "js").mkdir()
        (site_path / "assets" / "images").mkdir()
        (site_path / "templates").mkdir()

        # Create any additional directories from template
        for additional_dir in site_template.additional_dirs:
            (site_path / "content" / additional_dir).mkdir(parents=True, exist_ok=True)

        click.echo(click.style("   ├─ ", fg="cyan") + "Created directory structure")

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

        atomic_write_text(site_path / "bengal.toml", config_content)
        click.echo(click.style("   ├─ ", fg="cyan") + "Created bengal.toml")

        # Create data files if this template has them (e.g., resume template)
        from bengal.cli.site_templates import RESUME_DATA

        if template.lower() == "resume" and RESUME_DATA:
            data_dir = site_path / "data"
            data_dir.mkdir(exist_ok=True)
            for filename, content in RESUME_DATA.items():
                data_path = data_dir / filename
                atomic_write_text(data_path, content)
                click.echo(click.style("   ├─ ", fg="cyan") + f"Created data/{filename}")

        # Create pages from template
        pages_created = 0
        for page_template in site_template.pages:
            page_path = site_path / "content" / page_template.path
            page_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(page_path, page_template.content)
            pages_created += 1

        if pages_created == 1:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {pages_created} page")
        else:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {pages_created} pages")

        click.echo(click.style("\n✅ Site created successfully!", fg="green", bold=True))
        click.echo(click.style("\n📚 Next steps:", fg="cyan", bold=True))
        click.echo(click.style("   ├─ ", fg="cyan") + f"cd {name}")
        click.echo(click.style("   └─ ", fg="cyan") + "bengal serve")
        click.echo()

    except Exception as e:
        show_error(f"Failed to create site: {e}", show_art=False)
        raise click.Abort() from e


@new.command()
@click.argument("name")
@click.option("--section", default="", help="Section to create page in")
def page(name: str, section: str) -> None:
    """
    📄 Create a new page.
    """
    try:
        # Ensure we're in a Bengal site
        content_dir = Path("content")
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
title: {name.replace("-", " ").title()}
date: {datetime.now().isoformat()}
---

# {name.replace("-", " ").title()}

Your content goes here.
"""
        # Write new page atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text

        atomic_write_text(page_path, page_content)

        click.echo(
            click.style("\n✨ Created new page: ", fg="cyan")
            + click.style(str(page_path), fg="green", bold=True)
        )
        click.echo()

    except Exception as e:
        show_error(f"Failed to create page: {e}", show_art=False)
        raise click.Abort() from e
