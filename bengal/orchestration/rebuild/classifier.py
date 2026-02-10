"""
Rebuild classification service for server file-change events.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bengal.orchestration.rebuild.types import RebuildDecision
from bengal.utils.paths.normalize import to_posix

SVG_THEMES_SEGMENT = "/themes/"
SVG_ICONS_SEGMENT = "/assets/icons/"


class RebuildClassifier:
    """Pure classification logic for full vs incremental rebuild decisions."""

    def classify(
        self,
        changed_paths: set[Path],
        event_types: set[str],
        *,
        is_template_change: Callable[[set[Path]], bool],
        should_regenerate_autodoc: Callable[[set[Path]], bool],
        is_shared_content_change: Callable[[set[Path]], bool],
        is_version_config_change: Callable[[set[Path]], bool],
    ) -> RebuildDecision:
        """Classify this change set using injected predicates."""
        if {"created", "deleted", "moved"} & event_types:
            return RebuildDecision(full_rebuild=True, reason="structural")

        if is_template_change(changed_paths):
            return RebuildDecision(full_rebuild=True, reason="template")

        if should_regenerate_autodoc(changed_paths):
            return RebuildDecision(full_rebuild=True, reason="autodoc")

        for path in changed_paths:
            path_str = to_posix(path)
            if (
                path.suffix.lower() == ".svg"
                and SVG_THEMES_SEGMENT in path_str
                and SVG_ICONS_SEGMENT in path_str
            ):
                return RebuildDecision(full_rebuild=True, reason="svg-icon")

        if is_shared_content_change(changed_paths):
            return RebuildDecision(full_rebuild=True, reason="shared-content")

        if is_version_config_change(changed_paths):
            return RebuildDecision(full_rebuild=True, reason="version-config")

        return RebuildDecision(full_rebuild=False, reason="incremental")
