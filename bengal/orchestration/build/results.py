"""
Result dataclasses for build orchestration phases.

Provides typed dataclasses for better type safety, readability, and IDE support.

All dataclasses support convenient access patterns:
- Tuple unpacking via __iter__() methods
- Dict-like access for ChangeSummary (to_dict(), items(), get(), __getitem__())

See Also:
    - plan/active/rfc-dataclass-improvements.md - Design rationale
"""

from __future__ import annotations

from collections.abc import ItemsView
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.page import Page


@dataclass
class ConfigCheckResult:
    """
    Result of configuration check phase.

    Determines whether incremental builds are still valid after
    checking for configuration changes.

    Attributes:
        incremental: Whether incremental build should proceed (False if config changed)
        config_changed: Whether configuration file was modified
    """

    incremental: bool
    config_changed: bool

    def __iter__(self) -> tuple[bool, bool]:
        """Allow tuple unpacking."""
        return (self.incremental, self.config_changed)


@dataclass
class FilterResult:
    """
    Result of incremental filtering phase.

    Contains the work items and change information determined during
    Phase 5: Incremental Filtering.

    Attributes:
        pages_to_build: Pages that need rendering (changed or dependent)
        assets_to_process: Assets that need processing
        affected_tags: Tags that have changed (triggers taxonomy rebuild)
        changed_page_paths: Source paths of changed pages
        affected_sections: Sections with changes (None if all sections affected)
    """

    pages_to_build: list[Page]
    assets_to_process: list[Asset]
    affected_tags: set[str]
    changed_page_paths: set[Path]
    affected_sections: set[str] | None

    def __iter__(
        self,
    ) -> tuple[list[Page], list[Asset], set[str], set[Path], set[str] | None]:
        """Allow tuple unpacking."""
        return (
            self.pages_to_build,
            self.assets_to_process,
            self.affected_tags,
            self.changed_page_paths,
            self.affected_sections,
        )


@dataclass
class ChangeSummary:
    """
    Summary of changes detected during incremental build.

    Used for verbose logging and debugging. Contains lists of paths
    that changed, organized by change type.

    Attributes:
        modified_content: Source paths of modified content files
        modified_assets: Paths of modified asset files
        modified_templates: Paths of modified template files
        taxonomy_changes: Tag slugs that have taxonomy changes
        extra_changes: Additional dynamic change types (e.g., "Cascade changes", "Navigation changes")
    """

    modified_content: list[Path] = field(default_factory=list)
    modified_assets: list[Path] = field(default_factory=list)
    modified_templates: list[Path] = field(default_factory=list)
    taxonomy_changes: list[str] = field(default_factory=list)
    extra_changes: dict[str, list[Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, list[Any]]:
        """
        Convert to dict format.

        Returns dict with string keys matching the original format.
        """
        result: dict[str, list[Any]] = {}
        if self.modified_content:
            result["Modified content"] = self.modified_content
        if self.modified_assets:
            result["Modified assets"] = self.modified_assets
        if self.modified_templates:
            result["Modified templates"] = self.modified_templates
        if self.taxonomy_changes:
            result["Taxonomy changes"] = self.taxonomy_changes
        # Merge extra_changes
        result.update(self.extra_changes)
        return result

    def items(self) -> ItemsView[str, list[Any]]:
        """Allow dict-like iteration."""
        return self.to_dict().items()

    def get(self, key: str, default: list[Any] | None = None) -> list[Any]:
        """Allow dict-like get()."""
        result = self.to_dict().get(key, default)
        return result if result is not None else []

    def __getitem__(self, key: str) -> list[Any]:
        """Allow dict-like indexing."""
        result = self.to_dict()
        if key not in result:
            # Return empty list for missing keys to match original dict behavior
            return []
        return result[key]

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return key in self.to_dict()
