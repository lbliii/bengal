"""Unit tests for page metadata helpers and compatibility properties."""

from pathlib import Path
from typing import Any

import pytest

from bengal.core.page import Page
from bengal.core.page.metadata_helpers import (
    coerce_weight,
    fallback_url,
    get_internal_metadata,
    get_user_metadata,
    infer_nav_title,
    infer_slug,
    infer_title,
    normalize_edition,
    normalize_keywords,
    normalize_visibility,
    should_render_visibility,
)


def _make_page(metadata: dict[str, Any] | None = None) -> Page:
    return Page(
        source_path=Path("content/test.md"),
        _raw_content="Test content",
        _raw_metadata=dict(metadata or {}),
    )


class TestPureMetadataHelpers:
    """Test pure helpers that back Page metadata compatibility properties."""

    @pytest.mark.parametrize(
        ("source_path", "expected"),
        [
            (Path("content/about.md"), "About"),
            (Path("content/api/_index.md"), "Api"),
            (Path("content/data-designer/index.md"), "Data Designer"),
            (Path("content/my_module/index.md"), "My Module"),
            (Path("content/my_module.md"), "My_Module"),
        ],
    )
    def test_infer_title_from_source_path(self, source_path: Path, expected: str):
        assert infer_title({}, source_path) == expected

    def test_infer_title_prefers_metadata_title(self):
        assert infer_title({"title": "Custom Title"}, Path("content/about.md")) == "Custom Title"

    def test_infer_nav_title_precedence(self):
        metadata = {"nav_title": "Short"}

        assert (
            infer_nav_title(
                core_nav_title="Core Short",
                metadata=metadata,
                fallback_title="Long Title",
            )
            == "Core Short"
        )
        assert (
            infer_nav_title(
                core_nav_title=None,
                metadata=metadata,
                fallback_title="Long Title",
            )
            == "Short"
        )
        assert (
            infer_nav_title(
                core_nav_title=None,
                metadata={},
                fallback_title="Long Title",
            )
            == "Long Title"
        )

    @pytest.mark.parametrize(
        ("source_path", "expected"),
        [
            (Path("content/about.md"), "about"),
            (Path("content/api/_index.md"), "api"),
            (Path("content/docs/index.md"), "index"),
        ],
    )
    def test_infer_slug_from_source_path(self, source_path: Path, expected: str):
        assert infer_slug({}, source_path) == expected

    def test_infer_slug_prefers_metadata_slug(self):
        assert infer_slug({"slug": "custom"}, Path("content/about.md")) == "custom"

    def test_fallback_url_uses_slug(self):
        assert fallback_url("guide") == "/guide/"

    def test_coerce_weight_precedence_and_fallbacks(self):
        assert coerce_weight("2.5", {"weight": 9}) == 2.5
        assert coerce_weight(None, {"weight": "4"}) == 4.0
        assert coerce_weight("not-a-number", {"weight": "6"}) == 6.0
        assert coerce_weight(None, {"weight": "not-a-number"}) == float("inf")

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("one, two,, three ", ["one", "two", "three"]),
            (["one", None, " two ", ""], ["one", "two"]),
            ({"not": "valid"}, []),
        ],
    )
    def test_normalize_keywords(self, value, expected):
        assert normalize_keywords(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, []),
            ("enterprise", ["enterprise"]),
            ("", []),
            (["oss", None, " enterprise ", ""], ["oss", "enterprise"]),
            ({"not": "valid"}, []),
        ],
    )
    def test_normalize_edition(self, value, expected):
        assert normalize_edition(value) == expected

    def test_normalize_visibility_defaults_to_permissive_values(self):
        visibility = normalize_visibility({}, {})

        assert visibility == {
            "menu": True,
            "listings": True,
            "sitemap": True,
            "robots": "index, follow",
            "render": "always",
            "search": True,
            "rss": True,
            "ai_train": False,
            "ai_input": True,
        }

    def test_normalize_visibility_applies_hidden_shorthand(self):
        visibility = normalize_visibility(
            {
                "hidden": True,
                "visibility": {"listings": True, "ai_input": True},
            },
            {"search": True, "ai_train": True, "ai_input": True},
        )

        assert visibility == {
            "menu": False,
            "listings": False,
            "sitemap": False,
            "robots": "noindex, nofollow",
            "render": "always",
            "search": False,
            "rss": False,
            "ai_train": False,
            "ai_input": False,
        }

    def test_normalize_visibility_merges_overrides_and_content_signal_defaults(self):
        visibility = normalize_visibility(
            {"visibility": {"menu": False, "render": "local", "ai_input": False}},
            {"search": False, "ai_train": True, "ai_input": True},
        )

        assert visibility["menu"] is False
        assert visibility["listings"] is True
        assert visibility["render"] == "local"
        assert visibility["search"] is False
        assert visibility["ai_train"] is True
        assert visibility["ai_input"] is False

    def test_normalize_visibility_ignores_non_mapping_visibility(self):
        visibility = normalize_visibility({"visibility": "nope"}, {})

        assert visibility["menu"] is True
        assert visibility["render"] == "always"

    def test_should_render_visibility(self):
        assert should_render_visibility({}, is_production=True) is True
        assert should_render_visibility({"render": "always"}, is_production=True) is True
        assert should_render_visibility({"render": "local"}, is_production=False) is True
        assert should_render_visibility({"render": "local"}, is_production=True) is False
        assert should_render_visibility({"render": "never"}, is_production=False) is False

    def test_metadata_access_helpers(self):
        metadata = {"author": "Jane", "_generated": True}

        assert get_user_metadata(metadata, "author") == "Jane"
        assert get_user_metadata(metadata, "_generated", "blocked") == "blocked"
        assert get_internal_metadata(metadata, "generated") is True
        assert get_internal_metadata(metadata, "_generated") is True
        assert get_internal_metadata(metadata, "author", "missing") == "missing"


