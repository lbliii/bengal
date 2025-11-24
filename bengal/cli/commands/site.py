from __future__ import annotations

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import command_metadata, handle_cli_errors

from .build import build
from .clean import clean
from .new import _create_site
from .serve import serve


@click.group("site", cls=BengalGroup)
def site_cli():
    """
    Site building and serving commands.
    """
    pass


# Register the new site command as an alias: bengal site new
@site_cli.command("new")
@command_metadata(
    category="content",
    description="Create a new Bengal site with optional structure initialization",
    examples=[
        "bengal site new my-blog",
        "bengal site new --template blog",
        "bengal site new --init-preset docs",
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
def site_new(name: str, theme: str, template: str, no_init: bool, init_preset: str) -> None:
    """
    🏗️  Create a new Bengal site with optional structure initialization.

    Creates a new site directory with configuration, content structure, and
    optional sample content. Use --template to choose a preset layout.

    Examples:
        bengal site new my-blog
        bengal site new --template blog
        bengal site new --init-preset docs

    See also:
        bengal new site - Alternative command (same functionality)
        bengal site build - Build the site
    """
    # Delegate to the shared site creation logic
    _create_site(name, theme, template, no_init, init_preset)


site_cli.add_command(build)
site_cli.add_command(serve)
site_cli.add_command(clean)

# Compatibility exports expected by some tests
build_command = build
serve_command = serve
clean_command = clean
