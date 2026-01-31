"""
Content-aware diffing service for template blocks.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)

BlockDiffService is a refactored version of block_detector.py that integrates
with the Effect system. It performs specialized content-aware diffing to
determine if a dependency change actually necessitates a re-render.

Key optimizations:
- Ignore frontmatter-only changes for content-only rebuilds
- Detect site-scoped block changes (nav, footer, header)
- Skip page rebuilds when only site-scoped blocks change
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.snapshots.types import PageSnapshot, SiteSnapshot


@dataclass(frozen=True, slots=True)
class DiffResult:
    """
    Result of content-aware diffing.

    Attributes:
        requires_rebuild: Whether the change requires a rebuild
        reason: Human-readable reason for the decision
        affected_blocks: Blocks that changed (if template change)
        is_content_only: Whether only content changed (no metadata)
        is_metadata_only: Whether only metadata changed (no content)
    """

    requires_rebuild: bool
    reason: str
    affected_blocks: frozenset[str] = field(default_factory=frozenset)
    is_content_only: bool = False
    is_metadata_only: bool = False


class BlockDiffService:
    """
    Content-aware diffing for determining rebuild necessity.

    Integrates with the Effect system to provide smart rebuild decisions.

    Features:
    - Frontmatter-only change detection
    - Site-scoped vs page-scoped block differentiation
    - Content hash comparison for quick change detection

    Usage:
        >>> service = BlockDiffService(old_snapshot, new_snapshot)
        >>> result = service.diff_page(page_path)
        >>> if result.requires_rebuild:
        ...     rebuild(page_path)
    """

    # Blocks that are site-scoped (don't require page rebuilds)
    SITE_SCOPED_BLOCKS = frozenset({
        "nav",
        "navigation",
        "header",
        "footer",
        "sidebar",
        "menu",
        "breadcrumbs",
    })

    def __init__(
        self,
        old_snapshot: SiteSnapshot | None,
        new_snapshot: SiteSnapshot,
    ) -> None:
        """
        Initialize diff service.

        Args:
            old_snapshot: Previous build snapshot (None for fresh build)
            new_snapshot: Current snapshot
        """
        self._old = old_snapshot
        self._new = new_snapshot

        # Build page lookup maps
        self._old_pages: dict[Path, PageSnapshot] = {}
        if old_snapshot:
            self._old_pages = {p.source_path: p for p in old_snapshot.pages}

        self._new_pages: dict[Path, PageSnapshot] = {
            p.source_path: p for p in new_snapshot.pages
        }

    def diff_page(self, source_path: Path) -> DiffResult:
        """
        Determine if a page needs rebuilding.

        Args:
            source_path: Path to the page source file

        Returns:
            DiffResult with rebuild decision and reason
        """
        new_page = self._new_pages.get(source_path)
        if not new_page:
            return DiffResult(
                requires_rebuild=False,
                reason="Page no longer exists",
            )

        old_page = self._old_pages.get(source_path)
        if not old_page:
            return DiffResult(
                requires_rebuild=True,
                reason="New page",
            )

        # Fast path: content hash comparison
        if old_page.content_hash == new_page.content_hash:
            # Check if metadata changed
            if old_page.metadata == new_page.metadata:
                return DiffResult(
                    requires_rebuild=False,
                    reason="No changes (hash match)",
                )
            else:
                # Metadata changed but content didn't
                return self._analyze_metadata_change(old_page, new_page)

        # Content changed - analyze the diff
        return self._analyze_content_change(old_page, new_page)

    def _analyze_metadata_change(
        self,
        old_page: PageSnapshot,
        new_page: PageSnapshot,
    ) -> DiffResult:
        """Analyze metadata-only changes."""
        # Check what metadata fields changed
        old_meta = dict(old_page.metadata)
        new_meta = dict(new_page.metadata)

        # Fields that don't require rebuild
        ignore_fields = {"_parsed_at", "_build_id", "_generated"}

        changed_fields = set()
        for key in set(old_meta.keys()) | set(new_meta.keys()):
            if key in ignore_fields:
                continue
            if old_meta.get(key) != new_meta.get(key):
                changed_fields.add(key)

        if not changed_fields:
            return DiffResult(
                requires_rebuild=False,
                reason="Only internal metadata changed",
                is_metadata_only=True,
            )

        # Some metadata changes don't require full rebuild
        display_only_fields = {"reading_time", "word_count", "excerpt"}
        if changed_fields <= display_only_fields:
            return DiffResult(
                requires_rebuild=True,
                reason=f"Display metadata changed: {changed_fields}",
                is_metadata_only=True,
            )

        return DiffResult(
            requires_rebuild=True,
            reason=f"Metadata changed: {changed_fields}",
            is_metadata_only=True,
        )

    def _analyze_content_change(
        self,
        old_page: PageSnapshot,
        new_page: PageSnapshot,
    ) -> DiffResult:
        """Analyze content changes."""
        # Check if only frontmatter changed
        old_content = self._extract_body(old_page.content)
        new_content = self._extract_body(new_page.content)

        if old_content == new_content:
            return DiffResult(
                requires_rebuild=True,
                reason="Frontmatter changed",
                is_metadata_only=True,
            )

        return DiffResult(
            requires_rebuild=True,
            reason="Content changed",
            is_content_only=True,
        )

    def _extract_body(self, content: str) -> str:
        """Extract body content (after frontmatter)."""
        if not content.startswith("---"):
            return content

        # Find end of frontmatter
        lines = content.split("\n")
        in_frontmatter = False
        body_start = 0

        for i, line in enumerate(lines):
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    body_start = i + 1
                    break

        return "\n".join(lines[body_start:])

    def diff_template(
        self,
        template_name: str,
        changed_blocks: frozenset[str] | None = None,
    ) -> DiffResult:
        """
        Determine rebuild impact of a template change.

        Args:
            template_name: Name of the changed template
            changed_blocks: Specific blocks that changed (if known)

        Returns:
            DiffResult indicating rebuild necessity
        """
        if changed_blocks is None:
            # Can't determine specific blocks - require rebuild
            return DiffResult(
                requires_rebuild=True,
                reason="Template changed (blocks unknown)",
            )

        # Check if only site-scoped blocks changed
        page_scoped_changes = changed_blocks - self.SITE_SCOPED_BLOCKS

        if not page_scoped_changes:
            return DiffResult(
                requires_rebuild=False,
                reason="Only site-scoped blocks changed",
                affected_blocks=changed_blocks,
            )

        return DiffResult(
            requires_rebuild=True,
            reason=f"Page-scoped blocks changed: {page_scoped_changes}",
            affected_blocks=changed_blocks,
        )

    def get_affected_pages(
        self,
        changed_paths: set[Path],
    ) -> set[Path]:
        """
        Get pages affected by file changes.

        Uses content-aware diffing to minimize rebuilds.

        Args:
            changed_paths: Files that changed

        Returns:
            Set of page source paths that need rebuilding
        """
        affected: set[Path] = set()

        for path in changed_paths:
            # Direct page change
            if path in self._new_pages:
                result = self.diff_page(path)
                if result.requires_rebuild:
                    affected.add(path)

            # Template change
            elif path.suffix in (".html", ".jinja", ".j2"):
                template_name = path.name
                template_result = self.diff_template(template_name)

                if template_result.requires_rebuild:
                    # Find all pages using this template
                    for page_path, page in self._new_pages.items():
                        if page.template_name == template_name:
                            affected.add(page_path)
                        # Also check template dependencies
                        if template_name in self._new.templates:
                            template_snap = self._new.templates[template_name]
                            if page.template_name in template_snap.all_dependencies:
                                affected.add(page_path)

        return affected


def compute_content_hash(content: str) -> str:
    """
    Compute content hash for change detection.

    Args:
        content: Raw content string

    Returns:
        SHA-256 hash (first 16 chars)
    """
    return hashlib.sha256(content.encode()).hexdigest()[:16]
