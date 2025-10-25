"""Template system primitives used by all built‑in site templates.

This module defines two dataclasses that describe what a site template is and
the files it contributes when instantiated via CLI commands (e.g.
`bengal new site --template blog`). These classes are intentionally small and
framework‑agnostic so they can be reused by both built‑in and custom templates.

Key concepts:
- ``TemplateFile``: a single file that will be written to a target area of the
  project (``content/``, ``data/``, ``templates/``, etc.).
- ``SiteTemplate``: a collection of ``TemplateFile`` items plus optional
  directory scaffolding and menu hints that describe a complete starter layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TemplateFile:
    """Represents a file to be created from a site template.

    A ``TemplateFile`` encapsulates the rendered content and the relative path
    where the file should be placed inside a specific target area of the
    project tree. The CLI will iterate these instances and write them to disk.

    Attributes:
        relative_path: Project‑relative path under ``target_dir`` (e.g.
            ``"posts/first-post.md"`` or ``"_index.md"``).
        content: The fully rendered file contents to be written.
        target_dir: Top‑level destination directory. Common values are
            ``"content"``, ``"data"``, and ``"templates"``.
    """

    relative_path: str  # Relative path from content/data directory
    content: str
    target_dir: str = "content"  # "content", "data", "templates", etc.


@dataclass
class SiteTemplate:
    """A concrete site template definition.

    A ``SiteTemplate`` declares all files and optional directories that should
    be created when the template is applied. Template providers typically
    construct one instance per template (e.g. ``blog``, ``docs``) and expose it
    via a module‑level ``TEMPLATE`` variable for discovery.

    Attributes:
        id: Stable identifier used from the CLI (e.g. ``"blog"``).
        name: Human‑friendly display name.
        description: One‑line summary shown in listings.
        files: Files to materialize when the template is applied.
        additional_dirs: Extra directories to ensure exist before writing
            files (useful for empty folders that should be tracked).
        menu_sections: Section slugs that can be used by generators to seed a
            default navigation menu for the site.
    """

    id: str
    name: str
    description: str
    files: list[TemplateFile] = field(default_factory=list)
    additional_dirs: list[str] = field(default_factory=list)
    menu_sections: list[str] = field(default_factory=list)  # Sections for auto-menu generation

    def get_files(self) -> list[TemplateFile]:
        """Return all files that should be written for this template.

        Returns:
            A list of ``TemplateFile`` instances in write order.
        """
        return self.files

    def get_additional_dirs(self) -> list[str]:
        """Return additional directories that should be created.

        Returns:
            A list of directory paths (relative to project root).
        """
        return self.additional_dirs

    def get_menu_sections(self) -> list[str]:
        """Return section slugs that can seed menu auto‑generation.

        Returns:
            A list of section identifiers (e.g. ``["posts", "about"]``).
        """
        return self.menu_sections


class TemplateProvider(Protocol):
    """Protocol for template providers.

    Custom template packages can implement this protocol and expose a
    ``get_template`` classmethod that returns a fully constructed
    ``SiteTemplate`` instance. The registry will import such providers during
    discovery.
    """

    @classmethod
    def get_template(cls) -> SiteTemplate:
        """Return the concrete ``SiteTemplate`` definition for this provider."""
        ...
