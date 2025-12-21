"""
Tests for autodoc output prefix functionality.

Tests the configurable output_prefix feature that enables each documentation
type (Python, OpenAPI, CLI) to occupy distinct URL namespaces.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.autodoc.orchestration import VirtualAutodocOrchestrator
from bengal.autodoc.orchestration.utils import slugify

# Note: VirtualAutodocOrchestrator creates template_env lazily during generate(),
# so no mocking is needed for tests that don't call generate().


class TestSlugify:
    """Tests for the slugify() utility function."""

    def test_slugify_basic_text(self):
        """Test basic text slugification."""
        assert slugify("Commerce API") == "commerce"

    def test_slugify_strips_api_suffix(self):
        """Test that 'API' suffix is stripped."""
        assert slugify("Commerce API") == "commerce"
        assert slugify("Payments API") == "payments"

    def test_slugify_strips_reference_suffix(self):
        """Test that 'Reference' suffix is stripped."""
        assert slugify("Commerce Reference") == "commerce"

    def test_slugify_strips_documentation_suffix(self):
        """Test that 'Documentation' suffix is stripped."""
        assert slugify("Commerce Documentation") == "commerce"

    def test_slugify_strips_docs_suffix(self):
        """Test that 'Docs' suffix is stripped."""
        assert slugify("Commerce Docs") == "commerce"

    def test_slugify_strips_service_suffix(self):
        """Test that 'Service' suffix is stripped."""
        assert slugify("Payment Service") == "payment"

    def test_slugify_empty_string(self):
        """Test that empty string returns 'rest' fallback."""
        assert slugify("") == "rest"

    def test_slugify_whitespace_only(self):
        """Test that whitespace-only returns 'rest' fallback."""
        assert slugify("   ") == "rest"
        assert slugify("\t\n") == "rest"

    def test_slugify_only_suffix(self):
        """Test that suffix-only text returns 'rest' fallback."""
        assert slugify("API") == "rest"
        assert slugify("Reference") == "rest"

    def test_slugify_special_characters(self):
        """Test that special characters are replaced with hyphens."""
        assert slugify("Commerce & Payments") == "commerce-payments"
        assert slugify("E-Commerce API") == "e-commerce"

    def test_slugify_multiple_spaces(self):
        """Test that multiple spaces collapse to single hyphen."""
        assert slugify("Commerce   Payments") == "commerce-payments"

    def test_slugify_uppercase(self):
        """Test that uppercase is converted to lowercase."""
        assert slugify("COMMERCE API") == "commerce"

    def test_slugify_mixed_case(self):
        """Test mixed case handling."""
        assert slugify("CommerceAPI") == "commerceapi"

    def test_slugify_long_title(self):
        """Test long title handling."""
        # "API Reference" at end is stripped, but "API" in middle is preserved
        long_title = "The Super Amazing Commerce Platform API Reference"
        result = slugify(long_title)
        assert result == "the-super-amazing-commerce-platform-api"

    def test_slugify_numbers(self):
        """Test that numbers are preserved."""
        # "API" in middle is preserved (only end suffixes are stripped)
        assert slugify("Commerce API v2") == "commerce-api-v2"
        # But "API" at end is stripped
        assert slugify("Commerce v2 API") == "commerce-v2"

    def test_slugify_leading_trailing_hyphens(self):
        """Test that leading/trailing hyphens are stripped."""
        assert slugify("-Commerce-") == "commerce"
        # Note: "--Commerce API--" -> "--commerce api--" (lowercase)
        # Suffix " api" not stripped because text ends with "--", not " api"
        # Result: "commerce-api" (hyphens stripped at ends, spaces replaced)
        assert slugify("--Commerce API--") == "commerce-api"
        # But "Commerce API" (no trailing chars) strips the suffix correctly
        assert slugify("Commerce API") == "commerce"


class TestDeriveOpenapiPrefix:
    """Tests for the _derive_openapi_prefix() method."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create an orchestrator with mock site pointing to tmp_path."""
        mock_site = MagicMock()
        mock_site.config = {"autodoc": {"openapi": {"spec_file": "api/openapi.yaml"}}}
        mock_site.root_path = tmp_path
        mock_site.theme = None
        # Template env is created lazily during generate(), not needed for these tests
        return VirtualAutodocOrchestrator(mock_site)

    def test_derive_prefix_from_title(self, orchestrator, tmp_path):
        """Test prefix derivation from spec title."""
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text(
            """
openapi: 3.0.0
info:
  title: Commerce API
  version: 1.0.0
"""
        )

        result = orchestrator._derive_openapi_prefix()
        assert result == "api/commerce"

    def test_derive_prefix_missing_spec(self, orchestrator, tmp_path):
        """Test fallback when spec file doesn't exist."""
        # Don't create the spec file
        result = orchestrator._derive_openapi_prefix()
        assert result == "api/rest"

    def test_derive_prefix_missing_title(self, orchestrator, tmp_path):
        """Test fallback when spec has no title."""
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text(
            """
openapi: 3.0.0
info:
  version: 1.0.0
"""
        )

        result = orchestrator._derive_openapi_prefix()
        assert result == "api/rest"

    def test_derive_prefix_empty_title(self, orchestrator, tmp_path):
        """Test fallback when spec has empty title."""
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text(
            """
openapi: 3.0.0
info:
  title: ""
  version: 1.0.0
"""
        )

        result = orchestrator._derive_openapi_prefix()
        assert result == "api/rest"

    def test_derive_prefix_invalid_yaml(self, orchestrator, tmp_path):
        """Test fallback when spec has invalid YAML."""
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text("not: valid: yaml: content: [")

        result = orchestrator._derive_openapi_prefix()
        assert result == "api/rest"

    def test_derive_prefix_no_spec_file_config(self, tmp_path):
        """Test fallback when no spec_file is configured."""
        mock_site = MagicMock()
        mock_site.config = {"autodoc": {"openapi": {}}}
        mock_site.root_path = tmp_path
        mock_site.theme = None
        # Template env is created lazily during generate(), not needed for these tests
        orchestrator = VirtualAutodocOrchestrator(mock_site)

        result = orchestrator._derive_openapi_prefix()
        assert result == "api/rest"


