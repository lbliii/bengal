"""
Site preset definitions for the new site wizard.

Presets define predefined configurations for common site types:
- Blog: Personal or professional blog
- Documentation: Technical docs or guides
- Portfolio: Showcase work
- Business: Company or product site
- Resume: Professional CV site
"""

from __future__ import annotations

from typing import Any

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


def get_preset(name: str) -> dict[str, Any] | None:
    """
    Get a preset by name.

    Args:
        name: Preset name (blog, docs, portfolio, business, resume)

    Returns:
        Preset configuration dict or None if not found
    """
    return PRESETS.get(name)


def get_preset_names() -> list[str]:
    """Get list of available preset names."""
    return list(PRESETS.keys())


def get_preset_template_id(name: str) -> str:
    """
    Get the template ID for a preset.

    Args:
        name: Preset name

    Returns:
        Template ID (defaults to 'default' if preset not found)
    """
    preset = PRESETS.get(name)
    if preset:
        return str(preset.get("template_id", "default"))
    return "default"
