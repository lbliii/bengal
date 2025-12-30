"""
Unit tests for template engine capabilities.

Tests the EngineCapability enum and capability detection.
"""

import pytest

from bengal.rendering.engines.protocol import EngineCapability


class TestEngineCapability:
    """Test EngineCapability enum."""

    def test_none_capability(self):
        """NONE should represent no capabilities."""
        assert EngineCapability.NONE.value == 0

    def test_individual_capabilities_are_unique(self):
        """Each capability should have a unique value."""
        capabilities = [
            EngineCapability.BLOCK_CACHING,
            EngineCapability.BLOCK_LEVEL_DETECTION,
            EngineCapability.INTROSPECTION,
            EngineCapability.PIPELINE_OPERATORS,
            EngineCapability.PATTERN_MATCHING,
        ]

        values = [cap.value for cap in capabilities]
        assert len(values) == len(set(values)), "Capabilities should have unique values"

    def test_capability_composition(self):
        """Capabilities should be composable with bitwise OR."""
        combined = EngineCapability.BLOCK_CACHING | EngineCapability.INTROSPECTION

        assert EngineCapability.BLOCK_CACHING in combined
        assert EngineCapability.INTROSPECTION in combined
        assert EngineCapability.BLOCK_LEVEL_DETECTION not in combined

    def test_capability_check_with_in_operator(self):
        """Should support 'in' operator for capability checks."""
        capabilities = (
            EngineCapability.BLOCK_CACHING
            | EngineCapability.BLOCK_LEVEL_DETECTION
            | EngineCapability.INTROSPECTION
        )

        assert EngineCapability.BLOCK_CACHING in capabilities
        assert EngineCapability.PIPELINE_OPERATORS not in capabilities

    def test_none_contains_nothing(self):
        """NONE should not contain any capabilities."""
        assert EngineCapability.BLOCK_CACHING not in EngineCapability.NONE
        assert EngineCapability.INTROSPECTION not in EngineCapability.NONE

    def test_all_kida_capabilities(self):
        """Test typical Kida capability set."""
        kida_caps = (
            EngineCapability.BLOCK_CACHING
            | EngineCapability.BLOCK_LEVEL_DETECTION
            | EngineCapability.INTROSPECTION
            | EngineCapability.PIPELINE_OPERATORS
            | EngineCapability.PATTERN_MATCHING
        )

        # All Kida capabilities should be present
        assert EngineCapability.BLOCK_CACHING in kida_caps
        assert EngineCapability.BLOCK_LEVEL_DETECTION in kida_caps
        assert EngineCapability.INTROSPECTION in kida_caps
        assert EngineCapability.PIPELINE_OPERATORS in kida_caps
        assert EngineCapability.PATTERN_MATCHING in kida_caps


class TestKidaEngineCapabilities:
    """Test KidaTemplateEngine capabilities (requires Kida to be available)."""

    @pytest.fixture
    def mock_site(self):
        """Create a minimal mock site for testing."""
        from pathlib import Path
        from unittest.mock import Mock

        site = Mock()
        site.root_path = Path("/tmp/test-site")
        site.theme = "default"
        site.config = {
            "template_engine": "kida",
            "development": {"auto_reload": False},
            "kida": {"bytecode_cache": False},
        }
        return site

    def test_kida_has_all_capabilities(self, mock_site, monkeypatch):
        """Kida engine should have all capabilities."""
        # Skip if Kida isn't available
        pytest.importorskip("bengal.rendering.kida")

        # Mock dependencies
        from unittest.mock import MagicMock

        # Mock the environment creation to avoid needing actual templates
        monkeypatch.setattr(
            "bengal.rendering.engines.kida.Environment",
            MagicMock,
        )
        monkeypatch.setattr(
            "bengal.rendering.engines.kida.FileSystemLoader",
            MagicMock,
        )
        monkeypatch.setattr(
            "bengal.rendering.engines.kida.KidaTemplateEngine._build_template_dirs",
            lambda self: [],
        )
        monkeypatch.setattr(
            "bengal.rendering.engines.kida.KidaTemplateEngine._register_bengal_template_functions",
            lambda self: None,
        )

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(mock_site)

        # Check all capabilities
        assert engine.has_capability(EngineCapability.BLOCK_CACHING)
        assert engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION)
        assert engine.has_capability(EngineCapability.INTROSPECTION)
        assert engine.has_capability(EngineCapability.PIPELINE_OPERATORS)
        assert engine.has_capability(EngineCapability.PATTERN_MATCHING)


class TestJinjaEngineCapabilities:
    """Test JinjaTemplateEngine capabilities."""

    @pytest.fixture
    def mock_site(self):
        """Create a minimal mock site for testing."""
        from pathlib import Path
        from unittest.mock import Mock

        site = Mock()
        site.root_path = Path("/tmp/test-site")
        site.output_dir = Path("/tmp/test-site/public")
        site.theme = "default"
        site.config = {"template_engine": "jinja2"}
        site.dev_mode = False
        return site

    def test_jinja_has_no_special_capabilities(self, mock_site, monkeypatch):
        """Jinja engine should have no special capabilities."""
        # Mock the environment creation
        from unittest.mock import MagicMock

        monkeypatch.setattr(
            "bengal.rendering.engines.jinja.create_jinja_environment",
            lambda site, engine, profile: (MagicMock(), []),
        )

        from bengal.rendering.engines.jinja import JinjaTemplateEngine

        engine = JinjaTemplateEngine(mock_site)

        # Should have no capabilities
        assert engine.capabilities == EngineCapability.NONE
        assert not engine.has_capability(EngineCapability.BLOCK_CACHING)
        assert not engine.has_capability(EngineCapability.INTROSPECTION)
        assert not engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION)
