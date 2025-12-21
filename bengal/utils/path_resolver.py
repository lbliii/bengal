"""
Centralized path resolution utility.

Provides consistent path resolution across Bengal subsystems by eliminating
CWD-dependent behavior. All paths are resolved relative to a fixed base
(typically site.root_path).

Key Principles:
    - Base path must always be absolute
    - No Path.cwd() calls - all resolution is explicit
    - Paths resolved once at ingestion, not repeatedly

Usage:

```python
resolver = PathResolver(site.root_path)
abs_path = resolver.resolve("../bengal")  # Always absolute

# Or from site instance
resolver = PathResolver.from_site(site)
```

Architecture:
    This utility is part of the centralized path resolution architecture.
    See plan/active/rfc-path-resolution-architecture.md for design rationale.

Related Modules:
    - bengal.core.site: Site.root_path is always absolute
    - bengal.config.loader: Config paths resolved on load
    - bengal.directives: Directives use resolver
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

__all__ = ["PathResolver", "resolve_path"]

logger = get_logger(__name__)


class PathResolver:
    """
    Centralized path resolution utility.

    All paths resolved relative to a fixed base (site root).
    Eliminates CWD-dependent behavior across the codebase.

    Attributes:
        base: Absolute base path for resolution

    Example:
        >>> resolver = PathResolver(Path("/home/user/site").resolve())
        >>> resolver.resolve("../bengal")
        PosixPath('/home/user/bengal')

        >>> resolver.resolve("/absolute/path")
        PosixPath('/absolute/path')
    """

    def __init__(self, base: Path) -> None:
        """
        Initialize resolver with absolute base path.

        Args:
            base: Base path for resolution (will be resolved to absolute)

        Raises:
            ValueError: If base cannot be resolved to absolute path
        """
        # Ensure base is absolute
        from bengal.errors import BengalError

        resolved_base = base.resolve() if not base.is_absolute() else base
        if not resolved_base.is_absolute():
            raise BengalError(
                f"PathResolver base must be absolute, got: {base}",
                suggestion="Use Path.resolve() or provide an absolute path",
            )
        self.base = resolved_base

        logger.debug(
            "path_resolver_initialized",
            base=str(self.base),
        )

    def resolve(self, path: str | Path) -> Path:
        """
        Resolve path to absolute, relative to base.

        If path is already absolute, returns it unchanged.
        If path is relative, resolves it relative to self.base.

        Args:
            path: Path to resolve (absolute or relative)

        Returns:
            Absolute path

        Example:
            >>> resolver = PathResolver(Path("/site"))
            >>> resolver.resolve("content/post.md")
            PosixPath('/site/content/post.md')

            >>> resolver.resolve("../other/file.md")
            PosixPath('/other/file.md')

            >>> resolver.resolve("/absolute/path.md")
            PosixPath('/absolute/path.md')
        """
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.base / p).resolve()

    def resolve_many(self, paths: list[str | Path]) -> list[Path]:
        """
        Resolve multiple paths.

        Args:
            paths: List of paths to resolve

        Returns:
            List of absolute paths

        Example:
            >>> resolver = PathResolver(Path("/site"))
            >>> resolver.resolve_many(["a.md", "b.md"])
            [PosixPath('/site/a.md'), PosixPath('/site/b.md')]
        """
        return [self.resolve(p) for p in paths]

    def resolve_if_exists(self, path: str | Path) -> Path | None:
        """
        Resolve path and return only if it exists.

        Args:
            path: Path to resolve

        Returns:
            Absolute path if exists, None otherwise
        """
        resolved = self.resolve(path)
        return resolved if resolved.exists() else None

    def is_within_base(self, path: str | Path) -> bool:
        """
        Check if a path is within the base directory.

        Useful for security checks to prevent path traversal attacks.

        Args:
            path: Path to check (will be resolved first)

        Returns:
            True if resolved path is under base directory

        Example:
            >>> resolver = PathResolver(Path("/site"))
            >>> resolver.is_within_base("content/post.md")
            True
            >>> resolver.is_within_base("../../etc/passwd")
            False
        """
        resolved = self.resolve(path)
        try:
            resolved.relative_to(self.base)
            return True
        except ValueError:
            return False

    def relative_to_base(self, path: str | Path) -> Path:
        """
        Get path relative to base.

        Args:
            path: Path to make relative (resolved first)

        Returns:
            Path relative to base

        Raises:
            ValueError: If path is not under base directory

        Example:
            >>> resolver = PathResolver(Path("/site"))
            >>> resolver.relative_to_base("/site/content/post.md")
            PosixPath('content/post.md')
        """
        resolved = self.resolve(path)
        return resolved.relative_to(self.base)

    @classmethod
    def from_site(cls, site: Site) -> PathResolver:
        """
        Create resolver from site instance.

        Args:
            site: Site instance (uses site.root_path as base)

        Returns:
            PathResolver with site root as base

        Example:
            >>> site = Site.from_config(Path("."))
            >>> resolver = PathResolver.from_site(site)
        """
        return cls(site.root_path)

    def __repr__(self) -> str:
        return f"PathResolver(base={self.base})"


def resolve_path(path: str | Path, base: Path) -> Path:
    """
    Convenience function to resolve a single path.

    For one-off resolutions without creating a resolver instance.

    Args:
        path: Path to resolve
        base: Base path for resolution

    Returns:
        Absolute path

    Example:
        >>> resolve_path("content/post.md", Path("/site"))
        PosixPath('/site/content/post.md')
    """
    resolver = PathResolver(base)
    return resolver.resolve(path)
