"""Template registry and discovery.

This module discovers built‑in templates (and optionally custom ones on
``PYTHONPATH``) by importing ``bengal.cli.templates.<name>.template`` and
looking for a module‑level ``TEMPLATE`` variable. The registry provides a small
API to list, retrieve, and register templates programmatically.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from .base import SiteTemplate


class TemplateRegistry:
    """Registry for discovering and managing site templates.

    The registry scans the sibling directories of this file for template
    packages that expose a ``TEMPLATE`` variable.
    """

    def __init__(self):
        self._templates: dict[str, SiteTemplate] = {}
        self._discover_templates()

    def _discover_templates(self) -> None:
        """Discover all available templates in the built‑in package tree."""
        templates_dir = Path(__file__).parent

        for item in templates_dir.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            # Try to import the template module
            try:
                module = importlib.import_module(
                    f".{item.name}.template", package="bengal.cli.templates"
                )
                if hasattr(module, "TEMPLATE"):
                    template = module.TEMPLATE
                    self._templates[template.id] = template
            except (ImportError, AttributeError):
                # Skip directories that don't contain templates
                continue

    def get(self, template_id: str) -> SiteTemplate | None:
        """Get a template by its identifier.

        Args:
            template_id: The template ID (e.g. ``"blog"``).

        Returns:
            The matching :class:`SiteTemplate` or ``None`` if not found.
        """
        return self._templates.get(template_id)

    def list(self) -> list[tuple[str, str]]:
        """List all templates as ``(id, description)`` tuples."""
        return [(t.id, t.description) for t in self._templates.values()]

    def exists(self, template_id: str) -> bool:
        """Return True if a template with ``template_id`` exists."""
        return template_id in self._templates


# Global registry instance
_registry: TemplateRegistry | None = None


def _get_registry() -> TemplateRegistry:
    """Get or create the global registry instance (singleton)."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry


def get_template(template_id: str) -> SiteTemplate | None:
    """Convenience wrapper to get a template by ID from the global registry."""
    return _get_registry().get(template_id)


def list_templates() -> list[tuple[str, str]]:
    """Convenience wrapper to list all available templates."""
    return _get_registry().list()


def register_template(template: SiteTemplate) -> None:
    """Register a custom template with the global registry.

    This allows applications and plugins to add templates at runtime.
    """
    _get_registry()._templates[template.id] = template
