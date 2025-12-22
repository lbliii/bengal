"""
Menu configuration generation helpers.

Provides utilities for automatically generating TOML menu configuration
from site sections. Used by the new site wizard to create sensible
default navigation menus.

Functions:
    generate_menu_config: Generate TOML menu entries from section list
    append_menu_to_config: Safely append menu to existing bengal.toml
    get_menu_suggestions: Get structured menu data for display/prompts

Example:
    >>> sections = ['blog', 'about', 'projects']
    >>> toml = generate_menu_config(sections)
    >>> print(toml)
    # Navigation Menu
    [[menu.main]]
    name = "Home"
    url = "/"
    weight = 1
    ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_menu_config(sections: list[str], menu_name: str = "main") -> str:
    """
    Generate menu configuration entries for given sections.

    Creates [[menu.main]] entries with appropriate weights based on
    common conventions (Home first, then other sections in order).

    Args:
        sections: List of section slugs (e.g., ['blog', 'about', 'projects'])
        menu_name: Menu identifier (default: 'main')

    Returns:
        TOML-formatted menu configuration string

    Example:
        >>> generate_menu_config(['blog', 'about'])
        '''
        # Navigation Menu
        [[menu.main]]
        name = "Home"
        url = "/"
        weight = 1

        [[menu.main]]
        name = "Blog"
        url = "/blog/"
        weight = 10

        [[menu.main]]
        name = "About"
        url = "/about/"
        weight = 20
        '''
    """
    lines = []
    lines.append("# Navigation Menu")

    # Always start with Home (weight 1)
    lines.append(f"[[menu.{menu_name}]]")
    lines.append('name = "Home"')
    lines.append('url = "/"')
    lines.append("weight = 1")
    lines.append("")

    # Add sections with incremental weights
    for idx, section in enumerate(sections, start=1):
        # Get display name (title-case with proper spacing)
        display_name = _get_display_name(section)

        lines.append(f"[[menu.{menu_name}]]")
        lines.append(f'name = "{display_name}"')
        lines.append(f'url = "/{section}/"')
        lines.append(f"weight = {idx * 10}")

        # Add blank line between entries (except last)
        if idx < len(sections):
            lines.append("")

    return "\n".join(lines)


def _get_display_name(section_slug: str) -> str:
    """
    Convert section slug to display name.

    Uses intelligent title-casing with special handling for
    common terms and acronyms.

    Args:
        section_slug: Section slug (e.g., 'getting-started', 'api')

    Returns:
        Display name (e.g., 'Getting Started', 'API')

    Examples:
        >>> _get_display_name('blog')
        'Blog'
        >>> _get_display_name('getting-started')
        'Getting Started'
        >>> _get_display_name('api')
        'API'
    """
    # Special cases for common acronyms/terms
    special_cases = {
        "api": "API",
        "faq": "FAQ",
        "cli": "CLI",
        "ui": "UI",
        "ux": "UX",
        "seo": "SEO",
        "rss": "RSS",
        "pdf": "PDF",
        "html": "HTML",
        "css": "CSS",
        "js": "JavaScript",
    }

    # Check for exact match
    if section_slug in special_cases:
        return special_cases[section_slug]

    # Convert slug to title case
    return section_slug.replace("-", " ").replace("_", " ").title()


def append_menu_to_config(config_path: Path, sections: list[str], menu_name: str = "main") -> bool:
    """
    Append menu configuration to existing bengal.toml file.

    Safely appends menu entries to the config file, checking if
    menu configuration already exists to avoid duplicates.

    Args:
        config_path: Path to bengal.toml
        sections: List of section slugs to add
        menu_name: Menu identifier (default: 'main')

    Returns:
        True if menu was added, False if menu already exists

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Read existing config
    with open(config_path) as f:
        content = f.read()

    # Check if menu already exists
    if f"[[menu.{menu_name}]]" in content:
        return False

    # Generate menu config
    menu_config = generate_menu_config(sections, menu_name)

    # Append to file (with blank lines for separation)
    with open(config_path, "a") as f:
        # Add spacing if file doesn't end with newlines
        if not content.endswith("\n\n"):
            if content.endswith("\n"):
                f.write("\n")
            else:
                f.write("\n\n")

        f.write(menu_config)
        f.write("\n")

    return True


def get_menu_suggestions(sections: list[str], menu_name: str = "main") -> dict[str, Any]:
    """
    Get menu configuration suggestions for display to user.

    Returns structured menu data that can be used for:
    - CLI display/preview
    - Interactive prompts
    - Configuration generation

    Args:
        sections: List of section slugs
        menu_name: Menu identifier (default: 'main')

    Returns:
        Dictionary with menu items and TOML representation

    Example:
        >>> get_menu_suggestions(['blog', 'about'])
        {
            'menu_name': 'main',
            'items': [
                {'name': 'Home', 'url': '/', 'weight': 1},
                {'name': 'Blog', 'url': '/blog/', 'weight': 10},
                {'name': 'About', 'url': '/about/', 'weight': 20}
            ],
            'toml': '[[menu.main]]\\nname = "Home"...'
        }
    """
    items = [{"name": "Home", "url": "/", "weight": 1}]

    for idx, section in enumerate(sections, start=1):
        items.append(
            {
                "name": _get_display_name(section),
                "url": f"/{section}/",
                "weight": idx * 10,
            }
        )

    return {
        "menu_name": menu_name,
        "items": items,
        "toml": generate_menu_config(sections, menu_name),
    }
