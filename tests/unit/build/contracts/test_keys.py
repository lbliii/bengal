from __future__ import annotations

from pathlib import Path

from bengal.build.contracts.keys import CacheKey, content_key, data_key, parse_key


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
