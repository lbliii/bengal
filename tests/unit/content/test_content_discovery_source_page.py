from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from bengal.content.discovery.content_discovery import ContentDiscovery

if TYPE_CHECKING:
    from pathlib import Path


def test_i18n_metadata_is_resolved_before_source_page_creation(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    source_path = content_dir / "fr" / "docs" / "guide.md"
    discovery = ContentDiscovery(
        content_dir,
        site=SimpleNamespace(config={"i18n": {"strategy": "prefix", "content_structure": "dir"}}),
    )

    metadata = discovery._metadata_with_i18n(source_path, "fr", {"title": "Guide"})
    source_page = discovery._build_source_page(
        source_path,
        "# Guide",
        metadata,
        "fr",
        section=None,
    )

    assert source_page.lang == "fr"
    assert source_page.translation_key == "docs/guide"
    assert source_page.raw_metadata_dict()["translation_key"] == "docs/guide"


def test_frontmatter_lang_and_translation_key_win(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    source_path = content_dir / "fr" / "docs" / "guide.md"
    discovery = ContentDiscovery(
        content_dir,
        site=SimpleNamespace(config={"i18n": {"strategy": "prefix", "content_structure": "dir"}}),
    )

    metadata = discovery._metadata_with_i18n(
        source_path,
        "fr",
        {"lang": "fr-CA", "title": "Guide", "translation_key": "custom-guide"},
    )
    source_page = discovery._build_source_page(
        source_path,
        "# Guide",
        metadata,
        "fr",
        section=None,
    )

    assert source_page.lang == "fr-CA"
    assert source_page.translation_key == "custom-guide"
