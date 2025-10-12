"""Base classes for site templates."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TemplateFile:
    """Represents a file to be created from a template."""

    relative_path: str  # Relative path from content/data directory
    content: str
    target_dir: str = "content"  # "content", "data", "templates", etc.


@dataclass
class SiteTemplate:
    """Base class for site templates."""

    id: str
    name: str
    description: str
    files: list[TemplateFile] = field(default_factory=list)
    additional_dirs: list[str] = field(default_factory=list)
    menu_sections: list[str] = field(default_factory=list)  # Sections for auto-menu generation

    def get_files(self) -> list[TemplateFile]:
        """Get all files for this template."""
        return self.files

    def get_additional_dirs(self) -> list[str]:
        """Get additional directories to create."""
        return self.additional_dirs

    def get_menu_sections(self) -> list[str]:
        """Get sections for menu auto-generation."""
        return self.menu_sections


class TemplateProvider(Protocol):
    """Protocol for template providers."""

    @classmethod
    def get_template(cls) -> SiteTemplate:
        """Return the site template."""
        ...