class TestMetadataHelpers:
    """Test page metadata helper methods."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock page with metadata."""
        return _make_page(
            {
                "title": "Test Page",
                "author": "Jane Doe",
                "date": "2025-01-15",
                "template": "custom/landing.html",
                "content_type": "blog",
                "_generated": True,
                "_version": "v3",
                "_internal_id": "abc123",
            }
        )

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
        page = _make_page({"_generated": True})
        assert page.is_generated is True

    def test_is_generated_false_when_missing(self):
        """Should return False when _generated is not set."""
        page = _make_page()
        assert page.is_generated is False

    def test_is_generated_false_when_false(self):
        """Should return False when _generated is explicitly False."""
        page = _make_page({"_generated": False})
        assert page.is_generated is False

    def test_assigned_template_returns_value(self):
        """Should return template from metadata."""
        page = _make_page({"template": "custom/landing.html"})
        assert page.assigned_template == "custom/landing.html"

    def test_assigned_template_returns_none_when_missing(self):
        """Should return None when template not set."""
        page = _make_page()
        assert page.assigned_template is None

    def test_content_type_name_returns_value(self):
        """Should return content_type from metadata."""
        page = _make_page({"content_type": "blog"})
        assert page.content_type_name == "blog"

    def test_content_type_name_returns_none_when_missing(self):
        """Should return None when content_type not set."""
        page = _make_page()
        assert page.content_type_name is None


class TestEditionVariantFiltering:
    """Test edition and in_variant for multi-variant builds."""

    def test_edition_empty_when_missing(self):
        """Should return empty list when edition not set."""
        page = _make_page()
        assert page.edition == []

    def test_edition_list_from_frontmatter(self):
        """Should return list when edition is list."""
        page = _make_page({"edition": ["oss", "enterprise"]})
        assert page.edition == ["oss", "enterprise"]

    def test_edition_string_normalized_to_list(self):
        """Should normalize single string to list."""
        page = _make_page({"edition": "enterprise"})
        assert page.edition == ["enterprise"]

    def test_in_variant_none_always_included(self):
        """Should include page when variant is None (no filtering)."""
        page = _make_page({"edition": ["enterprise"]})
        assert page.in_variant(None) is True

    def test_in_variant_empty_string_included(self):
        """Should include page when variant is empty string."""
        page = _make_page({"edition": ["enterprise"]})
        assert page.in_variant("") is True

    def test_in_variant_no_edition_included(self):
        """Should include page with no edition in any variant."""
        page = _make_page()
        assert page.in_variant("oss") is True
        assert page.in_variant("enterprise") is True

    def test_in_variant_match_included(self):
        """Should include page when variant matches edition."""
        page = _make_page({"edition": ["oss", "enterprise"]})
        assert page.in_variant("oss") is True
        assert page.in_variant("enterprise") is True

    def test_in_variant_no_match_excluded(self):
        """Should exclude page when variant does not match edition."""
        page = _make_page({"edition": ["enterprise"]})
        assert page.in_variant("enterprise") is True
        assert page.in_variant("oss") is False
