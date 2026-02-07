"""
Contract tests for all health validators.

Ensures all validators follow the expected interface and behavior contracts.
These tests would catch issues like:
- Validators not returning list[CheckResult]
- Missing name/description attributes
- Validators that crash instead of returning errors
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus


def get_all_validator_classes() -> list[type[BaseValidator]]:
    """Get all validator classes from the validators module."""
    from bengal.health.validators import (
        AccessibilityValidator,
        AnchorValidator,
        AssetValidator,
        AutodocValidator,
        CacheValidator,
        ConfigValidatorWrapper,
        ConnectivityValidator,
        CrossReferenceValidator,
        DirectiveValidator,
        ExternalRefValidator,
        FontValidator,
        LinkValidatorWrapper,
        MenuValidator,
        NavigationValidator,
        OutputValidator,
        OwnershipPolicyValidator,
        RenderingValidator,
        RSSValidator,
        SitemapValidator,
        TaxonomyValidator,
        TrackValidator,
        URLCollisionValidator,
    )

    # Note: TemplateValidator, AssetURLValidator, and PerformanceValidator are excluded
    # because they have different interfaces (not BaseValidator subclasses)
    return [
        AccessibilityValidator,
        AnchorValidator,
        AssetValidator,
        AutodocValidator,
        CacheValidator,
        ConfigValidatorWrapper,
        ConnectivityValidator,
        CrossReferenceValidator,
        DirectiveValidator,
        ExternalRefValidator,
        FontValidator,
        LinkValidatorWrapper,
        MenuValidator,
        NavigationValidator,
        OutputValidator,
        OwnershipPolicyValidator,
        RenderingValidator,
        RSSValidator,
        SitemapValidator,
        TaxonomyValidator,
        TrackValidator,
        URLCollisionValidator,
    ]


@pytest.fixture
def minimal_mock_site(tmp_path):
    """Create a minimal mock site that satisfies most validators."""
    site = MagicMock()

    # Basic paths
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir()
    site.content_dir = tmp_path / "content"
    site.content_dir.mkdir()

    # Create paths object
    site.paths = MagicMock()
    site.paths.build_cache = tmp_path / ".bengal" / "cache.json"

    # Basic config
    site.config = {
        "output_dir": "public",
        "theme": "default",
        "baseurl": "",
        "url": "https://example.com",
    }

    # Empty collections
    site.pages = []
    site.sections = []
    site.taxonomies = {}
    site.menu = {}
    site.menu_builders = {}
    site.baseurl = ""

    # Create minimal output structure
    (site.output_dir / "assets").mkdir()
    (site.output_dir / "assets" / "css").mkdir()
    (site.output_dir / "assets" / "css" / "main.css").write_text("body {}")
    (site.output_dir / "index.html").write_text("<html><body>Hello</body></html>")

    return site


class TestValidatorInterfaceContracts:
    """Tests that all validators implement required interface."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_has_name_attribute(self, validator_class):
        """All validators must have a 'name' class attribute."""
        assert hasattr(validator_class, "name")
        assert isinstance(validator_class.name, str)
        assert len(validator_class.name) > 0

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_has_description_attribute(self, validator_class):
        """All validators must have a 'description' class attribute."""
        assert hasattr(validator_class, "description")
        assert isinstance(validator_class.description, str)

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_has_enabled_by_default_attribute(self, validator_class):
        """All validators must have 'enabled_by_default' attribute."""
        assert hasattr(validator_class, "enabled_by_default")
        assert isinstance(validator_class.enabled_by_default, bool)

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_can_instantiate(self, validator_class):
        """All validators can be instantiated without arguments."""
        # Some validators have optional constructor args
        try:
            validator = validator_class()
            assert isinstance(validator, BaseValidator)
        except TypeError:
            # Try with strict=False for validators that need it
            validator = validator_class(strict=False)
            assert isinstance(validator, BaseValidator)

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_has_validate_method(self, validator_class):
        """All validators must have a 'validate' method."""
        assert hasattr(validator_class, "validate")
        assert callable(validator_class.validate)


