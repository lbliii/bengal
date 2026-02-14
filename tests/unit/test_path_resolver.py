"""
Unit tests for PathResolver utility.

Tests the centralized path resolution architecture to ensure:
- Paths are resolved relative to a fixed base (not CWD)
- Security checks prevent path traversal
- All resolution methods work correctly

See: plan/active/rfc-path-resolution-architecture.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.utils.paths.path_resolver import PathResolver, resolve_path


class TestPathResolver:
    """Tests for PathResolver class."""

    def test_init_with_absolute_path(self, tmp_path: Path) -> None:
        """PathResolver accepts absolute paths."""
        resolver = PathResolver(tmp_path)
        assert resolver.base == tmp_path
        assert resolver.base.is_absolute()

    def test_init_with_relative_path_resolves_to_absolute(self) -> None:
        """PathResolver converts relative paths to absolute."""
        resolver = PathResolver(Path("."))
        assert resolver.base.is_absolute()

    def test_resolve_relative_path(self, tmp_path: Path) -> None:
        """Resolve relative path relative to base."""
        resolver = PathResolver(tmp_path)
        result = resolver.resolve("content/post.md")
        assert result == tmp_path / "content" / "post.md"
        assert result.is_absolute()

    def test_resolve_absolute_path_unchanged(self, tmp_path: Path) -> None:
        """Absolute paths are returned unchanged."""
        resolver = PathResolver(tmp_path)
        absolute_path = Path("/absolute/path.md")
        result = resolver.resolve(absolute_path)
        assert result == absolute_path

    def test_resolve_parent_traversal(self, tmp_path: Path) -> None:
        """Resolve paths with parent traversal (..)."""
        resolver = PathResolver(tmp_path / "site")
        result = resolver.resolve("../other/file.md")
        assert result == (tmp_path / "other" / "file.md").resolve()

    def test_resolve_string_path(self, tmp_path: Path) -> None:
        """Resolve string paths."""
        resolver = PathResolver(tmp_path)
        result = resolver.resolve("content/page.md")
        assert result == tmp_path / "content" / "page.md"

    def test_resolve_many(self, tmp_path: Path) -> None:
        """Resolve multiple paths at once."""
        resolver = PathResolver(tmp_path)
        paths = ["a.md", "b.md", "subdir/c.md"]
        results = resolver.resolve_many(paths)

        assert len(results) == 3
        assert results[0] == tmp_path / "a.md"
        assert results[1] == tmp_path / "b.md"
        assert results[2] == tmp_path / "subdir" / "c.md"

    def test_resolve_if_exists_returns_path(self, tmp_path: Path) -> None:
        """resolve_if_exists returns path when file exists."""
        test_file = tmp_path / "exists.txt"
        test_file.touch()

        resolver = PathResolver(tmp_path)
        result = resolver.resolve_if_exists("exists.txt")
        assert result == test_file

    def test_resolve_if_exists_returns_none(self, tmp_path: Path) -> None:
        """resolve_if_exists returns None when file doesn't exist."""
        resolver = PathResolver(tmp_path)
        result = resolver.resolve_if_exists("does-not-exist.txt")
        assert result is None

    def test_is_within_base_true(self, tmp_path: Path) -> None:
        """is_within_base returns True for paths under base."""
        resolver = PathResolver(tmp_path)
        assert resolver.is_within_base("content/post.md")
        assert resolver.is_within_base("nested/deep/file.md")

    def test_is_within_base_false_for_traversal(self, tmp_path: Path) -> None:
        """is_within_base returns False for paths escaping base."""
        resolver = PathResolver(tmp_path / "site")
        # Create the parent path scenario
        assert not resolver.is_within_base("../../etc/passwd")

    def test_relative_to_base(self, tmp_path: Path) -> None:
        """relative_to_base returns path relative to base."""
        resolver = PathResolver(tmp_path)
        full_path = tmp_path / "content" / "post.md"
        result = resolver.relative_to_base(full_path)
        assert result == Path("content/post.md")

    def test_relative_to_base_raises_for_outside(self, tmp_path: Path) -> None:
        """relative_to_base raises for paths outside base."""
        resolver = PathResolver(tmp_path / "site")
        outside_path = tmp_path / "other" / "file.md"
        with pytest.raises(ValueError, match=r"is not in the subpath of"):
            resolver.relative_to_base(outside_path)

    def test_from_site(self, tmp_path: Path) -> None:
        """Create resolver from Site instance."""

        # Create a minimal mock site
        class MockSite:
            root_path = tmp_path

        resolver = PathResolver.from_site(MockSite())
        assert resolver.base == tmp_path

    def test_repr(self, tmp_path: Path) -> None:
        """Test string representation."""
        resolver = PathResolver(tmp_path)
        assert f"PathResolver(base={tmp_path})" == repr(resolver)


class TestResolvePath:
    """Tests for resolve_path convenience function."""

    def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Resolve relative path using convenience function."""
        result = resolve_path("content/post.md", tmp_path)
        assert result == tmp_path / "content" / "post.md"

    def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Absolute paths returned unchanged."""
        absolute = Path("/absolute/path.md")
        result = resolve_path(absolute, tmp_path)
        assert result == absolute


class TestSiteRootPathAbsolute:
    """Tests to verify Site.root_path is always absolute."""

    def test_site_root_path_relative_becomes_absolute(self, tmp_path: Path) -> None:
        """Site with relative root_path resolves to absolute."""
        from bengal.core.site import Site

        # Create site with relative path
        site = Site(root_path=Path("."), config={})
        assert site.root_path.is_absolute()

    def test_site_root_path_absolute_stays_absolute(self, tmp_path: Path) -> None:
        """Site with absolute root_path stays absolute."""
        from bengal.core.site import Site

        site = Site(root_path=tmp_path, config={})
        assert site.root_path == tmp_path
        assert site.root_path.is_absolute()

    def test_site_from_config_root_path_absolute(self, tmp_path: Path) -> None:
        """Site.from_config always has absolute root_path."""
        from bengal.core.site import Site

        # Create minimal config file
        config_file = tmp_path / "bengal.toml"
        config_file.write_text('[site]\ntitle = "Test"')

        site = Site.from_config(tmp_path)
        assert site.root_path.is_absolute()
        assert site.root_path == tmp_path
