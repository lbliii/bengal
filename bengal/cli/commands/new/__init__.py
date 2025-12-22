"""
Commands for creating new sites, pages, layouts, partials, and themes.

This package provides the 'bengal new' command group with subcommands:
- site: Create a new Bengal site with optional presets
- page: Create a new content page
- layout: Create a new layout template
- partial: Create a new partial template
- theme: Create a new theme scaffold

Structure:
- presets.py: Preset definitions for wizard
- config.py: Configuration directory generation
- wizard.py: Interactive site initialization wizard
- site.py: Site creation command and logic
- scaffolds.py: Page, layout, partial, theme commands
"""

from __future__ import annotations

import click

from bengal.cli.base import BengalGroup
from bengal.utils.text import slugify

from .scaffolds import layout_command, page_command, partial_command, theme_command
from .site import create_site, site_command

__all__ = [
    "new",
    "site_command",
    "page_command",
    "layout_command",
    "partial_command",
    "theme_command",
    "create_site",
    "slugify",
]


@click.group(cls=BengalGroup)
def new() -> None:
    """
    Create new site, page, layout, partial, or theme.

    Subcommands:
        site      Create a new Bengal site with optional presets
        page      Create a new page in content directory
        layout    Create a new layout template in templates/layouts/
        partial   Create a new partial template in templates/partials/
        theme     Create a new theme scaffold with templates and assets
    """
    pass


# Register commands
new.add_command(site_command, name="site")
new.add_command(page_command, name="page")
new.add_command(layout_command, name="layout")
new.add_command(partial_command, name="partial")
new.add_command(theme_command, name="theme")