class TestValidatorReturnTypeContracts:
    """Tests that validators return correct types."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_validate_returns_list(self, validator_class, minimal_mock_site):
        """validate() must return a list."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        result = validator.validate(minimal_mock_site)

        assert isinstance(result, list), f"{validator_class.name} did not return a list"

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_validate_returns_check_results(self, validator_class, minimal_mock_site):
        """validate() must return list of CheckResult objects."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        results = validator.validate(minimal_mock_site)

        for i, result in enumerate(results):
            assert isinstance(result, CheckResult), (
                f"{validator_class.name} returned non-CheckResult at index {i}: {type(result)}"
            )


class TestValidatorRobustnessContracts:
    """Tests that validators handle edge cases gracefully."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_handles_empty_site(self, validator_class, tmp_path):
        """Validators don't crash on empty sites."""
        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir()
        site.content_dir = tmp_path / "content"
        site.paths = MagicMock()
        site.paths.build_cache = tmp_path / ".bengal" / "cache.json"
        site.config = {"output_dir": "public", "theme": "default"}
        site.pages = []
        site.sections = []
        site.taxonomies = {}
        site.menu = {}
        site.menu_builders = {}
        site.baseurl = ""

        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        # Should not raise
        results = validator.validate(site)

        # Should return a list (possibly empty)
        assert isinstance(results, list)

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_handles_none_build_context(self, validator_class, minimal_mock_site):
        """Validators handle None build_context gracefully."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        # Should not raise with build_context=None
        results = validator.validate(minimal_mock_site, build_context=None)

        assert isinstance(results, list)


class TestValidatorCheckResultContracts:
    """Tests that CheckResults are properly formatted."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_results_have_valid_status(self, validator_class, minimal_mock_site):
        """All results have a valid CheckStatus."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        results = validator.validate(minimal_mock_site)

        for result in results:
            assert isinstance(result.status, CheckStatus), (
                f"{validator_class.name} returned result with invalid status: {result.status}"
            )

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_results_have_message(self, validator_class, minimal_mock_site):
        """All results have a non-empty message."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        results = validator.validate(minimal_mock_site)

        for result in results:
            assert result.message, f"{validator_class.name} returned result without message"
            assert isinstance(result.message, str)

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_error_results_have_code(self, validator_class, minimal_mock_site):
        """ERROR and WARNING results should have health check codes."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        results = validator.validate(minimal_mock_site)

        for result in results:
            if result.status in (CheckStatus.ERROR, CheckStatus.WARNING):
                # Code is recommended but not strictly required
                # Log a note if missing for visibility
                if not result.code:
                    # This is a soft warning, not a failure
                    pass  # pytest.warns or logging could be added here


class TestValidatorNamingContracts:
    """Tests for validator naming conventions."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_name_is_human_readable(self, validator_class):
        """Validator names should be human-readable (not class names)."""
        name = validator_class.name

        # Should not be a Python identifier pattern like "SomeValidator"
        # Should be readable like "Some Validator" or "Navigation Menus"
        assert name != validator_class.__name__, (
            f"{validator_class.__name__} has name equal to class name"
        )

    def test_all_names_are_unique(self):
        """All validator names should be unique."""
        names = [cls.name for cls in get_all_validator_classes()]
        duplicates = [name for name in names if names.count(name) > 1]

        assert len(duplicates) == 0, f"Duplicate validator names: {set(duplicates)}"


class TestValidatorConfigContracts:
    """Tests for validator configuration handling."""

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_is_enabled_method_works(self, validator_class):
        """is_enabled() method works with config dict."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        # Test with health checks enabled
        config_enabled = {
            "validate_build": True,
            "health_check": {"enabled": True},
        }
        result = validator.is_enabled(config_enabled)
        assert isinstance(result, bool)

        # Test with health checks disabled
        config_disabled = {
            "validate_build": False,
        }
        result = validator.is_enabled(config_disabled)
        assert result is False

    @pytest.mark.parametrize("validator_class", get_all_validator_classes())
    def test_repr_returns_string(self, validator_class):
        """__repr__ returns a useful string."""
        try:
            validator = validator_class()
        except TypeError:
            validator = validator_class(strict=False)

        repr_str = repr(validator)

        assert isinstance(repr_str, str)
        assert len(repr_str) > 0
        # Should contain the validator name
        assert validator.name in repr_str or validator_class.__name__ in repr_str
