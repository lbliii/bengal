"""Commands for creating new sites and pages."""

from datetime import datetime
from pathlib import Path

import click

from bengal.cli.site_templates import get_template
from bengal.utils.build_stats import show_error

# Preset definitions for wizard
PRESETS = {
    "blog": {
        "name": "Blog",
        "emoji": "📝",
        "description": "Personal or professional blog",
        "sections": ["blog", "about"],
        "with_content": True,
        "pages_per_section": 3,
    },
    "docs": {
        "name": "Documentation",
        "emoji": "📚",
        "description": "Technical docs or guides",
        "sections": ["getting-started", "guides", "reference"],
        "with_content": True,
        "pages_per_section": 3,
    },
    "portfolio": {
        "name": "Portfolio",
        "emoji": "💼",
        "description": "Showcase your work",
        "sections": ["about", "projects", "blog", "contact"],
        "with_content": True,
        "pages_per_section": 3,
    },
    "business": {
        "name": "Business",
        "emoji": "🏢",
        "description": "Company or product site",
        "sections": ["products", "services", "about", "contact"],
        "with_content": True,
        "pages_per_section": 2,
    },
    "resume": {
        "name": "Resume",
        "emoji": "📄",
        "description": "Professional resume/CV site",
        "sections": ["resume"],
        "with_content": True,
        "pages_per_section": 1,
    },
}


def _should_run_init_wizard(template: str, no_init: bool, init_preset: str) -> bool:
    """Determine if we should run the initialization wizard."""
    # Skip if user explicitly said no
    if no_init:
        return False

    # Skip if user provided a preset (they know what they want)
    if init_preset:
        return True

    # Skip if template is non-default (template already has structure)
    # Otherwise, prompt the user
    return template == "default"


