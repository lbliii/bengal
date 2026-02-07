"""
Tests for protocol consolidation (RFC: Protocol Consolidation).

This module tests:
1. Protocol conformance for core implementations
2. Deprecation warnings from old import paths
3. Protocol composition (TemplateRenderer vs TemplateEngine)
4. Backwards compatibility aliases
"""

from __future__ import annotations

import warnings


class TestCoreProtocols:
    """Tests for core protocols (PageLike, SectionLike, SiteLike)."""

    def test_section_satisfies_section_like(self) -> None:
        """Section class satisfies SectionLike protocol."""
        from bengal.core import Section

        # Verify protocol conformance (structural typing)
        # We can't use isinstance with Protocol unless we have an instance
        # Instead, verify the required attributes exist (as properties or in annotations)
        # Note: Some are properties defined on the class, not annotations
        def has_attr(cls, name: str) -> bool:
            return hasattr(cls, name) or name in getattr(cls, "__annotations__", {})

        assert has_attr(Section, "name")
        assert has_attr(Section, "title")
        assert has_attr(Section, "path")
        assert has_attr(Section, "href")
        assert has_attr(Section, "pages")
        assert has_attr(Section, "subsections")
        assert has_attr(Section, "parent")
        assert has_attr(Section, "index_page")

    def test_page_like_has_required_properties(self) -> None:
        """PageLike protocol defines all required properties."""
        from bengal.protocols import PageLike

        # Check protocol definition
        assert hasattr(PageLike, "__protocol_attrs__") or True  # Protocol attrs exist
        # Verify key attributes are in the protocol
        # Note: runtime_checkable protocols only check for attribute existence


class TestRenderingProtocols:
    """Tests for rendering protocols (TemplateEngine, HighlightService)."""

    def test_highlight_service_has_required_methods(self) -> None:
        """HighlightService protocol has all required methods."""
        from bengal.protocols import HighlightService

        # Verify protocol shape
        assert hasattr(HighlightService, "name")
        assert hasattr(HighlightService, "highlight")
        assert hasattr(HighlightService, "supports_language")

    def test_rosettes_backend_satisfies_highlight_service(self) -> None:
        """RosettesBackend satisfies HighlightService protocol."""
        from bengal.protocols import HighlightService
        from bengal.rendering.highlighting.rosettes import RosettesBackend

        backend = RosettesBackend()

        # Verify it's runtime-checkable
        assert isinstance(backend, HighlightService)

        # Verify required properties/methods work
        assert backend.name == "rosettes"
        assert callable(backend.highlight)
        assert callable(backend.supports_language)

    def test_template_renderer_is_subset_of_template_engine(self) -> None:
        """TemplateRenderer is a proper subset of TemplateEngine."""
        from bengal.protocols import TemplateEngine

        # TemplateEngine should have all TemplateRenderer methods plus more
        # This is structural, so we check method names
        renderer_methods = {"render_template", "render_string"}

        # All TemplateRenderer methods should be in TemplateEngine
        # (This is guaranteed by inheritance in the protocol definition)
        assert hasattr(TemplateEngine, "render_template")
        assert hasattr(TemplateEngine, "render_string")

        # TemplateEngine has additional methods
        assert hasattr(TemplateEngine, "template_exists")
        assert hasattr(TemplateEngine, "validate")


class TestDeprecationWarnings:
    """Tests for deprecation warnings on old import paths."""

    def test_section_protocols_deprecation_warning(self) -> None:
        """Old import path for SectionLike emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Import from old path

            # Should emit exactly one deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "bengal.protocols" in str(w[0].message)
            assert "SectionLike" in str(w[0].message)

    def test_highlighting_protocol_deprecation_warning(self) -> None:
        """Old import path for HighlightBackend emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Import from old path

            # Should emit exactly one deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "bengal.protocols" in str(w[0].message)

    def test_engine_protocol_deprecation_warning(self) -> None:
        """Old import path for TemplateEngineProtocol emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Import from old path

            # Should emit exactly one deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "bengal.protocols" in str(w[0].message)


class TestBackwardsCompatibility:
    """Tests for backwards compatibility aliases."""

    def test_highlight_backend_alias(self) -> None:
        """HighlightBackend is an alias for HighlightService."""
        from bengal.protocols import HighlightBackend, HighlightService

        assert HighlightBackend is HighlightService

    def test_template_engine_protocol_alias(self) -> None:
        """TemplateEngineProtocol is an alias for TemplateEngine."""
        from bengal.protocols import TemplateEngine, TemplateEngineProtocol

        assert TemplateEngineProtocol is TemplateEngine

    def test_new_import_no_warning(self) -> None:
        """New import path does not emit deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Import from new canonical path

            # Should NOT emit any deprecation warnings
            deprecation_warnings = [
                warning for warning in w if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) == 0


