"""Unit tests for Content Signals visibility properties.

Tests the ai_train/ai_input visibility keys and the in_ai_train/in_ai_input
boolean properties that gate output format generation and robots.txt signals.
"""

from pathlib import Path

from bengal.core.page_visibility import (
    get_page_visibility,
    is_page_in_ai_input,
    is_page_in_ai_train,
    is_page_in_search,
)
from tests._testing.mocks import make_mock_page as _page


class TestContentSignalDefaults:
    """Content signal defaults when no site config is attached."""

    def test_ai_train_defaults_false(self):
        """ai_train defaults to False (privacy-first)."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata={"title": "Test"},
        )
        assert get_page_visibility(page)["ai_train"] is False

    def test_ai_input_defaults_true(self):
        """ai_input defaults to True (allow RAG/grounding)."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata={"title": "Test"},
        )
        assert get_page_visibility(page)["ai_input"] is True

    def test_in_ai_train_false_by_default(self):
        """in_ai_train is False by default (matches ai_train default)."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata={"title": "Test"},
        )
        assert is_page_in_ai_train(page) is False

    def test_in_ai_input_true_by_default(self):
        """in_ai_input is True by default."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata={"title": "Test"},
        )
        assert is_page_in_ai_input(page) is True


class TestContentSignalFrontmatterOverride:
    """Override content signals via page frontmatter."""

    def test_ai_train_override_true(self):
        """Can enable ai_train via visibility frontmatter."""
        page = _page(
            source_path=Path("content/open.md"),
            _raw_content="Open content",
            _raw_metadata={
                "title": "Open",
                "visibility": {"ai_train": True},
            },
        )
        assert get_page_visibility(page)["ai_train"] is True
        assert is_page_in_ai_train(page) is True

    def test_ai_input_override_false(self):
        """Can disable ai_input via visibility frontmatter."""
        page = _page(
            source_path=Path("content/restricted.md"),
            _raw_content="Restricted",
            _raw_metadata={
                "title": "Restricted",
                "visibility": {"ai_input": False},
            },
        )
        assert get_page_visibility(page)["ai_input"] is False
        assert is_page_in_ai_input(page) is False

    def test_both_signals_override(self):
        """Can override both signals at once."""
        page = _page(
            source_path=Path("content/locked.md"),
            _raw_content="Locked",
            _raw_metadata={
                "title": "Locked",
                "visibility": {"ai_train": False, "ai_input": False},
            },
        )
        visibility = get_page_visibility(page)
        assert visibility["ai_train"] is False
        assert visibility["ai_input"] is False
        assert is_page_in_ai_train(page) is False
        assert is_page_in_ai_input(page) is False

    def test_partial_override_preserves_other_visibility(self):
        """Overriding ai_train doesn't affect other visibility keys."""
        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata={
                "title": "Test",
                "visibility": {"ai_train": True, "menu": False},
            },
        )
        vis = get_page_visibility(page)
        assert vis["ai_train"] is True
        assert vis["menu"] is False
        assert vis["sitemap"] is True
        assert vis["search"] is True


class TestContentSignalHiddenInteraction:
    """Content signals for hidden pages."""

    def test_hidden_denies_all_signals(self):
        """hidden: true sets both ai_train and ai_input to False."""
        page = _page(
            source_path=Path("content/secret.md"),
            _raw_content="Secret",
            _raw_metadata={"title": "Secret", "hidden": True},
        )
        vis = get_page_visibility(page)
        assert vis["ai_train"] is False
        assert vis["ai_input"] is False
        assert is_page_in_ai_train(page) is False
        assert is_page_in_ai_input(page) is False


class TestContentSignalDraftInteraction:
    """Content signals for draft pages."""

    def test_draft_excludes_from_ai_train(self):
        """Draft pages are excluded from AI training regardless of visibility."""
        page = _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={
                "title": "Draft",
                "draft": True,
                "visibility": {"ai_train": True},
            },
        )
        assert is_page_in_ai_train(page) is False

    def test_draft_excludes_from_ai_input(self):
        """Draft pages are excluded from AI input regardless of visibility."""
        page = _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft",
            _raw_metadata={
                "title": "Draft",
                "draft": True,
                "visibility": {"ai_input": True},
            },
        )
        assert is_page_in_ai_input(page) is False


class TestContentSignalWithSiteConfig:
    """Content signals with site-level config defaults."""

    def _make_page_with_site(self, metadata, content_signals_config):
        """Create a page with a mock site that has content_signals config."""
        from unittest.mock import MagicMock

        page = _page(
            source_path=Path("content/test.md"),
            _raw_content="Test",
            _raw_metadata=metadata,
        )
        site = MagicMock()
        site.config = MagicMock()
        site.config.get = lambda key, default=None: (
            content_signals_config if key == "content_signals" else default
        )
        page._site = site
        return page

    def test_site_config_ai_train_true(self):
        """Site config can enable ai_train globally."""
        page = self._make_page_with_site(
            {"title": "Test"},
            {"ai_train": True, "ai_input": True, "search": True},
        )
        assert get_page_visibility(page)["ai_train"] is True
        assert is_page_in_ai_train(page) is True

    def test_site_config_ai_input_false(self):
        """Site config can disable ai_input globally."""
        page = self._make_page_with_site(
            {"title": "Test"},
            {"ai_train": False, "ai_input": False, "search": True},
        )
        assert get_page_visibility(page)["ai_input"] is False
        assert is_page_in_ai_input(page) is False

    def test_frontmatter_overrides_site_config(self):
        """Page frontmatter takes precedence over site config."""
        page = self._make_page_with_site(
            {"title": "Override", "visibility": {"ai_train": True}},
            {"ai_train": False, "ai_input": True, "search": True},
        )
        assert get_page_visibility(page)["ai_train"] is True
        assert is_page_in_ai_train(page) is True

    def test_site_config_search_default(self):
        """Site config search default flows into visibility."""
        page = self._make_page_with_site(
            {"title": "Test"},
            {"search": False, "ai_train": False, "ai_input": True},
        )
        assert get_page_visibility(page)["search"] is False
        assert is_page_in_search(page) is False
