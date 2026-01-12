"""
Taxonomy and autodoc change detection for incremental builds.

Handles checking for tag changes and autodoc source file changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)


class TaxonomyChangeDetector:
    """
    Detects changes in taxonomies (tags) and autodoc sources.

    Handles:
    - Tag changes on pages (added/removed tags)
    - Autodoc source file changes
    - Archive page rebuilds when sections change
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
    ) -> None:
        """
        Initialize taxonomy change detector.

        Args:
            site: Site instance for content access
            cache: BuildCache for change detection
        """
        self.site = site
        self.cache = cache

    def check_taxonomy_changes(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check for taxonomy (tag) changes in full phase."""
        affected_tags: set[str] = set()
        affected_sections: set[Section] = set()

        for page in self.site.regular_pages:
            if page.source_path in pages_to_rebuild:
                old_tags = self.cache.get_previous_tags(page.source_path)
                new_tags = set(page.tags) if page.tags else set()

                added_tags = new_tags - old_tags
                removed_tags = old_tags - new_tags

                for tag in added_tags | removed_tags:
                    # Ensure tag is a string (YAML may parse 'null' as None)
                    if tag is not None:
                        affected_tags.add(str(tag).lower().replace(" ", "-"))
                    if verbose:
                        change_summary.extra_changes.setdefault("Taxonomy changes", [])
                        change_summary.extra_changes["Taxonomy changes"].append(
                            f"Tag '{tag}' changed on {page.source_path.name}"
                        )

                if hasattr(page, "section"):
                    affected_sections.add(page.section)

        if affected_tags:
            for page in self.site.generated_pages:
                if page.metadata.get("type") in ("tag", "tag-index"):
                    tag_slug = page.metadata.get("_tag_slug")
                    if (
                        tag_slug
                        and tag_slug in affected_tags
                        or page.metadata.get("type") == "tag-index"
                    ):
                        pages_to_rebuild.add(page.source_path)

        if affected_sections:
            for page in self.site.pages:
                if page.metadata.get("_generated") and page.metadata.get("type") == "archive":
                    page_section = page.metadata.get("_section")
                    if page_section and page_section in affected_sections:
                        pages_to_rebuild.add(page.source_path)

    def check_autodoc_changes(
        self,
        *,
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> set[str]:
        """
        Check for autodoc source file changes.

        Uses two detection mechanisms:
        1. Standard change detection (mtime-based via is_changed)
        2. Self-validation (hash-based via get_stale_autodoc_sources)

        The self-validation provides defense-in-depth: even if CI cache keys
        are incorrect, Bengal will detect stale autodoc sources and rebuild
        affected pages automatically.

        See: plan/rfc-ci-cache-inputs.md (Phase 4: Self-Validating Cache)
        """
        autodoc_pages_to_rebuild: set[str] = set()

        if not hasattr(self.cache, "autodoc_dependencies") or not hasattr(
            self.cache, "get_autodoc_source_files"
        ):
            return autodoc_pages_to_rebuild

        try:

            def _is_external_autodoc_source(path: Path) -> bool:
                parts = path.parts
                return (
                    "site-packages" in parts
                    or "dist-packages" in parts
                    or ".venv" in parts
                    or ".tox" in parts
                )

            # Method 1: Standard change detection (mtime-based)
            source_files = self.cache.get_autodoc_source_files()
            if source_files:
                for source_file in source_files:
                    source_path = Path(source_file)
                    if _is_external_autodoc_source(source_path):
                        continue
                    if self.cache.is_changed(source_path):
                        affected_pages = self.cache.get_affected_autodoc_pages(source_path)
                        if affected_pages:
                            autodoc_pages_to_rebuild.update(affected_pages)

                            if verbose:
                                if "Autodoc changes" not in change_summary.extra_changes:
                                    change_summary.extra_changes["Autodoc changes"] = []
                                msg = f"{source_path.name} changed"
                                msg += f", affects {len(affected_pages)}"
                                msg += " autodoc pages"
                                change_summary.extra_changes["Autodoc changes"].append(msg)

            # Method 2: Self-validation (hash-based) - defense in depth
            # This catches stale autodoc even when CI cache keys are incorrect
            if hasattr(self.cache, "get_stale_autodoc_sources"):
                stale_sources = self.cache.get_stale_autodoc_sources(self.site.root_path)
                if stale_sources:
                    for source_key in stale_sources:
                        affected_pages = self.cache.get_affected_autodoc_pages(source_key)
                        if affected_pages:
                            autodoc_pages_to_rebuild.update(affected_pages)

                            if verbose:
                                if "Autodoc self-validation" not in change_summary.extra_changes:
                                    change_summary.extra_changes["Autodoc self-validation"] = []
                                source_name = Path(source_key).name
                                msg = f"{source_name} stale (hash mismatch)"
                                msg += f", affects {len(affected_pages)}"
                                msg += " autodoc pages"
                                change_summary.extra_changes["Autodoc self-validation"].append(msg)

                    logger.info(
                        "autodoc_self_validation_detected_stale",
                        stale_count=len(stale_sources),
                        affected_pages=len(autodoc_pages_to_rebuild),
                    )

            if autodoc_pages_to_rebuild:
                logger.info(
                    "autodoc_selective_rebuild",
                    affected_pages=len(autodoc_pages_to_rebuild),
                    reason="source_files_changed",
                )
        except (TypeError, AttributeError):
            pass

        return autodoc_pages_to_rebuild
