"""
Git version adapter for discovering documentation versions from branches/tags.

This module provides the GitVersionAdapter for building versioned documentation
from Git branches and tags without requiring folder duplication.

Key Features:
    - Discover versions from Git branches matching patterns (e.g., `release/*`)
    - Support both branches and tags as version sources
    - Use Git worktrees for parallel builds of multiple versions
    - Cache worktrees to avoid repeated checkouts
    - Track commits for incremental build detection

Architecture:
    The adapter integrates with Bengal's versioning system by:
    1. Discovering branches/tags matching configured patterns
    2. Creating Version objects for each match
    3. Managing worktrees for building each version
    4. Cleaning up worktrees after builds complete

    This enables single-source versioned documentation where different versions
    live in different Git branches, avoiding folder duplication.

Related:
    - bengal/core/version.py: Version and GitVersionConfig models
    - bengal/orchestration/build_orchestrator.py: Multi-version builds
    - bengal/discovery/version_resolver.py: Path resolution for versions

Example:
    >>> from bengal.discovery import GitVersionAdapter
    >>> from bengal.core.version import GitVersionConfig, GitBranchPattern
    >>> from pathlib import Path
    >>>
    >>> config = GitVersionConfig(
    ...     branches=[
    ...         GitBranchPattern(name="main", latest=True),
    ...         GitBranchPattern(pattern="release/*", strip_prefix="release/"),
    ...     ],
    ... )
    >>> adapter = GitVersionAdapter(Path("."), config)
    >>> versions = adapter.discover_versions()
    >>> for v in versions:
    ...     print(f"{v.id}: {v.source}")
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.version import GitVersionConfig, Version

logger = get_logger(__name__)


@dataclass
class GitRef:
    """
    Represents a Git reference (branch or tag).

    Attributes:
        name: Full ref name (e.g., "refs/heads/release/0.1.6")
        short_name: Short name (e.g., "release/0.1.6")
        commit: Commit SHA
        ref_type: Type of ref ("branch" or "tag")
    """

    name: str
    short_name: str
    commit: str
    ref_type: str  # "branch" or "tag"


@dataclass
class GitWorktree:
    """
    Represents a Git worktree for a version.

    Attributes:
        version_id: Version ID this worktree is for
        path: Path to the worktree directory
        ref: Git ref (branch/tag) checked out
        commit: Commit SHA checked out
    """

    version_id: str
    path: Path
    ref: str
    commit: str


class GitVersionAdapter:
    """
    Discovers and manages versioned documentation from Git branches/tags.

    This adapter enables building documentation from multiple Git branches
    without requiring folder duplication. It uses Git worktrees for
    parallel builds.

    Attributes:
        repo_path: Path to the Git repository
        config: Git versioning configuration
        worktrees_dir: Directory for worktrees (default: .bengal/worktrees)

    Example:
        >>> adapter = GitVersionAdapter(Path("."), git_config)
        >>>
        >>> # Discover versions from branches
        >>> versions = adapter.discover_versions()
        >>>
        >>> # Get worktree for a version
        >>> worktree = adapter.get_or_create_worktree("0.1.6")
        >>> print(worktree.path)  # .bengal/worktrees/0.1.6
        >>>
        >>> # Build from worktree path
        >>> site = Site(root_path=worktree.path)
        >>>
        >>> # Cleanup
        >>> adapter.cleanup_worktrees()
    """

    def __init__(
        self,
        repo_path: Path,
        config: GitVersionConfig,
        worktrees_dir: Path | None = None,
    ) -> None:
        """
        Initialize the Git version adapter.

        Args:
            repo_path: Path to the Git repository root
            config: Git versioning configuration
            worktrees_dir: Directory for worktrees (default: .bengal/worktrees)
        """
        self.repo_path = repo_path.resolve()
        self.config = config
        self.worktrees_dir = worktrees_dir or (repo_path / ".bengal" / "worktrees")

        # Cache for discovered refs
        self._refs_cache: list[GitRef] | None = None

        # Active worktrees
        self._worktrees: dict[str, GitWorktree] = {}

    def discover_versions(self) -> list[Version]:
        """
        Discover versions from Git branches and tags.

        Scans Git refs matching configured patterns and creates
        Version objects for each match.

        Returns:
            List of Version objects discovered from Git

        Raises:
            RuntimeError: If Git commands fail
        """
        from bengal.core.version import Version

        versions: list[Version] = []
        refs = self._get_refs()

        # Match branches
        for pattern in self.config.branches:
            for ref in refs:
                if ref.ref_type != "branch":
                    continue
                if pattern.matches(ref.short_name):
                    version_id = pattern.extract_version_id(ref.short_name)
                    versions.append(
                        Version(
                            id=version_id,
                            source=f"git:{ref.short_name}",
                            label=version_id,
                            latest=pattern.latest,
                        )
                    )
                    logger.debug(
                        "git_version_discovered",
                        version_id=version_id,
                        ref=ref.short_name,
                        type="branch",
                    )

        # Match tags
        for pattern in self.config.tags:
            for ref in refs:
                if ref.ref_type != "tag":
                    continue
                if pattern.matches(ref.short_name):
                    version_id = pattern.extract_version_id(ref.short_name)
                    versions.append(
                        Version(
                            id=version_id,
                            source=f"git:{ref.short_name}",
                            label=version_id,
                            latest=pattern.latest,
                        )
                    )
                    logger.debug(
                        "git_version_discovered",
                        version_id=version_id,
                        ref=ref.short_name,
                        type="tag",
                    )

        # Sort by version ID (reverse for semantic versioning)
        versions.sort(key=lambda v: v.id, reverse=True)

        logger.info(
            "git_versions_discovered",
            count=len(versions),
            versions=[v.id for v in versions[:5]],  # Log first 5
        )

        return versions

    def get_or_create_worktree(self, version_id: str, ref: str) -> GitWorktree:
        """
        Get or create a worktree for a version.

        Uses Git worktrees to check out a specific ref without
        affecting the main working directory.

        Args:
            version_id: Version ID for the worktree
            ref: Git ref to check out (branch name or tag)

        Returns:
            GitWorktree with path to the checked-out content

        Raises:
            RuntimeError: If worktree creation fails
        """
        # Check cache first
        if version_id in self._worktrees:
            worktree = self._worktrees[version_id]
            if worktree.path.exists():
                return worktree

        # Create worktree directory
        worktree_path = self.worktrees_dir / version_id
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing worktree if it exists but is stale
        if worktree_path.exists():
            self._remove_worktree(worktree_path)

        # Create new worktree
        try:
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(
                "git_worktree_created",
                version_id=version_id,
                ref=ref,
                path=str(worktree_path),
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                "git_worktree_failed",
                version_id=version_id,
                ref=ref,
                error=e.stderr,
            )
            from bengal.errors import BengalDiscoveryError

            raise BengalDiscoveryError(
                f"Failed to create worktree for {ref}: {e.stderr}",
                suggestion="Check git repository state and permissions. Ensure git is installed and the repository is accessible.",
                original_error=e,
            ) from e

        # Get commit SHA
        commit = self._get_commit_sha(ref)

        worktree = GitWorktree(
            version_id=version_id,
            path=worktree_path,
            ref=ref,
            commit=commit,
        )
        self._worktrees[version_id] = worktree

        return worktree

    def cleanup_worktrees(self, keep_cached: bool = False) -> None:
        """
        Clean up worktrees after builds complete.

        Args:
            keep_cached: If True, keep worktrees for faster rebuilds
        """
        if keep_cached and self.config.cache_worktrees:
            logger.debug("git_worktrees_cached", count=len(self._worktrees))
            return

        for version_id, worktree in list(self._worktrees.items()):
            self._remove_worktree(worktree.path)
            del self._worktrees[version_id]

        logger.info("git_worktrees_cleaned", count=len(self._worktrees))

    def is_version_changed(self, version_id: str, cached_commit: str | None) -> bool:
        """
        Check if a version has changed since last build.

        Args:
            version_id: Version ID to check
            cached_commit: Commit SHA from last build (or None)

        Returns:
            True if version has changed (or no cache)
        """
        if cached_commit is None:
            return True

        worktree = self._worktrees.get(version_id)
        if worktree is None:
            return True

        return worktree.commit != cached_commit

    def _get_refs(self) -> list[GitRef]:
        """Get all Git refs (branches and tags)."""
        if self._refs_cache is not None:
            return self._refs_cache

        refs: list[GitRef] = []

        # Get branches
        try:
            result = subprocess.run(
                ["git", "for-each-ref", "--format=%(refname)\t%(objectname)", "refs/heads/"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    ref_name, commit = parts
                    short_name = ref_name.replace("refs/heads/", "")
                    refs.append(
                        GitRef(
                            name=ref_name,
                            short_name=short_name,
                            commit=commit,
                            ref_type="branch",
                        )
                    )
        except subprocess.CalledProcessError as e:
            logger.warning("git_branches_failed", error=e.stderr)

        # Get tags
        try:
            result = subprocess.run(
                ["git", "for-each-ref", "--format=%(refname)\t%(objectname)", "refs/tags/"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    ref_name, commit = parts
                    short_name = ref_name.replace("refs/tags/", "")
                    refs.append(
                        GitRef(
                            name=ref_name,
                            short_name=short_name,
                            commit=commit,
                            ref_type="tag",
                        )
                    )
        except subprocess.CalledProcessError as e:
            logger.warning("git_tags_failed", error=e.stderr)

        self._refs_cache = refs
        return refs

    def _get_commit_sha(self, ref: str) -> str:
        """Get the commit SHA for a ref."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def _remove_worktree(self, path: Path) -> None:
        """Remove a worktree."""
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(path)],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            # Fallback: manually remove directory
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

        # Prune worktree list
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repo_path,
            capture_output=True,
        )