class TestResolveOutputPrefix:
    """Tests for the _resolve_output_prefix() method."""

    @pytest.fixture
    def orchestrator_factory(self, tmp_path):
        """Factory to create orchestrators with different configs."""

        def create(config):
            mock_site = MagicMock()
            mock_site.config = {"autodoc": config}
            mock_site.root_path = tmp_path
            mock_site.theme = None
            # Template env is created lazily during generate(), not needed for these tests
            return VirtualAutodocOrchestrator(mock_site)

        return create

    def test_python_default(self, orchestrator_factory):
        """Test Python default prefix is 'api/python'."""
        orchestrator = orchestrator_factory({"python": {}})
        assert orchestrator._resolve_output_prefix("python") == "api/python"

    def test_python_explicit(self, orchestrator_factory):
        """Test Python with explicit prefix."""
        orchestrator = orchestrator_factory({"python": {"output_prefix": "custom/python"}})
        assert orchestrator._resolve_output_prefix("python") == "custom/python"

    def test_python_explicit_strips_slashes(self, orchestrator_factory):
        """Test that leading/trailing slashes are stripped."""
        orchestrator = orchestrator_factory({"python": {"output_prefix": "/api/python/"}})
        assert orchestrator._resolve_output_prefix("python") == "api/python"

    def test_cli_default(self, orchestrator_factory):
        """Test CLI default prefix is 'cli'."""
        orchestrator = orchestrator_factory({"cli": {}})
        assert orchestrator._resolve_output_prefix("cli") == "cli"

    def test_cli_explicit(self, orchestrator_factory):
        """Test CLI with explicit prefix."""
        orchestrator = orchestrator_factory({"cli": {"output_prefix": "commands"}})
        assert orchestrator._resolve_output_prefix("cli") == "commands"

    def test_openapi_default_auto_derive(self, orchestrator_factory, tmp_path):
        """Test OpenAPI auto-derives from spec title."""
        # Create spec file
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text(
            """
openapi: 3.0.0
info:
  title: Payments API
  version: 1.0.0
"""
        )

        orchestrator = orchestrator_factory({"openapi": {"spec_file": "api/openapi.yaml"}})
        assert orchestrator._resolve_output_prefix("openapi") == "api/payments"

    def test_openapi_explicit(self, orchestrator_factory):
        """Test OpenAPI with explicit prefix."""
        orchestrator = orchestrator_factory(
            {"openapi": {"output_prefix": "rest-api", "spec_file": "api/openapi.yaml"}}
        )
        assert orchestrator._resolve_output_prefix("openapi") == "rest-api"

    def test_openapi_empty_string_auto_derives(self, orchestrator_factory, tmp_path):
        """Test OpenAPI with empty string auto-derives from spec."""
        # Create spec file
        spec_dir = tmp_path / "api"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text(
            """
openapi: 3.0.0
info:
  title: Inventory API
  version: 1.0.0
"""
        )

        orchestrator = orchestrator_factory(
            {"openapi": {"output_prefix": "", "spec_file": "api/openapi.yaml"}}
        )
        assert orchestrator._resolve_output_prefix("openapi") == "api/inventory"

    def test_unknown_doc_type(self, orchestrator_factory):
        """Test unknown doc type returns type-based fallback."""
        orchestrator = orchestrator_factory({})
        assert orchestrator._resolve_output_prefix("unknown") == "api/unknown"


