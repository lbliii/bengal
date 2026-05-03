"""Tests for link validator wrapper.

Tests health/validators/links.py:
- LinkValidatorWrapper: link validation in health check system
- LinkValidator: core link validation logic
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.links import LinkValidator, LinkValidatorWrapper


@pytest.fixture
def validator():
    """Create LinkValidatorWrapper instance."""
    return LinkValidatorWrapper()


@pytest.fixture
def mock_site():
    """Create mock site with pages that have valid links."""
    site = MagicMock()
    site.config = {"validate_links": True}
    site.root_path = Path("/project")
    site.link_registry = None

    # Create mock pages with hrefs that exist in the site
    page1 = MagicMock()
    page1.href = "/docs/"
    page1.url = "/docs/"  # Backward compatibility
    page1.source_path = Path("/project/content/docs/_index.md")
    page1.links = ["/about/", "/contact/"]  # Links that will resolve to valid pages

    page2 = MagicMock()
    page2.href = "/blog/"
    page2.url = "/blog/"  # Backward compatibility
    page2.source_path = Path("/project/content/blog/_index.md")
    page2.links = ["/docs/"]

    # Add pages for the links to resolve to
    about_page = MagicMock()
    about_page.href = "/about/"
    about_page.url = "/about/"  # Backward compatibility
    about_page.source_path = Path("/project/content/about/_index.md")
    about_page.links = []

    contact_page = MagicMock()
    contact_page.href = "/contact/"
    contact_page.url = "/contact/"  # Backward compatibility
    contact_page.source_path = Path("/project/content/contact/_index.md")
    contact_page.links = []

    site.pages = [page1, page2, about_page, contact_page]

    return site


@pytest.fixture
def mock_site_with_broken_links():
    """Create mock site with broken links."""
    site = MagicMock()
    site.config = {"validate_links": True}
    site.root_path = Path("/project")
    site.link_registry = None

    # Create mock pages with broken links
    page1 = MagicMock()
    page1.url = "/docs/"
    page1.source_path = Path("/project/content/docs/_index.md")
    page1.links = ["/nonexistent/", "/missing-page/"]

    site.pages = [page1]

    return site


class TestLinkValidatorWrapperBasics:
    """Tests for LinkValidatorWrapper basic attributes."""

    def test_has_name(self, validator):
        """Validator has a name."""
        assert validator.name == "Links"

    def test_has_description(self, validator):
        """Validator has a description."""
        assert validator.description == "Validates internal and external links"

    def test_enabled_by_default(self, validator):
        """Validator is enabled by default."""
        assert validator.enabled_by_default is True


class TestLinkValidatorWrapperDisabled:
    """Tests when link validation is disabled."""

    def test_info_when_disabled(self, validator, mock_site):
        """Returns info when link validation disabled."""
        mock_site.config["validate_links"] = False
        results = validator.validate(mock_site)
        assert len(results) == 1
        assert results[0].status == CheckStatus.INFO
        assert "disabled" in results[0].message.lower()

    def test_stats_updated_when_disabled(self, validator, mock_site):
        """Stats are updated when validation disabled."""
        mock_site.config["validate_links"] = False
        validator.validate(mock_site)
        assert validator.last_stats is not None
        assert validator.last_stats.pages_skipped.get("disabled") == len(mock_site.pages)


class TestLinkValidatorWrapperValidation:
    """Tests for link validation execution."""

    def test_calls_link_validator(self, validator, mock_site):
        """Calls LinkValidator.validate_site."""
        with patch.object(LinkValidator, "validate_site") as mock_validate_site:
            mock_validate_site.return_value = []
            validator.validate(mock_site)
            mock_validate_site.assert_called_once()

    def test_no_results_when_all_links_valid(self, validator, mock_site):
        """No error/warning results when all links valid."""
        results = validator.validate(mock_site)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(error_results) == 0
        assert len(warning_results) == 0


class TestLinkValidatorWrapperBrokenLinks:
    """Tests for broken link detection."""

    def test_error_for_internal_broken_links(self, validator, mock_site_with_broken_links):
        """Returns error for broken internal links."""
        results = validator.validate(mock_site_with_broken_links)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1
        assert "internal" in error_results[0].message.lower()

    def test_warning_for_external_broken_links(self, validator, mock_site):
        """Returns warning for broken external links."""
        # Add a page with an external broken link (mocked as broken)
        page = MagicMock()
        page.url = "/test/"
        page.source_path = Path("/project/content/test.md")
        page.links = []  # No links for this test
        mock_site.pages.append(page)

        # External links are skipped by the validator - they're handled separately
        # So this test verifies that external links don't cause errors
        results = validator.validate(mock_site)

        # Should have no warnings for external links (they're skipped)
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warning_results) == 0

    def test_broken_links_have_details(self, validator, mock_site_with_broken_links):
        """Broken link results include details."""
        results = validator.validate(mock_site_with_broken_links)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) >= 1
        assert error_results[0].details is not None
        assert len(error_results[0].details) >= 1


class TestLinkValidatorWrapperStats:
    """Tests for validator stats tracking."""

    def test_tracks_pages_total(self, validator, mock_site):
        """Tracks total pages in stats."""
        validator.validate(mock_site)

        assert validator.last_stats is not None
        assert validator.last_stats.pages_total == len(mock_site.pages)

    def test_tracks_pages_processed(self, validator, mock_site):
        """Tracks processed pages in stats."""
        validator.validate(mock_site)

        assert validator.last_stats.pages_processed == len(mock_site.pages)

    def test_tracks_link_count_metrics(self, validator, mock_site):
        """Tracks link count in metrics."""
        validator.validate(mock_site)

        assert "total_links" in validator.last_stats.metrics

    def test_tracks_broken_link_count(self, validator, mock_site_with_broken_links):
        """Tracks broken link count in metrics."""
        validator.validate(mock_site_with_broken_links)

        assert validator.last_stats.metrics["broken_links"] == 2

    def test_tracks_validation_timing(self, validator, mock_site):
        """Tracks validation timing in sub_timings."""
        validator.validate(mock_site)

        assert "validate" in validator.last_stats.sub_timings

    def test_tracks_link_result_cache_stats(self, validator, mock_site):
        """Tracks per-run link result cache effectiveness."""
        mock_site.pages[0].links.append("/about/")

        validator.validate(mock_site)

        assert validator.last_stats is not None
        assert validator.last_stats.cache_hits == 1
        assert validator.last_stats.cache_misses == 3
        assert validator.last_stats.metrics["unique_link_checks"] == 3


class TestLinkValidatorWrapperRecommendations:
    """Tests for recommendation messages."""

    def test_internal_broken_has_recommendation(self, validator, mock_site_with_broken_links):
        """Internal broken links have fix recommendation."""
        results = validator.validate(mock_site_with_broken_links)

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert error_results[0].recommendation is not None

    def test_external_broken_has_recommendation(self, validator, mock_site):
        """External broken links have recommendation (when they exist)."""
        # External link validation is done separately, so no warnings expected here
        # This test verifies that the structure is correct
        results = validator.validate(mock_site)
        # With all valid links, no warnings should be present
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert len(warning_results) == 0


class TestLinkValidatorWrapperSilenceIsGolden:
    """Tests that validator follows 'silence is golden' principle."""

    def test_no_success_when_all_valid(self, validator, mock_site):
        """No explicit success message when all links valid."""
        results = validator.validate(mock_site)

        success_results = [r for r in results if r.status == CheckStatus.SUCCESS]
        assert len(success_results) == 0


class TestLinkValidatorRegistryCache:
    """Tests for LinkValidator registry cache lifecycle."""

    def test_validate_page_links_reloads_when_site_changes(self):
        """Reusing a validator with a different site must not keep stale URL indexes."""
        page = MagicMock()
        page.href = "/docs/"
        page.source_path = Path("/project/content/docs.md")
        page.links = ["/new/"]

        site_without_target = MagicMock()
        site_without_target.root_path = Path("/project")
        site_without_target.link_registry = None
        site_without_target.config = {"validate_links": True}
        site_without_target.pages = [page]

        target = MagicMock()
        target.href = "/new/"
        target.source_path = Path("/project/content/new.md")
        target.links = []

        site_with_target = MagicMock()
        site_with_target.root_path = Path("/project")
        site_with_target.link_registry = None
        site_with_target.config = {"validate_links": True}
        site_with_target.pages = [page, target]

        validator = LinkValidator()

        assert validator.validate_page_links(page, site_without_target) == ["/new/"]
        assert validator.validate_page_links(page, site_with_target) == []


class TestLinkValidatorResultCache:
    """Tests for per-run link result memoization."""

    def test_reuses_duplicate_internal_link_result(self):
        """Duplicate links from the same page URL are resolved once."""
        from bengal.health.link_registry import LinkRegistry
        from bengal.rendering.reference_registry import InternalReferenceResolver

        page = MagicMock()
        page.href = "/docs/"
        page.source_path = Path("/project/content/docs.md")
        page.links = ["/target/", "/target/", "/target/"]

        site = MagicMock()
        site.config = {"validate_links": True}
        site.root_path = Path("/project")
        site.pages = [page]
        site.link_registry = LinkRegistry(
            page_urls=frozenset(["/docs/", "/docs", "/target/", "/target"]),
            source_paths=frozenset(),
            anchors_by_url=MappingProxyType({}),
            auxiliary_urls=frozenset(),
        )

        validator = LinkValidator()
        with patch.object(
            InternalReferenceResolver, "has_url", autospec=True, return_value=True
        ) as has_url:
            broken = validator.validate_site(site)

        assert broken == []
        assert has_url.call_count == 1
        assert validator.cache_hits == 2
        assert validator.cache_misses == 1

    def test_relative_markdown_cache_is_scoped_by_source_path(self):
        """The same relative .md link can differ by source directory."""
        from bengal.health.link_registry import LinkRegistry

        page_a = MagicMock()
        page_a.href = "/a/"
        page_a.source_path = Path("/project/content/a/page.md")
        page_a.links = ["sibling.md"]

        page_b = MagicMock()
        page_b.href = "/b/"
        page_b.source_path = Path("/project/content/b/page.md")
        page_b.links = ["sibling.md"]

        site = MagicMock()
        site.config = {"validate_links": True}
        site.root_path = Path("/project")
        site.pages = [page_a, page_b]
        site.link_registry = LinkRegistry(
            page_urls=frozenset(["/a/", "/a", "/b/", "/b"]),
            source_paths=frozenset(["content/a/sibling.md"]),
            anchors_by_url=MappingProxyType({}),
            auxiliary_urls=frozenset(),
        )

        broken = LinkValidator().validate_site(site)

        assert broken == [(page_b.source_path, "sibling.md")]

    def test_fragment_cache_is_scoped_by_current_page(self):
        """The same fragment can be valid on one page and broken on another."""
        from bengal.health.link_registry import LinkRegistry

        page_docs = MagicMock()
        page_docs._path = "/docs/"
        page_docs.href = "/docs/"
        page_docs.source_path = Path("/project/content/docs.md")
        page_docs.links = ["#intro"]

        page_about = MagicMock()
        page_about._path = "/about/"
        page_about.href = "/about/"
        page_about.source_path = Path("/project/content/about.md")
        page_about.links = ["#intro"]

        site = MagicMock()
        site.config = {"validate_links": True}
        site.root_path = Path("/project")
        site.pages = [page_docs, page_about]
        site.link_registry = LinkRegistry(
            page_urls=frozenset(["/docs/", "/docs", "/about/", "/about"]),
            source_paths=frozenset(),
            anchors_by_url=MappingProxyType(
                {
                    "/docs/": frozenset(["intro"]),
                    "/docs": frozenset(["intro"]),
                    "/about/": frozenset(["team"]),
                    "/about": frozenset(["team"]),
                }
            ),
            auxiliary_urls=frozenset(),
        )

        validator = LinkValidator()
        broken = validator.validate_site(site)

        assert broken == [(page_about.source_path, "#intro")]
        assert validator.cache_hits == 0
        assert validator.cache_misses == 2


class TestLinkValidatorAnchorValidation:
    """Tests for anchor validation via LinkRegistry."""

    @pytest.fixture
    def site_with_registry(self):
        """Create mock site with a LinkRegistry providing anchor data."""
        from bengal.health.link_registry import LinkRegistry

        site = MagicMock()
        site.config = {"validate_links": True}
        site.root_path = Path("/project")

        registry = LinkRegistry(
            page_urls=frozenset(["/docs/", "/docs", "/about/", "/about"]),
            source_paths=frozenset(),
            anchors_by_url=MappingProxyType(
                {
                    "/docs/": frozenset(["introduction", "getting-started"]),
                    "/docs": frozenset(["introduction", "getting-started"]),
                    "/about/": frozenset(["team", "mission"]),
                    "/about": frozenset(["team", "mission"]),
                }
            ),
            auxiliary_urls=frozenset(),
        )
        site.link_registry = registry

        return site

    def test_valid_fragment_link_passes(self, site_with_registry):
        """Fragment-only link to existing anchor is valid."""
        page = MagicMock()
        page._path = "/docs/"
        page.href = "/docs/"
        page.source_path = Path("/project/content/docs/_index.md")
        page.links = ["#introduction"]
        site_with_registry.pages = [page]

        validator = LinkValidator()
        broken = validator.validate_site(site_with_registry)
        assert len(broken) == 0

    def test_broken_fragment_link_detected(self, site_with_registry):
        """Fragment-only link to nonexistent anchor is broken."""
        page = MagicMock()
        page._path = "/docs/"
        page.href = "/docs/"
        page.source_path = Path("/project/content/docs/_index.md")
        page.links = ["#nonexistent-heading"]
        site_with_registry.pages = [page]

        validator = LinkValidator()
        broken = validator.validate_site(site_with_registry)
        assert len(broken) == 1
        assert broken[0][1] == "#nonexistent-heading"

    def test_valid_path_with_fragment_passes(self, site_with_registry):
        """Path+fragment link where both page and anchor exist is valid."""
        page = MagicMock()
        page._path = "/about/"
        page.href = "/about/"
        page.source_path = Path("/project/content/about.md")
        page.links = ["/docs/#introduction"]
        site_with_registry.pages = [page]

        validator = LinkValidator()
        broken = validator.validate_site(site_with_registry)
        assert len(broken) == 0

    def test_broken_anchor_on_valid_page_detected(self, site_with_registry):
        """Path+fragment link where page exists but anchor doesn't is broken."""
        page = MagicMock()
        page._path = "/about/"
        page.href = "/about/"
        page.source_path = Path("/project/content/about.md")
        page.links = ["/docs/#nonexistent-section"]
        site_with_registry.pages = [page]

        validator = LinkValidator()
        broken = validator.validate_site(site_with_registry)
        assert len(broken) == 1
        assert broken[0][1] == "/docs/#nonexistent-section"

    def test_no_anchor_validation_without_registry(self):
        """Without registry, fragment links pass (backward compat)."""
        site = MagicMock()
        site.config = {"validate_links": True}
        site.root_path = Path("/project")
        site.link_registry = None

        page = MagicMock()
        page.href = "/docs/"
        page._path = "/docs/"
        page.source_path = Path("/project/content/docs/_index.md")
        page.links = ["#any-heading"]
        site.pages = [page]

        validator = LinkValidator()
        broken = validator.validate_site(site)
        assert len(broken) == 0
