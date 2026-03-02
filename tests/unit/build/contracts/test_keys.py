from __future__ import annotations

from pathlib import Path

from bengal.build.contracts.keys import (
    CacheKey,
    content_key,
    data_key,
    parse_key,
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
