"""
Tests for protocol signature stability.

Guards against accidental changes to protocol method signatures that would
break implementations. These tests act as a contract specification.

Note:
    These tests are intentionally conservative. If a test fails because you're
    adding a new required method to a protocol, you should:
    1. Update the test to include the new method
    2. Update all implementations of the protocol
    3. Consider if this is a breaking change for external users
"""

from __future__ import annotations

import inspect
from typing import get_type_hints

from bengal.protocols import (
    Cacheable,
    DirectiveHandler,
    HighlightService,
    OutputCollector,
    OutputTarget,
    PageLike,
    ProgressReporter,
    RoleHandler,
    SectionLike,
    SiteLike,
    TemplateEngine,
    TemplateIntrospector,
    TemplateRenderer,
    TemplateValidator,
)


class TestProgressReporterStability:
    """Guard against breaking changes to ProgressReporter."""

    REQUIRED_METHODS = {"add_phase", "start_phase", "update_phase", "complete_phase", "log"}

    def test_has_required_methods(self) -> None:
        """ProgressReporter must have these exact methods."""
        actual = {m for m in dir(ProgressReporter) if not m.startswith("_")}
        missing = self.REQUIRED_METHODS - actual
        assert not missing, f"ProgressReporter missing methods: {missing}"

    def test_add_phase_signature(self) -> None:
        """add_phase(phase_id, label, total=None) signature."""
        sig = inspect.signature(ProgressReporter.add_phase)
        params = list(sig.parameters.keys())

        assert "self" in params or len(params) >= 2
        assert "phase_id" in params
        assert "label" in params
        assert "total" in params

    def test_update_phase_signature(self) -> None:
        """update_phase(phase_id, current=None, current_item=None) signature."""
        sig = inspect.signature(ProgressReporter.update_phase)
        params = list(sig.parameters.keys())

        assert "phase_id" in params
        assert "current" in params
        assert "current_item" in params


class TestCacheableStability:
    """Guard against breaking changes to Cacheable."""

    def test_has_to_cache_dict(self) -> None:
        """Cacheable must have to_cache_dict method."""
        assert hasattr(Cacheable, "to_cache_dict")
        assert callable(getattr(Cacheable, "to_cache_dict", None))

    def test_has_from_cache_dict(self) -> None:
        """Cacheable must have from_cache_dict classmethod."""
        assert hasattr(Cacheable, "from_cache_dict")
        # from_cache_dict should be a classmethod
        method = Cacheable.from_cache_dict
        assert callable(method)

    def test_to_cache_dict_returns_dict(self) -> None:
        """to_cache_dict should return dict[str, Any]."""
        # We can check the annotation exists
        hints = get_type_hints(Cacheable.to_cache_dict)
        assert "return" in hints


class TestOutputCollectorStability:
    """Guard against breaking changes to OutputCollector."""

    REQUIRED_METHODS = {"record", "get_outputs", "css_only", "clear"}

    def test_has_required_methods(self) -> None:
        """OutputCollector must have these methods."""
        actual = {m for m in dir(OutputCollector) if not m.startswith("_")}
        missing = self.REQUIRED_METHODS - actual
        assert not missing, f"OutputCollector missing methods: {missing}"

    def test_record_signature(self) -> None:
        """record(path, output_type=None, phase='render') signature."""
        sig = inspect.signature(OutputCollector.record)
        params = list(sig.parameters.keys())

        assert "path" in params
        assert "output_type" in params
        assert "phase" in params


class TestHighlightServiceStability:
    """Guard against breaking changes to HighlightService."""

    def test_has_name_property(self) -> None:
        """HighlightService must have name property."""
        assert hasattr(HighlightService, "name")

    def test_has_highlight_method(self) -> None:
        """HighlightService must have highlight method."""
        assert hasattr(HighlightService, "highlight")
        assert callable(getattr(HighlightService, "highlight", None))

    def test_has_supports_language_method(self) -> None:
        """HighlightService must have supports_language method."""
        assert hasattr(HighlightService, "supports_language")
        assert callable(getattr(HighlightService, "supports_language", None))

    def test_highlight_signature(self) -> None:
        """highlight(code, language, *, hl_lines=None, show_linenos=False) signature."""
        sig = inspect.signature(HighlightService.highlight)
        params = list(sig.parameters.keys())

        assert "code" in params
        assert "language" in params


