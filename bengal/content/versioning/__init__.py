"""
Version management for Bengal SSG.

This package provides versioning support for building multi-version documentation
from Git branches/tags or folder-based version sources.

Components:
GitVersionAdapter: Discovers versions from Git branches and tags.
    Manages worktrees for parallel multi-version builds.
VersionResolver: Resolves versioned content paths, manages shared content
    injection, and handles cross-version linking.

Architecture:
Versioning modules handle version discovery and path resolution. They integrate
with content discovery but operate independently from rendering. Git worktree
management enables parallel builds of multiple versions.

Related:
- bengal/core/version.py: Version and GitVersionConfig models
- bengal/content/discovery/: Content discovery (uses versioning)
- bengal/orchestration/build_orchestrator.py: Multi-version builds

Example:
    >>> from bengal.content.versioning import GitVersionAdapter, VersionResolver
    >>> from bengal.core.version import GitVersionConfig
    >>> from pathlib import Path
    >>>
    >>> # Git-based versioning
    >>> adapter = GitVersionAdapter(Path("."), git_config)
    >>> versions = adapter.discover_versions()
    >>>
    >>> # Path resolution
    >>> resolver = VersionResolver(version_config, Path("."))
    >>> version = resolver.get_version_for_path("_versions/v2/docs/guide.md")

"""

from __future__ import annotations

from bengal.content.versioning.git_adapter import GitRef, GitVersionAdapter, GitWorktree
from bengal.content.versioning.resolver import VersionResolver

__all__ = ["GitRef", "GitVersionAdapter", "GitWorktree", "VersionResolver"]