class TestPrefixOverlapWarning:
    """Tests for prefix overlap detection."""

    @pytest.fixture
    def orchestrator_factory(self, tmp_path):
        """Factory to create orchestrators with different configs."""

        def create(config):
            mock_site = MagicMock()
            mock_site.config = {"autodoc": config}
            mock_site.root_path = tmp_path
            mock_site.theme = None
            # Template env is created lazily during generate(), not needed for these tests
            return VirtualAutodocOrchestrator(mock_site)

        return create

    def test_no_overlap_distinct_prefixes(self, orchestrator_factory):
        """Test no overlap when prefixes are distinct."""
        orchestrator = orchestrator_factory(
            {
                "python": {"enabled": True, "output_prefix": "api/python"},
                "openapi": {"enabled": True, "output_prefix": "api/rest"},
                "cli": {"enabled": True, "output_prefix": "cli"},
            }
        )

        # Should not raise any exceptions
        orchestrator._check_prefix_overlaps()

    def test_exact_overlap_detected(self, orchestrator_factory):
        """Test that exact overlap is detected (same prefix for multiple types)."""
        orchestrator = orchestrator_factory(
            {
                "python": {"enabled": True, "output_prefix": "api"},
                "openapi": {"enabled": True, "output_prefix": "api"},
            }
        )

        # Should not raise - just logs warning
        orchestrator._check_prefix_overlaps()

        # Verify the config causes overlap - both resolve to same prefix
        assert orchestrator._resolve_output_prefix("python") == "api"
        assert orchestrator._resolve_output_prefix("openapi") == "api"

    def test_hierarchy_overlap_detected(self, orchestrator_factory):
        """Test that hierarchical overlap is detected (one prefix is parent of another)."""
        orchestrator = orchestrator_factory(
            {
                "python": {"enabled": True, "output_prefix": "api"},
                "openapi": {"enabled": True, "output_prefix": "api/rest"},
            }
        )

        # Should not raise - just logs warning
        orchestrator._check_prefix_overlaps()

        # Verify the relationship exists
        python_prefix = orchestrator._resolve_output_prefix("python")
        openapi_prefix = orchestrator._resolve_output_prefix("openapi")
        assert openapi_prefix.startswith(f"{python_prefix}/")

    def test_disabled_types_not_checked(self, orchestrator_factory):
        """Test that disabled doc types are not included in overlap check."""
        orchestrator = orchestrator_factory(
            {
                "python": {"enabled": True, "output_prefix": "api"},
                "openapi": {"enabled": False, "output_prefix": "api"},  # Disabled
            }
        )

        # Should not raise any warnings since only one type is enabled
        orchestrator._check_prefix_overlaps()

        # Verify only python is enabled
        assert orchestrator.python_config.get("enabled", False) is True
        assert orchestrator.openapi_config.get("enabled", False) is False
