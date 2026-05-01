"""Tests for SourcePage frozen record and create_virtual_source_page factory.

Sprint 4: Immutable Page Pipeline — verifies that SourcePage captures
discovery-phase output as an immutable record.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from bengal.core.page.page_core import PageCore
from bengal.core.records import SourcePage, create_virtual_source_page
from tests._testing.page_records import make_page_core, make_source_page


class TestSourcePageConstruction:
    """SourcePage can be constructed with all required fields."""

    def test_basic_construction(self):
        sp = make_source_page(content_hash="abc123")
        assert sp.core.title == "Hello World"
        assert sp.raw_content == "# Hello\n\nWorld"
        assert sp.content_hash == "abc123"
        assert sp.is_virtual is False
        assert sp.lang is None
        assert sp.translation_key is None

    def test_all_fields(self):
        sp = make_source_page(
            content_hash="def456",
            is_virtual=True,
            lang="fr",
            translation_key="posts/hello",
        )
        assert sp.content_hash == "def456"
        assert sp.is_virtual is True
        assert sp.lang == "fr"
        assert sp.translation_key == "posts/hello"


class TestSourcePageImmutability:
    """SourcePage is frozen and cannot be mutated."""

    def test_cannot_set_raw_content(self):
        sp = make_source_page()
        with pytest.raises(FrozenInstanceError):
            sp.raw_content = "new content"

    def test_cannot_set_content_hash(self):
        sp = make_source_page()
        with pytest.raises(FrozenInstanceError):
            sp.content_hash = "new_hash"

    def test_cannot_set_core(self):
        sp = make_source_page()
        with pytest.raises(FrozenInstanceError):
            sp.core = make_page_core(metadata={"title": "Different"})

    def test_raw_metadata_is_readonly(self):
        sp = make_source_page()
        assert isinstance(sp.raw_metadata, MappingProxyType)
        with pytest.raises(TypeError):
            sp.raw_metadata["new_key"] = "value"


class TestSourcePageDelegates:
    """Property delegates forward to core."""

    def test_source_path_delegate(self):
        sp = SourcePage(
            core=make_page_core(source_path="content/docs/guide.md"),
            raw_content="# Guide",
            raw_metadata=MappingProxyType({"title": "Hello World"}),
            content_hash="abc123",
        )
        assert sp.source_path == "content/docs/guide.md"

    def test_title_delegate(self):
        sp = make_source_page(metadata={"title": "My Guide"})
        assert sp.title == "My Guide"


class TestSourcePageMetadataRoundTrip:
    """raw_metadata_dict() produces a mutable dict copy."""

    def test_round_trip(self):
        original = {"title": "Hello", "tags": ["a", "b"], "custom": 42}
        sp = SourcePage(
            core=make_page_core(metadata=original),
            raw_content="# Hello",
            raw_metadata=MappingProxyType(original),
            content_hash="abc123",
        )
        result = sp.raw_metadata_dict()
        assert result == original
        assert isinstance(result, dict)
        # Mutating the copy doesn't affect the record
        result["new_key"] = "new_value"
        assert "new_key" not in sp.raw_metadata


class TestSourcePageCoreCache:
    """SourcePage.core round-trips through PageCore cache serialization."""

    def test_core_cache_round_trip(self):
        sp = make_source_page(content_hash="hash123")
        cache_dict = sp.core.to_cache_dict()
        restored = PageCore.from_cache_dict(cache_dict)
        assert restored.source_path == sp.core.source_path
        assert restored.title == sp.core.title
        assert restored.tags == sp.core.tags


class TestCreateVirtualSourcePage:
    """Factory for virtual SourcePage records."""

    def test_basic_virtual(self):
        sp = create_virtual_source_page(
            source_id="__virtual__/tags/python/page_1.md",
            title="Posts tagged 'python'",
        )
        assert sp.is_virtual is True
        assert sp.content_hash is None
        assert sp.source_path == "__virtual__/tags/python/page_1.md"
        assert sp.title == "Posts tagged 'python'"
        assert sp.raw_content == ""

    def test_virtual_with_metadata(self):
        sp = create_virtual_source_page(
            source_id="__virtual__/tags/go.md",
            title="Go Posts",
            metadata={"type": "tag", "tags": ["go"], "custom_field": "value"},
        )
        assert sp.core.type == "tag"
        assert sp.core.tags == ["go"]
        assert sp.raw_metadata["custom_field"] == "value"
        assert isinstance(sp.raw_metadata, MappingProxyType)

    def test_virtual_with_lang(self):
        sp = create_virtual_source_page(
            source_id="__virtual__/tags/python.md",
            title="Python",
            lang="es",
        )
        assert sp.lang == "es"
        assert sp.core.lang == "es"

    def test_virtual_with_section(self):
        sp = create_virtual_source_page(
            source_id="__virtual__/archive.md",
            title="Archive",
            section_path="content/blog",
        )
        assert sp.core.section == "content/blog"

    def test_virtual_lang_from_metadata(self):
        """SourcePage.lang matches core.lang when lang comes from metadata, not arg."""
        sp = create_virtual_source_page(
            source_id="__virtual__/tags/python.md",
            title="Python",
            metadata={"lang": "fr"},
        )
        assert sp.core.lang == "fr"
        assert sp.lang == "fr"

    def test_virtual_empty_content(self):
        sp = create_virtual_source_page(
            source_id="__virtual__/test.md",
            title="Test",
            content="# Custom Content",
        )
        assert sp.raw_content == "# Custom Content"
