"""
Version diff utility for comparing documentation between versions.

This module provides utilities for:
    - Diffing content between versions
    - Identifying new, changed, and removed pages
    - Generating migration guides based on diffs

Related:
    - bengal/core/version.py: Version models
    - bengal/discovery/git_version_adapter.py: Git version adapter
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class PageDiff:
    """
    Represents the diff between two versions of a page.

    Attributes:
        path: Logical path of the page (e.g., "docs/guide.md")
        status: Change status ("added", "modified", "removed", "unchanged")
        old_content: Content in the older version (None if added)
        new_content: Content in the newer version (None if removed)
        diff_lines: Unified diff output (if modified)
        change_percentage: Percentage of content changed
    """

    path: str
    status: str  # "added", "modified", "removed", "unchanged"
    old_content: str | None = None
    new_content: str | None = None
    diff_lines: list[str] = field(default_factory=list)
    change_percentage: float = 0.0


@dataclass
class VersionDiff:
    """
    Represents the diff between two versions.

    Attributes:
        old_version: Older version ID
        new_version: Newer version ID
        added_pages: Pages that exist only in new version
        removed_pages: Pages that exist only in old version
        modified_pages: Pages that exist in both but have changes
        unchanged_pages: Pages that are identical
    """

    old_version: str
    new_version: str
    added_pages: list[PageDiff] = field(default_factory=list)
    removed_pages: list[PageDiff] = field(default_factory=list)
    modified_pages: list[PageDiff] = field(default_factory=list)
    unchanged_pages: list[PageDiff] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        """Total number of changed pages."""
        return len(self.added_pages) + len(self.removed_pages) + len(self.modified_pages)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes between versions."""
        return self.total_changes > 0

    def summary(self) -> str:
        """Generate a summary of changes."""
        lines = [
            f"Version diff: {self.old_version} → {self.new_version}",
            f"  Added: {len(self.added_pages)} pages",
            f"  Removed: {len(self.removed_pages)} pages",
            f"  Modified: {len(self.modified_pages)} pages",
            f"  Unchanged: {len(self.unchanged_pages)} pages",
        ]
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Generate a markdown changelog."""
        lines = [
            f"# Changes: {self.old_version} → {self.new_version}",
            "",
        ]

        if self.added_pages:
            lines.append("## ✨ New Pages")
            lines.append("")
            for page in self.added_pages:
                lines.append(f"- `{page.path}`")
            lines.append("")

        if self.removed_pages:
            lines.append("## 🗑️ Removed Pages")
            lines.append("")
            for page in self.removed_pages:
                lines.append(f"- `{page.path}`")
            lines.append("")

        if self.modified_pages:
            lines.append("## 📝 Modified Pages")
            lines.append("")
            for page in self.modified_pages:
                lines.append(f"- `{page.path}` ({page.change_percentage:.1f}% changed)")
            lines.append("")

        if not self.has_changes:
            lines.append("No changes between versions.")

        return "\n".join(lines)


class VersionDiffer:
    """
    Compares content between two versions.

    Can work with:
    - Folder-based versions (comparing directories)
    - Git-based versions (comparing branches/tags)
    """

    def __init__(
        self,
        old_path: Path,
        new_path: Path,
        content_extensions: list[str] | None = None,
    ) -> None:
        """
        Initialize the version differ.

        Args:
            old_path: Path to older version content
            new_path: Path to newer version content
            content_extensions: File extensions to compare (default: [".md", ".rst"])
        """
        self.old_path = old_path
        self.new_path = new_path
        self.content_extensions = content_extensions or [".md", ".rst"]

    def diff(self, old_version_id: str, new_version_id: str) -> VersionDiff:
        """
        Compare two versions and return the diff.

        Args:
            old_version_id: ID of the older version
            new_version_id: ID of the newer version

        Returns:
            VersionDiff containing all changes
        """
        result = VersionDiff(
            old_version=old_version_id,
            new_version=new_version_id,
        )

        # Get all content files in each version
        old_files = self._get_content_files(self.old_path)
        new_files = self._get_content_files(self.new_path)

        # Find added pages (in new, not in old)
        for path in new_files - old_files:
            content = (self.new_path / path).read_text(encoding="utf-8")
            result.added_pages.append(
                PageDiff(
                    path=path,
                    status="added",
                    new_content=content,
                )
            )

        # Find removed pages (in old, not in new)
        for path in old_files - new_files:
            content = (self.old_path / path).read_text(encoding="utf-8")
            result.removed_pages.append(
                PageDiff(
                    path=path,
                    status="removed",
                    old_content=content,
                )
            )

        # Compare pages that exist in both
        for path in old_files & new_files:
            old_content = (self.old_path / path).read_text(encoding="utf-8")
            new_content = (self.new_path / path).read_text(encoding="utf-8")

            if old_content == new_content:
                result.unchanged_pages.append(
                    PageDiff(
                        path=path,
                        status="unchanged",
                        old_content=old_content,
                        new_content=new_content,
                    )
                )
            else:
                # Generate diff
                diff_lines = list(
                    difflib.unified_diff(
                        old_content.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                    )
                )

                # Calculate change percentage
                change_percentage = self._calculate_change_percentage(old_content, new_content)

                result.modified_pages.append(
                    PageDiff(
                        path=path,
                        status="modified",
                        old_content=old_content,
                        new_content=new_content,
                        diff_lines=diff_lines,
                        change_percentage=change_percentage,
                    )
                )

        logger.info(
            "version_diff_complete",
            old=old_version_id,
            new=new_version_id,
            added=len(result.added_pages),
            removed=len(result.removed_pages),
            modified=len(result.modified_pages),
        )

        return result

    def _get_content_files(self, path: Path) -> set[str]:
        """Get all content files in a path as relative path strings."""
        files: set[str] = set()

        if not path.exists():
            return files

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.content_extensions:
                # Get relative path as string
                rel_path = str(file_path.relative_to(path))
                files.add(rel_path)

        return files

    def _calculate_change_percentage(self, old: str, new: str) -> float:
        """Calculate what percentage of content changed."""
        if not old and not new:
            return 0.0
        if not old:
            return 100.0
        if not new:
            return 100.0

        # Use SequenceMatcher to calculate similarity
        matcher = difflib.SequenceMatcher(None, old, new)
        similarity = matcher.ratio()

        # Convert to change percentage
        return (1.0 - similarity) * 100


def diff_git_versions(
    repo_path: Path,
    old_ref: str,
    new_ref: str,
    content_dir: str = "docs",
) -> VersionDiff:
    """
    Diff two git refs (branches/tags) without checking out.

    Uses git diff-tree to compare file lists and git show
    to get file contents.

    Args:
        repo_path: Path to git repository
        old_ref: Old git ref (branch/tag/commit)
        new_ref: New git ref (branch/tag/commit)
        content_dir: Content directory to compare

    Returns:
        VersionDiff with changes between refs
    """
    import subprocess

    result = VersionDiff(
        old_version=old_ref,
        new_version=new_ref,
    )

    # Get list of changed files using git diff
    try:
        diff_output = subprocess.run(
            ["git", "diff", "--name-status", f"{old_ref}..{new_ref}", "--", content_dir],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error("git_diff_failed", error=e.stderr)
        return result

    # Parse diff output
    for line in diff_output.stdout.strip().split("\n"):
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status, path = parts[0], parts[1]

        # Only process content files
        if not any(path.endswith(ext) for ext in [".md", ".rst"]):
            continue

        if status == "A":
            # Added
            content = _git_show_file(repo_path, new_ref, path)
            result.added_pages.append(PageDiff(path=path, status="added", new_content=content))
        elif status == "D":
            # Deleted
            content = _git_show_file(repo_path, old_ref, path)
            result.removed_pages.append(PageDiff(path=path, status="removed", old_content=content))
        elif status.startswith("M") or status.startswith("R"):
            # Modified or Renamed
            old_content = _git_show_file(repo_path, old_ref, path)
            new_content = _git_show_file(repo_path, new_ref, path)

            if old_content != new_content:
                diff_lines = list(
                    difflib.unified_diff(
                        (old_content or "").splitlines(keepends=True),
                        (new_content or "").splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                    )
                )

                # Calculate change percentage
                matcher = difflib.SequenceMatcher(None, old_content or "", new_content or "")
                change_pct = (1.0 - matcher.ratio()) * 100

                result.modified_pages.append(
                    PageDiff(
                        path=path,
                        status="modified",
                        old_content=old_content,
                        new_content=new_content,
                        diff_lines=diff_lines,
                        change_percentage=change_pct,
                    )
                )

    return result


def _git_show_file(repo_path: Path, ref: str, path: str) -> str | None:
    """Get file content from a specific git ref."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None