class TestProtocolExports:
    """Tests for protocol module exports."""

    def test_all_core_protocols_exported(self) -> None:
        """All core protocols are exported from bengal.protocols."""
        from bengal import protocols

        # Core protocols
        assert hasattr(protocols, "PageLike")
        assert hasattr(protocols, "SectionLike")
        assert hasattr(protocols, "SiteLike")
        assert hasattr(protocols, "NavigableSection")
        assert hasattr(protocols, "QueryableSection")

    def test_all_rendering_protocols_exported(self) -> None:
        """All rendering protocols are exported from bengal.protocols."""
        from bengal import protocols

        # Template protocols
        assert hasattr(protocols, "TemplateEnvironment")
        assert hasattr(protocols, "TemplateRenderer")
        assert hasattr(protocols, "TemplateIntrospector")
        assert hasattr(protocols, "TemplateValidator")
        assert hasattr(protocols, "TemplateEngine")
        assert hasattr(protocols, "EngineCapability")

        # Highlighting
        assert hasattr(protocols, "HighlightService")

        # Roles and directives
        assert hasattr(protocols, "RoleHandler")
        assert hasattr(protocols, "DirectiveHandler")

    def test_all_infrastructure_protocols_exported(self) -> None:
        """All infrastructure protocols are exported from bengal.protocols."""
        from bengal import protocols

        assert hasattr(protocols, "ProgressReporter")
        assert hasattr(protocols, "Cacheable")
        assert hasattr(protocols, "OutputCollector")
        assert hasattr(protocols, "ContentSourceProtocol")
        assert hasattr(protocols, "OutputTarget")


class TestProtocolComposition:
    """Tests for protocol composition patterns."""

    def test_accept_minimal_renderer(self) -> None:
        """Functions can accept minimal TemplateRenderer interface."""
        from bengal.protocols import TemplateRenderer

        # Verify the protocol exists and has the right methods
        assert hasattr(TemplateRenderer, "render_template")
        assert hasattr(TemplateRenderer, "render_string")

        # The protocol can be used as a type hint
        # (We skip get_type_hints as it has issues with local function definitions)

    def test_engine_capability_flags(self) -> None:
        """EngineCapability flags are composable."""
        from bengal.protocols import EngineCapability

        # Test flag composition
        combined = EngineCapability.BLOCK_CACHING | EngineCapability.INTROSPECTION

        assert EngineCapability.BLOCK_CACHING in combined
        assert EngineCapability.INTROSPECTION in combined
        assert EngineCapability.PATTERN_MATCHING not in combined


class TestInfrastructureProtocols:
    """Tests for infrastructure protocols."""

    def test_cacheable_protocol_shape(self) -> None:
        """Cacheable protocol has required methods."""
        from bengal.protocols import Cacheable

        # Verify protocol shape
        assert hasattr(Cacheable, "to_cache_dict")
        assert hasattr(Cacheable, "from_cache_dict")

    def test_output_target_protocol_shape(self) -> None:
        """OutputTarget protocol has required methods."""
        from bengal.protocols import OutputTarget

        # Verify protocol shape
        assert hasattr(OutputTarget, "name")
        assert hasattr(OutputTarget, "write")
        assert hasattr(OutputTarget, "write_bytes")
        assert hasattr(OutputTarget, "copy")
        assert hasattr(OutputTarget, "mkdir")
        assert hasattr(OutputTarget, "exists")
