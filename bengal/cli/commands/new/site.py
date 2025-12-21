"""
Site creation command and logic.

Creates new Bengal sites with optional structure initialization.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click
import questionary

from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors
from bengal.cli.site_templates import get_template
from bengal.utils.atomic_write import atomic_write_text
from bengal.utils.text import slugify

from .config import create_config_directory
from .wizard import run_init_wizard, should_run_init_wizard

if TYPE_CHECKING:
    from bengal.cli.templates.base import SiteTemplate
    from bengal.output import CLIOutput

# .gitignore content for new sites
GITIGNORE_CONTENT = """# Bengal build outputs
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


def create_site(
    name: str | None,
    theme: str,
    template: str,
    no_init: bool,
    init_preset: str | None,
) -> None:
    """
    Core logic for creating a new site.

    🏗️  Create a new Bengal site with optional structure initialization.

    Creates a new site directory with configuration, content structure, and
    optional sample content. Use --template to choose a preset layout.

    Args:
        name: Site name (or None to prompt)
        theme: Theme to use
        template: Site template name
        no_init: Skip structure initialization wizard
        init_preset: Preset name if provided via flag
    """
    cli = get_cli_output()

    # Prompt for site name if not provided
    if not name:
        cli.blank()
        cli.header("🏗️  Create a new Bengal site")
        name = cli.prompt("Enter site name")
        if not name:
            cli.warning("✨ Cancelled.")
            raise click.Abort()

    # Store the original name for site title and slugify for directory
    site_title = name.strip()
    site_dir_name = slugify(site_title)

    # Validate that slugified name is not empty
    if not site_dir_name:
        cli.error("Site name must contain at least one alphanumeric character!")
        raise click.Abort()

    site_path = Path(site_dir_name)

    if site_path.exists():
        cli.error(f"Directory {site_dir_name} already exists!")
        raise click.Abort()

    # Prompt for base URL (skip if non-interactive mode)
    baseurl = _prompt_for_baseurl(no_init, cli)

    # Determine effective template
    effective_template, is_custom, wizard_selection = _determine_template(
        template, no_init, init_preset
    )

    # Get the effective template
    site_template = get_template(effective_template)
    if site_template is None:
        cli.error(f"Template '{effective_template}' not found")
        raise click.Abort()

    # Show what we're creating
    display_text = site_title
    if site_title != site_dir_name:
        display_text += f" → {site_dir_name}"

    cli.blank()
    cli.header(f"🏗️  Creating new Bengal site: {display_text}")
    cli.info(f"   ({site_template.description})")

    # Create directory structure
    _create_directory_structure(site_path, site_template)
    cli.info("   ├─ Created directory structure")

    # Create config directory structure
    create_config_directory(site_path, site_title, theme, cli, effective_template, baseurl)

    # Create .gitignore
    atomic_write_text(site_path / ".gitignore", GITIGNORE_CONTENT)
    cli.info("   ├─ Created .gitignore")

    # Create files from template
    files_created = _create_template_files(site_path, site_template)
    if files_created == 1:
        cli.info(f"   └─ Created {files_created} file")
    else:
        cli.info(f"   └─ Created {files_created} files")

    cli.blank()
    cli.success("✅ Site created successfully!")

    # Show hints and next steps
    _show_post_creation_hints(cli, wizard_selection, init_preset, is_custom, site_dir_name, baseurl)


def _prompt_for_baseurl(no_init: bool, cli: CLIOutput) -> str:
    """Prompt user for base URL or return default."""
    if no_init:
        return "https://example.com"

    cli.blank()
    baseurl = questionary.text(
        "Base URL for your site:",
        default="https://example.com",
        instruction="(Production URL, e.g., https://mysite.com)",
        style=questionary.Style(
            [
                ("qmark", "fg:cyan bold"),
                ("question", "fg:cyan bold"),
                ("answer", "fg:green"),
            ]
        ),
    ).ask()

    if baseurl is None:
        cli.warning("✨ Cancelled.")
        raise click.Abort()

    return "https://example.com" if not baseurl.strip() else baseurl.strip()


def _determine_template(
    template: str, no_init: bool, init_preset: str | None
) -> tuple[str, bool, str | None]:
    """
    Determine the effective template based on wizard selection.

    Returns:
        Tuple of (effective_template, is_custom, wizard_selection)
    """
    effective_template = template
    is_custom = False
    wizard_selection = None

    should_run_wizard = should_run_init_wizard(template, no_init, init_preset)

    if should_run_wizard:
        wizard_selection = run_init_wizard(init_preset)

        if wizard_selection is not None and wizard_selection != "default":
            effective_template = wizard_selection
        elif wizard_selection == "__custom__":
            is_custom = True

    return effective_template, is_custom, wizard_selection


def _create_directory_structure(site_path: Path, site_template: SiteTemplate) -> None:
    """Create the site directory structure."""
    site_path.mkdir(parents=True)
    (site_path / "content").mkdir()
    (site_path / "assets" / "css").mkdir(parents=True)
    (site_path / "assets" / "js").mkdir()
    (site_path / "assets" / "images").mkdir()
    (site_path / "templates").mkdir()

    # Create any additional directories from template
    for additional_dir in site_template.additional_dirs:
        (site_path / additional_dir).mkdir(parents=True, exist_ok=True)


def _create_template_files(site_path: Path, site_template: SiteTemplate) -> int:
    """Create files from template. Returns count of files created."""
    files_created = 0
    for template_file in site_template.files:
        base_dir = site_path / template_file.target_dir
        base_dir.mkdir(parents=True, exist_ok=True)

        file_path = base_dir / template_file.relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(file_path, template_file.content)
        files_created += 1

    return files_created


def _show_post_creation_hints(
    cli: CLIOutput,
    wizard_selection: str | None,
    init_preset: str | None,
    is_custom: bool,
    site_dir_name: str,
    baseurl: str,
) -> None:
    """Show hints and next steps after site creation."""
    if wizard_selection is None and init_preset is None:
        cli.blank()
        cli.tip("Run 'bengal init' to add structure later.")
    if is_custom:
        cli.blank()
        cli.tip("For custom sections, run 'bengal init --sections <your-list> --with-content' now.")

    # Show next steps
    cli.subheader("Next steps:", icon="📚")
    cli.info(f"   ├─ cd {site_dir_name}")
    cli.info("   └─ bengal site serve")
    cli.blank()
    cli.tip("💡 Config uses environment-aware directory structure!")
    cli.tip(f"   • Base URL: {baseurl}")
    cli.tip("   • Local dev: config/environments/local.yaml")
    cli.tip("   • Production: config/environments/production.yaml")
    cli.tip("   • Run 'bengal config show' to see merged config")
    cli.blank()


# Click command decorator
@click.command("site")
@command_metadata(
    category="content",
    description="Create a new Bengal site with optional structure initialization",
    examples=[
        "bengal new site my-blog",
        "bengal new site --template blog",
        "bengal new site --init-preset docs",
    ],
    requires_site=False,
    tags=["setup", "quick", "content"],
)
@handle_cli_errors(show_art=False)
@click.argument("name", required=False)
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
def site_command(name: str, theme: str, template: str, no_init: bool, init_preset: str) -> None:
    """Create a new Bengal site (bengal new site)."""
    create_site(name, theme, template, no_init, init_preset)
