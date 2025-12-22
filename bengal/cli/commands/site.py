from __future__ import annotations

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import command_metadata, get_cli_output, handle_cli_errors

from .build import build
from .clean import clean
from .new import create_site
from .serve import serve


@click.group("site", cls=BengalGroup)
def site_cli() -> None:
    """
    Site building and serving commands.
    """
    pass


# Hidden from help (use 'bengal new site' instead)
@site_cli.command("new", hidden=True)
@command_metadata(
    category="content",
    description="[DEPRECATED] Use 'bengal new site' instead",
    examples=[
        "bengal new site my-blog",
        "bengal new site --template blog",
    ],
    requires_site=False,
    tags=["setup", "deprecated"],
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
    [DEPRECATED] Create a new Bengal site.

    This command is deprecated. Use 'bengal new site' instead.

    Examples:
        bengal new site my-blog
        bengal new site --template blog
    """
    # Show deprecation warning
    cli = get_cli_output()
    cli.warning("⚠️  'bengal site new' is deprecated. Use 'bengal new site' instead.")
    cli.blank()

    # Delegate to the shared site creation logic
    create_site(name, theme, template, no_init, init_preset)


site_cli.add_command(build)
site_cli.add_command(serve)
site_cli.add_command(clean)

# Compatibility exports expected by some tests
build_command = build
serve_command = serve
clean_command = clean