def _run_init_wizard(site_path: Path, preset: str = None) -> bool:
    """Run the site initialization wizard."""
    from bengal.cli.commands.init import plan_init_operations

    # If preset was provided via flag, use it directly
    if preset:
        if preset not in PRESETS:
            click.echo(
                click.style(f"⚠️  Unknown preset '{preset}'. Available: ", fg="yellow")
                + ", ".join(PRESETS.keys())
            )
            return False

        selected_preset = PRESETS[preset]
        click.echo(
            click.style("🏗️  Initializing with ", fg="cyan")
            + click.style(
                f"{selected_preset['emoji']} {selected_preset['name']}", fg="cyan", bold=True
            )
            + click.style(" preset...", fg="cyan")
        )
    else:
        # Interactive wizard - show options immediately
        click.echo(click.style("\n> What kind of site are you building?", fg="cyan", bold=True))
        click.echo()

        preset_items = list(PRESETS.items())
        for idx, (_key, info) in enumerate(preset_items, 1):
            click.echo(
                click.style(f"  {idx}. ", fg="bright_black")
                + click.style(f"{info['emoji']} {info['name']:<15}", fg="cyan", bold=True)
                + click.style(f" - {info['description']}", fg="bright_black")
            )

        click.echo(
            click.style(f"  {len(preset_items) + 1}. ", fg="bright_black")
            + click.style("📦 Blank          ", fg="cyan", bold=True)
            + click.style(" - Empty site, no initial structure", fg="bright_black")
        )

        click.echo(
            click.style(f"  {len(preset_items) + 2}. ", fg="bright_black")
            + click.style("⚙️  Custom         ", fg="cyan", bold=True)
            + click.style(" - Define your own structure", fg="bright_black")
        )

        # Get user selection
        click.echo()
        selection = click.prompt(
            click.style("Selection", fg="cyan"),
            type=int,
            default=1,
            show_default=True,
        )

        if selection < 1 or selection > len(preset_items) + 2:
            click.echo(click.style("Invalid selection. Skipping initialization.", fg="yellow"))
            return False

        # Handle blank
        if selection == len(preset_items) + 1:
            click.echo(
                click.style(
                    "\n✨ Creating blank site. Run 'bengal init' later to add structure.",
                    fg="cyan",
                )
            )
            return False

        # Handle custom
        if selection == len(preset_items) + 2:
            sections_input = click.prompt(
                click.style("\nEnter section names (comma-separated)", fg="cyan"),
                type=str,
                default="blog,about",
            )
            selected_preset = {
                "name": "Custom",
                "sections": [s.strip() for s in sections_input.split(",")],
                "with_content": click.confirm(
                    click.style("Generate sample content?", fg="cyan"),
                    default=True,
                ),
                "pages_per_section": click.prompt(
                    click.style("Pages per section", fg="cyan"),
                    type=int,
                    default=3,
                ),
            }
        else:
            preset_key = preset_items[selection - 1][0]
            selected_preset = PRESETS[preset_key]

        click.echo()  # Blank line before execution

    # Execute the initialization
    content_dir = site_path / "content"

    try:
        operations, warnings = plan_init_operations(
            content_dir,
            selected_preset["sections"],
            selected_preset["with_content"],
            selected_preset["pages_per_section"],
            force=False,
        )

        if warnings:
            for warning in warnings:
                click.echo(click.style(f"⚠️  {warning}", fg="yellow"))

        if not operations:
            return False

        # Execute operations
        click.echo(click.style("🏗️  Initializing site structure...\n", fg="cyan", bold=True))

        sections_created = set()
        pages_created = 0

        for op in operations:
            op.execute()

            if op.path.name == "_index.md":
                sections_created.add(op.path.parent.name)
                rel_path = op.path.relative_to(site_path)
                click.echo(click.style("   ✓ ", fg="green") + f"Created {rel_path}")
            else:
                pages_created += 1
                rel_path = op.path.relative_to(site_path)
                click.echo(click.style("   ✓ ", fg="green") + f"Created {rel_path}")

        # Summary
        click.echo(click.style("\n✨ Site initialized successfully!", fg="green", bold=True))
        click.echo(click.style("\nCreated:", fg="cyan"))
        click.echo(f"  • {len(sections_created)} sections")
        click.echo(f"  • {pages_created} pages")

        # Show tip about auto-navigation
        if sections_created:
            click.echo(click.style("\n🎯 Navigation configured!", fg="green", bold=True))
            click.echo(click.style("   Sections will appear automatically in nav:", fg="green"))
            for section in sorted(sections_created):
                display_name = section.replace("-", " ").replace("_", " ").title()
                click.echo(click.style(f"   • {display_name}", fg="green"))
            click.echo()
            click.echo(
                click.style("   💡 Tip: ", fg="cyan")
                + click.style("Navigation auto-discovers sections. To customize,", fg="white")
            )
            click.echo(click.style("      add [[menu.main]] entries to bengal.toml", fg="white"))

        return True

    except Exception as e:
        click.echo(click.style(f"\n❌ Initialization failed: {e}", fg="red"))
        return False


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
@click.option(
    "--no-init",
    is_flag=True,
    help="Skip structure initialization wizard",
)
@click.option(
    "--init-preset",
    help="Initialize with preset (blog, docs, portfolio, business, resume) without prompting",
)
def site(name: str, theme: str, template: str, no_init: bool, init_preset: str) -> None:
    """
    🏗️  Create a new Bengal site with optional structure initialization.
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
            (site_path / additional_dir).mkdir(parents=True, exist_ok=True)

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

        # Create files from template (pages, data files, etc.)
        files_created = 0
        for template_file in site_template.files:
            # Determine the base directory (content, data, templates, etc.)
            base_dir = site_path / template_file.target_dir
            base_dir.mkdir(parents=True, exist_ok=True)

            # Create the file
            file_path = base_dir / template_file.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(file_path, template_file.content)
            files_created += 1

        if files_created == 1:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {files_created} file")
        else:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {files_created} files")

        click.echo(click.style("\n✅ Site created successfully!", fg="green", bold=True))

        # Run initialization wizard unless skipped or template was non-default
        should_init = _should_run_init_wizard(template, no_init, init_preset)

        if should_init:
            click.echo()  # Blank line
            init_result = _run_init_wizard(site_path, init_preset)

            if init_result:
                click.echo()  # Blank line after init

        # Show next steps
        click.echo(click.style("\n📚 Next steps:", fg="cyan", bold=True))
        click.echo(click.style("   ├─ ", fg="cyan") + f"cd {name}")
        click.echo(click.style("   └─ ", fg="cyan") + "bengal serve")
        click.echo()

    except Exception as e:
        show_error(f"Failed to create site: {e}", show_art=False)
        raise click.Abort() from e


def _slugify(text: str) -> str:
    """
    Convert text to URL-safe slug with Unicode support.

    This function preserves Unicode word characters (letters, digits, underscore)
    to support international content. Modern browsers and web servers handle
    Unicode URLs correctly.

    Examples:
        "My Awesome Page" → "my-awesome-page"
        "Hello, World!" → "hello-world"
        "Test   Multiple   Spaces" → "test-multiple-spaces"
        "你好世界" → "你好世界" (Chinese characters preserved)
        "مرحبا" → "مرحبا" (Arabic characters preserved)

    Note:
        Uses Python's \\w pattern which includes Unicode word characters.
        Special punctuation is removed, but international letters/digits are kept.
    """
    import re

    # Lowercase
    text = text.lower()

    # Remove special characters (keep alphanumeric, spaces, hyphens)
    # Note: \w matches [a-zA-Z0-9_] plus Unicode letters and digits
    text = re.sub(r"[^\w\s-]", "", text)

    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r"[-\s]+", "-", text)

    # Strip leading/trailing hyphens
    return text.strip("-")


@new.command()
@click.argument("name")
@click.option("--section", default="", help="Section to create page in")
def page(name: str, section: str) -> None:
    """
    📄 Create a new page.

    The page name will be automatically slugified for the filename.
    Example: "My Awesome Page" → my-awesome-page.md
    """
    try:
        # Ensure we're in a Bengal site
        content_dir = Path("content")
        if not content_dir.exists():
            show_error("Not in a Bengal site directory!", show_art=False)
            raise click.Abort()

        # Slugify the name for filename
        slug = _slugify(name)

        # Use original name for title (capitalize properly)
        title = name.replace("-", " ").title()

        # Determine page path
        if section:
            page_dir = content_dir / section
            page_dir.mkdir(parents=True, exist_ok=True)
        else:
            page_dir = content_dir

        # Create page file with slugified name
        page_path = page_dir / f"{slug}.md"

        if page_path.exists():
            show_error(f"Page {page_path} already exists!", show_art=False)
            raise click.Abort()

        # Create page content with current timestamp
        page_content = f"""---
title: {title}
date: {datetime.now().isoformat()}
---

# {title}

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