class TestPageLikeStability:
    """Guard against breaking changes to PageLike."""

    REQUIRED_PROPERTIES = {
        "title",
        "href",
        "content",
        "frontmatter",
        "date",
        "draft",
        "weight",
        "source_path",
    }

    def test_has_required_properties(self) -> None:
        """PageLike must have these properties."""
        for prop in self.REQUIRED_PROPERTIES:
            assert hasattr(PageLike, prop), f"PageLike missing property: {prop}"


class TestSectionLikeStability:
    """Guard against breaking changes to SectionLike."""

    REQUIRED_PROPERTIES = {
        "name",
        "title",
        "path",
        "href",
        "pages",
        "subsections",
        "parent",
        "index_page",
    }

    def test_has_required_properties(self) -> None:
        """SectionLike must have these properties."""
        for prop in self.REQUIRED_PROPERTIES:
            assert hasattr(SectionLike, prop), f"SectionLike missing property: {prop}"


class TestSiteLikeStability:
    """Guard against breaking changes to SiteLike."""

    REQUIRED_PROPERTIES = {
        "title",
        "baseurl",
        "config",
        "pages",
        "sections",
        "root_section",
        "root_path",
    }

    def test_has_required_properties(self) -> None:
        """SiteLike must have these properties."""
        for prop in self.REQUIRED_PROPERTIES:
            assert hasattr(SiteLike, prop), f"SiteLike missing property: {prop}"


class TestTemplateProtocolsStability:
    """Guard against breaking changes to template protocols."""

    def test_renderer_has_required_methods(self) -> None:
        """TemplateRenderer must have render methods."""
        assert hasattr(TemplateRenderer, "render_template")
        assert hasattr(TemplateRenderer, "render_string")

        # site and template_dirs are class-level attributes defined in the protocol
        # They appear in __annotations__ rather than as regular attributes
        annotations = getattr(TemplateRenderer, "__annotations__", {})
        assert "site" in annotations, "TemplateRenderer missing 'site' annotation"
        assert "template_dirs" in annotations, "TemplateRenderer missing 'template_dirs' annotation"

    def test_introspector_has_required_methods(self) -> None:
        """TemplateIntrospector must have introspection methods."""
        assert hasattr(TemplateIntrospector, "template_exists")
        assert hasattr(TemplateIntrospector, "get_template_path")
        assert hasattr(TemplateIntrospector, "list_templates")

    def test_validator_has_validate_method(self) -> None:
        """TemplateValidator must have validate method."""
        assert hasattr(TemplateValidator, "validate")

    def test_engine_has_all_capabilities(self) -> None:
        """TemplateEngine must have capabilities from all sub-protocols."""
        # From TemplateRenderer
        assert hasattr(TemplateEngine, "render_template")
        assert hasattr(TemplateEngine, "render_string")

        # From TemplateIntrospector
        assert hasattr(TemplateEngine, "template_exists")
        assert hasattr(TemplateEngine, "list_templates")

        # From TemplateValidator
        assert hasattr(TemplateEngine, "validate")

        # Engine-specific
        assert hasattr(TemplateEngine, "capabilities")
        assert hasattr(TemplateEngine, "has_capability")


class TestOutputTargetStability:
    """Guard against breaking changes to OutputTarget."""

    REQUIRED_METHODS = {"name", "write", "write_bytes", "copy", "mkdir", "exists"}

    def test_has_required_methods(self) -> None:
        """OutputTarget must have these methods."""
        for method in self.REQUIRED_METHODS:
            assert hasattr(OutputTarget, method), f"OutputTarget missing: {method}"


class TestRoleAndDirectiveStability:
    """Guard against breaking changes to role/directive protocols."""

    def test_role_handler_has_required_members(self) -> None:
        """RoleHandler must have name and render."""
        assert hasattr(RoleHandler, "name")
        assert hasattr(RoleHandler, "render")

    def test_directive_handler_has_required_members(self) -> None:
        """DirectiveHandler must have name, has_content, and render."""
        assert hasattr(DirectiveHandler, "name")
        assert hasattr(DirectiveHandler, "has_content")
        assert hasattr(DirectiveHandler, "render")
