from __future__ import annotations

from pathlib import Path

from bengal.build.contracts.keys import (
    CacheKey,
    content_key,
    data_key,
    parse_key,
    synthetic_key,
    watcher_key,
    xref_path_key,
)


def test_content_key_relative() -> None:
    """Content key is relative to site root."""
    key = content_key(Path("/site/content/about.md"), Path("/site"))
    assert key == "content/about.md"


def test_content_key_normalizes_backslashes() -> None:
    """Windows paths are normalized to forward slashes."""
    key = content_key(Path("content\\docs\\guide.md"), Path("."))
    assert "/" in key
    assert "\\" not in key


def test_data_key_prefix() -> None:
    """Data keys have 'data:' prefix."""
    key = data_key(Path("/site/data/team.yaml"), Path("/site"))
    assert key == "data:data/team.yaml"


def test_parse_key_with_prefix() -> None:
    """Parse key extracts prefix and path."""
    prefix, path = parse_key(CacheKey("data:data/team.yaml"))
    assert prefix == "data"
    assert path == "data/team.yaml"


def test_parse_key_without_prefix() -> None:
    """Parse key handles keys without prefix."""
    prefix, path = parse_key(CacheKey("content/about.md"))
    assert prefix == ""
    assert path == "content/about.md"


def test_xref_path_key_content_page() -> None:
    """xref_path_key strips content/ prefix and .md extension."""
    key = xref_path_key(Path("/site/content/docs/guide.md"), Path("/site"))
    assert key == "docs/guide"


def test_xref_path_key_index_page() -> None:
    """xref_path_key maps _index.md to directory path."""
    key = xref_path_key(Path("/site/content/docs/_index.md"), Path("/site"))
    assert key == "docs"


def test_xref_path_key_root_index() -> None:
    """xref_path_key handles root _index.md."""
    key = xref_path_key(Path("/site/content/_index.md"), Path("/site"))
    assert key == "_index"


def test_watcher_key_absolute_posix() -> None:
    """watcher_key returns resolved absolute path in POSIX style."""
    key = watcher_key(Path("/Users/foo/site/content/about.md"))
    assert key.startswith("/")
    assert "\\" not in key
    assert "content/about.md" in key


def test_watcher_key_resolves_path() -> None:
    """watcher_key uses resolve() for canonical path."""
    # Relative path gets resolved to absolute
    p = Path("content/page.md")
    key = watcher_key(p)
    assert key == str(p.resolve()).replace("\\", "/")


def test_synthetic_key_tags_format() -> None:
    """synthetic_key produces format matching provenance_filter and taxonomy_index."""
    key = synthetic_key("_generated/tags", "tag:python")
    assert key == "_generated/tags/tag:python"


def test_synthetic_key_categories_format() -> None:
    """synthetic_key produces format for category pages."""
    key = synthetic_key("_generated/categories", "category:docs")
    assert key == "_generated/categories/category:docs"
