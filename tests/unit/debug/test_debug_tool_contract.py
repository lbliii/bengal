"""
Unit tests for DebugTool contract compliance.

Verifies that all DebugTool subclasses properly initialize the base class
and honor the DebugTool contract (site, cache, root_path attributes).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.debug.base import DebugRegistry, DebugTool


def _has_shortcode_sandbox() -> bool:
    """Check if the shortcode_sandbox module exists."""
    try:
        import bengal.debug.shortcode_sandbox

        return True
    except ModuleNotFoundError:
        return False


class TestDebugToolContract:
    """All DebugTool subclasses must properly initialize base class."""

    @pytest.fixture
    def mock_site(self, tmp_path: Path) -> MagicMock:
        """Create minimal Site-like object for testing."""
        site = MagicMock()
        site.root_path = tmp_path
        site.pages = []
        site.config = {}
        site.theme = "default"
        site.output_dir = tmp_path / "public"
        return site

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create minimal BuildCache-like object for testing."""
        cache = MagicMock()
        cache.file_fingerprints = {}
        cache.dependencies = {}
        cache.taxonomy_index.taxonomy_deps = {}
        cache.parsed_content = {}
        cache.rendered_output = {}
        return cache

    # Only test tools that are registered with @DebugRegistry.register
    # ConfigInspector and ShortcodeSandbox are NOT registered (they're standalone)
    @pytest.mark.parametrize(
        "tool_name",
        [
            "migrate",  # ContentMigrator
            "incremental",  # IncrementalBuildDebugger
            "delta",  # BuildDeltaAnalyzer
            "deps",  # DependencyVisualizer
        ],
    )
    def test_base_attributes_initialized(
        self,
        tool_name: str,
        mock_site: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """DebugTool subclasses must have site, cache, root_path after init.

        This test ensures that all registered debug tools properly call
        super().__init__() and inherit the base class attributes.
        """
        tool = DebugRegistry.create(tool_name, site=mock_site, cache=mock_cache)
        if tool is None:
            pytest.skip(f"Tool {tool_name} not registered")

        # These attributes must exist (from super().__init__)
        assert hasattr(tool, "site"), f"{tool_name} missing 'site' attribute"
        assert hasattr(tool, "cache"), f"{tool_name} missing 'cache' attribute"
        assert hasattr(tool, "root_path"), f"{tool_name} missing 'root_path' attribute"

    @pytest.mark.parametrize(
        "tool_name",
        [
            "migrate",
            "incremental",
            "delta",
            "deps",
        ],
    )
    def test_base_attributes_values_correct(
        self,
        tool_name: str,
        mock_site: MagicMock,
        mock_cache: MagicMock,
        tmp_path: Path,
    ) -> None:
        """DebugTool subclasses must pass through constructor arguments."""
        tool = DebugRegistry.create(
            tool_name,
            site=mock_site,
            cache=mock_cache,
            root_path=tmp_path,
        )
        if tool is None:
            pytest.skip(f"Tool {tool_name} not registered")

        # Values should match what was passed to constructor
        assert tool.site is mock_site, f"{tool_name} didn't preserve site"
        assert tool.cache is mock_cache, f"{tool_name} didn't preserve cache"
        assert tool.root_path == tmp_path, f"{tool_name} didn't preserve root_path"


class TestConfigInspectorContract:
    """Specific contract tests for ConfigInspector."""

    def test_uses_root_path_not_root(self, tmp_path: Path) -> None:
        """ConfigInspector must use site.root_path, not site.root.

        This test would have caught the bug where ConfigInspector used
        site.root (which doesn't exist) instead of site.root_path.
        """
        from bengal.debug import ConfigInspector

        # Create mock site with root_path but NO root attribute
        mock_site = MagicMock(spec=["root_path", "config", "pages"])
        mock_site.root_path = tmp_path
        mock_site.config = {}

        # This should NOT raise AttributeError
        inspector = ConfigInspector(site=mock_site)

        # Verify _config_dir was set correctly
        assert inspector._config_dir == tmp_path / "config"

    def test_inherits_debug_tool_interface(self, tmp_path: Path) -> None:
        """ConfigInspector should be a proper DebugTool subclass."""
        from bengal.debug import ConfigInspector

        mock_site = MagicMock()
        mock_site.root_path = tmp_path

        inspector = ConfigInspector(site=mock_site)

        # Should have all DebugTool methods
        assert hasattr(inspector, "analyze")
        assert hasattr(inspector, "run")
        assert hasattr(inspector, "create_report")
        assert callable(inspector.analyze)


@pytest.mark.skipif(
    not _has_shortcode_sandbox(),
    reason="ShortcodeSandbox module not yet implemented",
)
class TestShortcodeSandboxContract:
    """Specific contract tests for ShortcodeSandbox."""

    def test_inherits_debug_tool_attributes(self) -> None:
        """ShortcodeSandbox must inherit DebugTool attributes.

        This test would have caught the bug where ShortcodeSandbox used
        self._site instead of self.site and didn't call super().__init__().
        """
        from bengal.debug import ShortcodeSandbox

        mock_site = MagicMock()
        sandbox = ShortcodeSandbox(site=mock_site)

        # Should have base class attributes
        assert hasattr(sandbox, "site")
        assert hasattr(sandbox, "cache")
        assert hasattr(sandbox, "root_path")

        # site should be the mock, not stored in _site
        assert sandbox.site is mock_site

    def test_accepts_all_debug_tool_params(self, tmp_path: Path) -> None:
        """ShortcodeSandbox should accept standard DebugTool parameters."""
        from bengal.debug import ShortcodeSandbox

        mock_site = MagicMock()
        mock_cache = MagicMock()

        # Should not raise TypeError for unexpected keyword arguments
        sandbox = ShortcodeSandbox(
            site=mock_site,
            cache=mock_cache,
            root_path=tmp_path,
        )

        assert sandbox.site is mock_site
        assert sandbox.cache is mock_cache
        assert sandbox.root_path == tmp_path


class TestDebugToolSubclassDiscovery:
    """Test that all DebugTool subclasses are properly registered."""

    def test_registered_tools_are_present(self) -> None:
        """Verify registered debug tools are in the registry.

        Note: Not all DebugTool subclasses are registered. ConfigInspector
        and ShortcodeSandbox are standalone tools used directly.
        """
        # Only tools with @DebugRegistry.register decorator
        expected_registered = {
            "migrate",  # ContentMigrator
            "incremental",  # IncrementalBuildDebugger
            "delta",  # BuildDeltaAnalyzer
            "deps",  # DependencyVisualizer
        }

        registered = {name for name, _ in DebugRegistry.list_tools()}

        # All expected tools should be registered
        missing = expected_registered - registered
        assert not missing, f"Missing tools from registry: {missing}"

    def test_registered_tools_are_debug_tool_subclasses(self) -> None:
        """All registered tools must be DebugTool subclasses."""
        for name, _ in DebugRegistry.list_tools():
            tool_class = DebugRegistry.get(name)
            assert tool_class is not None
            assert issubclass(tool_class, DebugTool), (
                f"{name} ({tool_class}) is not a DebugTool subclass"
            )
