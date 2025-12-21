"""
Integration tests for autodoc output prefix functionality.

Tests that Python and OpenAPI autodocs create distinct section trees when
configured with different output prefixes.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestSeparateSectionTrees:
    """Tests for separate section tree creation."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for testing."""
        mock = MagicMock()
        mock.root_path = tmp_path
        mock.output_dir = tmp_path / "public"
        mock.theme = "default"
        mock.theme_config = {}
        mock.config = {
            "autodoc": {
                "python": {
                    "enabled": True,
                    "output_prefix": "api/python",
                    "source_dirs": [str(tmp_path / "src")],
                },
                "openapi": {
                    "enabled": True,
                    "output_prefix": "api/rest",
                    "spec_file": "api/openapi.yaml",
                },
            }
        }
        mock.menu = {}
        mock.menu_localized = {}
        return mock

    def test_python_and_openapi_create_distinct_sections(self, mock_site, tmp_path):
        """Test that Python and OpenAPI create separate root sections."""
        from bengal.autodoc.base import DocElement
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        # Create minimal Python source
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')

        # Create OpenAPI spec
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "openapi.yaml").write_text(
            """
openapi: 3.0.0
info:
  title: Test REST API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: OK
"""
        )

        python_element = DocElement(
            name="src",
            qualified_name="src",
            element_type="module",
            description="Test module",
        )

        openapi_element = DocElement(
            name="List users",
            qualified_name="get-users",
            element_type="openapi_endpoint",
            description="List all users",
            metadata={"method": "get", "path": "/users", "tags": []},
        )

        # Patch the module-level extraction functions
        with (
            patch.object(
                VirtualAutodocOrchestrator,
                "_ensure_template_env",
                return_value=MagicMock(),
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_python",
                return_value=[python_element],
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_openapi",
                return_value=[openapi_element],
            ),
        ):
            orchestrator = VirtualAutodocOrchestrator(mock_site)
            pages, sections, result = orchestrator.generate()

        # Root sections prefer an aggregating parent when multiple autodoc types share a prefix.
        # With /api/python/ and /api/rest/, we should return a single /api/ root section that
        # aggregates both children.
        assert [s.name for s in sections] == ["api"]
        assert [s.relative_url for s in sections] == ["/api/"]

        root = sections[0]
        child_names = [s.name for s in root.subsections]
        child_urls = [s.relative_url for s in root.subsections]

        assert "python" in child_names
        assert "rest" in child_names
        assert "/api/python/" in child_urls
        assert "/api/rest/" in child_urls

    def test_cli_output_prefix_drops_root_name(self, mock_site, tmp_path):
        """Test that CLI output prefix drops the root command name ('bengal')."""
        from bengal.autodoc.base import DocElement
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        # Configure CLI
        mock_site.config["autodoc"] = {
            "cli": {
                "enabled": True,
                "output_prefix": "cli",
                "app_module": "bengal.cli:main",
            }
        }

        # Mock CLI elements
        cli_elements = [
            DocElement(
                name="bengal",
                qualified_name="bengal",
                element_type="command-group",
                description="Root command",
            ),
            DocElement(
                name="build",
                qualified_name="bengal.build",
                element_type="command",
                description="Build command",
            ),
            DocElement(
                name="swizzle",
                qualified_name="bengal.theme.swizzle",
                element_type="command",
                description="Swizzle command",
            ),
        ]

        with (
            patch.object(
                VirtualAutodocOrchestrator,
                "_ensure_template_env",
                return_value=MagicMock(),
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_cli",
                return_value=cli_elements,
            ),
        ):
            orchestrator = VirtualAutodocOrchestrator(mock_site)
            pages, sections, result = orchestrator.generate()

        # Check page URLs
        page_urls = {p.url for p in pages}

        # Root command group is NOT a separate page - the section index represents it
        # (see page_builders.py: "Skip root command-groups - the section index page represents them")
        # So we verify that root URL is NOT in pages (it's the section index instead)
        assert "/cli/" not in page_urls, "Root command group should be section index, not a page"

        # Subcommands should drop 'bengal'
        # bengal.build -> /cli/build/
        # bengal.theme.swizzle -> /cli/theme/swizzle/
        assert "/cli/build/" in page_urls
        assert "/cli/theme/swizzle/" in page_urls

        # qualified names should NOT appear in URLs if they include root
        assert "/cli/bengal/build/" not in page_urls
        assert "/cli/bengal/theme/swizzle/" not in page_urls

        # Verify the CLI section exists (represents the root command group)
        # sections is a list of Section objects
        section_urls = {s.url for s in sections}
        assert "/cli/" in section_urls, "CLI section should exist at /cli/"


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with existing configs."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for testing."""
        mock = MagicMock()
        mock.root_path = tmp_path
        mock.output_dir = tmp_path / "public"
        mock.theme = "default"
        mock.theme_config = {}
        mock.menu = {}
        mock.menu_localized = {}
        return mock

    def test_python_only_with_api_prefix(self, mock_site, tmp_path):
        """Test Python-only config with 'api' prefix works unchanged."""
        from bengal.autodoc.base import DocElement
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        mock_site.config = {
            "autodoc": {
                "python": {
                    "enabled": True,
                    "output_prefix": "api",  # Legacy-style single "api" prefix
                    "source_dirs": [str(tmp_path / "src")],
                },
                "openapi": {"enabled": False},
                "cli": {"enabled": False},
            }
        }

        # Create minimal Python source
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')

        python_element = DocElement(
            name="src",
            qualified_name="src",
            element_type="module",
            description="Test module",
        )

        with (
            patch.object(
                VirtualAutodocOrchestrator,
                "_ensure_template_env",
                return_value=MagicMock(),
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_python",
                return_value=[python_element],
            ),
        ):
            orchestrator = VirtualAutodocOrchestrator(mock_site)
            pages, sections, result = orchestrator.generate()

        # Should have root section at /api/
        assert any(s.relative_url == "/api/" for s in sections)

    def test_openapi_only_with_api_prefix(self, mock_site, tmp_path):
        """Test OpenAPI-only config with explicit 'api' prefix works unchanged."""
        from bengal.autodoc.base import DocElement
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        mock_site.config = {
            "autodoc": {
                "python": {"enabled": False},
                "openapi": {
                    "enabled": True,
                    "output_prefix": "api",  # Explicit "api" prefix
                    "spec_file": "api/openapi.yaml",
                },
                "cli": {"enabled": False},
            }
        }

        # Create OpenAPI spec
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "openapi.yaml").write_text(
            """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
"""
        )

        openapi_element = DocElement(
            name="Overview",
            qualified_name="overview",
            element_type="openapi_overview",
            description="API Overview",
        )

        with (
            patch.object(
                VirtualAutodocOrchestrator,
                "_ensure_template_env",
                return_value=MagicMock(),
            ),
            patch(
                "bengal.autodoc.orchestration.orchestrator.extract_openapi",
                return_value=[openapi_element],
            ),
        ):
            orchestrator = VirtualAutodocOrchestrator(mock_site)
            pages, sections, result = orchestrator.generate()

        # Should have root section at /api/
        assert any(s.relative_url == "/api/" for s in sections)

    def test_default_prefixes_when_not_specified(self, mock_site, tmp_path):
        """Test that default prefixes are used when not explicitly configured."""
        from bengal.autodoc.orchestration import VirtualAutodocOrchestrator

        mock_site.config = {
            "autodoc": {
                "python": {
                    "enabled": True,
                    # No output_prefix - should derive from source_dirs
                    "source_dirs": [str(tmp_path / "src")],
                },
                "cli": {
                    "enabled": True,
                    # No output_prefix - should default to "cli"
                    "app_module": "test:app",
                },
            }
        }

        # Create minimal Python source
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')

        with patch.object(
            VirtualAutodocOrchestrator,
            "_ensure_template_env",
            return_value=MagicMock(),
        ):
            orchestrator = VirtualAutodocOrchestrator(mock_site)

            # Verify default prefixes:
            # - Python: derived from source_dirs[0] name => "api/src"
            # - CLI: default is "cli"
            assert orchestrator._resolve_output_prefix("python") == "api/src"
            assert orchestrator._resolve_output_prefix("cli") == "cli"
