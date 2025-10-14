"""Commands for creating new sites and pages."""

from datetime import datetime
from pathlib import Path

import click

from bengal.cli.site_templates import get_template

# Add these imports
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
        "template_id": "blog",
    },
    "docs": {
        "name": "Documentation",
        "emoji": "📚",
        "description": "Technical docs or guides",
        "sections": ["getting-started", "guides", "reference"],
        "with_content": True,
        "pages_per_section": 3,
        "template_id": "docs",
    },
    "portfolio": {
        "name": "Portfolio",
        "emoji": "💼",
        "description": "Showcase your work",
        "sections": ["about", "projects", "blog", "contact"],
        "with_content": True,
        "pages_per_section": 3,
        "template_id": "portfolio",
    },
    "business": {
        "name": "Business",
        "emoji": "🏢",
        "description": "Company or product site",
        "sections": ["products", "services", "about", "contact"],
        "with_content": True,
        "pages_per_section": 2,
        "template_id": "default",  # Fallback if no business template yet
    },
    "resume": {
        "name": "Resume",
        "emoji": "📄",
        "description": "Professional resume/CV site",
        "sections": ["resume"],
        "with_content": True,
        "pages_per_section": 1,
        "template_id": "resume",
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


def _run_init_wizard(preset: str = None) -> str | None:
    """Run the site initialization wizard and return the selected template ID or None."""
    import click

    # If preset was provided via flag, use it directly
    if preset:
        if preset not in PRESETS:
            click.echo(
                click.style(f"⚠️  Unknown preset '{preset}'. Available: ", fg="yellow")
                + ", ".join(PRESETS.keys())
            )
            return None

        selected_preset = PRESETS[preset]
        click.echo(
            click.style("🏗️  Selected ", fg="cyan")
            + click.style(
                f"{selected_preset['emoji']} {selected_preset['name']}", fg="cyan", bold=True
            )
            + click.style(" preset.", fg="cyan")
        )
        return selected_preset.get("template_id", "default")

    # Interactive wizard with questionary
    try:
        import questionary
    except ImportError:
        click.echo(
            click.style(
                "\n⚠️  Install questionary for better interactive prompts: pip install questionary",
                fg="yellow",
            )
        )
        return None

    # Build choices list
    choices = []
    preset_items = list(PRESETS.items())

    for key, info in preset_items:
        choices.append(
            {
                "name": f"{info['emoji']} {info['name']:<15} - {info['description']}",
                "value": key,
            }
        )

    choices.append(
        {
            "name": "📦 Blank          - Empty site, no initial structure",
            "value": "__blank__",
        }
    )

    choices.append(
        {
            "name": "⚙️  Custom         - Define your own structure",
            "value": "__custom__",
        }
    )

    # Show interactive menu
    click.echo(click.style("\n🎯 What kind of site are you building?", fg="cyan", bold=True))
    selection = questionary.select(
        "Select a preset:",
        choices=choices,
        style=questionary.Style(
            [
                ("qmark", "fg:cyan bold"),
                ("question", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
                ("selected", "fg:green"),
            ]
        ),
    ).ask()

    # Handle cancellation (Ctrl+C)
    if selection is None:
        click.echo(click.style("\n✨ Cancelled. Will create basic default site.", fg="yellow"))
        return "default"

    # Handle blank
    if selection == "__blank__":
        click.echo(click.style("\n✨ Blank site selected. No initial structure added.", fg="cyan"))
        return None

    # Handle custom
    if selection == "__custom__":
        sections_input = click.prompt(
            click.style("\nEnter section names (comma-separated, e.g., blog,about):", fg="cyan"),
            type=str,
            default="blog,about",
        )
        pages_per = click.prompt(
            click.style("Pages per section:", fg="cyan"),
            type=int,
            default=3,
        )
        click.echo(
            click.style(
                f"\n✨ Custom structure noted (sections={sections_input}, pages={pages_per}). Basic site created; run 'bengal init --sections {sections_input} --pages-per-section {pages_per} --with-content' after to add structure.",
                fg="cyan",
            )
        )
        return "default"  # Custom needs post-creation init

    # Regular preset selected
    selected_preset = PRESETS[selection]
    click.echo(click.style(f"\n✨ {selected_preset['name']} preset selected.", fg="cyan"))
    return selected_preset.get("template_id", "default")


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

        # Determine effective template
        effective_template = template
        is_custom = False

        # Check if we should run wizard (only for default + interactive/non-no-init)
        should_run_wizard = _should_run_init_wizard(template, no_init, init_preset)

        if should_run_wizard:
            # Run wizard before creation to get selection
            wizard_selection = _run_init_wizard(init_preset)

            if wizard_selection is not None and wizard_selection != "default":
                effective_template = wizard_selection
            elif wizard_selection == "__custom__":  # Track for advice
                is_custom = True
            # Else: blank/cancel uses default (None -> default)

        # Get the effective template
        site_template = get_template(effective_template)

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
        from bengal.utils.atomic_write import atomic_write_text

        atomic_write_text(site_path / "bengal.toml", config_content)
        click.echo(click.style("   ├─ ", fg="cyan") + "Created bengal.toml")

        # Create .gitignore
        gitignore_content = """# Bengal build outputs
public/

# Bengal cache and dev files
.bengal/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
        atomic_write_text(site_path / ".gitignore", gitignore_content)
        click.echo(click.style("   ├─ ", fg="cyan") + "Created .gitignore")

        # Create files from template (pages, data files, etc.)
        files_created = 0
        for template_file in site_template.files:
            base_dir = site_path / template_file.target_dir
            base_dir.mkdir(parents=True, exist_ok=True)

            file_path = base_dir / template_file.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(file_path, template_file.content)
            files_created += 1

        if files_created == 1:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {files_created} file")
        else:
            click.echo(click.style("   └─ ", fg="cyan") + f"Created {files_created} files")

        click.echo(click.style("\n✅ Site created successfully!", fg="green", bold=True))

        # Handle special cases for wizard
        if wizard_selection is None and init_preset is None:
            click.echo(click.style("\n💡 Run 'bengal init' to add structure later.", fg="yellow"))
        if is_custom:
            click.echo(
                click.style(
                    "\n💡 For custom sections, run 'bengal init --sections <your-list> --with-content' now.",
                    fg="yellow",
                )
            )

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
