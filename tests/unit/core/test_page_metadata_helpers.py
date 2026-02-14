"""
Unit tests for page metadata helper methods.

Tests the new metadata access helpers: get_user_metadata, get_internal_metadata,
and related convenience properties.
"""

from typing import ClassVar
from unittest.mock import Mock

import pytest


class TestMetadataHelpers:
    """Test page metadata helper methods."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock page with metadata."""
        from bengal.core.page import Page

        # Create a minimal page for testing
        page = Mock(spec=Page)
        page.metadata = {
            "title": "Test Page",
            "author": "Jane Doe",
            "date": "2025-01-15",
            "template": "custom/landing.html",
            "content_type": "blog",
            "_generated": True,
            "_version": "v3",
            "_internal_id": "abc123",
        }
        # Add the mixin methods
        from bengal.core.page.metadata import PageMetadataMixin

        page.get_user_metadata = lambda key, default=None: PageMetadataMixin.get_user_metadata(
            page, key, default
        )
        page.get_internal_metadata = (
            lambda key, default=None: PageMetadataMixin.get_internal_metadata(page, key, default)
        )
        return page

    def test_get_user_metadata_returns_value(self, mock_page):
        """Should return user-defined metadata value."""
        assert mock_page.get_user_metadata("title") == "Test Page"
        assert mock_page.get_user_metadata("author") == "Jane Doe"

    def test_get_user_metadata_returns_default_for_missing(self, mock_page):
        """Should return default for missing keys."""
        assert mock_page.get_user_metadata("nonexistent") is None
        assert mock_page.get_user_metadata("nonexistent", "default") == "default"

    def test_get_user_metadata_blocks_internal_keys(self, mock_page):
        """Should not return internal keys (prefixed with _)."""
        assert mock_page.get_user_metadata("_generated") is None
        assert mock_page.get_user_metadata("_version") is None
        assert mock_page.get_user_metadata("_internal_id", "blocked") == "blocked"

    def test_get_internal_metadata_returns_value(self, mock_page):
        """Should return internal metadata value."""
        assert mock_page.get_internal_metadata("_generated") is True
        assert mock_page.get_internal_metadata("_version") == "v3"

    def test_get_internal_metadata_auto_prefixes(self, mock_page):
        """Should auto-prefix key if not already prefixed."""
        # Without prefix
        assert mock_page.get_internal_metadata("generated") is True
        assert mock_page.get_internal_metadata("version") == "v3"
        # With prefix
        assert mock_page.get_internal_metadata("_generated") is True

    def test_get_internal_metadata_returns_default(self, mock_page):
        """Should return default for missing internal keys."""
        assert mock_page.get_internal_metadata("nonexistent") is None
        assert mock_page.get_internal_metadata("missing", "default") == "default"


class TestMetadataProperties:
    """Test metadata convenience properties."""

    def test_is_generated_true(self):
        """Should return True when _generated is set."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"_generated": True}

        page = TestPage()
        assert page.is_generated is True

    def test_is_generated_false_when_missing(self):
        """Should return False when _generated is not set."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {}

        page = TestPage()
        assert page.is_generated is False

    def test_is_generated_false_when_false(self):
        """Should return False when _generated is explicitly False."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"_generated": False}

        page = TestPage()
        assert page.is_generated is False

    def test_assigned_template_returns_value(self):
        """Should return template from metadata."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"template": "custom/landing.html"}

        page = TestPage()
        assert page.assigned_template == "custom/landing.html"

    def test_assigned_template_returns_none_when_missing(self):
        """Should return None when template not set."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {}

        page = TestPage()
        assert page.assigned_template is None

    def test_content_type_name_returns_value(self):
        """Should return content_type from metadata."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"content_type": "blog"}

        page = TestPage()
        assert page.content_type_name == "blog"

    def test_content_type_name_returns_none_when_missing(self):
        """Should return None when content_type not set."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {}

        page = TestPage()
        assert page.content_type_name is None


class TestEditionVariantFiltering:
    """Test edition and in_variant for multi-variant builds."""

    def test_edition_empty_when_missing(self):
        """Should return empty list when edition not set."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {}

        page = TestPage()
        assert page.edition == []

    def test_edition_list_from_frontmatter(self):
        """Should return list when edition is list."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": ["oss", "enterprise"]}

        page = TestPage()
        assert page.edition == ["oss", "enterprise"]

    def test_edition_string_normalized_to_list(self):
        """Should normalize single string to list."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": "enterprise"}

        page = TestPage()
        assert page.edition == ["enterprise"]

    def test_in_variant_none_always_included(self):
        """Should include page when variant is None (no filtering)."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": ["enterprise"]}

        page = TestPage()
        assert page.in_variant(None) is True

    def test_in_variant_empty_string_included(self):
        """Should include page when variant is empty string."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": ["enterprise"]}

        page = TestPage()
        assert page.in_variant("") is True

    def test_in_variant_no_edition_included(self):
        """Should include page with no edition in any variant."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {}

        page = TestPage()
        assert page.in_variant("oss") is True
        assert page.in_variant("enterprise") is True

    def test_in_variant_match_included(self):
        """Should include page when variant matches edition."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": ["oss", "enterprise"]}

        page = TestPage()
        assert page.in_variant("oss") is True
        assert page.in_variant("enterprise") is True

    def test_in_variant_no_match_excluded(self):
        """Should exclude page when variant does not match edition."""
        from bengal.core.page.metadata import PageMetadataMixin

        class TestPage(PageMetadataMixin):
            metadata: ClassVar[dict] = {"edition": ["enterprise"]}

        page = TestPage()
        assert page.in_variant("enterprise") is True
        assert page.in_variant("oss") is False
