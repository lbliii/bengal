"""Template registry and discovery.

This module discovers built‑in templates (and optionally custom ones on
``PYTHONPATH``) by importing ``bengal.cli.templates.<name>.template`` and
looking for a module‑level ``TEMPLATE`` variable. The registry provides a small
API to list, retrieve, and register templates programmatically.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

from .base import SiteTemplate, TemplateFile

if TYPE_CHECKING:
    from bengal.cli.skeleton.schema import Component, Skeleton

logger = get_logger(__name__)


class TemplateRegistry:
    """Registry for discovering and managing site templates.

    The registry scans the sibling directories of this file for template
    packages that expose a ``TEMPLATE`` variable.
    """

    def __init__(self) -> None:
        self._templates: dict[str, SiteTemplate] = {}
        self._discover_templates()

    def _discover_templates(self) -> None:
        """Discover all available templates in the built‑in package tree.

        Prefers skeleton.yaml manifests when available, falls back to Python templates.
        """
        templates_dir = Path(__file__).parent

        for item in templates_dir.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            # Check for skeleton manifest first
            skeleton_manifest = item / "skeleton.yaml"
            if skeleton_manifest.exists():
                try:
                    template = self._load_skeleton_template(skeleton_manifest, item.name)
                    if template:
                        self._templates[template.id] = template
                        continue
                except Exception as e:
                    # Fall back to Python template if skeleton fails
                    logger.debug(
                        "skeleton_template_load_failed",
                        template_name=item.name,
                        error=str(e),
                        error_type=type(e).__name__,
                        action="falling_back_to_python_template",
                    )
                    pass

            # Fall back to Python template
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

    def _load_skeleton_template(self, skeleton_path: Path, template_id: str) -> SiteTemplate | None:
        """Load a template from a skeleton manifest.

        Args:
            skeleton_path: Path to skeleton.yaml file
            template_id: Template identifier (directory name)

        Returns:
            SiteTemplate instance or None if loading fails
        """
        from datetime import datetime

        from bengal.cli.skeleton.schema import Skeleton

        skeleton_yaml = skeleton_path.read_text()

        # Replace {{date}} placeholders with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        skeleton_yaml = skeleton_yaml.replace("{{date}}", current_date)

        skeleton = Skeleton.from_yaml(skeleton_yaml)

        # Convert Skeleton to SiteTemplate
        return self._skeleton_to_site_template(skeleton, template_id)

    def _skeleton_to_site_template(self, skeleton: Skeleton, template_id: str) -> SiteTemplate:
        """Convert a Skeleton manifest to a SiteTemplate.

        Args:
            skeleton: Skeleton instance from manifest
            template_id: Template identifier

        Returns:
            SiteTemplate instance
        """

        # Convert Component structure to TemplateFile list
        files = []
        additional_dirs = set()
        menu_sections = []

        def process_component(comp: Component, base_path: str = "") -> None:
            """Recursively process components to build TemplateFile list."""
            full_path = f"{base_path}/{comp.path}" if base_path else comp.path

            # Build frontmatter from component
            frontmatter = {}
            if comp.type:
                frontmatter["type"] = comp.type
            if comp.variant:
                frontmatter["variant"] = comp.variant
            frontmatter.update(comp.props)
            if comp.cascade:
                frontmatter["cascade"] = comp.cascade

            # Generate file content using hydrator's logic
            import yaml

            yaml_str = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
            body = comp.content or ""

            content = f"---\n{yaml_str}\n---\n\n{body}\n"

            # Determine target_dir (content for markdown files)
            target_dir = "content"
            if full_path.endswith(".yaml") or full_path.endswith(".yml"):
                target_dir = "data"

            files.append(
                TemplateFile(relative_path=full_path, content=content, target_dir=target_dir)
            )

            # Track parent directories
            path_parts = full_path.split("/")
            for i in range(1, len(path_parts)):
                dir_path = "/".join(path_parts[:i])
                additional_dirs.add(f"{target_dir}/{dir_path}")

            # Track sections for menu (extract directory name, not filename)
            # Only add directories, not individual files
            if len(path_parts) > 1:  # Has subdirectories
                section_name = path_parts[0]
                # Remove file extension if present
                section_name = (
                    section_name.rsplit(".", 1)[0] if "." in section_name else section_name
                )
                # Skip common index files
                if (
                    section_name
                    and section_name not in ("_index", "index")
                    and section_name not in menu_sections
                ):
                    menu_sections.append(section_name)
            elif comp.type in ("blog", "doc", "section") and "/" in comp.path:
                # Component with type and path suggests it's a section
                section_name = comp.path.split("/")[0]
                if section_name and section_name not in menu_sections:
                    menu_sections.append(section_name)

            # Process child pages
            for child in comp.pages:
                process_component(
                    child, base_path=full_path.rsplit("/", 1)[0] if "/" in full_path else ""
                )

        # Process all top-level components
        for comp in skeleton.structure:
            process_component(comp)

        return SiteTemplate(
            id=template_id,
            name=skeleton.name or template_id.title(),
            description=skeleton.description or f"{template_id.title()} site template",
            files=files,
            additional_dirs=list(additional_dirs),
            menu_sections=menu_sections,
        )

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
